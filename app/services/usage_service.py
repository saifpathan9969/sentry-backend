"""
Service for retrieving usage statistics
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from uuid import UUID
from datetime import datetime, timedelta
from typing import Dict, Any, List

from app.models.api_usage import APIUsage
from app.models.scan import Scan
from app.models.user import User


class UsageService:
    """Service for usage tracking and statistics"""
    
    @classmethod
    async def get_user_statistics(
        cls,
        db: AsyncSession,
        user_id: UUID,
        days: int = 30,
    ) -> Dict[str, Any]:
        """
        Get comprehensive usage statistics for a user
        
        Args:
            db: Database session
            user_id: User ID
            days: Number of days to look back (default: 30)
            
        Returns:
            Dict with usage statistics
        """
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get scan count for period
        scan_count = await cls.get_scan_count(db, user_id, start_date, end_date)
        
        # Get scan count for today
        scans_today = await cls.get_today_scan_count(db, user_id)
        
        # Get scan count for this month
        scans_this_month = await cls.get_month_scan_count(db, user_id)
        
        # Get API call count
        api_call_count = await cls.get_api_call_count(db, user_id, start_date, end_date)
        
        # Get scan count by day
        scans_by_day = await cls.get_scans_by_day(db, user_id, start_date, end_date)
        
        # Get API calls by endpoint
        calls_by_endpoint = await cls.get_calls_by_endpoint(db, user_id, start_date, end_date)
        
        # Get average response time
        avg_response_time = await cls.get_average_response_time(db, user_id, start_date, end_date)
        
        return {
            "user_id": str(user_id),
            "period_days": days,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "scan_count": scan_count,
            "scans_today": scans_today,
            "scans_this_month": scans_this_month,
            "api_call_count": api_call_count,
            "scans_by_day": scans_by_day,
            "calls_by_endpoint": calls_by_endpoint,
            "average_response_time_ms": avg_response_time,
        }
    
    @classmethod
    async def get_scan_count(
        cls,
        db: AsyncSession,
        user_id: UUID,
        start_date: datetime,
        end_date: datetime,
    ) -> int:
        """
        Get total scan count for user in date range
        
        Args:
            db: Database session
            user_id: User ID
            start_date: Start date
            end_date: End date
            
        Returns:
            Total scan count
        """
        query = select(func.count(Scan.id)).where(
            and_(
                Scan.user_id == user_id,
                Scan.created_at >= start_date,
                Scan.created_at <= end_date,
            )
        )
        result = await db.execute(query)
        return result.scalar() or 0
    
    @classmethod
    async def get_api_call_count(
        cls,
        db: AsyncSession,
        user_id: UUID,
        start_date: datetime,
        end_date: datetime,
    ) -> int:
        """
        Get total API call count for user in date range
        
        Args:
            db: Database session
            user_id: User ID
            start_date: Start date
            end_date: End date
            
        Returns:
            Total API call count
        """
        query = select(func.count(APIUsage.id)).where(
            and_(
                APIUsage.user_id == user_id,
                APIUsage.created_at >= start_date,
                APIUsage.created_at <= end_date,
            )
        )
        result = await db.execute(query)
        return result.scalar() or 0
    
    @classmethod
    async def get_scans_by_day(
        cls,
        db: AsyncSession,
        user_id: UUID,
        start_date: datetime,
        end_date: datetime,
    ) -> List[Dict[str, Any]]:
        """
        Get scan count grouped by day
        
        Args:
            db: Database session
            user_id: User ID
            start_date: Start date
            end_date: End date
            
        Returns:
            List of dicts with date and count
        """
        query = select(
            func.date(Scan.created_at).label("date"),
            func.count(Scan.id).label("count"),
        ).where(
            and_(
                Scan.user_id == user_id,
                Scan.created_at >= start_date,
                Scan.created_at <= end_date,
            )
        ).group_by(
            func.date(Scan.created_at)
        ).order_by(
            func.date(Scan.created_at)
        )
        
        result = await db.execute(query)
        rows = result.all()
        
        return [
            {
                "date": row.date.isoformat() if row.date else None,
                "count": row.count,
            }
            for row in rows
        ]
    
    @classmethod
    async def get_calls_by_endpoint(
        cls,
        db: AsyncSession,
        user_id: UUID,
        start_date: datetime,
        end_date: datetime,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Get API call count grouped by endpoint
        
        Args:
            db: Database session
            user_id: User ID
            start_date: Start date
            end_date: End date
            limit: Maximum number of endpoints to return
            
        Returns:
            List of dicts with endpoint and count
        """
        query = select(
            APIUsage.endpoint,
            func.count(APIUsage.id).label("count"),
        ).where(
            and_(
                APIUsage.user_id == user_id,
                APIUsage.created_at >= start_date,
                APIUsage.created_at <= end_date,
            )
        ).group_by(
            APIUsage.endpoint
        ).order_by(
            func.count(APIUsage.id).desc()
        ).limit(limit)
        
        result = await db.execute(query)
        rows = result.all()
        
        return [
            {
                "endpoint": row.endpoint,
                "count": row.count,
            }
            for row in rows
        ]
    
    @classmethod
    async def get_average_response_time(
        cls,
        db: AsyncSession,
        user_id: UUID,
        start_date: datetime,
        end_date: datetime,
    ) -> float:
        """
        Get average response time for user's API calls
        
        Args:
            db: Database session
            user_id: User ID
            start_date: Start date
            end_date: End date
            
        Returns:
            Average response time in milliseconds
        """
        query = select(
            func.avg(APIUsage.response_time_ms)
        ).where(
            and_(
                APIUsage.user_id == user_id,
                APIUsage.created_at >= start_date,
                APIUsage.created_at <= end_date,
            )
        )
        
        result = await db.execute(query)
        avg_time = result.scalar()
        
        return round(avg_time, 2) if avg_time else 0.0
    
    @classmethod
    async def get_today_scan_count(
        cls,
        db: AsyncSession,
        user_id: UUID,
    ) -> int:
        """
        Get scan count for today (used for tier limit checking)
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Scan count for today
        """
        # Get start of today (midnight UTC)
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = datetime.utcnow()
        
        return await cls.get_scan_count(db, user_id, today_start, today_end)
    
    @classmethod
    async def get_month_api_call_count(
        cls,
        db: AsyncSession,
        user_id: UUID,
    ) -> int:
        """
        Get API call count for current month (used for tier limit checking)
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            API call count for current month
        """
        # Get start of current month
        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_end = now
        
        return await cls.get_api_call_count(db, user_id, month_start, month_end)
    
    @classmethod
    async def get_month_scan_count(
        cls,
        db: AsyncSession,
        user_id: UUID,
    ) -> int:
        """
        Get scan count for current month
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Scan count for current month
        """
        # Get start of current month
        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_end = now
        
        return await cls.get_scan_count(db, user_id, month_start, month_end)
