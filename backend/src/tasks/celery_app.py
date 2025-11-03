"""
Celery application configuration
"""

import os
from celery import Celery
from celery.schedules import crontab

# Get Redis URL from environment
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Create Celery app
celery_app = Celery(
    'ohada',
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        'src.tasks.document_tasks'
    ]
)

# Configuration
celery_app.conf.update(
    # Task routing
    task_routes={
        'src.tasks.document_tasks.process_document_task': {'queue': 'documents'},
        'src.tasks.document_tasks.generate_embeddings_task': {'queue': 'embeddings'},
        'src.tasks.document_tasks.reindex_document_task': {'queue': 'embeddings'},
        'src.tasks.document_tasks.cleanup_old_versions_task': {'queue': 'maintenance'},
    },

    # Task time limits
    task_soft_time_limit=300,  # 5 minutes soft limit
    task_time_limit=600,  # 10 minutes hard limit

    # Task result settings
    result_expires=3600,  # Results expire after 1 hour
    result_persistent=True,

    # Task execution settings
    task_acks_late=True,  # Acknowledge task after completion
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,  # Process one task at a time

    # Serialization
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],

    # Timezone
    timezone='UTC',
    enable_utc=True,

    # Logging
    worker_log_format='[%(asctime)s: %(levelname)s/%(processName)s] %(message)s',
    worker_task_log_format='[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s',
)

# Periodic tasks (Celery Beat)
celery_app.conf.beat_schedule = {
    # Cleanup old document versions every day at 2 AM
    'cleanup-old-versions': {
        'task': 'src.tasks.document_tasks.cleanup_old_versions_task',
        'schedule': crontab(hour=2, minute=0),
        'args': (30,)  # Keep versions for 30 days
    },

    # Re-index all documents weekly (Sunday at 3 AM)
    'weekly-reindex': {
        'task': 'src.tasks.document_tasks.reindex_all_documents_task',
        'schedule': crontab(day_of_week=0, hour=3, minute=0),
    },
}

if __name__ == '__main__':
    celery_app.start()
