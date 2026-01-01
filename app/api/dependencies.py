"""
FastAPI dependencies for authentication and authorization
"""
from fastapi import Depends, HTTPException, status, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.db.session import get_db
from app.services.auth_service import AuthService
from app.services.api_key_service import APIKeyService
from app.models import User

# HTTP Bearer token security scheme
security = HTTPBearer()


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency to get current authenticated user from JWT token
    
    Args:
        request: FastAPI request object
        credentials: HTTP Bearer credentials
        db: Database session
        
    Returns:
        Current user
        
    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials
    auth_service = AuthService(db)
    user = await auth_service.get_current_user(token)
    
    # Set user_id, user_tier, and user_email in request state for middleware
    request.state.user_id = user.id
    request.state.user_tier = user.tier
    request.state.user_email = user.email
    
    return user


async def get_current_user_or_api_key(
    request: Request,
    x_api_key: Optional[str] = Header(None),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency to get current user from either JWT token or API key
    
    Args:
        request: FastAPI request object
        x_api_key: API key from X-API-Key header
        credentials: HTTP Bearer credentials (JWT token)
        db: Database session
        
    Returns:
        Current user
        
    Raises:
        HTTPException: If authentication fails
    """
    user = None
    
    # Try API key first
    if x_api_key:
        api_key_service = APIKeyService(db)
        user = await api_key_service.validate_api_key(x_api_key)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
    # Fall back to JWT token
    elif credentials:
        token = credentials.credentials
        auth_service = AuthService(db)
        user = await auth_service.get_current_user(token)
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No authentication credentials provided"
        )
    
    # Set user_id, user_tier, and user_email in request state for middleware
    request.state.user_id = user.id
    request.state.user_tier = user.tier
    request.state.user_email = user.email
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to get current active user
    
    Args:
        current_user: Current user from token
        
    Returns:
        Current active user
        
    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


async def get_current_verified_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Dependency to get current verified user
    
    Args:
        current_user: Current active user
        
    Returns:
        Current verified user
        
    Raises:
        HTTPException: If email is not verified
    """
    if not current_user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified"
        )
    return current_user
