#!/usr/bin/env python3
"""
Script to import a single OHADA Word document into PostgreSQL

Usage:
    python scripts/import_document.py <path_to_docx> [--user-email admin@ohada.com] [--publish]

Examples:
    # Import as draft
    python scripts/import_document.py base_connaissances/chapitre_1.docx

    # Import and publish immediately
    python scripts/import_document.py base_connaissances/chapitre_1.docx --publish

    # Import with specific user
    python scripts/import_document.py base_connaissances/chapitre_1.docx --user-email user@example.com
"""

import sys
import os
import argparse
import logging
from pathlib import Path
from datetime import datetime

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


def get_user_id_by_email(db: Session, email: str):
    """Get user_id from email"""
    from src.models.user import User
    user = db.query(User).filter(User.email == email).first()
    if not user:
        logger.warning(f"User not found: {email}, using default admin")
        # Try to get admin user
        admin = db.query(User).filter(User.is_admin == True).first()
        if admin:
            return admin.user_id
        # If no admin, create a system user
        logger.error("No admin user found in database")
        return None
    return user.user_id


def import_document(
    file_path: str,
    user_email: str = "admin@ohada.com",
    publish: bool = False,
    db_url: str = None
) -> str:
    """
    Import a Word document into PostgreSQL

    Args:
        file_path: Path to .docx file
        user_email: Email of user creating the document
        publish: Whether to publish immediately (default: draft)
        db_url: Database URL (optional, uses DATABASE_URL env var if not provided)

    Returns:
        Document ID (UUID) as string

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file is invalid or duplicate
    """
    logger.info(f"Starting import of: {file_path}")

    # Parse document
    parser = OhadaDocumentParser()
    doc_data = parser.parse_docx(file_path)

    logger.info(f"Parsed document: {doc_data['title']}")
    logger.info(f"  Type: {doc_data['document_type']}")
    logger.info(f"  Hierarchy: Partie {doc_data.get('partie')}, "
               f"Chapitre {doc_data.get('chapitre')}, "
               f"Section {doc_data.get('section')}")

    # Validate
    warnings = parser.validate_document_data(doc_data)
    if warnings:
        logger.warning(f"Validation warnings: {', '.join(warnings)}")

    # Connect to database
    if db_url is None:
        db_url = DATABASE_URL

    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # Get user ID
        user_id = get_user_id_by_email(db, user_email)
        if user_id is None:
            raise ValueError(f"Could not find user: {user_email}")

        # Check for duplicates
        existing = db.query(Document).filter(
            Document.content_hash == doc_data['content_hash'],
            Document.is_latest == True
        ).first()

        if existing:
            logger.warning(f"Document with same content already exists: {existing.id}")
            logger.warning(f"Existing document: {existing.title}")

            response = input("Do you want to update the existing document? (y/n): ")
            if response.lower() != 'y':
                raise ValueError(f"Duplicate document: {existing.id}")

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

            db.commit()
            db.refresh(existing)

            logger.info(f"Updated existing document: {existing.id} (version {existing.version})")
            return str(existing.id)

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

        logger.info(f"✓ Created document: {new_doc.id}")
        logger.info(f"  Status: {new_doc.status}")
        logger.info(f"  Title: {new_doc.title}")

        return str(new_doc.id)

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to import document: {e}")
        raise

    finally:
        db.close()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Import OHADA Word document into PostgreSQL',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        'file_path',
        help='Path to .docx file to import'
    )

    parser.add_argument(
        '--user-email',
        default='admin@ohada.com',
        help='Email of user creating the document (default: admin@ohada.com)'
    )

    parser.add_argument(
        '--publish',
        action='store_true',
        help='Publish document immediately (default: create as draft)'
    )

    parser.add_argument(
        '--db-url',
        help='Database URL (default: from DATABASE_URL env var)'
    )

    args = parser.parse_args()

    try:
        doc_id = import_document(
            file_path=args.file_path,
            user_email=args.user_email,
            publish=args.publish,
            db_url=args.db_url
        )

        print(f"\n✓ Success! Document ID: {doc_id}")
        print(f"  Status: {'published' if args.publish else 'draft'}")

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        sys.exit(1)

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        sys.exit(2)

    except Exception as e:
        logger.error(f"Import failed: {e}", exc_info=True)
        sys.exit(3)


if __name__ == '__main__':
    main()
