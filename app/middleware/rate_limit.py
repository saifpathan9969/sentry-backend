"""
Rate limiting middleware using Redis sliding window
"""
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import time
import logging
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


def is_owner_email(email: str) -> bool:
    """Check if email belongs to an owner (gets full access)"""
    if not email:
        return False
    return email.lower() in [e.lower() for e in settings.OWNER_EMAILS]


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware for rate limiting based on user tier
    
    Rate limits:
    - Free tier: 100 requests/hour
    - Premium tier: 10,000 requests/month (calculated as ~14 requests/minute)
    - Enterprise tier: Unlimited
    
    Uses Redis sliding window algorithm for accurate rate limiting
    """
    
    # Rate limits by tier (requests per window)
    RATE_LIMITS = {
        "free": {"limit": 100, "window": 3600},  # 100 requests per hour
        "premium": {"limit": 10000, "window": 2592000},  # 10,000 requests per month (30 days)
        "enterprise": {"limit": None, "window": None},  # Unlimited
    }
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.redis_client = None
        self._init_redis()
    
    def _init_redis(self):
        """Initialize Redis connection"""
        try:
            import redis
            self.redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                decode_responses=True,
            )
            # Test connection
            self.redis_client.ping()
            logger.info("Rate limiter Redis connection established")
        except Exception as e:
            logger.warning(f"Rate limiter Redis connection failed: {e}. Rate limiting disabled.")
            self.redis_client = None
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request and enforce rate limits
        
        Args:
            request: Incoming request
            call_next: Next middleware/endpoint
            
        Returns:
            Response from endpoint or 429 Too Many Requests
        """
        # Skip rate limiting for certain endpoints
        skip_paths = [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/favicon.ico",
        ]
        
        if any(request.url.path.startswith(path) for path in skip_paths):
            return await call_next(request)
        
        # Skip if Redis is not available
        if not self.redis_client:
            return await call_next(request)
        
        # Get user info from request state (set by auth middleware)
        user_id = getattr(request.state, "user_id", None)
        user_tier = getattr(request.state, "user_tier", "free")
        user_email = getattr(request.state, "user_email", None)
        
        # Skip rate limiting for unauthenticated requests
        if not user_id:
            return await call_next(request)
        
        # Skip rate limiting for owners (full access)
        if is_owner_email(user_email):
            return await call_next(request)
        
        # Check rate limit
        allowed, remaining, reset_time = await self._check_rate_limit(
            user_id, user_tier
        )
        
        # Add rate limit headers to response
        response = await call_next(request) if allowed else Response(
            content='{"detail":"Rate limit exceeded"}',
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            media_type="application/json"
        )
        
        # Add rate limit headers
        rate_limit_info = self.RATE_LIMITS.get(user_tier.lower(), self.RATE_LIMITS["free"])
        if rate_limit_info["limit"] is not None:
            response.headers["X-RateLimit-Limit"] = str(rate_limit_info["limit"])
            response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
            response.headers["X-RateLimit-Reset"] = str(reset_time)
        
        return response
    
    async def _check_rate_limit(
        self,
        user_id: str,
        user_tier: str,
    ) -> tuple[bool, int, int]:
        """
        Check if request is within rate limit using sliding window
        
        Args:
            user_id: User ID
            user_tier: User tier
            
        Returns:
            Tuple of (allowed, remaining, reset_time)
        """
        # Get rate limit for tier
        rate_limit_info = self.RATE_LIMITS.get(user_tier.lower(), self.RATE_LIMITS["free"])
        
        # Enterprise tier has unlimited requests
        if rate_limit_info["limit"] is None:
            return True, 999999, 0
        
        limit = rate_limit_info["limit"]
        window = rate_limit_info["window"]
        
        # Redis key for this user
        key = f"rate_limit:{user_id}:{user_tier}"
        
        try:
            # Current timestamp
            now = int(time.time())
            window_start = now - window
            
            # Remove old entries outside the window
            self.redis_client.zremrangebyscore(key, 0, window_start)
            
            # Count requests in current window
            current_count = self.redis_client.zcard(key)
            
            # Check if limit exceeded
            if current_count >= limit:
                # Calculate reset time (when oldest request expires)
                oldest = self.redis_client.zrange(key, 0, 0, withscores=True)
                reset_time = int(oldest[0][1]) + window if oldest else now + window
                return False, 0, reset_time
            
            # Add current request
            self.redis_client.zadd(key, {str(now): now})
            
            # Set expiry on key
            self.redis_client.expire(key, window)
            
            # Calculate remaining requests
            remaining = limit - (current_count + 1)
            reset_time = now + window
            
            return True, remaining, reset_time
            
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            # Allow request if rate limiting fails
            return True, limit, int(time.time()) + window
