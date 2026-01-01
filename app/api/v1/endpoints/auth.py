"""
Authentication endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.auth_service import AuthService
from app.schemas.auth import (
    UserRegister,
    UserLogin,
    TokenPair,
    TokenRefresh,
    AccessToken,
    EmailVerification,
    PasswordResetRequest,
    PasswordReset,
    UserResponse,
    AuthResponse
)
from app.api.dependencies import get_current_user
from app.models import User

router = APIRouter()


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user
    
    - **email**: Valid email address (unique)
    - **password**: Strong password (min 8 chars, uppercase, lowercase, digit)
    - **full_name**: Optional full name
    
    Returns the created user with JWT tokens
    """
    auth_service = AuthService(db)
    user = await auth_service.register_user(user_data)
    
    # Auto-login after registration - generate tokens
    from app.schemas.auth import UserLogin
    login_data = UserLogin(email=user_data.email, password=user_data.password)
    tokens = await auth_service.login(login_data)
    
    return AuthResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            tier=user.tier,
            is_active=user.is_active,
            email_verified=user.email_verified,
            created_at=user.created_at,
            last_login=user.last_login
        )
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    login_data: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """
    Login with email and password
    
    - **email**: User email
    - **password**: User password
    
    Returns JWT access token (15 min), refresh token (7 days), and user info
    """
    from sqlalchemy import select
    
    auth_service = AuthService(db)
    tokens = await auth_service.login(login_data)
    
    # Get user info
    result = await db.execute(select(User).where(User.email == login_data.email))
    user = result.scalar_one()
    
    return AuthResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            tier=user.tier,
            is_active=user.is_active,
            email_verified=user.email_verified,
            created_at=user.created_at,
            last_login=user.last_login
        )
    )


@router.post("/refresh", response_model=AccessToken)
async def refresh_token(
    token_data: TokenRefresh,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token using refresh token
    
    - **refresh_token**: Valid JWT refresh token
    
    Returns new access token
    """
    auth_service = AuthService(db)
    access_token = await auth_service.refresh_access_token(token_data.refresh_token)
    return access_token


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user)
):
    """
    Logout current user
    
    Note: Since we're using stateless JWT tokens, logout is handled client-side
    by deleting the tokens. In production, consider implementing token blacklisting.
    """
    return {"message": "Successfully logged out"}


@router.post("/verify-email")
async def verify_email(
    verification_data: EmailVerification,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify user email with verification token
    
    - **token**: Email verification token sent to user's email
    """
    auth_service = AuthService(db)
    success = await auth_service.verify_email(verification_data.token)
    return {"message": "Email verified successfully"}


@router.post("/forgot-password")
async def forgot_password(
    reset_request: PasswordResetRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Request password reset
    
    - **email**: User email
    
    Sends password reset email if user exists
    """
    auth_service = AuthService(db)
    await auth_service.request_password_reset(reset_request.email)
    return {"message": "If the email exists, a password reset link has been sent"}


@router.post("/reset-password")
async def reset_password(
    reset_data: PasswordReset,
    db: AsyncSession = Depends(get_db)
):
    """
    Reset password with reset token
    
    - **token**: Password reset token from email
    - **new_password**: New strong password
    """
    auth_service = AuthService(db)
    success = await auth_service.reset_password(reset_data.token, reset_data.new_password)
    return {"message": "Password reset successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user information
    
    Requires valid JWT access token in Authorization header
    """
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
