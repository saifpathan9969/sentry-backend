"""
Unit tests for rate limiting middleware
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi import Request, Response
from starlette.datastructures import Headers

from app.middleware.rate_limit import RateLimitMiddleware


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    redis_mock = MagicMock()
    redis_mock.ping.return_value = True
    redis_mock.zremrangebyscore.return_value = None
    redis_mock.zcard.return_value = 0
    redis_mock.zadd.return_value = None
    redis_mock.expire.return_value = None
    redis_mock.zrange.return_value = []
    return redis_mock


@pytest.mark.asyncio
async def test_rate_limit_free_tier_within_limit(mock_redis):
    """Test rate limiting for free tier within limit"""
    middleware = RateLimitMiddleware(app=Mock())
    middleware.redis_client = mock_redis
    
    # Mock request
    request = Mock(spec=Request)
    request.url.path = "/api/v1/scans"
    request.state.user_id = "test-user-id"
    request.state.user_tier = "free"
    
    # Mock call_next
    async def call_next(req):
        return Response(content="OK", status_code=200)
    
    # Set Redis to return 50 requests (within limit of 100)
    mock_redis.zcard.return_value = 50
    
    # Check rate limit
    allowed, remaining, reset_time = await middleware._check_rate_limit(
        "test-user-id", "free"
    )
    
    assert allowed is True
    assert remaining == 49  # 100 - 50 - 1


@pytest.mark.asyncio
async def test_rate_limit_free_tier_exceeded(mock_redis):
    """Test rate limiting for free tier when limit exceeded"""
    middleware = RateLimitMiddleware(app=Mock())
    middleware.redis_client = mock_redis
    
    # Set Redis to return 100 requests (at limit)
    mock_redis.zcard.return_value = 100
    mock_redis.zrange.return_value = [(b"timestamp", 1234567890)]
    
    # Check rate limit
    allowed, remaining, reset_time = await middleware._check_rate_limit(
        "test-user-id", "free"
    )
    
    assert allowed is False
    assert remaining == 0


@pytest.mark.asyncio
async def test_rate_limit_premium_tier_within_limit(mock_redis):
    """Test rate limiting for premium tier within limit"""
    middleware = RateLimitMiddleware(app=Mock())
    middleware.redis_client = mock_redis
    
    # Set Redis to return 5000 requests (within limit of 10,000)
    mock_redis.zcard.return_value = 5000
    
    # Check rate limit
    allowed, remaining, reset_time = await middleware._check_rate_limit(
        "test-user-id", "premium"
    )
    
    assert allowed is True
    assert remaining == 4999  # 10,000 - 5000 - 1


@pytest.mark.asyncio
async def test_rate_limit_enterprise_tier_unlimited(mock_redis):
    """Test that enterprise tier has unlimited requests"""
    middleware = RateLimitMiddleware(app=Mock())
    middleware.redis_client = mock_redis
    
    # Check rate limit (should always be allowed)
    allowed, remaining, reset_time = await middleware._check_rate_limit(
        "test-user-id", "enterprise"
    )
    
    assert allowed is True
    assert remaining == 999999  # Unlimited indicator


@pytest.mark.asyncio
async def test_rate_limit_headers_added(mock_redis):
    """Test that rate limit headers are added to response"""
    middleware = RateLimitMiddleware(app=Mock())
    middleware.redis_client = mock_redis
    
    # Mock request
    request = Mock(spec=Request)
    request.url.path = "/api/v1/scans"
    request.state.user_id = "test-user-id"
    request.state.user_tier = "free"
    
    # Mock call_next
    async def call_next(req):
        return Response(content="OK", status_code=200)
    
    # Set Redis to return 50 requests
    mock_redis.zcard.return_value = 50
    
    # Process request
    response = await middleware.dispatch(request, call_next)
    
    # Check headers
    assert "X-RateLimit-Limit" in response.headers
    assert "X-RateLimit-Remaining" in response.headers
    assert "X-RateLimit-Reset" in response.headers


@pytest.mark.asyncio
async def test_rate_limit_skip_unauthenticated():
    """Test that rate limiting is skipped for unauthenticated requests"""
    middleware = RateLimitMiddleware(app=Mock())
    middleware.redis_client = MagicMock()
    
    # Mock request without user_id
    request = Mock(spec=Request)
    request.url.path = "/api/v1/scans"
    request.state.user_id = None
    
    # Mock call_next
    async def call_next(req):
        return Response(content="OK", status_code=200)
    
    # Process request
    response = await middleware.dispatch(request, call_next)
    
    # Should not call Redis
    middleware.redis_client.zcard.assert_not_called()
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_rate_limit_skip_docs_endpoints():
    """Test that rate limiting is skipped for documentation endpoints"""
    middleware = RateLimitMiddleware(app=Mock())
    middleware.redis_client = MagicMock()
    
    # Mock request to /docs
    request = Mock(spec=Request)
    request.url.path = "/docs"
    request.state.user_id = "test-user-id"
    request.state.user_tier = "free"
    
    # Mock call_next
    async def call_next(req):
        return Response(content="OK", status_code=200)
    
    # Process request
    response = await middleware.dispatch(request, call_next)
    
    # Should not call Redis
    middleware.redis_client.zcard.assert_not_called()
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_rate_limit_redis_failure_allows_request(mock_redis):
    """Test that requests are allowed if Redis fails"""
    middleware = RateLimitMiddleware(app=Mock())
    middleware.redis_client = mock_redis
    
    # Make Redis raise an exception
    mock_redis.zcard.side_effect = Exception("Redis connection failed")
    
    # Check rate limit
    allowed, remaining, reset_time = await middleware._check_rate_limit(
        "test-user-id", "free"
    )
    
    # Should allow request despite Redis failure
    assert allowed is True


@pytest.mark.asyncio
async def test_rate_limit_window_cleanup(mock_redis):
    """Test that old entries are removed from sliding window"""
    middleware = RateLimitMiddleware(app=Mock())
    middleware.redis_client = mock_redis
    
    # Check rate limit
    await middleware._check_rate_limit("test-user-id", "free")
    
    # Verify old entries were removed
    mock_redis.zremrangebyscore.assert_called_once()
