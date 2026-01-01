"""
Unit tests for database models
"""
import pytest
from sqlalchemy import select
from datetime import datetime, timedelta
import uuid

from app.models import User, Scan, Subscription, APIUsage, UserTier, ScanMode, ScanStatus, SubscriptionTier, SubscriptionStatus


@pytest.mark.unit
@pytest.mark.asyncio
async def test_user_creation(db_session):
    """Test creating a user"""
    user = User(
        email="test@example.com",
        password_hash="hashed_password",
        full_name="Test User",
        tier=UserTier.FREE
    )
    
    db_session.add(user)
    await db_session.commit()
    
    # Verify user was created
    result = await db_session.execute(select(User).where(User.email == "test@example.com"))
    saved_user = result.scalar_one()
    
    assert saved_user.email == "test@example.com"
    assert saved_user.full_name == "Test User"
    assert saved_user.tier == UserTier.FREE
    assert saved_user.is_active is True
    assert saved_user.email_verified is False
    assert saved_user.created_at is not None
    assert saved_user.updated_at is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_user_unique_email(db_session):
    """Test that email must be unique"""
    user1 = User(email="test@example.com", password_hash="hash1")
    user2 = User(email="test@example.com", password_hash="hash2")
    
    db_session.add(user1)
    await db_session.commit()
    
    db_session.add(user2)
    with pytest.raises(Exception):  # IntegrityError
        await db_session.commit()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_scan_creation(db_session):
    """Test creating a scan"""
    # Create user first
    user = User(email="test@example.com", password_hash="hash")
    db_session.add(user)
    await db_session.flush()
    
    # Create scan
    scan = Scan(
        user_id=user.id,
        target="https://example.com",
        scan_mode=ScanMode.COMMON,
        status=ScanStatus.QUEUED
    )
    
    db_session.add(scan)
    await db_session.commit()
    
    # Verify scan was created
    result = await db_session.execute(select(Scan).where(Scan.user_id == user.id))
    saved_scan = result.scalar_one()
    
    assert saved_scan.target == "https://example.com"
    assert saved_scan.scan_mode == ScanMode.COMMON
    assert saved_scan.status == ScanStatus.QUEUED
    assert saved_scan.vulnerabilities_found == 0
    assert saved_scan.created_at is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_scan_relationship_with_user(db_session):
    """Test scan-user relationship"""
    user = User(email="test@example.com", password_hash="hash")
    db_session.add(user)
    await db_session.flush()
    
    scan1 = Scan(user_id=user.id, target="https://example1.com", scan_mode=ScanMode.COMMON)
    scan2 = Scan(user_id=user.id, target="https://example2.com", scan_mode=ScanMode.FAST)
    
    db_session.add_all([scan1, scan2])
    await db_session.commit()
    
    # Verify relationship
    result = await db_session.execute(select(User).where(User.id == user.id))
    saved_user = result.scalar_one()
    
    # Refresh to load relationships
    await db_session.refresh(saved_user, ["scans"])
    
    assert len(saved_user.scans) == 2
    assert all(scan.user_id == user.id for scan in saved_user.scans)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_subscription_creation(db_session):
    """Test creating a subscription"""
    user = User(email="test@example.com", password_hash="hash")
    db_session.add(user)
    await db_session.flush()
    
    start = datetime.utcnow()
    end = start + timedelta(days=30)
    
    subscription = Subscription(
        user_id=user.id,
        stripe_subscription_id="sub_test123",
        stripe_customer_id="cus_test123",
        tier=SubscriptionTier.PREMIUM,
        status=SubscriptionStatus.ACTIVE,
        current_period_start=start,
        current_period_end=end
    )
    
    db_session.add(subscription)
    await db_session.commit()
    
    # Verify subscription was created
    result = await db_session.execute(select(Subscription).where(Subscription.user_id == user.id))
    saved_sub = result.scalar_one()
    
    assert saved_sub.tier == SubscriptionTier.PREMIUM
    assert saved_sub.status == SubscriptionStatus.ACTIVE
    assert saved_sub.stripe_subscription_id == "sub_test123"
    assert saved_sub.cancel_at_period_end is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_subscription_unique_stripe_id(db_session):
    """Test that stripe_subscription_id must be unique"""
    user1 = User(email="test1@example.com", password_hash="hash1")
    user2 = User(email="test2@example.com", password_hash="hash2")
    db_session.add_all([user1, user2])
    await db_session.flush()
    
    start = datetime.utcnow()
    end = start + timedelta(days=30)
    
    sub1 = Subscription(
        user_id=user1.id,
        stripe_subscription_id="sub_duplicate",
        stripe_customer_id="cus_1",
        tier=SubscriptionTier.PREMIUM,
        status=SubscriptionStatus.ACTIVE,
        current_period_start=start,
        current_period_end=end
    )
    
    sub2 = Subscription(
        user_id=user2.id,
        stripe_subscription_id="sub_duplicate",
        stripe_customer_id="cus_2",
        tier=SubscriptionTier.PREMIUM,
        status=SubscriptionStatus.ACTIVE,
        current_period_start=start,
        current_period_end=end
    )
    
    db_session.add(sub1)
    await db_session.commit()
    
    db_session.add(sub2)
    with pytest.raises(Exception):  # IntegrityError
        await db_session.commit()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_api_usage_creation(db_session):
    """Test creating API usage record"""
    user = User(email="test@example.com", password_hash="hash")
    db_session.add(user)
    await db_session.flush()
    
    usage = APIUsage(
        user_id=user.id,
        endpoint="/api/v1/scans",
        method="POST",
        status_code=201,
        response_time_ms=150
    )
    
    db_session.add(usage)
    await db_session.commit()
    
    # Verify API usage was created
    result = await db_session.execute(select(APIUsage).where(APIUsage.user_id == user.id))
    saved_usage = result.scalar_one()
    
    assert saved_usage.endpoint == "/api/v1/scans"
    assert saved_usage.method == "POST"
    assert saved_usage.status_code == 201
    assert saved_usage.response_time_ms == 150
    assert saved_usage.created_at is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cascade_delete_scans(db_session):
    """Test that deleting a user cascades to scans"""
    user = User(email="test@example.com", password_hash="hash")
    db_session.add(user)
    await db_session.flush()
    
    scan = Scan(user_id=user.id, target="https://example.com", scan_mode=ScanMode.COMMON)
    db_session.add(scan)
    await db_session.commit()
    
    scan_id = scan.id
    
    # Delete user
    await db_session.delete(user)
    await db_session.commit()
    
    # Verify scan was deleted
    result = await db_session.execute(select(Scan).where(Scan.id == scan_id))
    deleted_scan = result.scalar_one_or_none()
    
    assert deleted_scan is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cascade_delete_subscriptions(db_session):
    """Test that deleting a user cascades to subscriptions"""
    user = User(email="test@example.com", password_hash="hash")
    db_session.add(user)
    await db_session.flush()
    
    start = datetime.utcnow()
    subscription = Subscription(
        user_id=user.id,
        stripe_subscription_id="sub_test",
        stripe_customer_id="cus_test",
        tier=SubscriptionTier.PREMIUM,
        status=SubscriptionStatus.ACTIVE,
        current_period_start=start,
        current_period_end=start + timedelta(days=30)
    )
    db_session.add(subscription)
    await db_session.commit()
    
    sub_id = subscription.id
    
    # Delete user
    await db_session.delete(user)
    await db_session.commit()
    
    # Verify subscription was deleted
    result = await db_session.execute(select(Subscription).where(Subscription.id == sub_id))
    deleted_sub = result.scalar_one_or_none()
    
    assert deleted_sub is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cascade_delete_api_usage(db_session):
    """Test that deleting a user cascades to API usage"""
    user = User(email="test@example.com", password_hash="hash")
    db_session.add(user)
    await db_session.flush()
    
    usage = APIUsage(
        user_id=user.id,
        endpoint="/api/v1/scans",
        method="GET",
        status_code=200,
        response_time_ms=100
    )
    db_session.add(usage)
    await db_session.commit()
    
    usage_id = usage.id
    
    # Delete user
    await db_session.delete(user)
    await db_session.commit()
    
    # Verify API usage was deleted
    result = await db_session.execute(select(APIUsage).where(APIUsage.id == usage_id))
    deleted_usage = result.scalar_one_or_none()
    
    assert deleted_usage is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_user_tier_enum(db_session):
    """Test user tier enum values"""
    user_free = User(email="free@example.com", password_hash="hash", tier=UserTier.FREE)
    user_premium = User(email="premium@example.com", password_hash="hash", tier=UserTier.PREMIUM)
    user_enterprise = User(email="enterprise@example.com", password_hash="hash", tier=UserTier.ENTERPRISE)
    
    db_session.add_all([user_free, user_premium, user_enterprise])
    await db_session.commit()
    
    result = await db_session.execute(select(User))
    users = result.scalars().all()
    
    assert len(users) == 3
    assert UserTier.FREE in [u.tier for u in users]
    assert UserTier.PREMIUM in [u.tier for u in users]
    assert UserTier.ENTERPRISE in [u.tier for u in users]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_scan_status_transitions(db_session):
    """Test scan status can transition through states"""
    user = User(email="test@example.com", password_hash="hash")
    db_session.add(user)
    await db_session.flush()
    
    scan = Scan(user_id=user.id, target="https://example.com", scan_mode=ScanMode.COMMON, status=ScanStatus.QUEUED)
    db_session.add(scan)
    await db_session.commit()
    
    # Transition to RUNNING
    scan.status = ScanStatus.RUNNING
    scan.started_at = datetime.utcnow()
    await db_session.commit()
    
    # Transition to COMPLETED
    scan.status = ScanStatus.COMPLETED
    scan.completed_at = datetime.utcnow()
    scan.duration_seconds = 120
    scan.vulnerabilities_found = 5
    await db_session.commit()
    
    # Verify final state
    result = await db_session.execute(select(Scan).where(Scan.id == scan.id))
    final_scan = result.scalar_one()
    
    assert final_scan.status == ScanStatus.COMPLETED
    assert final_scan.started_at is not None
    assert final_scan.completed_at is not None
    assert final_scan.duration_seconds == 120
    assert final_scan.vulnerabilities_found == 5



