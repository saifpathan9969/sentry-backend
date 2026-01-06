#!/usr/bin/env python3
"""
Test owner email registration
"""
import requests

def test_owner_registration():
    """Test registering with owner email"""
    print("🧪 Testing owner email registration...")
    
    # Test registration with owner email
    registration_data = {
        "first_name": "Saifullah",
        "last_name": "Pathan", 
        "email": "saifullahpathan49@gmail.com",
        "password": "Test1234"
    }
    
    try:
        response = requests.post(
            "http://localhost:8000/api/v1/auth/register",
            json=registration_data,
            timeout=10
        )
        
        if response.status_code == 201:
            print("✅ Registration successful!")
            user_data = response.json()
            print(f"📧 Email: {user_data.get('email')}")
            print(f"🎯 Tier: {user_data.get('tier')}")
            print(f"👤 Name: {user_data.get('full_name')}")
        elif response.status_code == 400:
            print("⚠️ User already exists (this is expected)")
            print("✅ You can login with existing credentials")
        else:
            print(f"❌ Registration failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Connection error: {e}")
        print("Make sure backend is running on http://localhost:8000")

if __name__ == "__main__":
    test_owner_registration()