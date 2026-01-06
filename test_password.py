#!/usr/bin/env python3
"""
Test password verification
"""
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models import User
from app.core.security import verify_password, hash_password

async def test_password():
    """Test password verification"""
    print("🔍 Testing password verification...")
    
    async with AsyncSessionLocal() as db:
        # Get test user
        result = await db.execute(
            select(User).where(User.email == "test@example.com")
        )
        user = result.scalar_one_or_none()
        
        if not user:
            print("❌ User not found!")
            return
            
        print(f"✅ Found user: {user.email}")
        print(f"📧 Email: {user.email}")
        print(f"🔑 Password hash: {user.password_hash[:50]}...")
        print(f"🎯 Tier: {user.tier}")
        print(f"✅ Active: {user.is_active}")
        
        # Test password verification
        test_password = "Test1234"
        print(f"\n🧪 Testing password: {test_password}")
        
        is_valid = verify_password(test_password, user.password_hash)
        print(f"🔐 Password valid: {is_valid}")
        
        if not is_valid:
            print("\n🔧 Creating new password hash...")
            new_hash = hash_password(test_password)
            print(f"🆕 New hash: {new_hash[:50]}...")
            
            # Update user password
            user.password_hash = new_hash
            await db.commit()
            print("✅ Password updated!")
            
            # Test again
            is_valid_new = verify_password(test_password, user.password_hash)
            print(f"🔐 New password valid: {is_valid_new}")

if __name__ == "__main__":
    asyncio.run(test_password())