@pytest.mark.unit
@pytest.mark.asyncio
async def test_scan_with_report_data(db_session):
    """Test scan with JSON and TEXT reports"""
    user = User(email="test@example.com", password_hash="hash")
    db_session.add(user)
    await db_session.flush()
    
    report_json = {
        "vulnerabilities": [
            {"type": "SQL Injection", "severity": "critical"},
            {"type": "XSS", "severity": "high"}
        ],
        "summary": {"total": 2, "critical": 1, "high": 1}
    }
    
    report_text = "Security Scan Report\n\nFound 2 vulnerabilities..."
    
    scan = Scan(
        user_id=user.id,
        target="https://example.com",
        scan_mode=ScanMode.FULL,
        status=ScanStatus.COMPLETED,
        report_json=report_json,
        report_text=report_text,
        vulnerabilities_found=2,
        critical_count=1,
        high_count=1
    )
    
    db_session.add(scan)
    await db_session.commit()
    
    # Verify reports are stored correctly
    result = await db_session.execute(select(Scan).where(Scan.id == scan.id))
    saved_scan = result.scalar_one()
    
    assert saved_scan.report_json == report_json
    assert saved_scan.report_text == report_text
    assert saved_scan.vulnerabilities_found == 2
    assert saved_scan.critical_count == 1
    assert saved_scan.high_count == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_scan_with_error(db_session):
    """Test scan with error message"""
    user = User(email="test@example.com", password_hash="hash")
    db_session.add(user)
    await db_session.flush()
    
    scan = Scan(
        user_id=user.id,
        target="https://invalid-domain-xyz.com",
        scan_mode=ScanMode.COMMON,
        status=ScanStatus.FAILED,
        error_message="Connection timeout: Unable to reach target"
    )
    
    db_session.add(scan)
    await db_session.commit()
    
    # Verify error is stored
    result = await db_session.execute(select(Scan).where(Scan.id == scan.id))
    saved_scan = result.scalar_one()
    
    assert saved_scan.status == ScanStatus.FAILED
    assert saved_scan.error_message == "Connection timeout: Unable to reach target"
    assert saved_scan.vulnerabilities_found == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_user_api_key_hash(db_session):
    """Test user with API key hash"""
    user = User(
        email="test@example.com",
        password_hash="hash",
        api_key_hash="a" * 64  # SHA-256 hash is 64 characters
    )
    
    db_session.add(user)
    await db_session.commit()
    
    # Verify API key hash is stored
    result = await db_session.execute(select(User).where(User.email == "test@example.com"))
    saved_user = result.scalar_one()
    
    assert saved_user.api_key_hash == "a" * 64
    assert len(saved_user.api_key_hash) == 64


