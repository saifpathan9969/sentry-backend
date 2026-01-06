#!/usr/bin/env python3
"""
Update owner email passwords to sentry@779969
"""
import sqlite3
from app.core.security import hash_password

def update_owner_passwords():
    """Update passwords for owner emails"""
    print("🔧 Updating owner email passwords...")
    
    # Connect to SQLite database directly
    conn = sqlite3.connect('pentest_brain.db')
    cursor = conn.cursor()
    
    # New password
    new_password = "sentry@779969"
    password_hash = hash_password(new_password)
    
    # Owner emails to update
    owner_emails = [
        'saifullahpathan49@gmail.com',
        'saifullah.pathan24@sanjivani.edu.in'
    ]
    
    for email in owner_emails:
        # Update password for the email
        cursor.execute("""
            UPDATE users 
            SET password_hash = ?, updated_at = datetime('now')
            WHERE email = ?
        """, (password_hash, email))
        
        if cursor.rowcount > 0:
            print(f"✅ Updated password for: {email}")
        else:
            print(f"⚠️ User not found: {email}")
    
    conn.commit()
    conn.close()
    
    print(f"🔑 Password updated to: {new_password}")
    print("🎯 You can now login with:")
    for email in owner_emails:
        print(f"   Email: {email}")
    print(f"   Password: {new_password}")
    print("   Tier: Enterprise (full access)")

if __name__ == "__main__":
    update_owner_passwords()