"""
Unit tests for API key management service and endpoints
"""
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models import User, UserTier
from app.core.security import hash_password, hash_api_key


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_api_key(client: AsyncClient, db_session):
    """Test generating API key"""
    # Create and login user
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
    token = login_response.json()["access_token"]
    
    # Generate API key
    response = await client.post(
        "/api/v1/users/me/api-key",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert "api_key" in data
    assert len(data["api_key"]) == 64
    assert "message" in data


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_api_key_info(client: AsyncClient, db_session):
    """Test getting API key info"""
    # Create and login user
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
    token = login_response.json()["access_token"]
    
    # Check info before generating key
    response = await client.get(
        "/api/v1/users/me/api-key",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["has_api_key"] is False
    assert data["created_at"] is None
    
    # Generate API key
    await client.post(
        "/api/v1/users/me/api-key",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Check info after generating key
    response = await client.get(
        "/api/v1/users/me/api-key",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["has_api_key"] is True
    assert data["created_at"] is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_regenerate_api_key(client: AsyncClient, db_session):
    """Test regenerating API key invalidates old key"""
    # Create and login user
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
    token = login_response.json()["access_token"]
    
    # Generate first API key
    response1 = await client.post(
        "/api/v1/users/me/api-key",
        headers={"Authorization": f"Bearer {token}"}
    )
    old_api_key = response1.json()["api_key"]
    
    # Regenerate API key
    response2 = await client.post(
        "/api/v1/users/me/api-key/regenerate",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response2.status_code == 200
    new_api_key = response2.json()["api_key"]
    
    # Keys should be different
    assert old_api_key != new_api_key
    
    # Verify old key is invalid by checking database
    result = await db_session.execute(select(User).where(User.email == "test@example.com"))
    user = result.scalar_one()
    
    old_hash = hash_api_key(old_api_key)
    new_hash = hash_api_key(new_api_key)
    
    assert user.api_key_hash == new_hash
    assert user.api_key_hash != old_hash


@pytest.mark.unit
@pytest.mark.asyncio
async def test_revoke_api_key(client: AsyncClient, db_session):
    """Test revoking API key"""
    # Create and login user
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
    token = login_response.json()["access_token"]
    
    # Generate API key
    await client.post(
        "/api/v1/users/me/api-key",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Revoke API key
    response = await client.delete(
        "/api/v1/users/me/api-key",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 204
    
    # Verify key is removed from database
    result = await db_session.execute(select(User).where(User.email == "test@example.com"))
    user = result.scalar_one()
    assert user.api_key_hash is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_api_key_authentication(client: AsyncClient, db_session):
    """Test authenticating with API key"""
    # Create and login user
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
    token = login_response.json()["access_token"]
    
    # Generate API key
    api_key_response = await client.post(
        "/api/v1/users/me/api-key",
        headers={"Authorization": f"Bearer {token}"}
    )
    api_key = api_key_response.json()["api_key"]
    
    # Use API key to access protected endpoint
    response = await client.get(
        "/api/v1/users/me",
        headers={"X-API-Key": api_key}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_invalid_api_key_authentication(client: AsyncClient):
    """Test authentication with invalid API key fails"""
    response = await client.get(
        "/api/v1/users/me",
        headers={"X-API-Key": "invalid_key_1234567890abcdef"}
    )
    
    assert response.status_code == 401


@pytest.mark.unit
@pytest.mark.asyncio
async def test_api_key_without_auth_fails(client: AsyncClient):
    """Test accessing protected endpoint without authentication"""
    response = await client.get("/api/v1/users/me")
    
    assert response.status_code == 403


@pytest.mark.unit
@pytest.mark.asyncio
async def test_api_key_stored_as_hash(client: AsyncClient, db_session):
    """Test that API key is stored as hash, not plain text"""
    # Create and login user
    user = User(
        email="test@example.com",
        password_hash=hash_password("StrongPass123"),
        tier=UserTier.FREE
    )
    db_session.add(user)
    await db_session.commit()
    user_id = user.id
    
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "StrongPass123"}
    )
    token = login_response.json()["access_token"]
    
    # Generate API key
    api_key_response = await client.post(
        "/api/v1/users/me/api-key",
        headers={"Authorization": f"Bearer {token}"}
    )
    plain_api_key = api_key_response.json()["api_key"]
    
    # Check database
    result = await db_session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()
    
    # Stored value should be hash, not plain text
    assert user.api_key_hash != plain_api_key
    assert len(user.api_key_hash) == 64  # SHA-256 hex length
    
    # Verify hash matches
    expected_hash = hash_api_key(plain_api_key)
    assert user.api_key_hash == expected_hash


@pytest.mark.unit
@pytest.mark.asyncio
async def test_multiple_users_different_api_keys(client: AsyncClient, db_session):
    """Test that different users get different API keys"""
    # Create two users
    user1 = User(email="user1@example.com", password_hash=hash_password("Pass123"), tier=UserTier.FREE)
    user2 = User(email="user2@example.com", password_hash=hash_password("Pass123"), tier=UserTier.FREE)
    db_session.add_all([user1, user2])
    await db_session.commit()
    
    # Login both users
    login1 = await client.post("/api/v1/auth/login", json={"email": "user1@example.com", "password": "Pass123"})
    login2 = await client.post("/api/v1/auth/login", json={"email": "user2@example.com", "password": "Pass123"})
    
    token1 = login1.json()["access_token"]
    token2 = login2.json()["access_token"]
    
    # Generate API keys for both
    key1_response = await client.post("/api/v1/users/me/api-key", headers={"Authorization": f"Bearer {token1}"})
    key2_response = await client.post("/api/v1/users/me/api-key", headers={"Authorization": f"Bearer {token2}"})
    
    key1 = key1_response.json()["api_key"]
    key2 = key2_response.json()["api_key"]
    
    # Keys should be different
    assert key1 != key2
    
    # Each key should authenticate its own user
    response1 = await client.get("/api/v1/users/me", headers={"X-API-Key": key1})
    response2 = await client.get("/api/v1/users/me", headers={"X-API-Key": key2})
    
    assert response1.json()["email"] == "user1@example.com"
    assert response2.json()["email"] == "user2@example.com"