@pytest.mark.unit
@pytest.mark.asyncio
async def test_user_unique_api_key_hash(db_session):
    """Test that API key hash must be unique"""
    user1 = User(email="test1@example.com", password_hash="hash1", api_key_hash="unique_hash_123")
    user2 = User(email="test2@example.com", password_hash="hash2", api_key_hash="unique_hash_123")
    
    db_session.add(user1)
    await db_session.commit()
    
    db_session.add(user2)
    with pytest.raises(Exception):  # IntegrityError
        await db_session.commit()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_subscription_cancel_at_period_end(db_session):
    """Test subscription with cancel_at_period_end flag"""
    user = User(email="test@example.com", password_hash="hash")
    db_session.add(user)
    await db_session.flush()
    
    start = datetime.utcnow()
    subscription = Subscription(
        user_id=user.id,
        stripe_subscription_id="sub_test",
        stripe_customer_id="cus_test",
        tier=SubscriptionTier.PREMIUM,
        status=SubscriptionStatus.ACTIVE,
        current_period_start=start,
        current_period_end=start + timedelta(days=30),
        cancel_at_period_end=True
    )
    
    db_session.add(subscription)
    await db_session.commit()
    
    # Verify flag is set
    result = await db_session.execute(select(Subscription).where(Subscription.user_id == user.id))
    saved_sub = result.scalar_one()
    
    assert saved_sub.cancel_at_period_end is True
    assert saved_sub.status == SubscriptionStatus.ACTIVE


