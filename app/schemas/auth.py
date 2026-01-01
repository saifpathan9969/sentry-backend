"""
Authentication schemas for request/response validation
"""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime
import re


class UserRegister(BaseModel):
    """Schema for user registration"""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    full_name: Optional[str] = Field(None, max_length=255)
    
    @validator('password')
    def validate_password_strength(cls, v):
        """Validate password meets security requirements"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserLogin(BaseModel):
    """Schema for user login"""
    email: EmailStr
    password: str


class TokenPair(BaseModel):
    """Schema for JWT token pair"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AuthResponse(BaseModel):
    """Schema for auth response with tokens and user"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class TokenRefresh(BaseModel):
    """Schema for token refresh request"""
    refresh_token: str


class AccessToken(BaseModel):
    """Schema for access token response"""
    access_token: str
    token_type: str = "bearer"


class EmailVerification(BaseModel):
    """Schema for email verification"""
    token: str


class PasswordResetRequest(BaseModel):
    """Schema for password reset request"""
    email: EmailStr


class PasswordReset(BaseModel):
    """Schema for password reset"""
    token: str
    new_password: str = Field(..., min_length=8, max_length=100)
    
    @validator('new_password')
    def validate_password_strength(cls, v):
        """Validate password meets security requirements"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserResponse(BaseModel):
    """Schema for user response"""
    id: str
    email: str
    full_name: Optional[str]
    tier: str
    is_active: bool
    email_verified: bool
    created_at: datetime
    last_login: Optional[datetime]
    
    class Config:
        from_attributes = True


# Update forward reference
AuthResponse.model_rebuild()
