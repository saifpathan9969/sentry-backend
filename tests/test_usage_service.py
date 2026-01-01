"""
Unit tests for usage tracking service
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from app.services.usage_service import UsageService
from app.models.api_usage import APIUsage
from app.models.scan import Scan
from app.models.user import User


@pytest.mark.asyncio
async def test_get_scan_count(db_session):
    """Test getting scan count for user in date range"""
    # Create test user
    user = User(
        id=uuid4(),
        email="test@example.com",
        hashed_password="hashed",
        tier="free"
    )
    db_session.add(user)
    await db_session.commit()
    
    # Create scans at different times
    now = datetime.utcnow()
    scans = [
        Scan(
            id=uuid4(),
            user_id=user.id,
            target_url="https://example.com",
            scan_mode="common",
            status="completed",
            created_at=now - timedelta(days=i)
        )
        for i in range(5)
    ]
    db_session.add_all(scans)
    await db_session.commit()
    
    # Test scan count for last 3 days
    start_date = now - timedelta(days=3)
    end_date = now
    count = await UsageService.get_scan_count(db_session, user.id, start_date, end_date)
    
    assert count == 4  # Days 0, 1, 2, 3


@pytest.mark.asyncio
async def test_get_scan_count_empty(db_session):
    """Test getting scan count when no scans exist"""
    user_id = uuid4()
    now = datetime.utcnow()
    start_date = now - timedelta(days=30)
    end_date = now
    
    count = await UsageService.get_scan_count(db_session, user_id, start_date, end_date)
    
    assert count == 0


@pytest.mark.asyncio
async def test_get_api_call_count(db_session):
    """Test getting API call count for user in date range"""
    # Create test user
    user = User(
        id=uuid4(),
        email="test@example.com",
        hashed_password="hashed",
        tier="free"
    )
    db_session.add(user)
    await db_session.commit()
    
    # Create API usage records
    now = datetime.utcnow()
    usage_records = [
        APIUsage(
            id=uuid4(),
            user_id=user.id,
            endpoint="/api/v1/scans",
            method="GET",
            status_code=200,
            response_time_ms=100,
            created_at=now - timedelta(hours=i)
        )
        for i in range(10)
    ]
    db_session.add_all(usage_records)
    await db_session.commit()
    
    # Test API call count for last 5 hours
    start_date = now - timedelta(hours=5)
    end_date = now
    count = await UsageService.get_api_call_count(db_session, user.id, start_date, end_date)
    
    assert count == 6  # Hours 0, 1, 2, 3, 4, 5


@pytest.mark.asyncio
async def test_get_api_call_count_empty(db_session):
    """Test getting API call count when no calls exist"""
    user_id = uuid4()
    now = datetime.utcnow()
    start_date = now - timedelta(days=30)
    end_date = now
    
    count = await UsageService.get_api_call_count(db_session, user_id, start_date, end_date)
    
    assert count == 0


@pytest.mark.asyncio
async def test_get_scans_by_day(db_session):
    """Test getting scan count grouped by day"""
    # Create test user
    user = User(
        id=uuid4(),
        email="test@example.com",
        hashed_password="hashed",
        tier="free"
    )
    db_session.add(user)
    await db_session.commit()
    
    # Create scans on different days
    now = datetime.utcnow()
    scans = [
        # 3 scans today
        Scan(id=uuid4(), user_id=user.id, target_url="https://example.com", scan_mode="common", status="completed", created_at=now),
        Scan(id=uuid4(), user_id=user.id, target_url="https://example.com", scan_mode="common", status="completed", created_at=now - timedelta(hours=1)),
        Scan(id=uuid4(), user_id=user.id, target_url="https://example.com", scan_mode="common", status="completed", created_at=now - timedelta(hours=2)),
        # 2 scans yesterday
        Scan(id=uuid4(), user_id=user.id, target_url="https://example.com", scan_mode="common", status="completed", created_at=now - timedelta(days=1)),
        Scan(id=uuid4(), user_id=user.id, target_url="https://example.com", scan_mode="common", status="completed", created_at=now - timedelta(days=1, hours=1)),
    ]
    db_session.add_all(scans)
    await db_session.commit()
    
    # Get scans by day
    start_date = now - timedelta(days=2)
    end_date = now
    scans_by_day = await UsageService.get_scans_by_day(db_session, user.id, start_date, end_date)
    
    assert len(scans_by_day) == 2
    assert scans_by_day[0]["count"] == 2  # Yesterday
    assert scans_by_day[1]["count"] == 3  # Today


@pytest.mark.asyncio
async def test_get_scans_by_day_empty(db_session):
    """Test getting scans by day when no scans exist"""
    user_id = uuid4()
    now = datetime.utcnow()
    start_date = now - timedelta(days=30)
    end_date = now
    
    scans_by_day = await UsageService.get_scans_by_day(db_session, user_id, start_date, end_date)
    
    assert scans_by_day == []


@pytest.mark.asyncio
async def test_get_calls_by_endpoint(db_session):
    """Test getting API call count grouped by endpoint"""
    # Create test user
    user = User(
        id=uuid4(),
        email="test@example.com",
        hashed_password="hashed",
        tier="free"
    )
    db_session.add(user)
    await db_session.commit()
    
    # Create API usage records for different endpoints
    now = datetime.utcnow()
    usage_records = [
        # 5 calls to /api/v1/scans
        *[APIUsage(id=uuid4(), user_id=user.id, endpoint="/api/v1/scans", method="GET", status_code=200, response_time_ms=100, created_at=now) for _ in range(5)],
        # 3 calls to /api/v1/scans/{id}
        *[APIUsage(id=uuid4(), user_id=user.id, endpoint="/api/v1/scans/123", method="GET", status_code=200, response_time_ms=100, created_at=now) for _ in range(3)],
        # 2 calls to /api/v1/users/me
        *[APIUsage(id=uuid4(), user_id=user.id, endpoint="/api/v1/users/me", method="GET", status_code=200, response_time_ms=100, created_at=now) for _ in range(2)],
    ]
    db_session.add_all(usage_records)
    await db_session.commit()
    
    # Get calls by endpoint
    start_date = now - timedelta(days=1)
    end_date = now
    calls_by_endpoint = await UsageService.get_calls_by_endpoint(db_session, user.id, start_date, end_date)
    
    assert len(calls_by_endpoint) == 3
    assert calls_by_endpoint[0]["endpoint"] == "/api/v1/scans"
    assert calls_by_endpoint[0]["count"] == 5
    assert calls_by_endpoint[1]["endpoint"] == "/api/v1/scans/123"
    assert calls_by_endpoint[1]["count"] == 3
    assert calls_by_endpoint[2]["endpoint"] == "/api/v1/users/me"
    assert calls_by_endpoint[2]["count"] == 2


@pytest.mark.asyncio
async def test_get_calls_by_endpoint_limit(db_session):
    """Test getting API calls by endpoint with limit"""
    # Create test user
    user = User(
        id=uuid4(),
        email="test@example.com",
        hashed_password="hashed",
        tier="free"
    )
    db_session.add(user)
    await db_session.commit()
    
    # Create API usage records for many endpoints
    now = datetime.utcnow()
    usage_records = []
    for i in range(15):
        usage_records.append(
            APIUsage(
                id=uuid4(),
                user_id=user.id,
                endpoint=f"/api/v1/endpoint{i}",
                method="GET",
                status_code=200,
                response_time_ms=100,
                created_at=now
            )
        )
    db_session.add_all(usage_records)
    await db_session.commit()
    
    # Get calls by endpoint with limit
    start_date = now - timedelta(days=1)
    end_date = now
    calls_by_endpoint = await UsageService.get_calls_by_endpoint(db_session, user.id, start_date, end_date, limit=5)
    
    assert len(calls_by_endpoint) == 5


@pytest.mark.asyncio
async def test_get_average_response_time(db_session):
    """Test getting average response time"""
    # Create test user
    user = User(
        id=uuid4(),
        email="test@example.com",
        hashed_password="hashed",
        tier="free"
    )
    db_session.add(user)
    await db_session.commit()
    
    # Create API usage records with different response times
    now = datetime.utcnow()
    usage_records = [
        APIUsage(id=uuid4(), user_id=user.id, endpoint="/api/v1/scans", method="GET", status_code=200, response_time_ms=100, created_at=now),
        APIUsage(id=uuid4(), user_id=user.id, endpoint="/api/v1/scans", method="GET", status_code=200, response_time_ms=200, created_at=now),
        APIUsage(id=uuid4(), user_id=user.id, endpoint="/api/v1/scans", method="GET", status_code=200, response_time_ms=300, created_at=now),
    ]
    db_session.add_all(usage_records)
    await db_session.commit()
    
    # Get average response time
    start_date = now - timedelta(days=1)
    end_date = now
    avg_time = await UsageService.get_average_response_time(db_session, user.id, start_date, end_date)
    
    assert avg_time == 200.0


@pytest.mark.asyncio
async def test_get_average_response_time_empty(db_session):
    """Test getting average response time when no calls exist"""
    user_id = uuid4()
    now = datetime.utcnow()
    start_date = now - timedelta(days=30)
    end_date = now
    
    avg_time = await UsageService.get_average_response_time(db_session, user_id, start_date, end_date)
    
    assert avg_time == 0.0


@pytest.mark.asyncio
async def test_get_today_scan_count(db_session):
    """Test getting scan count for today"""
    # Create test user
    user = User(
        id=uuid4(),
        email="test@example.com",
        hashed_password="hashed",
        tier="free"
    )
    db_session.add(user)
    await db_session.commit()
    
    # Create scans today and yesterday
    now = datetime.utcnow()
    scans = [
        # 3 scans today
        Scan(id=uuid4(), user_id=user.id, target_url="https://example.com", scan_mode="common", status="completed", created_at=now),
        Scan(id=uuid4(), user_id=user.id, target_url="https://example.com", scan_mode="common", status="completed", created_at=now - timedelta(hours=1)),
        Scan(id=uuid4(), user_id=user.id, target_url="https://example.com", scan_mode="common", status="completed", created_at=now - timedelta(hours=2)),
        # 2 scans yesterday (should not be counted)
        Scan(id=uuid4(), user_id=user.id, target_url="https://example.com", scan_mode="common", status="completed", created_at=now - timedelta(days=1)),
        Scan(id=uuid4(), user_id=user.id, target_url="https://example.com", scan_mode="common", status="completed", created_at=now - timedelta(days=1, hours=1)),
    ]
    db_session.add_all(scans)
    await db_session.commit()
    
    # Get today's scan count
    count = await UsageService.get_today_scan_count(db_session, user.id)
    
    assert count == 3


@pytest.mark.asyncio
async def test_get_month_api_call_count(db_session):
    """Test getting API call count for current month"""
    # Create test user
    user = User(
        id=uuid4(),
        email="test@example.com",
        hashed_password="hashed",
        tier="free"
    )
    db_session.add(user)
    await db_session.commit()
    
    # Create API usage records this month and last month
    now = datetime.utcnow()
    usage_records = [
        # 5 calls this month
        *[APIUsage(id=uuid4(), user_id=user.id, endpoint="/api/v1/scans", method="GET", status_code=200, response_time_ms=100, created_at=now - timedelta(days=i)) for i in range(5)],
        # 3 calls last month (should not be counted)
        *[APIUsage(id=uuid4(), user_id=user.id, endpoint="/api/v1/scans", method="GET", status_code=200, response_time_ms=100, created_at=now - timedelta(days=35 + i)) for i in range(3)],
    ]
    db_session.add_all(usage_records)
    await db_session.commit()
    
    # Get this month's API call count
    count = await UsageService.get_month_api_call_count(db_session, user.id)
    
    assert count == 5


@pytest.mark.asyncio
async def test_get_user_statistics(db_session):
    """Test getting comprehensive user statistics"""
    # Create test user
    user = User(
        id=uuid4(),
        email="test@example.com",
        hashed_password="hashed",
        tier="free"
    )
    db_session.add(user)
    await db_session.commit()
    
    # Create scans and API usage records
    now = datetime.utcnow()
    scans = [
        Scan(id=uuid4(), user_id=user.id, target_url="https://example.com", scan_mode="common", status="completed", created_at=now - timedelta(days=i))
        for i in range(5)
    ]
    usage_records = [
        APIUsage(id=uuid4(), user_id=user.id, endpoint="/api/v1/scans", method="GET", status_code=200, response_time_ms=100 + i * 10, created_at=now - timedelta(days=i))
        for i in range(10)
    ]
    db_session.add_all(scans + usage_records)
    await db_session.commit()
    
    # Get user statistics
    stats = await UsageService.get_user_statistics(db_session, user.id, days=30)
    
    assert stats["user_id"] == str(user.id)
    assert stats["period_days"] == 30
    assert stats["scan_count"] == 5
    assert stats["api_call_count"] == 10
    assert len(stats["scans_by_day"]) > 0
    assert len(stats["calls_by_endpoint"]) > 0
    assert stats["average_response_time_ms"] > 0


@pytest.mark.asyncio
async def test_get_user_statistics_empty(db_session):
    """Test getting user statistics when no data exists"""
    user_id = uuid4()
    
    stats = await UsageService.get_user_statistics(db_session, user_id, days=30)
    
    assert stats["user_id"] == str(user_id)
    assert stats["period_days"] == 30
    assert stats["scan_count"] == 0
    assert stats["api_call_count"] == 0
    assert stats["scans_by_day"] == []
    assert stats["calls_by_endpoint"] == []
    assert stats["average_response_time_ms"] == 0.0
