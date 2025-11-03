"""
Celery tasks for async processing
"""

from .celery_app import celery_app
from .document_tasks import (
    process_document_task,
    generate_embeddings_task,
    reindex_document_task,
    cleanup_old_versions_task
)

__all__ = [
    "celery_app",
    "process_document_task",
    "generate_embeddings_task",
    "reindex_document_task",
    "cleanup_old_versions_task"
]
