"""
Celery tasks for document processing
"""

import os
import logging
from datetime import datetime, timedelta
from typing import List
import uuid

from celery import Task
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .celery_app import celery_app
from src.db.base import DATABASE_URL
from src.models.document import Document, DocumentEmbedding
from src.document_parser.parser import OhadaDocumentParser

logger = logging.getLogger(__name__)


class DatabaseTask(Task):
    """Base task with database session"""
    _db_session = None

    @property
    def db_session(self):
        if self._db_session is None:
            engine = create_engine(DATABASE_URL)
            SessionLocal = sessionmaker(bind=engine)
            self._db_session = SessionLocal()
        return self._db_session

    def after_return(self, *args, **kwargs):
        if self._db_session is not None:
            self._db_session.close()


@celery_app.task(bind=True, base=DatabaseTask, name='src.tasks.document_tasks.process_document_task')
def process_document_task(self, file_path: str, user_id: str, publish: bool = False) -> dict:
    """
    Process a Word document: parse, validate, and store in database

    Args:
        file_path: Path to .docx file
        user_id: UUID of user creating document
        publish: Whether to publish immediately

    Returns:
        Dictionary with document_id and status
    """
    logger.info(f"Processing document: {file_path}")

    try:
        # Parse document
        parser = OhadaDocumentParser()
        doc_data = parser.parse_docx(file_path)

        # Validate
        warnings = parser.validate_document_data(doc_data)
        if warnings:
            logger.warning(f"Validation warnings: {warnings}")

        # Check for duplicates
        existing = self.db_session.query(Document).filter(
            Document.content_hash == doc_data['content_hash'],
            Document.is_latest == True
        ).first()

        if existing:
            logger.warning(f"Duplicate document found: {existing.id}")
            return {
                'status': 'duplicate',
                'document_id': str(existing.id),
                'message': f"Document already exists: {existing.title}"
            }

        # Create document
        new_doc = Document(
            id=uuid.uuid4(),
            title=doc_data['title'],
            document_type=doc_data['document_type'],
            content_text=doc_data['content_text'],
            content_hash=doc_data['content_hash'],
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
            created_by=uuid.UUID(user_id),
            updated_by=uuid.UUID(user_id),
            validated_by=uuid.UUID(user_id) if publish else None,
            validated_at=datetime.now() if publish else None
        )

        self.db_session.add(new_doc)
        self.db_session.commit()
        self.db_session.refresh(new_doc)

        logger.info(f"Document created: {new_doc.id}")

        # Trigger embedding generation
        generate_embeddings_task.delay(str(new_doc.id))

        return {
            'status': 'success',
            'document_id': str(new_doc.id),
            'title': new_doc.title,
            'warnings': warnings
        }

    except Exception as e:
        logger.error(f"Failed to process document: {e}", exc_info=True)
        self.db_session.rollback()
        return {
            'status': 'error',
            'message': str(e)
        }


