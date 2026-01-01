"""
Celery application configuration
"""
from celery import Celery
from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "pentest_brain_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.scan_worker"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per task
    task_soft_time_limit=3300,  # 55 minutes soft limit
    worker_prefetch_multiplier=1,  # One task at a time
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks
    task_acks_late=True,  # Acknowledge task after completion
    task_reject_on_worker_lost=True,  # Reject task if worker dies
    result_expires=86400,  # Results expire after 24 hours
)

# Task routes
celery_app.conf.task_routes = {
    "app.workers.scan_worker.process_scan": {"queue": "scans"},
}
