"""
Unit tests for scan service
"""
import pytest
from uuid import uuid4
from datetime import datetime, timedelta

from app.models.user import User, UserTier
from app.models.scan import Scan, ScanStatus
from app.schemas.scan import ScanCreate
from app.services.scan_service import ScanService
from fastapi import HTTPException


@pytest.mark.asyncio
class TestScanService:
    """Test suite for ScanService"""
    
    async def test_create_scan_success(self, async_db_session):
        """Test creating a scan successfully"""
        # Create user
        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash="hashed",
            tier=UserTier.FREE,
        )
        async_db_session.add(user)
        await async_db_session.commit()
        
        # Create scan
        scan_data = ScanCreate(
            target_url="https://example.com",
            scan_mode="common",
        )
        
        scan = await ScanService.create_scan(async_db_session, user, scan_data)
        
        assert scan.id is not None
        assert scan.user_id == user.id
        assert scan.target_url == "https://example.com/"
        assert scan.scan_mode == "common"
        assert scan.status == ScanStatus.QUEUED
    
    async def test_create_scan_exceeds_limit(self, async_db_session):
        """Test creating scan when daily limit is exceeded"""
        # Create Free tier user
        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash="hashed",
            tier=UserTier.FREE,
        )
        async_db_session.add(user)
        await async_db_session.commit()
        
        # Create 10 scans (at limit)
        now = datetime.utcnow()
        for i in range(10):
            scan = Scan(
                id=uuid4(),
                user_id=user.id,
                target_url=f"https://example{i}.com",
                scan_mode="common",
                status=ScanStatus.COMPLETED,
                created_at=now - timedelta(hours=i),
            )
            async_db_session.add(scan)
        await async_db_session.commit()
        
        # Try to create another scan
        scan_data = ScanCreate(
            target_url="https://example.com",
            scan_mode="common",
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await ScanService.create_scan(async_db_session, user, scan_data)
        
        assert exc_info.value.status_code == 403
        assert "limit" in exc_info.value.detail.lower()
    
    async def test_create_scan_invalid_mode(self, async_db_session):
        """Test creating scan with invalid mode for tier"""
        # Create Free tier user
        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash="hashed",
            tier=UserTier.FREE,
        )
        async_db_session.add(user)
        await async_db_session.commit()
        
        # Try to create scan with "full" mode (not allowed for Free tier)
        scan_data = ScanCreate(
            target_url="https://example.com",
            scan_mode="full",
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await ScanService.create_scan(async_db_session, user, scan_data)
        
        assert exc_info.value.status_code == 403
        assert "not allowed" in exc_info.value.detail.lower()
    
    async def test_get_scan_success(self, async_db_session):
        """Test getting a scan by ID"""
        # Create user and scan
        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash="hashed",
            tier=UserTier.FREE,
        )
        async_db_session.add(user)
        
        scan = Scan(
            id=uuid4(),
            user_id=user.id,
            target_url="https://example.com",
            scan_mode="common",
            status=ScanStatus.COMPLETED,
        )
        async_db_session.add(scan)
        await async_db_session.commit()
        
        # Get scan
        retrieved_scan = await ScanService.get_scan(
            async_db_session, scan.id, user.id
        )
        
        assert retrieved_scan.id == scan.id
        assert retrieved_scan.user_id == user.id
    
    async def test_get_scan_not_found(self, async_db_session):
        """Test getting a non-existent scan"""
        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash="hashed",
            tier=UserTier.FREE,
        )
        async_db_session.add(user)
        await async_db_session.commit()
        
        with pytest.raises(HTTPException) as exc_info:
            await ScanService.get_scan(async_db_session, uuid4(), user.id)
        
        assert exc_info.value.status_code == 404
    
    async def test_get_scan_unauthorized(self, async_db_session):
        """Test getting another user's scan"""
        # Create two users
        user1 = User(
            id=uuid4(),
            email="user1@example.com",
            password_hash="hashed",
            tier=UserTier.FREE,
        )
        user2 = User(
            id=uuid4(),
            email="user2@example.com",
            password_hash="hashed",
            tier=UserTier.FREE,
        )
        async_db_session.add(user1)
        async_db_session.add(user2)
        
        # Create scan for user1
        scan = Scan(
            id=uuid4(),
            user_id=user1.id,
            target_url="https://example.com",
            scan_mode="common",
            status=ScanStatus.COMPLETED,
        )
        async_db_session.add(scan)
        await async_db_session.commit()
        
        # Try to get scan as user2
        with pytest.raises(HTTPException) as exc_info:
            await ScanService.get_scan(async_db_session, scan.id, user2.id)
        
        assert exc_info.value.status_code == 404
    
    async def test_list_scans(self, async_db_session):
        """Test listing scans with pagination"""
        # Create user
        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash="hashed",
            tier=UserTier.FREE,
        )
        async_db_session.add(user)
        await async_db_session.commit()
        
        # Create 5 scans
        for i in range(5):
            scan = Scan(
                id=uuid4(),
                user_id=user.id,
                target_url=f"https://example{i}.com",
                scan_mode="common",
                status=ScanStatus.COMPLETED,
            )
            async_db_session.add(scan)
        await async_db_session.commit()
        
        # List scans
        scans, total = await ScanService.list_scans(async_db_session, user.id)
        
        assert len(scans) == 5
        assert total == 5
    
    async def test_list_scans_pagination(self, async_db_session):
        """Test listing scans with pagination"""
        # Create user
        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash="hashed",
            tier=UserTier.FREE,
        )
        async_db_session.add(user)
        await async_db_session.commit()
        
        # Create 10 scans
        for i in range(10):
            scan = Scan(
                id=uuid4(),
                user_id=user.id,
                target_url=f"https://example{i}.com",
                scan_mode="common",
                status=ScanStatus.COMPLETED,
            )
            async_db_session.add(scan)
        await async_db_session.commit()
        
        # List first 5 scans
        scans, total = await ScanService.list_scans(
            async_db_session, user.id, limit=5, offset=0
        )
        
        assert len(scans) == 5
        assert total == 10
        
        # List next 5 scans
        scans, total = await ScanService.list_scans(
            async_db_session, user.id, limit=5, offset=5
        )
        
        assert len(scans) == 5
        assert total == 10
    
    async def test_delete_scan_success(self, async_db_session):
        """Test deleting a scan"""
        # Create user and scan
        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash="hashed",
            tier=UserTier.FREE,
        )
        async_db_session.add(user)
        
        scan = Scan(
            id=uuid4(),
            user_id=user.id,
            target_url="https://example.com",
            scan_mode="common",
            status=ScanStatus.COMPLETED,
        )
        async_db_session.add(scan)
        await async_db_session.commit()
        
        # Delete scan
        result = await ScanService.delete_scan(async_db_session, scan.id, user.id)
        
        assert result is True
        
        # Verify scan is deleted
        with pytest.raises(HTTPException):
            await ScanService.get_scan(async_db_session, scan.id, user.id)
    
    async def test_get_scan_report_json(self, async_db_session):
        """Test getting scan report in JSON format"""
        # Create user and completed scan with report
        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash="hashed",
            tier=UserTier.FREE,
        )
        async_db_session.add(user)
        
        scan = Scan(
            id=uuid4(),
            user_id=user.id,
            target_url="https://example.com",
            scan_mode="common",
            status=ScanStatus.COMPLETED,
            report_json='{"vulnerabilities": []}',
        )
        async_db_session.add(scan)
        await async_db_session.commit()
        
        # Get report
        report = await ScanService.get_scan_report(
            async_db_session, scan.id, user.id, "json"
        )
        
        assert report == '{"vulnerabilities": []}'
    
    async def test_get_scan_report_text(self, async_db_session):
        """Test getting scan report in TEXT format"""
        # Create user and completed scan with report
        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash="hashed",
            tier=UserTier.FREE,
        )
        async_db_session.add(user)
        
        scan = Scan(
            id=uuid4(),
            user_id=user.id,
            target_url="https://example.com",
            scan_mode="common",
            status=ScanStatus.COMPLETED,
            report_text="Scan Report\n===========\nNo vulnerabilities found.",
        )
        async_db_session.add(scan)
        await async_db_session.commit()
        
        # Get report
        report = await ScanService.get_scan_report(
            async_db_session, scan.id, user.id, "text"
        )
        
        assert "Scan Report" in report
    
    async def test_get_scan_report_not_completed(self, async_db_session):
        """Test getting report for non-completed scan"""
        # Create user and queued scan
        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash="hashed",
            tier=UserTier.FREE,
        )
        async_db_session.add(user)
        
        scan = Scan(
            id=uuid4(),
            user_id=user.id,
            target_url="https://example.com",
            scan_mode="common",
            status=ScanStatus.QUEUED,
        )
        async_db_session.add(scan)
        await async_db_session.commit()
        
        # Try to get report
        with pytest.raises(HTTPException) as exc_info:
            await ScanService.get_scan_report(
                async_db_session, scan.id, user.id, "json"
            )
        
        assert exc_info.value.status_code == 400
        assert "not completed" in exc_info.value.detail.lower()
    
    async def test_cancel_scan_queued(self, async_db_session):
        """Test cancelling a queued scan"""
        # Create user and queued scan
        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash="hashed",
            tier=UserTier.FREE,
        )
        async_db_session.add(user)
        
        scan = Scan(
            id=uuid4(),
            user_id=user.id,
            target_url="https://example.com",
            scan_mode="common",
            status=ScanStatus.QUEUED,
        )
        async_db_session.add(scan)
        await async_db_session.commit()
        
        # Cancel scan
        cancelled_scan = await ScanService.cancel_scan(
            async_db_session, scan.id, user.id
        )
        
        assert cancelled_scan.status == ScanStatus.CANCELLED
        assert cancelled_scan.completed_at is not None
    
    async def test_cancel_scan_running(self, async_db_session):
        """Test cancelling a running scan"""
        # Create user and running scan
        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash="hashed",
            tier=UserTier.FREE,
        )
        async_db_session.add(user)
        
        scan = Scan(
            id=uuid4(),
            user_id=user.id,
            target_url="https://example.com",
            scan_mode="common",
            status=ScanStatus.RUNNING,
            started_at=datetime.utcnow(),
        )
        async_db_session.add(scan)
        await async_db_session.commit()
        
        # Cancel scan
        cancelled_scan = await ScanService.cancel_scan(
            async_db_session, scan.id, user.id
        )
        
        assert cancelled_scan.status == ScanStatus.CANCELLED
    
    async def test_cancel_scan_completed(self, async_db_session):
        """Test cancelling a completed scan (should fail)"""
        # Create user and completed scan
        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash="hashed",
            tier=UserTier.FREE,
        )
        async_db_session.add(user)
        
        scan = Scan(
            id=uuid4(),
            user_id=user.id,
            target_url="https://example.com",
            scan_mode="common",
            status=ScanStatus.COMPLETED,
            completed_at=datetime.utcnow(),
        )
        async_db_session.add(scan)
        await async_db_session.commit()
        
        # Try to cancel scan
        with pytest.raises(HTTPException) as exc_info:
            await ScanService.cancel_scan(async_db_session, scan.id, user.id)
        
        assert exc_info.value.status_code == 400
        assert "cannot cancel" in exc_info.value.detail.lower()
