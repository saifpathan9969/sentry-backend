"""
Property-based tests for API key management
Feature: pentest-brain-web-app
"""
import pytest
from hypothesis import given, strategies as st, settings
from hypothesis.strategies import composite

from app.core.security import generate_api_key, hash_api_key


# ============================================================================
# Property Tests
# ============================================================================

@pytest.mark.property
@settings(max_examples=100, deadline=None)
def test_property_api_key_uniqueness():
    """
    Feature: pentest-brain-web-app, Property 5: API key uniqueness and validity
    
    Property: For any user, generating an API key should produce a unique token 
    that can authenticate that specific user and no other
    
    Validates: Requirements 6.1, 6.4
    """
    # Generate multiple API keys
    keys = [generate_api_key() for _ in range(10)]
    
    # All keys should be unique
    assert len(keys) == len(set(keys)), "API keys should be unique"
    
    # All keys should be 64 characters (hex encoded 32 bytes)
    for key in keys:
        assert len(key) == 64
        assert all(c in '0123456789abcdef' for c in key)


@pytest.mark.property
@settings(max_examples=100, deadline=None)
def test_property_api_key_hash_consistency():
    """
    Feature: pentest-brain-web-app, Property 5: API key uniqueness and validity
    
    Property: For any API key, hashing it multiple times should produce the same hash
    
    Validates: Requirements 6.2
    """
    # Generate API key
    api_key = generate_api_key()
    
    # Hash multiple times
    hash1 = hash_api_key(api_key)
    hash2 = hash_api_key(api_key)
    hash3 = hash_api_key(api_key)
    
    # All hashes should be identical (deterministic)
    assert hash1 == hash2 == hash3


@pytest.mark.property
@settings(max_examples=100, deadline=None)
def test_property_api_key_hash_length():
    """
    Feature: pentest-brain-web-app, Property 5: API key uniqueness and validity
    
    Property: For any API key, the SHA-256 hash should be 64 characters (hex)
    
    Validates: Requirements 6.2
    """
    # Generate and hash API keys
    for _ in range(10):
        api_key = generate_api_key()
        hashed = hash_api_key(api_key)
        
        # SHA-256 hex digest is 64 characters
        assert len(hashed) == 64
        assert all(c in '0123456789abcdef' for c in hashed)


@pytest.mark.property
@settings(max_examples=100, deadline=None)
def test_property_different_keys_different_hashes():
    """
    Feature: pentest-brain-web-app, Property 5: API key uniqueness and validity
    
    Property: For any two different API keys, their hashes should be different
    
    Validates: Requirements 6.1, 6.2
    """
    # Generate multiple API keys
    keys = [generate_api_key() for _ in range(10)]
    hashes = [hash_api_key(key) for key in keys]
    
    # All hashes should be unique
    assert len(hashes) == len(set(hashes)), "Different API keys should have different hashes"


@pytest.mark.property
@settings(max_examples=50, deadline=None)
def test_property_api_key_format():
    """
    Feature: pentest-brain-web-app, Property 5: API key uniqueness and validity
    
    Property: For any generated API key, it should be a valid hex string of length 64
    
    Validates: Requirements 6.1
    """
    for _ in range(20):
        api_key = generate_api_key()
        
        # Should be string
        assert isinstance(api_key, str)
        
        # Should be 64 characters
        assert len(api_key) == 64
        
        # Should be valid hex
        try:
            int(api_key, 16)
        except ValueError:
            pytest.fail(f"API key is not valid hex: {api_key}")


@pytest.mark.property
@settings(max_examples=100, deadline=None)
def test_property_api_key_hash_irreversibility():
    """
    Feature: pentest-brain-web-app, Property 5: API key uniqueness and validity
    
    Property: For any API key, the hash should not reveal the original key
    
    Validates: Requirements 6.2
    """
    api_key = generate_api_key()
    hashed = hash_api_key(api_key)
    
    # Hash should be different from original
    assert hashed != api_key
    
    # Hash should not contain the original key
    assert api_key not in hashed
    
    # Original key should not be derivable from hash
    # (This is a property of SHA-256, we just verify they're different)
    assert len(hashed) == len(api_key)  # Both 64 chars but different values


@pytest.mark.property
@given(tampered_char=st.text(alphabet='0123456789abcdef', min_size=1, max_size=1))
@settings(max_examples=50, deadline=None)
def test_property_tampered_api_key_different_hash(tampered_char):
    """
    Feature: pentest-brain-web-app, Property 5: API key uniqueness and validity
    
    Property: For any API key, tampering with it should produce a different hash
    
    Validates: Requirements 6.4
    """
    # Generate API key
    api_key = generate_api_key()
    original_hash = hash_api_key(api_key)
    
    # Tamper with key (change one character)
    tampered_key = api_key[:10] + tampered_char + api_key[11:]
    
    if tampered_key != api_key:
        tampered_hash = hash_api_key(tampered_key)
        
        # Tampered key should have different hash
        assert tampered_hash != original_hash


@pytest.mark.property
@settings(max_examples=100, deadline=None)
def test_property_api_key_collision_resistance():
    """
    Feature: pentest-brain-web-app, Property 5: API key uniqueness and validity
    
    Property: Generating many API keys should not produce collisions
    
    Validates: Requirements 6.1
    """
    # Generate a large number of API keys
    num_keys = 1000
    keys = [generate_api_key() for _ in range(num_keys)]
    
    # Check for uniqueness
    unique_keys = set(keys)
    assert len(unique_keys) == num_keys, f"Found {num_keys - len(unique_keys)} collisions"


@pytest.mark.property
@settings(max_examples=100, deadline=None)
def test_property_api_key_hash_collision_resistance():
    """
    Feature: pentest-brain-web-app, Property 5: API key uniqueness and validity
    
    Property: Hashing many different API keys should not produce hash collisions
    
    Validates: Requirements 6.2
    """
    # Generate API keys and hash them
    num_keys = 1000
    keys = [generate_api_key() for _ in range(num_keys)]
    hashes = [hash_api_key(key) for key in keys]
    
    # Check for uniqueness in hashes
    unique_hashes = set(hashes)
    assert len(unique_hashes) == num_keys, f"Found {num_keys - len(unique_hashes)} hash collisions"
