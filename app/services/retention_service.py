"""
Service for managing scan history retention based on user tier
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_
from uuid import UUID
from datetime import datetime, timedelta
from typing import List, Optional
import logging

from app.models.scan import Scan
from app.models.user import User

logger = logging.getLogger(__name__)


class RetentionService:
    """Service for scan history retention management"""
    
    # Retention periods by tier (in days)
    RETENTION_PERIODS = {
        "free": 30,
        "premium": 365,
        "enterprise": None,  # Unlimited
    }
    
    @classmethod
    async def get_retention_period(cls, tier: str) -> Optional[int]:
        """
        Get retention period for a tier
        
        Args:
            tier: User tier (free, premium, enterprise)
            
        Returns:
            Retention period in days, or None for unlimited
        """
        return cls.RETENTION_PERIODS.get(tier.lower())
    
    @classmethod
    async def get_accessible_scans(
        cls,
        db: AsyncSession,
        user_id: UUID,
        tier: str,
    ) -> List[Scan]:
        """
        Get scans accessible to user based on tier retention policy
        
        Args:
            db: Database session
            user_id: User ID
            tier: User tier
            
        Returns:
            List of accessible scans
        """
        retention_days = await cls.get_retention_period(tier)
        
        # Build query
        query = select(Scan).where(Scan.user_id == user_id)
        
        # Apply retention filter if not unlimited
        if retention_days is not None:
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
            query = query.where(Scan.created_at >= cutoff_date)
        
        # Order by most recent first
        query = query.order_by(Scan.created_at.desc())
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    @classmethod
    async def archive_expired_scans(
        cls,
        db: AsyncSession,
        user_id: UUID,
        tier: str,
    ) -> int:
        """
        Archive scans that exceed retention period for user's tier
        
        Args:
            db: Database session
            user_id: User ID
            tier: User tier
            
        Returns:
            Number of scans archived (deleted)
        """
        retention_days = await cls.get_retention_period(tier)
        
        # Enterprise tier has unlimited retention
        if retention_days is None:
            return 0
        
        # Calculate cutoff date
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        # Delete expired scans
        stmt = delete(Scan).where(
            and_(
                Scan.user_id == user_id,
                Scan.created_at < cutoff_date
            )
        )
        
        result = await db.execute(stmt)
        await db.commit()
        
        archived_count = result.rowcount
        
        if archived_count > 0:
            logger.info(f"Archived {archived_count} scans for user {user_id} (tier: {tier})")
        
        return archived_count
    
    @classmethod
    async def cleanup_all_expired_scans(cls, db: AsyncSession) -> int:
        """
        Cleanup expired scans for all users based on their tier
        
        This should be run as a background task (e.g., daily cron job)
        
        Args:
            db: Database session
            
        Returns:
            Total number of scans archived
        """
        # Get all users
        query = select(User)
        result = await db.execute(query)
        users = result.scalars().all()
        
        total_archived = 0
        
        for user in users:
            try:
                archived = await cls.archive_expired_scans(db, user.id, user.tier)
                total_archived += archived
            except Exception as e:
                logger.error(f"Error archiving scans for user {user.id}: {e}")
                continue
        
        logger.info(f"Cleanup complete: archived {total_archived} scans total")
        
        return total_archived
    
    @classmethod
    async def restore_scans_on_upgrade(
        cls,
        db: AsyncSession,
        user_id: UUID,
        old_tier: str,
        new_tier: str,
    ) -> int:
        """
        Restore previously archived scans when user upgrades tier
        
        Note: This is a placeholder since we delete scans rather than archive them.
        In a production system, you would mark scans as archived and restore them here.
        
        Args:
            db: Database session
            user_id: User ID
            old_tier: Previous tier
            new_tier: New tier
            
        Returns:
            Number of scans restored (always 0 in current implementation)
        """
        # In current implementation, we delete scans so they cannot be restored
        # In production, you would:
        # 1. Add an 'archived' boolean field to Scan model
        # 2. Mark scans as archived instead of deleting them
        # 3. Restore archived scans here when user upgrades
        
        logger.info(
            f"User {user_id} upgraded from {old_tier} to {new_tier}. "
            f"Note: Previously deleted scans cannot be restored."
        )
        
        return 0
    
    @classmethod
    async def get_scan_count_by_retention(
        cls,
        db: AsyncSession,
        user_id: UUID,
        tier: str,
    ) -> dict:
        """
        Get scan count statistics for retention analysis
        
        Args:
            db: Database session
            user_id: User ID
            tier: User tier
            
        Returns:
            Dict with scan counts
        """
        retention_days = await cls.get_retention_period(tier)
        
        # Get total scans
        total_query = select(Scan).where(Scan.user_id == user_id)
        total_result = await db.execute(total_query)
        total_scans = len(list(total_result.scalars().all()))
        
        # Get accessible scans
        accessible_scans = await cls.get_accessible_scans(db, user_id, tier)
        accessible_count = len(accessible_scans)
        
        # Calculate expired count
        expired_count = total_scans - accessible_count
        
        return {
            "tier": tier,
            "retention_days": retention_days,
            "total_scans": total_scans,
            "accessible_scans": accessible_count,
            "expired_scans": expired_count,
        }
