#!/usr/bin/env python3
"""
Bulk migration script to import all OHADA Word documents from base_connaissances/

Usage:
    python scripts/migrate_all_documents.py [options]

Examples:
    # Dry run (preview only)
    python scripts/migrate_all_documents.py --dry-run

    # Import all documents as drafts
    python scripts/migrate_all_documents.py --source-dir base_connaissances

    # Import and publish all documents
    python scripts/migrate_all_documents.py --source-dir base_connaissances --publish

    # Import with progress bar
    python scripts/migrate_all_documents.py --source-dir base_connaissances --progress
"""

import sys
import os
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict
import json

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


class MigrationStats:
    """Track migration statistics"""

    def __init__(self):
        self.total_files = 0
        self.successful = 0
        self.failed = 0
        self.duplicates = 0
        self.skipped = 0
        self.errors = []
        self.start_time = datetime.now()

    def add_success(self):
        self.successful += 1

    def add_failure(self, filename: str, error: str):
        self.failed += 1
        self.errors.append({'file': filename, 'error': error})

    def add_duplicate(self):
        self.duplicates += 1

    def add_skip(self):
        self.skipped += 1

    def summary(self) -> Dict:
        duration = (datetime.now() - self.start_time).total_seconds()
        return {
            'total_files': self.total_files,
            'successful': self.successful,
            'failed': self.failed,
            'duplicates': self.duplicates,
            'skipped': self.skipped,
            'duration_seconds': duration,
            'errors': self.errors
        }

    def print_summary(self):
        summary = self.summary()
        print("\n" + "=" * 60)
        print("MIGRATION SUMMARY")
        print("=" * 60)
        print(f"Total files found:    {summary['total_files']}")
        print(f"Successfully imported: {summary['successful']}")
        print(f"Duplicates skipped:   {summary['duplicates']}")
        print(f"Failed:               {summary['failed']}")
        print(f"Skipped:              {summary['skipped']}")
        print(f"Duration:             {summary['duration_seconds']:.2f} seconds")

        if summary['errors']:
            print(f"\nErrors ({len(summary['errors'])}):")
            for error in summary['errors'][:10]:  # Show first 10
                print(f"  - {error['file']}: {error['error']}")
            if len(summary['errors']) > 10:
                print(f"  ... and {len(summary['errors']) - 10} more errors")

        print("=" * 60)


def get_user_id_by_email(db: Session, email: str):
    """Get user_id from email"""
    from src.models.user import User
    user = db.query(User).filter(User.email == email).first()
    if not user:
        # Try to get admin user
        admin = db.query(User).filter(User.is_admin == True).first()
        if admin:
            logger.warning(f"User {email} not found, using admin: {admin.email}")
            return admin.user_id
        logger.error("No admin user found in database")
        return None
    return user.user_id