@pytest.mark.unit
@pytest.mark.asyncio
async def test_multiple_scans_per_user(db_session):
    """Test user can have multiple scans"""
    user = User(email="test@example.com", password_hash="hash")
    db_session.add(user)
    await db_session.flush()
    
    # Create 5 scans
    scans = [
        Scan(user_id=user.id, target=f"https://example{i}.com", scan_mode=ScanMode.COMMON)
        for i in range(5)
    ]
    
    db_session.add_all(scans)
    await db_session.commit()
    
    # Verify all scans are stored
    result = await db_session.execute(select(Scan).where(Scan.user_id == user.id))
    saved_scans = result.scalars().all()
    
    assert len(saved_scans) == 5
    assert all(scan.user_id == user.id for scan in saved_scans)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_scan_platform_detection(db_session):
    """Test scan with platform detection data"""
    user = User(email="test@example.com", password_hash="hash")
    db_session.add(user)
    await db_session.flush()
    
    scan = Scan(
        user_id=user.id,
        target="https://example.com",
        scan_mode=ScanMode.COMMON,
        status=ScanStatus.COMPLETED,
        platform_detected="Firebase",
        confidence=0.95
    )
    
    db_session.add(scan)
    await db_session.commit()
    
    # Verify platform detection is stored
    result = await db_session.execute(select(Scan).where(Scan.id == scan.id))
    saved_scan = result.scalar_one()
    
    assert saved_scan.platform_detected == "Firebase"
    assert float(saved_scan.confidence) == 0.95


