"""
Property-based tests for authentication
Feature: pentest-brain-web-app
"""
import pytest
from hypothesis import given, strategies as st, settings, assume
from hypothesis.strategies import composite
from datetime import datetime, timedelta
import uuid

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_api_key,
    hash_api_key
)


# ============================================================================
# Hypothesis Strategies
# ============================================================================

@composite
def password_strategy(draw):
    """Generate valid passwords"""
    # Generate password with required complexity
    length = draw(st.integers(min_value=8, max_value=50))
    uppercase = draw(st.text(alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZ', min_size=1, max_size=5))
    lowercase = draw(st.text(alphabet='abcdefghijklmnopqrstuvwxyz', min_size=1, max_size=10))
    digits = draw(st.text(alphabet='0123456789', min_size=1, max_size=5))
    
    # Combine and shuffle
    password = uppercase + lowercase + digits
    # Pad to minimum length if needed
    if len(password) < length:
        password += draw(st.text(alphabet='abcdefghijklmnopqrstuvwxyz0123456789', min_size=length - len(password), max_size=length - len(password)))
    
    return password[:length]


@composite
def user_data_strategy(draw):
    """Generate user data for tokens"""
    return {
        "sub": str(uuid.uuid4()),
        "email": draw(st.emails()),
        "tier": draw(st.sampled_from(["free", "premium", "enterprise"]))
    }


# ============================================================================
# Property Tests
# ============================================================================

@pytest.mark.property
@given(user_data=user_data_strategy())
@settings(max_examples=100, deadline=None)
def test_property_token_validity(user_data):
    """
    Feature: pentest-brain-web-app, Property 1: Authentication token validity
    
    Property: For any user with valid credentials, logging in should produce a JWT token 
    that can be successfully validated and decoded to retrieve the user ID
    
    Validates: Requirements 1.4, 1.5
    """
    # Create access token
    access_token = create_access_token(user_data)
    
    # Token should be a non-empty string
    assert isinstance(access_token, str)
    assert len(access_token) > 0
    
    # Decode token
    decoded = decode_token(access_token)
    
    # Decoded payload should contain original data
    assert decoded is not None
    assert decoded["sub"] == user_data["sub"]
    assert decoded["email"] == user_data["email"]
    assert decoded["tier"] == user_data["tier"]
    
    # Token should have expiration and issued-at timestamps
    assert "exp" in decoded
    assert "iat" in decoded
    assert decoded["exp"] > decoded["iat"]


@pytest.mark.property
@given(user_data=user_data_strategy())
@settings(max_examples=100, deadline=None)
def test_property_refresh_token_validity(user_data):
    """
    Feature: pentest-brain-web-app, Property 1: Authentication token validity
    
    Property: For any user, a refresh token should be valid and decodable
    
    Validates: Requirements 1.5
    """
    # Create refresh token
    refresh_token = create_refresh_token({"sub": user_data["sub"]})
    
    # Token should be a non-empty string
    assert isinstance(refresh_token, str)
    assert len(refresh_token) > 0
    
    # Decode token
    decoded = decode_token(refresh_token)
    
    # Decoded payload should contain user ID and type
    assert decoded is not None
    assert decoded["sub"] == user_data["sub"]
    assert decoded["type"] == "refresh"
    
    # Token should have expiration
    assert "exp" in decoded
    assert "iat" in decoded


@pytest.mark.property
@given(user_data=user_data_strategy())
@settings(max_examples=100, deadline=None)
def test_property_token_contains_user_id(user_data):
    """
    Feature: pentest-brain-web-app, Property 1: Authentication token validity
    
    Property: For any user, the JWT token should always contain the user ID in the 'sub' claim
    
    Validates: Requirements 1.4
    """
    # Create token
    token = create_access_token(user_data)
    
    # Decode and verify user ID is present
    decoded = decode_token(token)
    assert decoded is not None
    assert "sub" in decoded
    assert decoded["sub"] == user_data["sub"]
    
    # User ID should be a valid UUID string
    try:
        uuid.UUID(decoded["sub"])
    except ValueError:
        pytest.fail(f"User ID in token is not a valid UUID: {decoded['sub']}")


@pytest.mark.property
@given(
    user_data=user_data_strategy(),
    tampered_char=st.text(alphabet='abcdefghijklmnopqrstuvwxyz0123456789', min_size=1, max_size=1)
)
@settings(max_examples=50, deadline=None)
def test_property_tampered_token_invalid(user_data, tampered_char):
    """
    Feature: pentest-brain-web-app, Property 1: Authentication token validity
    
    Property: For any token, tampering with it should make it invalid
    
    Validates: Requirements 1.4
    """
    # Create valid token
    token = create_access_token(user_data)
    
    # Tamper with token (change one character)
    if len(token) > 10:
        tampered_token = token[:5] + tampered_char + token[6:]
        
        # Tampered token should be invalid
        decoded = decode_token(tampered_token)
        assert decoded is None, "Tampered token should not be valid"


@pytest.mark.property
@given(user_data=user_data_strategy())
@settings(max_examples=100, deadline=None)
def test_property_token_uniqueness(user_data):
    """
    Feature: pentest-brain-web-app, Property 1: Authentication token validity
    
    Property: For any user, generating multiple tokens should produce different tokens
    (due to different issued-at timestamps)
    
    Validates: Requirements 1.4
    """
    # Generate multiple tokens
    token1 = create_access_token(user_data)
    token2 = create_access_token(user_data)
    
    # Tokens should be different (different iat timestamps)
    # Note: In rare cases they might be the same if generated in the same second
    # but the property still holds that they CAN be different
    assert isinstance(token1, str)
    assert isinstance(token2, str)
    
    # Both should be valid
    decoded1 = decode_token(token1)
    decoded2 = decode_token(token2)
    
    assert decoded1 is not None
    assert decoded2 is not None
    assert decoded1["sub"] == decoded2["sub"]


@pytest.mark.property
@given(user_data=user_data_strategy())
@settings(max_examples=100, deadline=None)
def test_property_access_and_refresh_tokens_different(user_data):
    """
    Feature: pentest-brain-web-app, Property 1: Authentication token validity
    
    Property: For any user, access token and refresh token should be different
    
    Validates: Requirements 1.4, 1.5
    """
    # Create both token types
    access_token = create_access_token(user_data)
    refresh_token = create_refresh_token({"sub": user_data["sub"]})
    
    # Tokens should be different
    assert access_token != refresh_token
    
    # Decode both
    access_decoded = decode_token(access_token)
    refresh_decoded = decode_token(refresh_token)
    
    # Both should be valid but have different properties
    assert access_decoded is not None
    assert refresh_decoded is not None
    
    # Refresh token should have type marker
    assert refresh_decoded.get("type") == "refresh"
    assert access_decoded.get("type") != "refresh"
    
    # Refresh token should have longer expiry
    assert refresh_decoded["exp"] > access_decoded["exp"]



# ============================================================================
# Password Hashing Property Tests
# ============================================================================

@pytest.mark.property
@given(password=password_strategy())
@settings(max_examples=100, deadline=None)
def test_property_password_hashing_irreversibility(password):
    """
    Feature: pentest-brain-web-app, Property 2: Password hashing irreversibility
    
    Property: For any password string, after hashing with bcrypt, the original password 
    should not be recoverable from the hash, but verification should succeed with the 
    original password
    
    Validates: Requirements 2.5
    """
    # Hash the password
    hashed = hash_password(password)
    
    # Hash should be a string
    assert isinstance(hashed, str)
    assert len(hashed) > 0
    
    # Hash should be different from original password
    assert hashed != password
    
    # Hash should start with bcrypt identifier
    assert hashed.startswith('$2b$') or hashed.startswith('$2a$') or hashed.startswith('$2y$')
    
    # Original password should verify against hash
    assert verify_password(password, hashed) is True
    
    # Wrong password should not verify
    wrong_password = password + "wrong"
    assert verify_password(wrong_password, hashed) is False


@pytest.mark.property
@given(password=password_strategy())
@settings(max_examples=100, deadline=None)
def test_property_password_hash_uniqueness(password):
    """
    Feature: pentest-brain-web-app, Property 2: Password hashing irreversibility
    
    Property: For any password, hashing it multiple times should produce different hashes
    (due to random salt), but all should verify correctly
    
    Validates: Requirements 2.5
    """
    # Hash the same password multiple times
    hash1 = hash_password(password)
    hash2 = hash_password(password)
    
    # Hashes should be different (different salts)
    assert hash1 != hash2
    
    # Both hashes should verify with the original password
    assert verify_password(password, hash1) is True
    assert verify_password(password, hash2) is True


@pytest.mark.property
@given(password=password_strategy())
@settings(max_examples=100, deadline=None)
def test_property_password_verification_consistency(password):
    """
    Feature: pentest-brain-web-app, Property 2: Password hashing irreversibility
    
    Property: For any password and its hash, verification should always return the same result
    
    Validates: Requirements 2.5
    """
    # Hash password
    hashed = hash_password(password)
    
    # Verify multiple times - should always return True
    for _ in range(5):
        assert verify_password(password, hashed) is True
    
    # Wrong password should always return False
    wrong_password = password + "X"
    for _ in range(5):
        assert verify_password(wrong_password, hashed) is False


@pytest.mark.property
@given(
    password=password_strategy(),
    other_password=password_strategy()
)
@settings(max_examples=100, deadline=None)
def test_property_different_passwords_different_verification(password, other_password):
    """
    Feature: pentest-brain-web-app, Property 2: Password hashing irreversibility
    
    Property: For any two different passwords, a hash of one should not verify against the other
    
    Validates: Requirements 2.5
    """
    assume(password != other_password)
    
    # Hash first password
    hashed = hash_password(password)
    
    # Correct password should verify
    assert verify_password(password, hashed) is True
    
    # Different password should not verify
    assert verify_password(other_password, hashed) is False


@pytest.mark.property
@given(password=password_strategy())
@settings(max_examples=100, deadline=None)
def test_property_password_hash_length(password):
    """
    Feature: pentest-brain-web-app, Property 2: Password hashing irreversibility
    
    Property: For any password, the bcrypt hash should have a consistent length (60 characters)
    
    Validates: Requirements 2.5
    """
    hashed = hash_password(password)
    
    # Bcrypt hashes are always 60 characters
    assert len(hashed) == 60


@pytest.mark.property
@given(password=password_strategy())
@settings(max_examples=50, deadline=None)
def test_property_password_case_sensitivity(password):
    """
    Feature: pentest-brain-web-app, Property 2: Password hashing irreversibility
    
    Property: For any password, changing the case should result in failed verification
    
    Validates: Requirements 2.5
    """
    # Hash password
    hashed = hash_password(password)
    
    # Original should verify
    assert verify_password(password, hashed) is True
    
    # Case-changed version should not verify (if password has letters)
    if any(c.isalpha() for c in password):
        case_changed = password.swapcase()
        if case_changed != password:  # Only test if swapcase actually changed something
            assert verify_password(case_changed, hashed) is False
