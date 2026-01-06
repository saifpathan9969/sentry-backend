"""
User management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.api_key_service import APIKeyService
from app.schemas.api_key import APIKeyResponse, APIKeyInfo
from app.schemas.auth import UserResponse
from app.api.dependencies import get_current_user
from app.models import User

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user information
    
    Requires valid JWT access token in Authorization header
    Fixed: User IDs are now strings, not UUIDs
    """
    # Convert User model to UserResponse with UUID as string
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        tier=current_user.tier,
        is_active=current_user.is_active,
        email_verified=current_user.email_verified,
        created_at=current_user.created_at,
        last_login=current_user.last_login
    )


@router.get("/me/api-key", response_model=APIKeyInfo)
async def get_api_key_info(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get API key information (not the actual key)
    
    Returns whether user has an API key and when it was created
    """
    api_key_service = APIKeyService(db)
    has_key = await api_key_service.has_api_key(current_user.id)
    
    return APIKeyInfo(
        has_api_key=has_key,
        created_at=current_user.updated_at if has_key else None
    )


@router.post("/me/api-key", response_model=APIKeyResponse, status_code=status.HTTP_201_CREATED)
async def generate_api_key(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate a new API key for the current user
    
    If user already has an API key, this will replace it (old key becomes invalid)
    
    **Important**: The API key is only shown once. Store it securely!
    """
    api_key_service = APIKeyService(db)
    api_key = await api_key_service.generate_api_key(current_user.id)
    
    return APIKeyResponse(
        api_key=api_key,
        message="Store this API key securely. It will not be shown again."
    )


@router.post("/me/api-key/regenerate", response_model=APIKeyResponse)
async def regenerate_api_key(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Regenerate API key (invalidates old key)
    
    **Important**: The new API key is only shown once. Store it securely!
    """
    api_key_service = APIKeyService(db)
    api_key = await api_key_service.regenerate_api_key(current_user.id)
    
    return APIKeyResponse(
        api_key=api_key,
        message="New API key generated. Old key is now invalid. Store this securely!"
    )


@router.delete("/me/api-key", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Revoke (delete) current API key
    
    After revocation, the API key will no longer work for authentication
    """
    api_key_service = APIKeyService(db)
    await api_key_service.revoke_api_key(current_user.id)
    return None


@router.get("/me/usage")
async def get_usage_statistics(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get usage statistics for current user
    
    Args:
        days: Number of days to look back (1-365, default: 30)
        
    Returns:
        Usage statistics including:
        - Total scan count
        - Total API call count
        - Scans by day
        - API calls by endpoint
        - Average response time
    """
    from app.services.usage_service import UsageService
    
    # Validate days parameter
    if days < 1 or days > 365:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Days must be between 1 and 365"
        )
    
    statistics = await UsageService.get_user_statistics(db, current_user.id, days)
    
    return statistics
