"""
Unit tests for scan retention service
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from app.services.retention_service import RetentionService
from app.models.scan import Scan
from app.models.user import User


@pytest.mark.asyncio
async def test_get_retention_period_free(db_session):
    """Test getting retention period for free tier"""
    period = await RetentionService.get_retention_period("free")
    assert period == 30


@pytest.mark.asyncio
async def test_get_retention_period_premium(db_session):
    """Test getting retention period for premium tier"""
    period = await RetentionService.get_retention_period("premium")
    assert period == 365


@pytest.mark.asyncio
async def test_get_retention_period_enterprise(db_session):
    """Test getting retention period for enterprise tier (unlimited)"""
    period = await RetentionService.get_retention_period("enterprise")
    assert period is None


@pytest.mark.asyncio
async def test_get_accessible_scans_free_tier(db_session):
    """Test getting accessible scans for free tier (30 days)"""
    # Create test user
    user = User(
        id=uuid4(),
        email="test@example.com",
        hashed_password="hashed",
        tier="free"
    )
    db_session.add(user)
    await db_session.commit()
    
    # Create scans at different ages
    now = datetime.utcnow()
    scans = [
        # Within 30 days (accessible)
        Scan(id=uuid4(), user_id=user.id, target_url="https://example.com", scan_mode="common", status="completed", created_at=now - timedelta(days=10)),
        Scan(id=uuid4(), user_id=user.id, target_url="https://example.com", scan_mode="common", status="completed", created_at=now - timedelta(days=20)),
        Scan(id=uuid4(), user_id=user.id, target_url="https://example.com", scan_mode="common", status="completed", created_at=now - timedelta(days=29)),
        # Beyond 30 days (not accessible)
        Scan(id=uuid4(), user_id=user.id, target_url="https://example.com", scan_mode="common", status="completed", created_at=now - timedelta(days=31)),
        Scan(id=uuid4(), user_id=user.id, target_url="https://example.com", scan_mode="common", status="completed", created_at=now - timedelta(days=60)),
    ]
    db_session.add_all(scans)
    await db_session.commit()
    
    # Get accessible scans
    accessible = await RetentionService.get_accessible_scans(db_session, user.id, "free")
    
    assert len(accessible) == 3


@pytest.mark.asyncio
async def test_get_accessible_scans_premium_tier(db_session):
    """Test getting accessible scans for premium tier (365 days)"""
    # Create test user
    user = User(
        id=uuid4(),
        email="test@example.com",
        hashed_password="hashed",
        tier="premium"
    )
    db_session.add(user)
    await db_session.commit()
    
    # Create scans at different ages
    now = datetime.utcnow()
    scans = [
        # Within 365 days (accessible)
        Scan(id=uuid4(), user_id=user.id, target_url="https://example.com", scan_mode="common", status="completed", created_at=now - timedelta(days=100)),
        Scan(id=uuid4(), user_id=user.id, target_url="https://example.com", scan_mode="common", status="completed", created_at=now - timedelta(days=300)),
        Scan(id=uuid4(), user_id=user.id, target_url="https://example.com", scan_mode="common", status="completed", created_at=now - timedelta(days=364)),
        # Beyond 365 days (not accessible)
        Scan(id=uuid4(), user_id=user.id, target_url="https://example.com", scan_mode="common", status="completed", created_at=now - timedelta(days=366)),
        Scan(id=uuid4(), user_id=user.id, target_url="https://example.com", scan_mode="common", status="completed", created_at=now - timedelta(days=400)),
    ]
    db_session.add_all(scans)
    await db_session.commit()
    
    # Get accessible scans
    accessible = await RetentionService.get_accessible_scans(db_session, user.id, "premium")
    
    assert len(accessible) == 3


@pytest.mark.asyncio
async def test_get_accessible_scans_enterprise_tier(db_session):
    """Test getting accessible scans for enterprise tier (unlimited)"""
    # Create test user
    user = User(
        id=uuid4(),
        email="test@example.com",
        hashed_password="hashed",
        tier="enterprise"
    )
    db_session.add(user)
    await db_session.commit()
    
    # Create scans at various ages (all should be accessible)
    now = datetime.utcnow()
    scans = [
        Scan(id=uuid4(), user_id=user.id, target_url="https://example.com", scan_mode="common", status="completed", created_at=now - timedelta(days=10)),
        Scan(id=uuid4(), user_id=user.id, target_url="https://example.com", scan_mode="common", status="completed", created_at=now - timedelta(days=100)),
        Scan(id=uuid4(), user_id=user.id, target_url="https://example.com", scan_mode="common", status="completed", created_at=now - timedelta(days=400)),
        Scan(id=uuid4(), user_id=user.id, target_url="https://example.com", scan_mode="common", status="completed", created_at=now - timedelta(days=1000)),
    ]
    db_session.add_all(scans)
    await db_session.commit()
    
    # Get accessible scans (all should be returned)
    accessible = await RetentionService.get_accessible_scans(db_session, user.id, "enterprise")
    
    assert len(accessible) == 4


@pytest.mark.asyncio
async def test_archive_expired_scans_free_tier(db_session):
    """Test archiving expired scans for free tier"""
    # Create test user
    user = User(
        id=uuid4(),
        email="test@example.com",
        hashed_password="hashed",
        tier="free"
    )
    db_session.add(user)
    await db_session.commit()
    
    # Create scans
    now = datetime.utcnow()
    scans = [
        # Within 30 days (should not be archived)
        Scan(id=uuid4(), user_id=user.id, target_url="https://example.com", scan_mode="common", status="completed", created_at=now - timedelta(days=10)),
        Scan(id=uuid4(), user_id=user.id, target_url="https://example.com", scan_mode="common", status="completed", created_at=now - timedelta(days=20)),
        # Beyond 30 days (should be archived)
        Scan(id=uuid4(), user_id=user.id, target_url="https://example.com", scan_mode="common", status="completed", created_at=now - timedelta(days=31)),
        Scan(id=uuid4(), user_id=user.id, target_url="https://example.com", scan_mode="common", status="completed", created_at=now - timedelta(days=60)),
    ]
    db_session.add_all(scans)
    await db_session.commit()
    
    # Archive expired scans
    archived_count = await RetentionService.archive_expired_scans(db_session, user.id, "free")
    
    assert archived_count == 2
    
    # Verify remaining scans
    remaining = await RetentionService.get_accessible_scans(db_session, user.id, "free")
    assert len(remaining) == 2


@pytest.mark.asyncio
async def test_archive_expired_scans_enterprise_tier(db_session):
    """Test that enterprise tier scans are never archived"""
    # Create test user
    user = User(
        id=uuid4(),
        email="test@example.com",
        hashed_password="hashed",
        tier="enterprise"
    )
    db_session.add(user)
    await db_session.commit()
    
    # Create old scans
    now = datetime.utcnow()
    scans = [
        Scan(id=uuid4(), user_id=user.id, target_url="https://example.com", scan_mode="common", status="completed", created_at=now - timedelta(days=400)),
        Scan(id=uuid4(), user_id=user.id, target_url="https://example.com", scan_mode="common", status="completed", created_at=now - timedelta(days=1000)),
    ]
    db_session.add_all(scans)
    await db_session.commit()
    
    # Try to archive (should archive 0)
    archived_count = await RetentionService.archive_expired_scans(db_session, user.id, "enterprise")
    
    assert archived_count == 0
    
    # Verify all scans still accessible
    remaining = await RetentionService.get_accessible_scans(db_session, user.id, "enterprise")
    assert len(remaining) == 2


@pytest.mark.asyncio
async def test_cleanup_all_expired_scans(db_session):
    """Test cleanup for all users"""
    # Create multiple users with different tiers
    now = datetime.utcnow()
    
    # Free tier user
    user1 = User(id=uuid4(), email="free@example.com", hashed_password="hashed", tier="free")
    db_session.add(user1)
    scans1 = [
        Scan(id=uuid4(), user_id=user1.id, target_url="https://example.com", scan_mode="common", status="completed", created_at=now - timedelta(days=10)),
        Scan(id=uuid4(), user_id=user1.id, target_url="https://example.com", scan_mode="common", status="completed", created_at=now - timedelta(days=40)),  # Expired
    ]
    db_session.add_all(scans1)
    
    # Premium tier user
    user2 = User(id=uuid4(), email="premium@example.com", hashed_password="hashed", tier="premium")
    db_session.add(user2)
    scans2 = [
        Scan(id=uuid4(), user_id=user2.id, target_url="https://example.com", scan_mode="common", status="completed", created_at=now - timedelta(days=100)),
        Scan(id=uuid4(), user_id=user2.id, target_url="https://example.com", scan_mode="common", status="completed", created_at=now - timedelta(days=400)),  # Expired
    ]
    db_session.add_all(scans2)
    
    await db_session.commit()
    
    # Run cleanup
    total_archived = await RetentionService.cleanup_all_expired_scans(db_session)
    
    assert total_archived == 2


@pytest.mark.asyncio
async def test_get_scan_count_by_retention(db_session):
    """Test getting scan count statistics"""
    # Create test user
    user = User(
        id=uuid4(),
        email="test@example.com",
        hashed_password="hashed",
        tier="free"
    )
    db_session.add(user)
    await db_session.commit()
    
    # Create scans
    now = datetime.utcnow()
    scans = [
        # Accessible (within 30 days)
        Scan(id=uuid4(), user_id=user.id, target_url="https://example.com", scan_mode="common", status="completed", created_at=now - timedelta(days=10)),
        Scan(id=uuid4(), user_id=user.id, target_url="https://example.com", scan_mode="common", status="completed", created_at=now - timedelta(days=20)),
        # Expired (beyond 30 days)
        Scan(id=uuid4(), user_id=user.id, target_url="https://example.com", scan_mode="common", status="completed", created_at=now - timedelta(days=40)),
        Scan(id=uuid4(), user_id=user.id, target_url="https://example.com", scan_mode="common", status="completed", created_at=now - timedelta(days=50)),
        Scan(id=uuid4(), user_id=user.id, target_url="https://example.com", scan_mode="common", status="completed", created_at=now - timedelta(days=60)),
    ]
    db_session.add_all(scans)
    await db_session.commit()
    
    # Get statistics
    stats = await RetentionService.get_scan_count_by_retention(db_session, user.id, "free")
    
    assert stats["tier"] == "free"
    assert stats["retention_days"] == 30
    assert stats["total_scans"] == 5
    assert stats["accessible_scans"] == 2
    assert stats["expired_scans"] == 3


@pytest.mark.asyncio
async def test_restore_scans_on_upgrade(db_session):
    """Test restore scans on tier upgrade (placeholder)"""
    user_id = uuid4()
    
    # Call restore (should return 0 since we delete scans)
    restored = await RetentionService.restore_scans_on_upgrade(
        db_session, user_id, "free", "premium"
    )
    
    assert restored == 0
