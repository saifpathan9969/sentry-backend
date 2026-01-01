"""
API Key service for managing user API keys
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from datetime import datetime
import uuid

from app.models import User
from app.core.security import generate_api_key, hash_api_key


class APIKeyService:
    """Service for API key operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def generate_api_key(self, user_id: uuid.UUID) -> str:
        """
        Generate a new API key for user
        
        Args:
            user_id: User ID
            
        Returns:
            Plain text API key (only shown once)
            
        Raises:
            HTTPException: If user not found
        """
        # Get user
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Generate new API key
        api_key = generate_api_key()
        api_key_hash = hash_api_key(api_key)
        
        # Store hashed API key
        user.api_key_hash = api_key_hash
        user.updated_at = datetime.utcnow()
        
        await self.db.commit()
        
        # Return plain text API key (only time it's shown)
        return api_key
    
    async def regenerate_api_key(self, user_id: uuid.UUID) -> str:
        """
        Regenerate API key for user (invalidates old key)
        
        Args:
            user_id: User ID
            
        Returns:
            New plain text API key
        """
        # Same as generate, but explicitly invalidates old key
        return await self.generate_api_key(user_id)
    
    async def revoke_api_key(self, user_id: uuid.UUID) -> bool:
        """
        Revoke user's API key
        
        Args:
            user_id: User ID
            
        Returns:
            True if revoked successfully
        """
        # Get user
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Remove API key
        user.api_key_hash = None
        user.updated_at = datetime.utcnow()
        
        await self.db.commit()
        
        return True
    
    async def validate_api_key(self, api_key: str) -> User | None:
        """
        Validate API key and return associated user
        
        Args:
            api_key: Plain text API key
            
        Returns:
            User if valid, None otherwise
        """
        # Hash the provided API key
        api_key_hash = hash_api_key(api_key)
        
        # Find user with this API key hash
        result = await self.db.execute(
            select(User).where(User.api_key_hash == api_key_hash)
        )
        user = result.scalar_one_or_none()
        
        if not user or not user.is_active:
            return None
        
        return user
    
    async def has_api_key(self, user_id: uuid.UUID) -> bool:
        """
        Check if user has an API key
        
        Args:
            user_id: User ID
            
        Returns:
            True if user has API key
        """
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return False
        
        return user.api_key_hash is not None
