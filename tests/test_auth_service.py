"""
Unit tests for authentication service and endpoints
"""
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models import User, UserTier
from app.core.security import hash_password, decode_token


@pytest.mark.unit
@pytest.mark.asyncio
async def test_register_user_success(client: AsyncClient):
    """Test successful user registration"""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "StrongPass123",
            "full_name": "New User"
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["full_name"] == "New User"
    assert data["tier"] == "free"
    assert data["is_active"] is True
    assert data["email_verified"] is False
    assert "id" in data


@pytest.mark.unit
@pytest.mark.asyncio
async def test_register_user_duplicate_email(client: AsyncClient, db_session):
    """Test registration with duplicate email fails"""
    # Create existing user
    user = User(
        email="existing@example.com",
        password_hash=hash_password("password123"),
        tier=UserTier.FREE
    )
    db_session.add(user)
    await db_session.commit()
    
    # Try to register with same email
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "existing@example.com",
            "password": "StrongPass123"
        }
    )
    
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"].lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_register_user_weak_password(client: AsyncClient):
    """Test registration with weak password fails"""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "weak"  # Too short, no uppercase, no digit
        }
    )
    
    assert response.status_code == 422  # Validation error


@pytest.mark.unit
@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, db_session):
    """Test successful login"""
    # Create user
    user = User(
        email="test@example.com",
        password_hash=hash_password("StrongPass123"),
        tier=UserTier.FREE
    )
    db_session.add(user)
    await db_session.commit()
    
    # Login
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "test@example.com",
            "password": "StrongPass123"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    
    # Verify access token
    access_token = data["access_token"]
    decoded = decode_token(access_token)
    assert decoded is not None
    assert decoded["email"] == "test@example.com"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_login_invalid_email(client: AsyncClient):
    """Test login with non-existent email"""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "nonexistent@example.com",
            "password": "StrongPass123"
        }
    )
    
    assert response.status_code == 401
    assert "invalid" in response.json()["detail"].lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient, db_session):
    """Test login with wrong password"""
    # Create user
    user = User(
        email="test@example.com",
        password_hash=hash_password("CorrectPass123"),
        tier=UserTier.FREE
    )
    db_session.add(user)
    await db_session.commit()
    
    # Login with wrong password
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "test@example.com",
            "password": "WrongPass123"
        }
    )
    
    assert response.status_code == 401
    assert "invalid" in response.json()["detail"].lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_login_inactive_user(client: AsyncClient, db_session):
    """Test login with inactive user"""
    # Create inactive user
    user = User(
        email="inactive@example.com",
        password_hash=hash_password("StrongPass123"),
        tier=UserTier.FREE,
        is_active=False
    )
    db_session.add(user)
    await db_session.commit()
    
    # Try to login
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "inactive@example.com",
            "password": "StrongPass123"
        }
    )
    
    assert response.status_code == 403
    assert "inactive" in response.json()["detail"].lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_refresh_token_success(client: AsyncClient, db_session):
    """Test successful token refresh"""
    # Create user and login
    user = User(
        email="test@example.com",
        password_hash=hash_password("StrongPass123"),
        tier=UserTier.FREE
    )
    db_session.add(user)
    await db_session.commit()
    
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "StrongPass123"}
    )
    refresh_token = login_response.json()["refresh_token"]
    
    # Refresh token
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_refresh_token_invalid(client: AsyncClient):
    """Test refresh with invalid token"""
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid_token"}
    )
    
    assert response.status_code == 401


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_current_user(client: AsyncClient, db_session):
    """Test getting current user info"""
    # Create user and login
    user = User(
        email="test@example.com",
        password_hash=hash_password("StrongPass123"),
        full_name="Test User",
        tier=UserTier.PREMIUM
    )
    db_session.add(user)
    await db_session.commit()
    
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "StrongPass123"}
    )
    access_token = login_response.json()["access_token"]
    
    # Get current user
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["full_name"] == "Test User"
    assert data["tier"] == "premium"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_current_user_no_token(client: AsyncClient):
    """Test getting current user without token"""
    response = await client.get("/api/v1/auth/me")
    
    assert response.status_code == 403  # No authorization header


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_current_user_invalid_token(client: AsyncClient):
    """Test getting current user with invalid token"""
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid_token"}
    )
    
    assert response.status_code == 401


@pytest.mark.unit
@pytest.mark.asyncio
async def test_logout(client: AsyncClient, db_session):
    """Test logout endpoint"""
    # Create user and login
    user = User(
        email="test@example.com",
        password_hash=hash_password("StrongPass123"),
        tier=UserTier.FREE
    )
    db_session.add(user)
    await db_session.commit()
    
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "StrongPass123"}
    )
    access_token = login_response.json()["access_token"]
    
    # Logout
    response = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    assert response.status_code == 200
    assert "logged out" in response.json()["message"].lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_password_validation_no_uppercase(client: AsyncClient):
    """Test password validation requires uppercase"""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "weakpass123"  # No uppercase
        }
    )
    
    assert response.status_code == 422


@pytest.mark.unit
@pytest.mark.asyncio
async def test_password_validation_no_digit(client: AsyncClient):
    """Test password validation requires digit"""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "WeakPassword"  # No digit
        }
    )
    
    assert response.status_code == 422


@pytest.mark.unit
@pytest.mark.asyncio
async def test_login_updates_last_login(client: AsyncClient, db_session):
    """Test that login updates last_login timestamp"""
    # Create user
    user = User(
        email="test@example.com",
        password_hash=hash_password("StrongPass123"),
        tier=UserTier.FREE
    )
    db_session.add(user)
    await db_session.commit()
    user_id = user.id
    
    # Verify last_login is None
    assert user.last_login is None
    
    # Login
    await client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "StrongPass123"}
    )
    
    # Check last_login was updated
    result = await db_session.execute(select(User).where(User.id == user_id))
    updated_user = result.scalar_one()
    assert updated_user.last_login is not None
