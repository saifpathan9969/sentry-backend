#!/usr/bin/env python3
"""
Create a test user for development
"""
import asyncio
import sqlite3
from app.core.security import hash_password
import uuid

async def create_test_user():
    """Create a test user in the database"""
    
    # Test user credentials
    email = "test@example.com"
    password = "Test1234"  # Meets all requirements
    full_name = "Test User"
    
    # Hash the password
    password_hash = hash_password(password)
    
    # Connect to SQLite database
    conn = sqlite3.connect("pentest_brain.db")
    cursor = conn.cursor()
    
    try:
        # Check if user already exists
        cursor.execute("SELECT email FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            print(f"User {email} already exists")
            return
        
        # Insert test user
        user_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO users (id, email, password_hash, full_name, tier, is_active, email_verified, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, (user_id, email, password_hash, full_name, 'free', True, True))
        
        conn.commit()
        print(f"✅ Test user created successfully!")
        print(f"Email: {email}")
        print(f"Password: {password}")
        print(f"Tier: free")
        
    except Exception as e:
        print(f"❌ Error creating test user: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    asyncio.run(create_test_user())