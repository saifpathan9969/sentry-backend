#!/usr/bin/env python3
"""
Test login with updated password sentry@779969
"""
import requests
import json

def test_login():
    """Test login with updated credentials"""
    print("🔐 Testing login with updated password...")
    
    # Test credentials
    test_emails = [
        'saifullahpathan49@gmail.com',
        'saifullah.pathan24@sanjivani.edu.in'
    ]
    password = 'sentry@779969'
    
    # Backend URL
    base_url = "http://localhost:8000"
    
    for email in test_emails:
        print(f"\n📧 Testing: {email}")
        
        try:
            # Test login
            login_data = {
                "email": email,
                "password": password
            }
            
            response = requests.post(
                f"{base_url}/api/v1/auth/login",
                json=login_data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Login successful!")
                print(f"   Access Token: {result['access_token'][:50]}...")
                print(f"   Refresh Token: {result['refresh_token'][:50]}...")
                
                # Test protected endpoint
                headers = {"Authorization": f"Bearer {result['access_token']}"}
                me_response = requests.get(f"{base_url}/api/v1/users/me", headers=headers)
                
                if me_response.status_code == 200:
                    user_data = me_response.json()
                    print(f"   User: {user_data['email']}")
                    print(f"   Tier: {user_data['tier']}")
                    print(f"   Full Name: {user_data['full_name']}")
                else:
                    print(f"⚠️ Protected endpoint failed: {me_response.status_code}")
                    
            else:
                print(f"❌ Login failed: {response.status_code}")
                print(f"   Error: {response.text}")
                
        except requests.exceptions.ConnectionError:
            print(f"❌ Cannot connect to backend at {base_url}")
            print("   Make sure the backend server is running")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print(f"\n🎯 Test completed!")
    print(f"📝 Your credentials:")
    for email in test_emails:
        print(f"   Email: {email}")
    print(f"   Password: {password}")

if __name__ == "__main__":
    test_login()