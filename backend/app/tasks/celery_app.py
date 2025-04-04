"""
Celery application configuration for background tasks.

This module configures the Celery application for running background
tasks such as data processing, scheduled scraping, and periodic updates.
"""
import os
from celery import Celery
from celery.schedules import crontab

from ..utils.config import settings
from ..utils.logger import get_logger

logger = get_logger("celery")

# Configure Celery application
celery_app = Celery(
    "duke_vc_insight_engine",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["backend.app.tasks.tasks"]
)

# Optional configuration for Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour task timeout
    worker_prefetch_multiplier=1,  # Fetch one task at a time
    task_acks_late=True,  # Acknowledge task after it's completed
)

# Allow overriding configuration from environment variables
celery_app.conf.update(
    {k.lower(): v for k, v in os.environ.items() if k.startswith("CELERY_")}
)

# Configure scheduled tasks
celery_app.conf.beat_schedule = {
    # Daily data update at 2:00 AM UTC
    'update-data-daily': {
        'task': 'backend.app.tasks.tasks.periodic_data_update',
        'schedule': crontab(hour=2, minute=0),
        'options': {'expires': 3600}  # Task expires after 1 hour
    },
    
    # Weekly bulk data processing on Sunday at 4:00 AM UTC
    'process-new-startups-weekly': {
        'task': 'backend.app.tasks.tasks.discover_new_startups',
        'schedule': crontab(hour=4, minute=0, day_of_week=0),  # Sunday
        'options': {'expires': 14400}  # Task expires after 4 hours
    }
}

logger.info("Celery application configured successfully")