@celery_app.task(bind=True, base=DatabaseTask, name='src.tasks.document_tasks.generate_embeddings_task')
def generate_embeddings_task(self, document_id: str) -> dict:
    """
    Generate embeddings for a document and store in ChromaDB

    Args:
        document_id: UUID of document

    Returns:
        Dictionary with status and embedding count
    """
    logger.info(f"Generating embeddings for document: {document_id}")

    try:
        # Get document
        doc = self.db_session.query(Document).filter(
            Document.id == uuid.UUID(document_id)
        ).first()

        if not doc:
            raise ValueError(f"Document not found: {document_id}")

        # Import here to avoid circular dependency
        from src.vector_db.ohada_vector_db_structure import OhadaEmbedder
        from src.config.ohada_config import get_config

        config = get_config()

        # Initialize embedder
        embedder = OhadaEmbedder(
            embedding_model=config.embedding_model_name,
            persist_directory=config.chroma_persist_directory
        )

        # Chunk document (simple chunking by paragraphs for now)
        chunks = self._chunk_document(doc.content_text, chunk_size=500, overlap=50)

        logger.info(f"Created {len(chunks)} chunks for document {document_id}")

        # Generate embeddings and store in ChromaDB
        collection_name = f"ohada_{doc.document_type}"

        embedding_count = 0
        for idx, chunk in enumerate(chunks):
            # Create metadata for chunk
            metadata = {
                'document_id': str(doc.id),
                'title': doc.title,
                'document_type': doc.document_type,
                'chunk_index': idx,
                'partie': doc.partie,
                'chapitre': doc.chapitre,
                'section': doc.section,
                'article': doc.article,
                'acte_uniforme': doc.acte_uniforme
            }

            # Generate embedding
            chromadb_id = f"{document_id}_chunk_{idx}"

            # Add to ChromaDB
            embedder.collection.add(
                documents=[chunk],
                metadatas=[metadata],
                ids=[chromadb_id]
            )

            # Track in PostgreSQL
            doc_embedding = DocumentEmbedding(
                id=uuid.uuid4(),
                document_id=doc.id,
                chunk_index=idx,
                chunk_text=chunk,
                chunk_title=doc.title,
                embedding_model=config.embedding_model_name,
                chromadb_id=chromadb_id,
                chromadb_collection=collection_name
            )

            self.db_session.add(doc_embedding)
            embedding_count += 1

        self.db_session.commit()

        logger.info(f"Generated {embedding_count} embeddings for document {document_id}")

        return {
            'status': 'success',
            'document_id': document_id,
            'embedding_count': embedding_count
        }

    except Exception as e:
        logger.error(f"Failed to generate embeddings: {e}", exc_info=True)
        self.db_session.rollback()
        return {
            'status': 'error',
            'message': str(e)
        }

    @staticmethod
    def _chunk_document(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """
        Chunk document text into overlapping chunks

        Args:
            text: Full document text
            chunk_size: Target size for each chunk (in words)
            overlap: Number of overlapping words between chunks

        Returns:
            List of text chunks
        """
        words = text.split()
        chunks = []

        for i in range(0, len(words), chunk_size - overlap):
            chunk_words = words[i:i + chunk_size]
            chunk = ' '.join(chunk_words)
            chunks.append(chunk)

            # Stop if we've processed all words
            if i + chunk_size >= len(words):
                break

        return chunks


@celery_app.task(bind=True, base=DatabaseTask, name='src.tasks.document_tasks.reindex_document_task')
def reindex_document_task(self, document_id: str) -> dict:
    """
    Re-index a document (regenerate embeddings)

    Args:
        document_id: UUID of document

    Returns:
        Dictionary with status
    """
    logger.info(f"Re-indexing document: {document_id}")

    try:
        # Delete existing embeddings
        self.db_session.query(DocumentEmbedding).filter(
            DocumentEmbedding.document_id == uuid.UUID(document_id)
        ).delete()

        self.db_session.commit()

        # Trigger new embedding generation
        result = generate_embeddings_task.delay(document_id)

        return {
            'status': 'success',
            'document_id': document_id,
            'task_id': result.id
        }

    except Exception as e:
        logger.error(f"Failed to re-index document: {e}", exc_info=True)
        self.db_session.rollback()
        return {
            'status': 'error',
            'message': str(e)
        }


@celery_app.task(bind=True, base=DatabaseTask, name='src.tasks.document_tasks.cleanup_old_versions_task')
def cleanup_old_versions_task(self, retention_days: int = 30) -> dict:
    """
    Clean up old document versions (keep only recent ones)

    Args:
        retention_days: Number of days to retain versions

    Returns:
        Dictionary with cleanup statistics
    """
    logger.info(f"Cleaning up document versions older than {retention_days} days")

    try:
        from src.models.document import DocumentVersion

        cutoff_date = datetime.now() - timedelta(days=retention_days)

        # Delete old versions
        deleted = self.db_session.query(DocumentVersion).filter(
            DocumentVersion.changed_at < cutoff_date
        ).delete()

        self.db_session.commit()

        logger.info(f"Deleted {deleted} old document versions")

        return {
            'status': 'success',
            'deleted_count': deleted,
            'cutoff_date': cutoff_date.isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to cleanup versions: {e}", exc_info=True)
        self.db_session.rollback()
        return {
            'status': 'error',
            'message': str(e)
        }


@celery_app.task(bind=True, base=DatabaseTask, name='src.tasks.document_tasks.reindex_all_documents_task')
def reindex_all_documents_task(self) -> dict:
    """
    Re-index all published documents

    Returns:
        Dictionary with status and count
    """
    logger.info("Re-indexing all published documents")

    try:
        # Get all published documents
        documents = self.db_session.query(Document).filter(
            Document.status == 'published',
            Document.is_latest == True
        ).all()

        logger.info(f"Found {len(documents)} documents to re-index")

        # Queue re-indexing tasks
        task_ids = []
        for doc in documents:
            result = reindex_document_task.delay(str(doc.id))
            task_ids.append(result.id)

        return {
            'status': 'success',
            'document_count': len(documents),
            'task_ids': task_ids
        }

    except Exception as e:
        logger.error(f"Failed to queue re-indexing: {e}", exc_info=True)
        return {
            'status': 'error',
            'message': str(e)
        }
