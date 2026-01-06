#!/usr/bin/env python3
"""
Simple authentication test using direct SQLite
"""
import sqlite3
import requests
from app.core.security import verify_password

def test_simple_auth():
    """Test authentication with direct database access"""
    print("🔍 Testing simple authentication...")
    
    # Connect to database directly
    conn = sqlite3.connect('pentest_brain.db')
    cursor = conn.cursor()
    
    # Get user
    cursor.execute("SELECT email, password_hash, tier FROM users WHERE email = ?", ("test@example.com",))
    result = cursor.fetchone()
    
    if not result:
        print("❌ User not found!")
        return
    
    email, password_hash, tier = result
    print(f"✅ Found user: {email} ({tier})")
    
    # Test password
    test_password = "Test1234"
    is_valid = verify_password(test_password, password_hash)
    print(f"🔐 Password valid: {is_valid}")
    
    conn.close()
    
    if is_valid:
        print("✅ Authentication working!")
        print("🎯 You can now login with:")
        print(f"   Email: {email}")
        print(f"   Password: {test_password}")
    else:
        print("❌ Password verification failed!")

if __name__ == "__main__":
    test_simple_auth()