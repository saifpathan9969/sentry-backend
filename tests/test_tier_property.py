"""
Property-based tests for tier-based access control

Feature: pentest-brain-web-app
"""
import pytest
from hypothesis import given, strategies as st, settings as hyp_settings, assume
from datetime import datetime, timedelta
from app.models.user import User, UserTier
from app.models.scan import Scan, ScanStatus
from app.services.tier_service import TierService
from app.core.config import settings as app_settings
import uuid


# Feature: pentest-brain-web-app, Property 3: Tier-based scan limit enforcement
# Validates: Requirements 5.1
@pytest.mark.asyncio
@given(
    scan_count=st.integers(min_value=0, max_value=20),
    tier=st.sampled_from([UserTier.FREE, UserTier.PREMIUM, UserTier.ENTERPRISE]),
)
@hyp_settings(max_examples=100, deadline=None)
async def test_property_scan_limit_enforcement(scan_count, tier, async_db_session):
    """
    Property: Free tier users are blocked after reaching daily limit,
    Premium and Enterprise users are never blocked
    """
    # Create user with specified tier
    user = User(
        id=uuid.uuid4(),
        email=f"test_{uuid.uuid4()}@example.com",
        password_hash="hashed",
        tier=tier,
    )
    async_db_session.add(user)
    await async_db_session.commit()
    
    # Create scans in the last 24 hours
    now = datetime.utcnow()
    for i in range(scan_count):
        scan = Scan(
            id=uuid.uuid4(),
            user_id=user.id,
            target_url=f"https://example{i}.com",
            scan_mode="common",
            status=ScanStatus.COMPLETED,
            created_at=now - timedelta(hours=i % 24),
        )
        async_db_session.add(scan)
    await async_db_session.commit()
    
    # Check scan limit
    result = await TierService.check_scan_limit(async_db_session, user)
    
    # Property verification
    if tier == UserTier.FREE:
        # Free tier should be blocked after reaching limit
        expected_allowed = scan_count < app_settings.SCAN_LIMIT_FREE_TIER
        assert result.allowed == expected_allowed, \
            f"Free tier with {scan_count} scans should be {'allowed' if expected_allowed else 'blocked'}"
        assert result.limit == app_settings.SCAN_LIMIT_FREE_TIER
        assert result.current_usage == scan_count
    else:
        # Premium and Enterprise should never be blocked
        assert result.allowed is True, \
            f"{tier.value} tier should never be blocked regardless of scan count"
        assert result.limit is None
        assert result.current_usage is None


# Feature: pentest-brain-web-app, Property 3: Tier-based scan limit enforcement (old scans)
# Validates: Requirements 5.1
@pytest.mark.asyncio
@given(
    recent_scans=st.integers(min_value=0, max_value=15),
    old_scans=st.integers(min_value=0, max_value=20),
)
@hyp_settings(max_examples=100, deadline=None)
async def test_property_scan_limit_only_counts_recent(recent_scans, old_scans, async_db_session):
    """
    Property: Only scans from the last 24 hours count toward the daily limit
    """
    # Create Free tier user
    user = User(
        id=uuid.uuid4(),
        email=f"test_{uuid.uuid4()}@example.com",
        password_hash="hashed",
        tier=UserTier.FREE,
    )
    async_db_session.add(user)
    await async_db_session.commit()
    
    now = datetime.utcnow()
    
    # Create recent scans (within 24 hours)
    for i in range(recent_scans):
        scan = Scan(
            id=uuid.uuid4(),
            user_id=user.id,
            target_url=f"https://recent{i}.com",
            scan_mode="common",
            status=ScanStatus.COMPLETED,
            created_at=now - timedelta(hours=i % 23),
        )
        async_db_session.add(scan)
    
    # Create old scans (more than 24 hours ago)
    for i in range(old_scans):
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
    
    # Check scan limit
    result = await TierService.check_scan_limit(async_db_session, user)
    
    # Property: Only recent scans count
    assert result.current_usage == recent_scans, \
        f"Should count only {recent_scans} recent scans, not {old_scans} old scans"
    expected_allowed = recent_scans < app_settings.SCAN_LIMIT_FREE_TIER
    assert result.allowed == expected_allowed


