"""
Middleware for tracking API usage
"""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from datetime import datetime
import time
import logging

from app.db.session import async_session_maker
from app.models.api_usage import APIUsage

logger = logging.getLogger(__name__)


class UsageTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track API usage for all requests
    
    Logs:
    - Endpoint accessed
    - HTTP method
    - Response status code
    - Response time in milliseconds
    - User ID (if authenticated)
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request and log usage
        
        Args:
            request: Incoming request
            call_next: Next middleware/endpoint
            
        Returns:
            Response from endpoint
        """
        # Skip usage tracking for certain endpoints
        skip_paths = [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/favicon.ico",
        ]
        
        if any(request.url.path.startswith(path) for path in skip_paths):
            return await call_next(request)
        
        # Record start time
        start_time = time.time()
        
        # Initialize user_id in request state
        request.state.user_id = None
        
        # Process request
        response = await call_next(request)
        
        # Calculate response time
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Get user ID from request state (set by dependencies during request processing)
        user_id = getattr(request.state, "user_id", None)
        
        # Log usage asynchronously (don't block response)
        try:
            await self._log_usage(
                user_id=user_id,
                endpoint=request.url.path,
                method=request.method,
                status_code=response.status_code,
                response_time_ms=response_time_ms,
            )
        except Exception as e:
            # Don't fail request if logging fails
            logger.error(f"Failed to log API usage: {e}")
        
        return response
    
    async def _log_usage(
        self,
        user_id,
        endpoint: str,
        method: str,
        status_code: int,
        response_time_ms: int,
    ):
        """
        Log API usage to database
        
        Args:
            user_id: User ID (None if not authenticated)
            endpoint: API endpoint path
            method: HTTP method
            status_code: Response status code
            response_time_ms: Response time in milliseconds
        """
        if not user_id:
            # Don't log usage for unauthenticated requests
            return
        
        try:
            async with async_session_maker() as db:
                usage = APIUsage(
                    user_id=user_id,
                    endpoint=endpoint,
                    method=method,
                    status_code=status_code,
                    response_time_ms=response_time_ms,
                    created_at=datetime.utcnow(),
                )
                db.add(usage)
                await db.commit()
        except Exception as e:
            logger.error(f"Error logging usage to database: {e}")
