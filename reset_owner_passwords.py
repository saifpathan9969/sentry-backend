#!/usr/bin/env python3
"""
Reset owner passwords via API call
"""
import asyncio
import sys
import os
from datetime import datetime
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import select, update
from app.db.session import AsyncSessionLocal
from app.models.user import User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def reset_owner_passwords():
    """Reset owner passwords to Sentry@779969"""
    
    owner_emails = [
        "saifullahpathan49@gmail.com",
        "saifullah.pathan24@sanjivani.edu.in"
    ]
    
    correct_password = "Sentry@779969"
    hashed_password = pwd_context.hash(correct_password)
    
    async with AsyncSessionLocal() as db:
        try:
            for email in owner_emails:
                print(f"Resetting password for: {email}")
                
                # Update password for existing user
                result = await db.execute(
                    update(User)
                    .where(User.email == email)
                    .values(
                        password_hash=hashed_password,
                        tier="enterprise",
                        is_active=True,
                        email_verified=True
                    )
                )
                
                if result.rowcount > 0:
                    print(f"  ✅ Password reset for: {email}")
                else:
                    print(f"  ❌ User not found: {email}")
            
            await db.commit()
            print(f"\n🎉 Password reset complete!")
            print(f"📧 Both accounts now use password: {correct_password}")
            
        except Exception as e:
            print(f"❌ Error resetting passwords: {e}")
            await db.rollback()
            raise

if __name__ == "__main__":
    asyncio.run(reset_owner_passwords())