def migrate_directory(
    source_dir: str,
    user_email: str = "admin@ohada.com",
    publish: bool = False,
    skip_duplicates: bool = True,
    dry_run: bool = False,
    db_url: str = None,
    show_progress: bool = False
) -> MigrationStats:
    """
    Migrate all .docx files from a directory to PostgreSQL

    Args:
        source_dir: Directory containing .docx files
        user_email: Email of user creating documents
        publish: Whether to publish documents immediately
        skip_duplicates: Skip duplicate documents instead of failing
        dry_run: Preview only, don't actually import
        db_url: Database URL (optional)
        show_progress: Show progress bar (requires tqdm)

    Returns:
        MigrationStats object with results
    """
    stats = MigrationStats()

    source_path = Path(source_dir)
    if not source_path.exists():
        raise FileNotFoundError(f"Source directory not found: {source_dir}")

    # Find all .docx files
    docx_files = list(source_path.rglob("*.docx"))
    # Filter out temporary files
    docx_files = [f for f in docx_files if not f.name.startswith('~$')]

    stats.total_files = len(docx_files)

    logger.info(f"Found {stats.total_files} .docx files in {source_dir}")

    if dry_run:
        logger.info("DRY RUN MODE - No changes will be made")

    # Initialize parser
    parser = OhadaDocumentParser()

    # Initialize database connection
    if not dry_run:
        if db_url is None:
            db_url = DATABASE_URL

        engine = create_engine(db_url)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()

        try:
            user_id = get_user_id_by_email(db, user_email)
            if user_id is None:
                raise ValueError(f"Could not find user: {user_email}")
        except Exception as e:
            db.close()
            raise

    # Optional progress bar
    iterator = docx_files
    if show_progress:
        try:
            from tqdm import tqdm
            iterator = tqdm(docx_files, desc="Migrating documents")
        except ImportError:
            logger.warning("tqdm not installed, progress bar disabled")

    # Process each file
    for file_path in iterator:
        try:
            # Parse document
            doc_data = parser.parse_docx(str(file_path))

            # Validate
            warnings = parser.validate_document_data(doc_data)
            if warnings:
                logger.warning(f"{file_path.name}: {', '.join(warnings)}")

            if dry_run:
                logger.info(f"Would import: {doc_data['title']} "
                           f"(Type: {doc_data['document_type']}, "
                           f"Partie {doc_data.get('partie')}, "
                           f"Chapitre {doc_data.get('chapitre')})")
                stats.add_success()
                continue

            # Check for duplicates
            existing = db.query(Document).filter(
                Document.content_hash == doc_data['content_hash'],
                Document.is_latest == True
            ).first()

            if existing:
                logger.info(f"Duplicate found: {file_path.name} (existing: {existing.id})")
                if skip_duplicates:
                    stats.add_duplicate()
                    continue
                else:
                    raise ValueError(f"Duplicate document: {existing.id}")

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

            logger.info(f"✓ Imported: {new_doc.title} ({new_doc.id})")
            stats.add_success()

        except Exception as e:
            logger.error(f"Failed to import {file_path.name}: {e}")
            stats.add_failure(file_path.name, str(e))
            if not dry_run:
                db.rollback()
            continue

    if not dry_run:
        db.close()

    return stats


def export_migration_report(stats: MigrationStats, output_file: str):
    """Export migration report to JSON file"""
    summary = stats.summary()

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    logger.info(f"Migration report exported to: {output_file}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Bulk migrate OHADA Word documents to PostgreSQL',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--source-dir',
        default='base_connaissances',
        help='Source directory containing .docx files (default: base_connaissances)'
    )

    parser.add_argument(
        '--user-email',
        default='admin@ohada.com',
        help='Email of user creating documents (default: admin@ohada.com)'
    )

    parser.add_argument(
        '--publish',
        action='store_true',
        help='Publish documents immediately (default: create as drafts)'
    )

    parser.add_argument(
        '--skip-duplicates',
        action='store_true',
        default=True,
        help='Skip duplicate documents instead of failing (default: True)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview migration without making changes'
    )

    parser.add_argument(
        '--db-url',
        help='Database URL (default: from DATABASE_URL env var)'
    )

    parser.add_argument(
        '--progress',
        action='store_true',
        help='Show progress bar (requires tqdm)'
    )

    parser.add_argument(
        '--report',
        help='Export migration report to JSON file'
    )

    args = parser.parse_args()

    try:
        stats = migrate_directory(
            source_dir=args.source_dir,
            user_email=args.user_email,
            publish=args.publish,
            skip_duplicates=args.skip_duplicates,
            dry_run=args.dry_run,
            db_url=args.db_url,
            show_progress=args.progress
        )

        stats.print_summary()

        if args.report:
            export_migration_report(stats, args.report)

        # Exit code based on results
        if stats.failed > 0:
            sys.exit(1)
        else:
            sys.exit(0)

    except FileNotFoundError as e:
        logger.error(f"Directory not found: {e}")
        sys.exit(1)

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(2)

    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        sys.exit(3)


if __name__ == '__main__':
    main()
