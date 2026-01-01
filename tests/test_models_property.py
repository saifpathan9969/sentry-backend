"""
Property-based tests for database models
Feature: pentest-brain-web-app
"""
import pytest
from hypothesis import given, strategies as st, settings, assume
from hypothesis.strategies import composite
from sqlalchemy import select
from datetime import datetime, timedelta
import uuid

from app.models import User, Scan, Subscription, APIUsage, UserTier, ScanMode, ScanStatus, SubscriptionTier, SubscriptionStatus


# ============================================================================
# Hypothesis Strategies
# ============================================================================

@composite
def user_strategy(draw):
    """Generate random User data"""
    return {
        "email": draw(st.emails()),
        "password_hash": draw(st.text(min_size=60, max_size=60)),  # bcrypt hash length
        "full_name": draw(st.one_of(st.none(), st.text(min_size=1, max_size=100))),
        "tier": draw(st.sampled_from([UserTier.FREE, UserTier.PREMIUM, UserTier.ENTERPRISE])),
        "is_active": draw(st.booleans()),
        "email_verified": draw(st.booleans()),
    }


@composite
def scan_strategy(draw, user_id):
    """Generate random Scan data"""
    return {
        "user_id": user_id,
        "target": draw(st.from_regex(r"https?://[a-z0-9-]+\.[a-z]{2,}", fullmatch=True)),
        "scan_mode": draw(st.sampled_from([ScanMode.COMMON, ScanMode.FAST, ScanMode.FULL])),
        "status": draw(st.sampled_from([ScanStatus.QUEUED, ScanStatus.RUNNING, ScanStatus.COMPLETED, ScanStatus.FAILED])),
        "vulnerabilities_found": draw(st.integers(min_value=0, max_value=100)),
        "critical_count": draw(st.integers(min_value=0, max_value=20)),
        "high_count": draw(st.integers(min_value=0, max_value=30)),
        "medium_count": draw(st.integers(min_value=0, max_value=40)),
        "low_count": draw(st.integers(min_value=0, max_value=50)),
    }


@composite
def subscription_strategy(draw, user_id):
    """Generate random Subscription data"""
    start = datetime.utcnow()
    return {
        "user_id": user_id,
        "stripe_subscription_id": f"sub_{draw(st.text(alphabet='abcdefghijklmnopqrstuvwxyz0123456789', min_size=24, max_size=24))}",
        "stripe_customer_id": f"cus_{draw(st.text(alphabet='abcdefghijklmnopqrstuvwxyz0123456789', min_size=24, max_size=24))}",
        "tier": draw(st.sampled_from([SubscriptionTier.PREMIUM, SubscriptionTier.ENTERPRISE])),
        "status": draw(st.sampled_from([SubscriptionStatus.ACTIVE, SubscriptionStatus.CANCELED, SubscriptionStatus.PAST_DUE])),
        "current_period_start": start,
        "current_period_end": start + timedelta(days=30),
        "cancel_at_period_end": draw(st.booleans()),
    }


@composite
def api_usage_strategy(draw, user_id):
    """Generate random APIUsage data"""
    return {
        "user_id": user_id,
        "endpoint": draw(st.sampled_from(["/api/v1/scans", "/api/v1/users/me", "/api/v1/subscriptions"])),
        "method": draw(st.sampled_from(["GET", "POST", "PUT", "DELETE"])),
        "status_code": draw(st.sampled_from([200, 201, 400, 401, 403, 404, 500])),
        "response_time_ms": draw(st.integers(min_value=10, max_value=5000)),
    }


# ============================================================================
# Property Tests
# ============================================================================

@pytest.mark.property
@pytest.mark.asyncio
@given(user_data=user_strategy(), num_scans=st.integers(min_value=1, max_value=5))
@settings(max_examples=100, deadline=None)
async def test_property_cascade_delete_scans(db_session, user_data, num_scans):
    """
    Feature: pentest-brain-web-app, Property 10: Cascade deletion integrity
    
    Property: For any user being deleted, all associated scans should also be deleted
    
    Validates: Requirements 14.5
    """
    # Create user
    user = User(**user_data)
    db_session.add(user)
    await db_session.flush()
    
    # Create multiple scans for the user
    scan_ids = []
    for _ in range(num_scans):
        scan_data = scan_strategy(user.id).example()
        scan = Scan(**scan_data)
        db_session.add(scan)
        scan_ids.append(scan.id)
    
    await db_session.commit()
    
    # Verify scans exist
    result = await db_session.execute(
        select(Scan).where(Scan.user_id == user.id)
    )
    scans_before = result.scalars().all()
    assert len(scans_before) == num_scans
    
    # Delete user
    await db_session.delete(user)
    await db_session.commit()
    
    # Verify all scans are deleted (cascade)
    for scan_id in scan_ids:
        result = await db_session.execute(
            select(Scan).where(Scan.id == scan_id)
        )
        scan = result.scalar_one_or_none()
        assert scan is None, f"Scan {scan_id} should have been cascade deleted"


