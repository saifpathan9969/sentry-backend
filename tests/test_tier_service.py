"""
Unit tests for tier-based access control service
"""
import pytest
from datetime import datetime, timedelta
from app.models.user import User, UserTier
from app.models.scan import Scan, ScanStatus
from app.services.tier_service import TierService
from app.core.config import settings as app_settings
import uuid


@pytest.mark.asyncio
class TestTierService:
    """Test suite for TierService"""
    
    async def test_get_tier_limits_free(self):
        """Test getting limits for Free tier"""
        limits = TierService.get_tier_limits(UserTier.FREE)
        
        assert limits.tier == UserTier.FREE
        assert limits.scans_per_day == app_settings.SCAN_LIMIT_FREE_TIER
        assert limits.allowed_scan_modes == ["common"]
        assert limits.rate_limit_per_hour == app_settings.RATE_LIMIT_FREE_TIER
        assert limits.scan_history_days == 30
    
    async def test_get_tier_limits_premium(self):
        """Test getting limits for Premium tier"""
        limits = TierService.get_tier_limits(UserTier.PREMIUM)
        
        assert limits.tier == UserTier.PREMIUM
        assert limits.scans_per_day is None  # Unlimited
        assert "common" in limits.allowed_scan_modes
        assert "full" in limits.allowed_scan_modes
        assert "stealth" in limits.allowed_scan_modes
        assert "aggressive" in limits.allowed_scan_modes
        assert "custom" not in limits.allowed_scan_modes
        assert limits.scan_history_days == 365
    
    async def test_get_tier_limits_enterprise(self):
        """Test getting limits for Enterprise tier"""
        limits = TierService.get_tier_limits(UserTier.ENTERPRISE)
        
        assert limits.tier == UserTier.ENTERPRISE
        assert limits.scans_per_day is None  # Unlimited
        assert "custom" in limits.allowed_scan_modes
        assert limits.scan_history_days is None  # Unlimited
    
    async def test_free_tier_scan_limit_not_reached(self, async_db_session):
        """Test Free tier user under daily scan limit"""
        user = User(
            id=uuid.uuid4(),
            email="free@example.com",
            password_hash="hashed",
            tier=UserTier.FREE,
        )
        async_db_session.add(user)
        await async_db_session.commit()
        
        # Create 5 scans (under limit of 10)
        now = datetime.utcnow()
        for i in range(5):
            scan = Scan(
                id=uuid.uuid4(),
                user_id=user.id,
                target_url=f"https://example{i}.com",
                scan_mode="common",
                status=ScanStatus.COMPLETED,
                created_at=now - timedelta(hours=i),
            )
            async_db_session.add(scan)
        await async_db_session.commit()
        
        result = await TierService.check_scan_limit(async_db_session, user)
        
        assert result.allowed is True
        assert result.current_usage == 5
        assert result.limit == app_settings.SCAN_LIMIT_FREE_TIER
        assert result.reason is None
    
    async def test_free_tier_scan_limit_reached(self, async_db_session):
        """Test Free tier user at daily scan limit"""
        user = User(
            id=uuid.uuid4(),
            email="free@example.com",
            password_hash="hashed",
            tier=UserTier.FREE,
        )
        async_db_session.add(user)
        await async_db_session.commit()
        
        # Create exactly 10 scans (at limit)
        now = datetime.utcnow()
        for i in range(app_settings.SCAN_LIMIT_FREE_TIER):
            scan = Scan(
                id=uuid.uuid4(),
                user_id=user.id,
                target_url=f"https://example{i}.com",
                scan_mode="common",
                status=ScanStatus.COMPLETED,
                created_at=now - timedelta(hours=i % 23),
            )
            async_db_session.add(scan)
        await async_db_session.commit()
        
        result = await TierService.check_scan_limit(async_db_session, user)
        
        assert result.allowed is False
        assert result.current_usage == app_settings.SCAN_LIMIT_FREE_TIER
        assert result.limit == app_settings.SCAN_LIMIT_FREE_TIER
        assert "limit reached" in result.reason.lower()
    
    async def test_free_tier_old_scans_not_counted(self, async_db_session):
        """Test that scans older than 24 hours don't count toward limit"""
        user = User(
            id=uuid.uuid4(),
            email="free@example.com",
            password_hash="hashed",
            tier=UserTier.FREE,
        )
        async_db_session.add(user)
        await async_db_session.commit()
        
        now = datetime.utcnow()
        
        # Create 5 recent scans
        for i in range(5):
            scan = Scan(
                id=uuid.uuid4(),
                user_id=user.id,
                target_url=f"https://recent{i}.com",
                scan_mode="common",
                status=ScanStatus.COMPLETED,
                created_at=now - timedelta(hours=i),
            )
            async_db_session.add(scan)
        
        # Create 10 old scans (more than 24 hours ago)
        for i in range(10):
            scan = Scan(
                id=uuid.uuid4(),
                user_id=user.id,
                target_url=f"https://old{i}.com",
                scan_mode="common",
                status=ScanStatus.COMPLETED,
                created_at=now - timedelta(hours=25 + i),
            )
            async_db_session.add(scan)
        
        await async_db_session.commit()
        
        result = await TierService.check_scan_limit(async_db_session, user)
        
        # Should only count the 5 recent scans
        assert result.allowed is True
        assert result.current_usage == 5
    
    async def test_premium_tier_unlimited_scans(self, async_db_session):
        """Test Premium tier has unlimited scans"""
        user = User(
            id=uuid.uuid4(),
            email="premium@example.com",
            password_hash="hashed",
            tier=UserTier.PREMIUM,
        )
        async_db_session.add(user)
        await async_db_session.commit()
        
        # Create 100 scans (way over Free limit)
        now = datetime.utcnow()
        for i in range(100):
            scan = Scan(
                id=uuid.uuid4(),
                user_id=user.id,
                target_url=f"https://example{i}.com",
                scan_mode="full",
                status=ScanStatus.COMPLETED,
                created_at=now - timedelta(hours=i % 23),
            )
            async_db_session.add(scan)
        await async_db_session.commit()
        
        result = await TierService.check_scan_limit(async_db_session, user)
        
        assert result.allowed is True
        assert result.limit is None
        assert result.current_usage is None
    
    async def test_enterprise_tier_unlimited_scans(self, async_db_session):
        """Test Enterprise tier has unlimited scans"""
        user = User(
            id=uuid.uuid4(),
            email="enterprise@example.com",
            password_hash="hashed",
            tier=UserTier.ENTERPRISE,
        )
        async_db_session.add(user)
        await async_db_session.commit()
        
        result = await TierService.check_scan_limit(async_db_session, user)
        
        assert result.allowed is True
        assert result.limit is None
    
    async def test_free_tier_scan_mode_common_allowed(self):
        """Test Free tier can use common scan mode"""
        user = User(
            id=uuid.uuid4(),
            email="free@example.com",
            password_hash="hashed",
            tier=UserTier.FREE,
        )
        
        result = TierService.check_scan_mode(user, "common")
        
        assert result.allowed is True
        assert result.reason is None
    
    async def test_free_tier_scan_mode_full_blocked(self):
        """Test Free tier cannot use full scan mode"""
        user = User(
            id=uuid.uuid4(),
            email="free@example.com",
            password_hash="hashed",
            tier=UserTier.FREE,
        )
        
        result = TierService.check_scan_mode(user, "full")
        
        assert result.allowed is False
        assert "not allowed" in result.reason.lower()
        assert "free" in result.reason.lower()
    
    async def test_premium_tier_scan_mode_full_allowed(self):
        """Test Premium tier can use full scan mode"""
        user = User(
            id=uuid.uuid4(),
            email="premium@example.com",
            password_hash="hashed",
            tier=UserTier.PREMIUM,
        )
        
        result = TierService.check_scan_mode(user, "full")
        
        assert result.allowed is True
    
    async def test_premium_tier_scan_mode_custom_blocked(self):
        """Test Premium tier cannot use custom scan mode"""
        user = User(
            id=uuid.uuid4(),
            email="premium@example.com",
            password_hash="hashed",
            tier=UserTier.PREMIUM,
        )
        
        result = TierService.check_scan_mode(user, "custom")
        
        assert result.allowed is False
        assert "not allowed" in result.reason.lower()
    
    async def test_enterprise_tier_scan_mode_custom_allowed(self):
        """Test Enterprise tier can use custom scan mode"""
        user = User(
            id=uuid.uuid4(),
            email="enterprise@example.com",
            password_hash="hashed",
            tier=UserTier.ENTERPRISE,
        )
        
        result = TierService.check_scan_mode(user, "custom")
        
        assert result.allowed is True
    
    async def test_comprehensive_check_mode_blocked(self, async_db_session):
        """Test comprehensive check fails when mode is not allowed"""
        user = User(
            id=uuid.uuid4(),
            email="free@example.com",
            password_hash="hashed",
            tier=UserTier.FREE,
        )
        async_db_session.add(user)
        await async_db_session.commit()
        
        # Try to use full mode (not allowed for Free tier)
        result = await TierService.check_scan_access(async_db_session, user, "full")
        
        assert result.allowed is False
        assert "not allowed" in result.reason.lower()
    
    async def test_comprehensive_check_limit_reached(self, async_db_session):
        """Test comprehensive check fails when scan limit is reached"""
        user = User(
            id=uuid.uuid4(),
            email="free@example.com",
            password_hash="hashed",
            tier=UserTier.FREE,
        )
        async_db_session.add(user)
        await async_db_session.commit()
        
        # Create 10 scans (at limit)
        now = datetime.utcnow()
        for i in range(app_settings.SCAN_LIMIT_FREE_TIER):
            scan = Scan(
                id=uuid.uuid4(),
                user_id=user.id,
                target_url=f"https://example{i}.com",
                scan_mode="common",
                status=ScanStatus.COMPLETED,
                created_at=now - timedelta(hours=i % 23),
            )
            async_db_session.add(scan)
        await async_db_session.commit()
        
        # Try to create another scan
        result = await TierService.check_scan_access(async_db_session, user, "common")
        
        assert result.allowed is False
        assert "limit" in result.reason.lower()
    
    async def test_comprehensive_check_success(self, async_db_session):
        """Test comprehensive check succeeds when both mode and limit are OK"""
        user = User(
            id=uuid.uuid4(),
            email="free@example.com",
            password_hash="hashed",
            tier=UserTier.FREE,
        )
        async_db_session.add(user)
        await async_db_session.commit()
        
        # Create 5 scans (under limit)
        now = datetime.utcnow()
        for i in range(5):
            scan = Scan(
                id=uuid.uuid4(),
                user_id=user.id,
                target_url=f"https://example{i}.com",
                scan_mode="common",
                status=ScanStatus.COMPLETED,
                created_at=now - timedelta(hours=i),
            )
            async_db_session.add(scan)
        await async_db_session.commit()
        
        # Try to create another scan with allowed mode
        result = await TierService.check_scan_access(async_db_session, user, "common")
        
        assert result.allowed is True
        assert result.reason is None
