#!/usr/bin/env python3
"""
Add owner emails with Enterprise tier access
"""
import sqlite3
import uuid
from app.core.security import hash_password

def add_owner_emails():
    """Add owner emails with Enterprise tier"""
    print("🔧 Adding owner emails with Enterprise tier...")
    
    # Connect to SQLite database directly
    conn = sqlite3.connect('pentest_brain.db')
    cursor = conn.cursor()
    
    # Password for owner accounts
    password = "Test1234"
    password_hash = hash_password(password)
    
    # Owner emails to add
    owner_emails = [
        {
            'email': 'saifullahpathan49@gmail.com',
            'full_name': 'Saifullah Pathan',
            'tier': 'enterprise'
        },
        {
            'email': 'saifullah.pathan24@sanjivani.edu.in', 
            'full_name': 'Saifullah Pathan',
            'tier': 'enterprise'
        }
    ]
    
    for owner in owner_emails:
        # Check if user already exists
        cursor.execute("SELECT id FROM users WHERE email = ?", (owner['email'],))
        existing = cursor.fetchone()
        
        if existing:
            # Update existing user to Enterprise tier
            cursor.execute("""
                UPDATE users 
                SET tier = ?, full_name = ?, password_hash = ?, is_active = 1, email_verified = 1
                WHERE email = ?
            """, (owner['tier'], owner['full_name'], password_hash, owner['email']))
            print(f"✅ Updated existing user: {owner['email']} → {owner['tier']}")
        else:
            # Create new user
            user_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO users (id, email, password_hash, full_name, tier, 
                                 created_at, updated_at, is_active, email_verified)
                VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'), 1, 1)
            """, (
                user_id, owner['email'], password_hash, 
                owner['full_name'], owner['tier']
            ))
            print(f"✅ Created new user: {owner['email']} ({owner['tier']})")
    
    conn.commit()
    conn.close()
    
    print(f"🔑 Owner accounts ready with password: {password}")
    print("🎯 You can now login with:")
    for owner in owner_emails:
        print(f"   Email: {owner['email']}")
    print(f"   Password: {password}")
    print("   Tier: Enterprise (full access)")

if __name__ == "__main__":
    add_owner_emails()