# Feature: pentest-brain-web-app, Property 4: Scan mode restriction by tier
# Validates: Requirements 5.2
@given(
    tier=st.sampled_from([UserTier.FREE, UserTier.PREMIUM, UserTier.ENTERPRISE]),
    scan_mode=st.sampled_from(["common", "full", "stealth", "aggressive", "custom"]),
)
@hyp_settings(max_examples=100, deadline=None)
def test_property_scan_mode_restriction(tier, scan_mode):
    """
    Property: Each tier has specific allowed scan modes
    - Free: only "common"
    - Premium: "common", "full", "stealth", "aggressive"
    - Enterprise: all modes including "custom"
    """
    # Create user with specified tier
    user = User(
        id=uuid.uuid4(),
        email=f"test_{uuid.uuid4()}@example.com",
        password_hash="hashed",
        tier=tier,
    )
    
    # Check scan mode
    result = TierService.check_scan_mode(user, scan_mode)
    
    # Property verification based on tier
    if tier == UserTier.FREE:
        expected_allowed = scan_mode == "common"
        assert result.allowed == expected_allowed, \
            f"Free tier should only allow 'common' mode, not '{scan_mode}'"
    elif tier == UserTier.PREMIUM:
        expected_allowed = scan_mode in ["common", "full", "stealth", "aggressive"]
        assert result.allowed == expected_allowed, \
            f"Premium tier should allow standard modes but not 'custom'"
    else:  # ENTERPRISE
        assert result.allowed is True, \
            f"Enterprise tier should allow all modes including '{scan_mode}'"


# Feature: pentest-brain-web-app, Property 4: Scan mode restriction consistency
# Validates: Requirements 5.2
@given(
    tier=st.sampled_from([UserTier.FREE, UserTier.PREMIUM, UserTier.ENTERPRISE]),
)
@hyp_settings(max_examples=100, deadline=None)
def test_property_tier_limits_consistency(tier):
    """
    Property: Tier limits are consistent and well-defined
    """
    limits = TierService.get_tier_limits(tier)
    
    # All tiers should have defined properties
    assert limits.tier == tier
    assert isinstance(limits.allowed_scan_modes, list)
    assert len(limits.allowed_scan_modes) > 0, "Each tier must allow at least one scan mode"
    
    # Free tier should have limits
    if tier == UserTier.FREE:
        assert limits.scans_per_day is not None and limits.scans_per_day > 0
        assert limits.scan_history_days is not None and limits.scan_history_days > 0
        assert "common" in limits.allowed_scan_modes
    
    # Premium tier should have more access than Free
    if tier == UserTier.PREMIUM:
        free_limits = TierService.get_tier_limits(UserTier.FREE)
        assert limits.scans_per_day is None or limits.scans_per_day > free_limits.scans_per_day
        assert len(limits.allowed_scan_modes) > len(free_limits.allowed_scan_modes)
    
    # Enterprise tier should have most access
    if tier == UserTier.ENTERPRISE:
        premium_limits = TierService.get_tier_limits(UserTier.PREMIUM)
        assert len(limits.allowed_scan_modes) >= len(premium_limits.allowed_scan_modes)
        assert limits.scans_per_day is None  # Unlimited
        assert limits.scan_history_days is None  # Unlimited


# Feature: pentest-brain-web-app, Property 3: Comprehensive scan access check
# Validates: Requirements 5.1, 5.2
@pytest.mark.asyncio
@given(
    tier=st.sampled_from([UserTier.FREE, UserTier.PREMIUM, UserTier.ENTERPRISE]),
    scan_mode=st.sampled_from(["common", "full", "stealth", "aggressive", "custom"]),
    existing_scans=st.integers(min_value=0, max_value=15),
)
@hyp_settings(max_examples=100, deadline=None)
async def test_property_comprehensive_scan_access(tier, scan_mode, existing_scans, async_db_session):
    """
    Property: Comprehensive scan access check combines both mode and limit checks
    """
    # Create user with specified tier
    user = User(
        id=uuid.uuid4(),
        email=f"test_{uuid.uuid4()}@example.com",
        password_hash="hashed",
        tier=tier,
    )
    async_db_session.add(user)
    await async_db_session.commit()
    
    # Create existing scans
    now = datetime.utcnow()
    for i in range(existing_scans):
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
    
    # Check comprehensive access
    result = await TierService.check_scan_access(async_db_session, user, scan_mode)
    
    # Verify mode check
    mode_result = TierService.check_scan_mode(user, scan_mode)
    if not mode_result.allowed:
        # If mode is not allowed, comprehensive check should fail
        assert not result.allowed
        assert "not allowed" in result.reason.lower()
        return
    
    # Verify limit check (only if mode is allowed)
    limit_result = await TierService.check_scan_limit(async_db_session, user)
    assert result.allowed == limit_result.allowed
    if not limit_result.allowed:
        assert "limit" in result.reason.lower()
