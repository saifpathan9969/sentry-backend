#!/usr/bin/env python3
"""
Create users using simple SQLite approach
"""
import sqlite3
import uuid
from datetime import datetime
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, '/app')

from app.core.security import hash_password

def create_users():
    """Create users using simple SQLite"""
    print("🔧 Creating users with simple SQLite...")
    
    # Connect to SQLite database
    conn = sqlite3.connect('pentest_brain.db')
    cursor = conn.cursor()
    
    # Users to create
    users = [
        {
            'email': 'saifullahpathan49@gmail.com',
            'password': 'sentry@779969',
            'full_name': 'Saifullah Pathan',
            'tier': 'enterprise'
        },
        {
            'email': 'saifullah.pathan24@sanjivani.edu.in',
            'password': 'sentry@779969',
            'full_name': 'Saifullah Pathan',
            'tier': 'enterprise'
        },
        {
            'email': 'test@example.com',
            'password': 'Test1234',
            'full_name': 'Test User',
            'tier': 'free'
        }
    ]
    
    for user in users:
        user_id = str(uuid.uuid4())
        password_hash = hash_password(user['password'])
        now = datetime.now().isoformat()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO users 
                (id, email, password_hash, full_name, tier, is_active, email_verified, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 1, 1, ?, ?)
            ''', (
                user_id,
                user['email'],
                password_hash,
                user['full_name'],
                user['tier'],
                now,
                now
            ))
            
            print(f"✅ Created user: {user['email']} (Tier: {user['tier']})")
            
        except Exception as e:
            print(f"❌ Error creating user {user['email']}: {e}")
    
    conn.commit()
    
    # Verify users were created
    cursor.execute('SELECT email, tier, full_name FROM users')
    all_users = cursor.fetchall()
    
    print(f"\n📊 Total users in database: {len(all_users)}")
    for user in all_users:
        print(f"   {user[0]} - {user[1]} - {user[2]}")
    
    conn.close()
    
    print(f"\n🎯 Users created successfully!")
    print(f"🔑 Your credentials:")
    print(f"   Email: saifullahpathan49@gmail.com")
    print(f"   Email: saifullah.pathan24@sanjivani.edu.in")
    print(f"   Password: sentry@779969")
    print(f"   Tier: Enterprise (Full Access)")

if __name__ == "__main__":
    create_users()