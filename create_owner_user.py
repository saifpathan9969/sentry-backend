#!/usr/bin/env python3
"""
Create owner user with enterprise tier
"""
import asyncio
import sqlite3
from app.core.security import hash_password
import uuid

async def create_owner_user():
    """Create owner user in the database"""
    
    # Owner credentials
    email = "saifullahpathan49@gmail.com"  # Your owner email
    password = "Test1234"  # You can change this
    full_name = "Saifullah Pathan"
    
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
        
        # Insert owner user with enterprise tier
        user_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO users (id, email, password_hash, full_name, tier, is_active, email_verified, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, (user_id, email, password_hash, full_name, 'enterprise', True, True))
        
        conn.commit()
        print(f"✅ Owner user created successfully!")
        print(f"Email: {email}")
        print(f"Password: {password}")
        print(f"Tier: enterprise (full access)")
        
    except Exception as e:
        print(f"❌ Error creating owner user: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    asyncio.run(create_owner_user())