#!/usr/bin/env python3
"""
Test direct login for owner emails
"""
import requests

def test_direct_login():
    """Test login for owner emails"""
    print("🔐 Testing direct login for owner emails...")
    
    # Test emails
    test_accounts = [
        {
            "email": "saifullahpathan49@gmail.com",
            "password": "Test1234"
        },
        {
            "email": "saifullah.pathan24@sanjivani.edu.in", 
            "password": "Test1234"
        }
    ]
    
    for account in test_accounts:
        print(f"\n🧪 Testing login for: {account['email']}")
        
        try:
            response = requests.post(
                "http://localhost:8000/api/v1/auth/login",
                json=account,
                timeout=10
            )
            
            if response.status_code == 200:
                print("✅ Login successful!")
                tokens = response.json()
                print(f"🔑 Access token received: {tokens.get('access_token')[:50]}...")
                print(f"🔄 Refresh token received: {tokens.get('refresh_token')[:50]}...")
            else:
                print(f"❌ Login failed: {response.status_code}")
                print(f"Response: {response.text}")
                
        except Exception as e:
            print(f"❌ Connection error: {e}")
    
    print("\n🎯 If login is successful, you can use these credentials in the frontend!")

if __name__ == "__main__":
    test_direct_login()