#!/usr/bin/env python3
"""
Check users in database
"""
import sqlite3

def check_users():
    """Check what users exist in the database"""
    
    try:
        conn = sqlite3.connect("pentest_brain.db")
        cursor = conn.cursor()
        
        # Check if users table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users';")
        if not cursor.fetchone():
            print("❌ Users table does not exist!")
            return
        
        # Get all users
        cursor.execute("SELECT email, full_name, tier, is_active, email_verified FROM users")
        users = cursor.fetchall()
        
        if not users:
            print("❌ No users found in database!")
        else:
            print(f"✅ Found {len(users)} users:")
            for user in users:
                email, full_name, tier, is_active, email_verified = user
                print(f"  - Email: {email}")
                print(f"    Name: {full_name}")
                print(f"    Tier: {tier}")
                print(f"    Active: {is_active}")
                print(f"    Verified: {email_verified}")
                print()
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error checking users: {e}")

if __name__ == "__main__":
    check_users()