"""
Authentication service for user management and JWT tokens
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import uuid

from app.models import User
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_verification_token
)
from app.core.config import settings
from app.schemas.auth import UserRegister, UserLogin, TokenPair, AccessToken


class AuthService:
    """Service for authentication operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def register_user(self, user_data: UserRegister) -> User:
        """
        Register a new user
        
        Args:
            user_data: User registration data
            
        Returns:
            Created user
            
        Raises:
            HTTPException: If email already exists
        """
        # Check if email already exists
        result = await self.db.execute(
            select(User).where(User.email == user_data.email)
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Hash password
        password_hash = hash_password(user_data.password)
        
        # Check if this is an owner email - give them enterprise tier
        user_tier = 'free'
        is_owner = user_data.email.lower() in [e.lower() for e in settings.OWNER_EMAILS]
        if is_owner:
            user_tier = 'enterprise'
        
        # Create user
        user = User(
            email=user_data.email,
            password_hash=password_hash,
            full_name=user_data.full_name,
            tier=user_tier,
            is_active=True,
            email_verified=True if is_owner else False
        )
        
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        
        # TODO: Send verification email
        # verification_token = generate_verification_token()
        # await self.send_verification_email(user.email, verification_token)
        
        return user
    
    async def login(self, login_data: UserLogin) -> TokenPair:
        """
        Authenticate user and return JWT tokens
        
        Args:
            login_data: User login credentials
            
        Returns:
            JWT token pair (access + refresh)
            
        Raises:
            HTTPException: If credentials are invalid
        """
        # Find user by email
        result = await self.db.execute(
            select(User).where(User.email == login_data.email)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Verify password
        if not verify_password(login_data.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive"
            )
        
        # Update last login
        user.last_login = datetime.utcnow()
        await self.db.commit()
        
        # Create tokens
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "tier": user.tier
        }
        
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token({"sub": str(user.id)})
        
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token
        )
    
    async def refresh_access_token(self, refresh_token: str) -> AccessToken:
        """
        Refresh access token using refresh token
        
        Args:
            refresh_token: JWT refresh token
            
        Returns:
            New access token
            
        Raises:
            HTTPException: If refresh token is invalid
        """
        # Decode refresh token
        payload = decode_token(refresh_token)
        
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Get user
        result = await self.db.execute(
            select(User).where(User.id == uuid.UUID(user_id))
        )
        user = result.scalar_one_or_none()
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Create new access token
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "tier": user.tier
        }
        
        access_token = create_access_token(token_data)
        
        return AccessToken(access_token=access_token)
    
    async def verify_email(self, token: str) -> bool:
        """
        Verify user email with verification token
        
        Args:
            token: Email verification token
            
        Returns:
            True if verification successful
            
        Raises:
            HTTPException: If token is invalid
        """
        # TODO: Implement token storage and validation
        # For now, this is a placeholder
        # In production, store tokens in Redis with expiry
        
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Email verification not yet implemented"
        )
    
    async def request_password_reset(self, email: str) -> bool:
        """
        Request password reset for user
        
        Args:
            email: User email
            
        Returns:
            True if reset email sent
        """
        # Find user
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()
        
        # Always return success to prevent email enumeration
        if not user:
            return True
        
        # TODO: Generate reset token and send email
        # reset_token = generate_verification_token()
        # await self.send_password_reset_email(user.email, reset_token)
        
        return True
    
    async def reset_password(self, token: str, new_password: str) -> bool:
        """
        Reset user password with reset token
        
        Args:
            token: Password reset token
            new_password: New password
            
        Returns:
            True if password reset successful
            
        Raises:
            HTTPException: If token is invalid
        """
        # TODO: Implement token storage and validation
        # For now, this is a placeholder
        
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Password reset not yet implemented"
        )
    
    async def get_current_user(self, token: str) -> User:
        """
        Get current user from JWT token
        
        Args:
            token: JWT access token
            
        Returns:
            Current user
            
        Raises:
            HTTPException: If token is invalid
        """
        payload = decode_token(token)
        
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )
        
        # Get user
        result = await self.db.execute(
            select(User).where(User.id == uuid.UUID(user_id))
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )
        
        return user
