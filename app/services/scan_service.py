"""
Scan service for managing security scans
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from uuid import UUID
from datetime import datetime
from typing import List, Tuple

from app.models.scan import Scan
from app.models.user import User
from app.schemas.scan import ScanCreate, ScanResponse, ScanListResponse
from app.services.tier_service import TierService
from app.services.queue_service import queue_service
from app.workers.scan_worker import process_scan
from fastapi import HTTPException, status


class ScanService:
    """Service for scan management"""
    
    @classmethod
    async def create_scan(
        cls,
        db: AsyncSession,
        user: User,
        scan_data: ScanCreate,
    ) -> Scan:
        """
        Create a new scan
        
        Args:
            db: Database session
            user: User creating the scan
            scan_data: Scan creation data
            
        Returns:
            Created scan
            
        Raises:
            HTTPException: If tier limits are exceeded
        """
        # Check tier-based access
        access_check = await TierService.check_scan_access(
            db, user, scan_data.scan_mode, scan_data.execution_mode
        )
        
        if not access_check.allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=access_check.reason
            )
        
        # Create scan - use string values for PostgreSQL enums
        scan = Scan(
            user_id=user.id,
            target=str(scan_data.target_url),
            scan_mode=scan_data.scan_mode,
            execution_mode=scan_data.execution_mode,
            status='queued',
        )
        
        db.add(scan)
        await db.commit()
        await db.refresh(scan)
        
        # For local development, run scan synchronously
        from app.core.config import settings
        if settings.ENVIRONMENT == "development":
            # Import here to avoid circular imports
            from app.workers.scan_worker import _process_scan_async
            import asyncio
            
            # Immediately set to running status for better UX
            scan.status = 'running'
            scan.started_at = datetime.utcnow()
            await db.commit()
            await db.refresh(scan)
            
            # Run scan in background task (non-blocking)
            asyncio.create_task(_process_scan_async(
                str(scan.id),
                str(user.id),
                scan.target,
                scan.scan_mode,
                scan.execution_mode,
            ))
        else:
            # Production: Use Celery
            process_scan.delay(
                scan_id=str(scan.id),
                user_id=str(user.id),
                target_url=scan.target,
                scan_mode=scan.scan_mode,
                execution_mode=scan.execution_mode,
            )
            
            # Also track in Redis queue for monitoring (optional)
            try:
                await queue_service.enqueue_scan(
                    scan_id=scan.id,
                    user_id=user.id,
                    target_url=scan.target,
                    scan_mode=scan.scan_mode,
                    execution_mode=scan.execution_mode,
                    user_tier=user.tier,
                )
            except Exception as e:
                print(f"Redis queue tracking failed (non-critical): {e}")
                # Continue without Redis tracking
        
        return scan
    
    @classmethod
    async def get_scan(
        cls,
        db: AsyncSession,
        scan_id: str,
        user_id: str,
    ) -> Scan:
        """
        Get a scan by ID
        
        Args:
            db: Database session
            scan_id: Scan ID
            user_id: User ID (for authorization)
            
        Returns:
            Scan object
            
        Raises:
            HTTPException: If scan not found or unauthorized
        """
        query = select(Scan).where(
            Scan.id == scan_id,
            Scan.user_id == user_id,
        )
        result = await db.execute(query)
        scan = result.scalar_one_or_none()
        
        if not scan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scan not found"
            )
        
        return scan
    
    @classmethod
    async def list_scans(
        cls,
        db: AsyncSession,
        user_id: str,
        user_tier: str,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Scan], int]:
        """
        List scans for a user with pagination and tier-based retention filtering
        
        Args:
            db: Database session
            user_id: User ID
            user_tier: User tier (for retention filtering)
            limit: Maximum number of scans to return
            offset: Number of scans to skip
            
        Returns:
            Tuple of (scans list, total count)
        """
        from app.services.retention_service import RetentionService
        from datetime import timedelta
        
        # Get retention period for tier
        retention_days = await RetentionService.get_retention_period(user_tier)
        
        # Build base query
        base_where = Scan.user_id == user_id
        
        # Apply retention filter if not unlimited
        if retention_days is not None:
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
            base_where = (Scan.user_id == user_id) & (Scan.created_at >= cutoff_date)
        
        # Get total count
        count_query = select(func.count(Scan.id)).where(base_where)
        count_result = await db.execute(count_query)
        total = count_result.scalar_one()
        
        # Get scans
        query = (
            select(Scan)
            .where(base_where)
            .order_by(desc(Scan.created_at))
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(query)
        scans = result.scalars().all()
        
        return list(scans), total
    
    @classmethod
    async def delete_scan(
        cls,
        db: AsyncSession,
        scan_id: str,
        user_id: str,
    ) -> bool:
        """
        Delete a scan
        
        Args:
            db: Database session
            scan_id: Scan ID
            user_id: User ID (for authorization)
            
        Returns:
            True if deleted
            
        Raises:
            HTTPException: If scan not found or unauthorized
        """
        scan = await cls.get_scan(db, scan_id, user_id)
        
        await db.delete(scan)
        await db.commit()
        
        return True
    
    @classmethod
    async def get_scan_report(
        cls,
        db: AsyncSession,
        scan_id: str,
        user_id: str,
        format: str = "json",
    ) -> str:
        """
        Get scan report in specified format
        
        Args:
            db: Database session
            scan_id: Scan ID
            user_id: User ID (for authorization)
            format: Report format ("json" or "text")
            
        Returns:
            Report content as string
            
        Raises:
            HTTPException: If scan not found, unauthorized, or not completed
        """
        scan = await cls.get_scan(db, scan_id, user_id)
        
        # Compare with string value since status column uses PostgreSQL enum
        scan_status = scan.status.value if hasattr(scan.status, 'value') else scan.status
        if scan_status != 'completed':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Scan is not completed (status: {scan_status})"
            )
        
        if format == "json":
            if not scan.report_json:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="JSON report not available"
                )
            return scan.report_json
        elif format == "text":
            if not scan.report_text:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Text report not available"
                )
            return scan.report_text
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid format. Must be 'json' or 'text'"
            )
    
    @classmethod
    async def cancel_scan(
        cls,
        db: AsyncSession,
        scan_id: str,
        user_id: str,
    ) -> Scan:
        """
        Cancel a running or queued scan
        
        Args:
            db: Database session
            scan_id: Scan ID
            user_id: User ID (for authorization)
            
        Returns:
            Updated scan
            
        Raises:
            HTTPException: If scan not found, unauthorized, or cannot be cancelled
        """
        scan = await cls.get_scan(db, scan_id, user_id)
        
        # Compare with string values
        scan_status = scan.status.value if hasattr(scan.status, 'value') else scan.status
        if scan_status not in ['queued', 'running']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel scan with status: {scan_status}"
            )
        
        scan.status = 'cancelled'
        scan.completed_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(scan)
        
        # Cancel background job (optional in development)
        try:
            await queue_service.cancel_job(scan.id)
        except Exception as e:
            print(f"Redis job cancellation failed (non-critical): {e}")
            # Continue without Redis cancellation
        
        return scan
