#!/usr/bin/env python3
"""
Script to import all OHADA Word documents from base_connaissances/ into PostgreSQL and ChromaDB

Usage:
    python scripts/import_all_documents.py [--publish] [--skip-existing] [--verbose]

Examples:
    # Import all as draft
    python scripts/import_all_documents.py

    # Import and publish immediately
    python scripts/import_all_documents.py --publish

    # Skip documents that already exist
    python scripts/import_all_documents.py --skip-existing
"""

import sys
import os
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import uuid

from src.db.base import Base, get_db, DATABASE_URL
from src.models.document import Document
from src.document_parser.parser import OhadaDocumentParser

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def find_all_documents(base_path: str = "base_connaissances") -> List[Path]:
    """
    Find all .docx documents in base_connaissances/

    Returns:
        List of Path objects for all .docx files
    """
    base = Path(base_path)
    if not base.exists():
        raise FileNotFoundError(f"Directory not found: {base_path}")

    documents = sorted(base.glob("**/*.docx"))

    # Filter out temporary files (starting with ~$)
    documents = [doc for doc in documents if not doc.name.startswith("~$")]

    logger.info(f"Found {len(documents)} documents to import")

    # Group by collection for reporting
    collections = {}
    for doc in documents:
        parts = doc.parts
        if "base_connaissances" in parts:
            idx = parts.index("base_connaissances")
            if len(parts) > idx + 1:
                collection = parts[idx + 1]
                collections[collection] = collections.get(collection, 0) + 1

    logger.info("Documents by collection:")
    for collection, count in sorted(collections.items()):
        logger.info(f"  - {collection}: {count} documents")

    return documents


def get_user_id_by_email(db: Session, email: str):
    """Get user_id from email"""
    from src.models.user import User
    user = db.query(User).filter(User.email == email).first()
    if not user:
        logger.warning(f"User not found: {email}, creating system user")
        # Create system user if not exists
        system_user = User(
            user_id=uuid.uuid4(),
            email="system@ohada.com",
            password_hash="",  # No password for system user
            full_name="System",
            is_active=True,
            is_admin=True
        )
        db.add(system_user)
        db.commit()
        db.refresh(system_user)
        return system_user.user_id
    return user.user_id


