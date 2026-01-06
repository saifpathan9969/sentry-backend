#!/usr/bin/env python3
"""
Fix authentication issue by recreating users with proper passwords
"""
import asyncio
import sqlite3
from app.core.security import hash_password

def fix_auth_issue():
    """Fix authentication by recreating users with proper passwords"""
    print("🔧 Fixing authentication issue...")
    
    # Connect to SQLite database directly
    conn = sqlite3.connect('pentest_brain.db')
    cursor = conn.cursor()
    
    # Delete existing users
    cursor.execute("DELETE FROM users")
    print("🗑️ Cleared existing users")
    
    # Create test users with proper password hashes
    test_password = "Test1234"
    password_hash = hash_password(test_password)
    
    users = [
        {
            'id': '550e8400-e29b-41d4-a716-446655440001',
            'email': 'saifullahpathan49@gmail.com',
            'full_name': 'Saifullah Pathan',
            'tier': 'enterprise',
            'password_hash': password_hash,
            'is_active': 1,
            'email_verified': 1
        },
        {
            'id': '550e8400-e29b-41d4-a716-446655440002',
            'email': 'saifullah.pathan24@sanjivani.edu.in',
            'full_name': 'Saifullah Pathan',
            'tier': 'enterprise',
            'password_hash': password_hash,
            'is_active': 1,
            'email_verified': 1
        },
        {
            'id': '550e8400-e29b-41d4-a716-446655440003',
            'email': 'test@example.com',
            'full_name': 'Test User',
            'tier': 'free',
            'password_hash': password_hash,
            'is_active': 1,
            'email_verified': 1
        }
    ]
    
    # Insert users
    for user in users:
        cursor.execute("""
            INSERT INTO users (id, email, password_hash, full_name, tier, 
                             created_at, updated_at, is_active, email_verified)
            VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'), ?, ?)
        """, (
            user['id'], user['email'], user['password_hash'], 
            user['full_name'], user['tier'], user['is_active'], user['email_verified']
        ))
        print(f"✅ Created user: {user['email']} ({user['tier']})")
    
    conn.commit()
    conn.close()
    
    print(f"🔑 All users created with password: {test_password}")
    print("✅ Authentication issue fixed!")

if __name__ == "__main__":
    fix_auth_issue()