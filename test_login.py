#!/usr/bin/env python3
"""
Test login functionality
"""
import requests
import json

def test_login():
    """Test login with the created test user"""
    
    # Test credentials
    login_data = {
        "email": "test@example.com",
        "password": "Test1234"
    }
    
    try:
        # Make login request
        response = requests.post(
            "http://localhost:8000/api/v1/auth/login",
            json=login_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Login successful!")
            print(f"Access token: {data.get('access_token', 'N/A')[:50]}...")
            print(f"User tier: {data.get('user', {}).get('tier', 'N/A')}")
        else:
            print(f"❌ Login failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend. Make sure it's running on http://localhost:8000")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_login()