@pytest.mark.property
@pytest.mark.asyncio
@given(user_data=user_strategy(), num_subscriptions=st.integers(min_value=1, max_value=3))
@settings(max_examples=100, deadline=None)
async def test_property_cascade_delete_subscriptions(db_session, user_data, num_subscriptions):
    """
    Feature: pentest-brain-web-app, Property 10: Cascade deletion integrity
    
    Property: For any user being deleted, all associated subscriptions should also be deleted
    
    Validates: Requirements 14.5
    """
    # Create user
    user = User(**user_data)
    db_session.add(user)
    await db_session.flush()
    
    # Create multiple subscriptions for the user
    subscription_ids = []
    for i in range(num_subscriptions):
        sub_data = subscription_strategy(user.id).example()
        # Ensure unique stripe IDs
        sub_data["stripe_subscription_id"] = f"sub_test_{uuid.uuid4().hex}"
        subscription = Subscription(**sub_data)
        db_session.add(subscription)
        subscription_ids.append(subscription.id)
    
    await db_session.commit()
    
    # Verify subscriptions exist
    result = await db_session.execute(
        select(Subscription).where(Subscription.user_id == user.id)
    )
    subs_before = result.scalars().all()
    assert len(subs_before) == num_subscriptions
    
    # Delete user
    await db_session.delete(user)
    await db_session.commit()
    
    # Verify all subscriptions are deleted (cascade)
    for sub_id in subscription_ids:
        result = await db_session.execute(
            select(Subscription).where(Subscription.id == sub_id)
        )
        subscription = result.scalar_one_or_none()
        assert subscription is None, f"Subscription {sub_id} should have been cascade deleted"


@pytest.mark.property
@pytest.mark.asyncio
@given(user_data=user_strategy(), num_api_usage=st.integers(min_value=1, max_value=10))
@settings(max_examples=100, deadline=None)
async def test_property_cascade_delete_api_usage(db_session, user_data, num_api_usage):
    """
    Feature: pentest-brain-web-app, Property 10: Cascade deletion integrity
    
    Property: For any user being deleted, all associated API usage records should also be deleted
    
    Validates: Requirements 14.5
    """
    # Create user
    user = User(**user_data)
    db_session.add(user)
    await db_session.flush()
    
    # Create multiple API usage records for the user
    usage_ids = []
    for _ in range(num_api_usage):
        usage_data = api_usage_strategy(user.id).example()
        usage = APIUsage(**usage_data)
        db_session.add(usage)
        usage_ids.append(usage.id)
    
    await db_session.commit()
    
    # Verify API usage records exist
    result = await db_session.execute(
        select(APIUsage).where(APIUsage.user_id == user.id)
    )
    usage_before = result.scalars().all()
    assert len(usage_before) == num_api_usage
    
    # Delete user
    await db_session.delete(user)
    await db_session.commit()
    
    # Verify all API usage records are deleted (cascade)
    for usage_id in usage_ids:
        result = await db_session.execute(
            select(APIUsage).where(APIUsage.id == usage_id)
        )
        usage = result.scalar_one_or_none()
        assert usage is None, f"APIUsage {usage_id} should have been cascade deleted"


@pytest.mark.property
@pytest.mark.asyncio
@given(
    user_data=user_strategy(),
    num_scans=st.integers(min_value=1, max_value=3),
    num_subscriptions=st.integers(min_value=1, max_value=2),
    num_api_usage=st.integers(min_value=1, max_value=5)
)
@settings(max_examples=50, deadline=None)
async def test_property_cascade_delete_all_relations(db_session, user_data, num_scans, num_subscriptions, num_api_usage):
    """
    Feature: pentest-brain-web-app, Property 10: Cascade deletion integrity
    
    Property: For any user being deleted, ALL associated records (scans, subscriptions, API usage) 
    should be deleted from the database
    
    Validates: Requirements 14.5
    """
    # Create user
    user = User(**user_data)
    db_session.add(user)
    await db_session.flush()
    
    # Create scans
    for _ in range(num_scans):
        scan_data = scan_strategy(user.id).example()
        db_session.add(Scan(**scan_data))
    
    # Create subscriptions
    for i in range(num_subscriptions):
        sub_data = subscription_strategy(user.id).example()
        sub_data["stripe_subscription_id"] = f"sub_cascade_{uuid.uuid4().hex}"
        db_session.add(Subscription(**sub_data))
    
    # Create API usage records
    for _ in range(num_api_usage):
        usage_data = api_usage_strategy(user.id).example()
        db_session.add(APIUsage(**usage_data))
    
    await db_session.commit()
    
    # Verify all records exist
    scans_result = await db_session.execute(select(Scan).where(Scan.user_id == user.id))
    assert len(scans_result.scalars().all()) == num_scans
    
    subs_result = await db_session.execute(select(Subscription).where(Subscription.user_id == user.id))
    assert len(subs_result.scalars().all()) == num_subscriptions
    
    usage_result = await db_session.execute(select(APIUsage).where(APIUsage.user_id == user.id))
    assert len(usage_result.scalars().all()) == num_api_usage
    
    # Delete user
    await db_session.delete(user)
    await db_session.commit()
    
    # Verify ALL related records are deleted
    scans_after = await db_session.execute(select(Scan).where(Scan.user_id == user.id))
    assert len(scans_after.scalars().all()) == 0, "All scans should be cascade deleted"
    
    subs_after = await db_session.execute(select(Subscription).where(Subscription.user_id == user.id))
    assert len(subs_after.scalars().all()) == 0, "All subscriptions should be cascade deleted"
    
    usage_after = await db_session.execute(select(APIUsage).where(APIUsage.user_id == user.id))
    assert len(usage_after.scalars().all()) == 0, "All API usage records should be cascade deleted"
