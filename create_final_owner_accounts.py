#!/usr/bin/env python3
"""
Final owner account creation script - DEFINITIVE VERSION
This will create/update owner accounts with the correct password
"""
import asyncio
import sys
import os
from datetime import datetime
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import select, delete
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.models.subscription import Subscription
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def create_final_owner_accounts():
    """Create owner accounts with correct password"""
    
    owner_emails = [
        "saifullahpathan49@gmail.com",
        "saifullah.pathan24@sanjivani.edu.in"
    ]
    
    correct_password = "Sentry@779969"
    hashed_password = pwd_context.hash(correct_password)
    
    async with AsyncSessionLocal() as db:
        try:
            for email in owner_emails:
                print(f"Processing owner account: {email}")
                
                # Delete existing user if exists
                existing_user_query = select(User).where(User.email == email)
                result = await db.execute(existing_user_query)
                existing_user = result.scalar_one_or_none()
                
                if existing_user:
                    print(f"  - Deleting existing user: {email}")
                    # Delete subscriptions first
                    await db.execute(delete(Subscription).where(Subscription.user_id == existing_user.id))
                    # Delete user
                    await db.execute(delete(User).where(User.id == existing_user.id))
                    await db.commit()
                
                # Create new user with correct password
                print(f"  - Creating new user: {email}")
                user = User(
                    email=email,
                    password_hash=hashed_password,
                    full_name="Owner Account",
                    tier="enterprise",
                    is_active=True,
                    email_verified=True
                )
                db.add(user)
                await db.flush()  # Get the user ID
                
                # Create enterprise subscription
                subscription = Subscription(
                    user_id=user.id,
                    stripe_subscription_id=f"sub_owner_{user.id[:8]}",
                    stripe_customer_id=f"cus_owner_{user.id[:8]}",
                    tier="enterprise",
                    status="active",
                    current_period_start=datetime.utcnow(),
                    current_period_end=datetime.utcnow().replace(year=datetime.utcnow().year + 10),  # 10 years
                    cancel_at_period_end=False
                )
                db.add(subscription)
                
                print(f"  ✅ Created owner account: {email} with Enterprise tier")
            
            await db.commit()
            print("\n🎉 All owner accounts created successfully!")
            print(f"📧 Email: saifullahpathan49@gmail.com")
            print(f"🔑 Password: {correct_password}")
            print(f"📧 Email: saifullah.pathan24@sanjivani.edu.in")
            print(f"🔑 Password: {correct_password}")
            
        except Exception as e:
            print(f"❌ Error creating owner accounts: {e}")
            await db.rollback()
            raise

if __name__ == "__main__":
    asyncio.run(create_final_owner_accounts())