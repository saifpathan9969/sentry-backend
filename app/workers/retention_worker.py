"""
Celery worker for scan retention cleanup
"""
from celery import Task
import logging

from app.workers.celery_app import celery_app
from app.db.session import async_session_maker
from app.services.retention_service import RetentionService

logger = logging.getLogger(__name__)


class RetentionTask(Task):
    """Base task for retention operations"""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure"""
        logger.error(f"Retention task {task_id} failed: {exc}")
        super().on_failure(exc, task_id, args, kwargs, einfo)


@celery_app.task(base=RetentionTask, name="cleanup_expired_scans")
def cleanup_expired_scans():
    """
    Cleanup expired scans for all users based on their tier
    
    This task should be scheduled to run daily (e.g., via Celery Beat)
    
    Returns:
        Number of scans archived
    """
    import asyncio
    
    async def _cleanup():
        async with async_session_maker() as db:
            try:
                total_archived = await RetentionService.cleanup_all_expired_scans(db)
                logger.info(f"Cleanup task complete: {total_archived} scans archived")
                return total_archived
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                raise
    
    # Run async function
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_cleanup())


@celery_app.task(base=RetentionTask, name="archive_user_scans")
def archive_user_scans(user_id: str, tier: str):
    """
    Archive expired scans for a specific user
    
    Args:
        user_id: User ID (as string)
        tier: User tier
        
    Returns:
        Number of scans archived
    """
    import asyncio
    from uuid import UUID
    
    async def _archive():
        async with async_session_maker() as db:
            try:
                user_uuid = UUID(user_id)
                archived = await RetentionService.archive_expired_scans(db, user_uuid, tier)
                logger.info(f"Archived {archived} scans for user {user_id}")
                return archived
            except Exception as e:
                logger.error(f"Error archiving scans for user {user_id}: {e}")
                raise
    
    # Run async function
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_archive())