def import_single_document(
    file_path: Path,
    db: Session,
    user_id: uuid.UUID,
    publish: bool = False,
    skip_existing: bool = False,
    parser: OhadaDocumentParser = None
) -> Dict[str, Any]:
    """
    Import a single document

    Returns:
        Dictionary with import results
    """
    if parser is None:
        parser = OhadaDocumentParser()

    try:
        # Parse document
        doc_data = parser.parse_docx(str(file_path))

        # Check for duplicates
        existing = db.query(Document).filter(
            Document.content_hash == doc_data['content_hash'],
            Document.is_latest == True
        ).first()

        if existing:
            if skip_existing:
                return {
                    'status': 'skipped',
                    'file': str(file_path),
                    'reason': 'already_exists',
                    'doc_id': str(existing.id)
                }
            else:
                # Update existing document
                existing.version += 1
                existing.content_text = doc_data['content_text']
                existing.updated_by = user_id
                existing.updated_at = datetime.now()

                if doc_data.get('title'):
                    existing.title = doc_data['title']
                if doc_data.get('tags'):
                    existing.tags = doc_data['tags']
                if doc_data.get('metadata'):
                    existing.doc_metadata = doc_data['metadata']
                if doc_data.get('collection'):
                    existing.collection = doc_data['collection']
                if doc_data.get('sub_collection'):
                    existing.sub_collection = doc_data['sub_collection']

                db.commit()
                db.refresh(existing)

                return {
                    'status': 'updated',
                    'file': str(file_path),
                    'doc_id': str(existing.id),
                    'version': existing.version,
                    'title': existing.title
                }

        # Create new document
        new_doc = Document(
            id=uuid.uuid4(),
            title=doc_data['title'],
            document_type=doc_data['document_type'],
            content_text=doc_data['content_text'],
            content_hash=doc_data['content_hash'],
            collection=doc_data.get('collection'),
            sub_collection=doc_data.get('sub_collection'),
            acte_uniforme=doc_data.get('acte_uniforme'),
            livre=doc_data.get('livre'),
            titre=doc_data.get('titre'),
            partie=doc_data.get('partie'),
            chapitre=doc_data.get('chapitre'),
            section=doc_data.get('section'),
            sous_section=doc_data.get('sous_section'),
            article=doc_data.get('article'),
            alinea=doc_data.get('alinea'),
            doc_metadata=doc_data.get('metadata', {}),
            tags=doc_data.get('tags', []),
            date_publication=datetime.fromisoformat(doc_data['date_publication']) if doc_data.get('date_publication') else None,
            version=1,
            is_latest=True,
            status='published' if publish else 'draft',
            created_by=user_id,
            updated_by=user_id,
            validated_by=user_id if publish else None,
            validated_at=datetime.now() if publish else None
        )

        db.add(new_doc)
        db.commit()
        db.refresh(new_doc)

        return {
            'status': 'created',
            'file': str(file_path),
            'doc_id': str(new_doc.id),
            'title': new_doc.title,
            'collection': new_doc.collection,
            'sub_collection': new_doc.sub_collection
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to import {file_path}: {e}")
        return {
            'status': 'failed',
            'file': str(file_path),
            'error': str(e)
        }


def import_all_documents(
    user_email: str = "admin@ohada.com",
    publish: bool = False,
    skip_existing: bool = False,
    db_url: str = None
) -> Dict[str, Any]:
    """
    Import all documents from base_connaissances/

    Returns:
        Summary statistics
    """
    # Find all documents
    documents = find_all_documents()

    if not documents:
        logger.warning("No documents found to import")
        return {
            'total': 0,
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'failed': 0,
            'results': []
        }

    # Connect to database
    if db_url is None:
        db_url = DATABASE_URL

    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    # Initialize parser once (reuse for all documents)
    parser = OhadaDocumentParser()

    try:
        # Get user ID
        user_id = get_user_id_by_email(db, user_email)

        # Import statistics
        stats = {
            'total': len(documents),
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'failed': 0,
            'results': []
        }

        # Import each document
        start_time = time.time()

        for i, doc_path in enumerate(documents, 1):
            logger.info(f"\n[{i}/{len(documents)}] Processing: {doc_path}")

            result = import_single_document(
                file_path=doc_path,
                db=db,
                user_id=user_id,
                publish=publish,
                skip_existing=skip_existing,
                parser=parser
            )

            stats['results'].append(result)
            stats[result['status']] += 1

            if result['status'] == 'created':
                logger.info(f"  [OK] Created: {result['title']}")
                logger.info(f"       ID: {result['doc_id']}")
                logger.info(f"       Collection: {result.get('collection')} > {result.get('sub_collection')}")
            elif result['status'] == 'updated':
                logger.info(f"  [OK] Updated: {result['title']} (v{result['version']})")
            elif result['status'] == 'skipped':
                logger.info(f"  [SKIP] Already exists")
            else:
                logger.error(f"  [ERROR] {result.get('error')}")

            # Progress update every 10 documents
            if i % 10 == 0:
                elapsed = time.time() - start_time
                avg_time = elapsed / i
                remaining = (len(documents) - i) * avg_time
                logger.info(f"\nProgress: {i}/{len(documents)} ({i/len(documents)*100:.1f}%)")
                logger.info(f"  Created: {stats['created']}, Updated: {stats['updated']}, "
                          f"Skipped: {stats['skipped']}, Failed: {stats['failed']}")
                logger.info(f"  Estimated time remaining: {remaining/60:.1f} minutes")

        # Final statistics
        elapsed_time = time.time() - start_time
        logger.info("\n" + "="*60)
        logger.info("IMPORT COMPLETE!")
        logger.info("="*60)
        logger.info(f"Total documents: {stats['total']}")
        logger.info(f"  Created: {stats['created']}")
        logger.info(f"  Updated: {stats['updated']}")
        logger.info(f"  Skipped: {stats['skipped']}")
        logger.info(f"  Failed: {stats['failed']}")
        logger.info(f"Time elapsed: {elapsed_time/60:.1f} minutes")
        logger.info(f"Average time per document: {elapsed_time/len(documents):.2f} seconds")

        return stats

    finally:
        db.close()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Import all OHADA Word documents into PostgreSQL',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--user-email',
        default='admin@ohada.com',
        help='Email of user creating the documents (default: admin@ohada.com)'
    )

    parser.add_argument(
        '--publish',
        action='store_true',
        help='Publish documents immediately (default: create as draft)'
    )

    parser.add_argument(
        '--skip-existing',
        action='store_true',
        help='Skip documents that already exist (default: update existing)'
    )

    parser.add_argument(
        '--db-url',
        help='Database URL (default: from DATABASE_URL env var)'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        stats = import_all_documents(
            user_email=args.user_email,
            publish=args.publish,
            skip_existing=args.skip_existing,
            db_url=args.db_url
        )

        if stats['failed'] > 0:
            logger.warning(f"\n{stats['failed']} documents failed to import")
            sys.exit(1)

        logger.info("\n[OK] All documents imported successfully!")

    except Exception as e:
        logger.error(f"Import failed: {e}", exc_info=True)
        sys.exit(2)


if __name__ == '__main__':
    main()