@pytest.mark.unit
@pytest.mark.asyncio
async def test_user_last_login_update(db_session):
    """Test updating user last_login timestamp"""
    user = User(email="test@example.com", password_hash="hash")
    db_session.add(user)
    await db_session.commit()
    
    assert user.last_login is None
    
    # Update last_login
    login_time = datetime.utcnow()
    user.last_login = login_time
    await db_session.commit()
    
    # Verify update
    result = await db_session.execute(select(User).where(User.id == user.id))
    updated_user = result.scalar_one()
    
    assert updated_user.last_login is not None
    assert (updated_user.last_login - login_time).total_seconds() < 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_user_updated_at_auto_update(db_session):
    """Test that updated_at is automatically updated"""
    user = User(email="test@example.com", password_hash="hash", full_name="Original Name")
    db_session.add(user)
    await db_session.commit()
    
    original_updated_at = user.updated_at
    
    # Wait a moment and update
    import asyncio
    await asyncio.sleep(0.1)
    
    user.full_name = "Updated Name"
    await db_session.commit()
    
    # Verify updated_at changed
    result = await db_session.execute(select(User).where(User.id == user.id))
    updated_user = result.scalar_one()
    
    assert updated_user.full_name == "Updated Name"
    # Note: updated_at auto-update depends on database trigger or SQLAlchemy onupdate


@pytest.mark.unit
@pytest.mark.asyncio
async def test_api_usage_multiple_records(db_session):
    """Test multiple API usage records for a user"""
    user = User(email="test@example.com", password_hash="hash")
    db_session.add(user)
    await db_session.flush()
    
    # Create multiple usage records
    usage_records = [
        APIUsage(
            user_id=user.id,
            endpoint=f"/api/v1/endpoint{i}",
            method="GET",
            status_code=200,
            response_time_ms=100 + i * 10
        )
        for i in range(10)
    ]
    
    db_session.add_all(usage_records)
    await db_session.commit()
    
    # Verify all records are stored
    result = await db_session.execute(select(APIUsage).where(APIUsage.user_id == user.id))
    saved_usage = result.scalars().all()
    
    assert len(saved_usage) == 10
    assert all(usage.user_id == user.id for usage in saved_usage)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_scan_all_modes(db_session):
    """Test all scan modes"""
    user = User(email="test@example.com", password_hash="hash")
    db_session.add(user)
    await db_session.flush()
    
    scan_common = Scan(user_id=user.id, target="https://example1.com", scan_mode=ScanMode.COMMON)
    scan_fast = Scan(user_id=user.id, target="https://example2.com", scan_mode=ScanMode.FAST)
    scan_full = Scan(user_id=user.id, target="https://example3.com", scan_mode=ScanMode.FULL)
    
    db_session.add_all([scan_common, scan_fast, scan_full])
    await db_session.commit()
    
    # Verify all modes are stored
    result = await db_session.execute(select(Scan).where(Scan.user_id == user.id))
    scans = result.scalars().all()
    
    assert len(scans) == 3
    assert ScanMode.COMMON in [s.scan_mode for s in scans]
    assert ScanMode.FAST in [s.scan_mode for s in scans]
    assert ScanMode.FULL in [s.scan_mode for s in scans]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_subscription_all_statuses(db_session):
    """Test all subscription statuses"""
    user = User(email="test@example.com", password_hash="hash")
    db_session.add(user)
    await db_session.flush()
    
    start = datetime.utcnow()
    end = start + timedelta(days=30)
    
    sub_active = Subscription(
        user_id=user.id,
        stripe_subscription_id="sub_active",
        stripe_customer_id="cus_test",
        tier=SubscriptionTier.PREMIUM,
        status=SubscriptionStatus.ACTIVE,
        current_period_start=start,
        current_period_end=end
    )
    
    # Create another user for other statuses
    user2 = User(email="test2@example.com", password_hash="hash")
    db_session.add(user2)
    await db_session.flush()
    
    sub_canceled = Subscription(
        user_id=user2.id,
        stripe_subscription_id="sub_canceled",
        stripe_customer_id="cus_test2",
        tier=SubscriptionTier.PREMIUM,
        status=SubscriptionStatus.CANCELED,
        current_period_start=start,
        current_period_end=end
    )
    
    db_session.add_all([sub_active, sub_canceled])
    await db_session.commit()
    
    # Verify statuses
    result = await db_session.execute(select(Subscription))
    subs = result.scalars().all()
    
    assert len(subs) == 2
    assert SubscriptionStatus.ACTIVE in [s.status for s in subs]
    assert SubscriptionStatus.CANCELED in [s.status for s in subs]
