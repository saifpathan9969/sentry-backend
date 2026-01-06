#!/usr/bin/env python3
"""
Create production owner users for Railway deployment
"""
import asyncio
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, '/app' if os.path.exists('/app') else '.')

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from app.models.user import User
from app.core.security import hash_password
from app.core.config import settings
from app.db.base import Base

async def create_production_owners():
    """Create production owner users"""
    print("🔧 Creating production owner users...")
    
    # Create async engine
    database_url = settings.DATABASE_URL
    print(f"📊 Database URL: {database_url[:50]}...")
    
    engine = create_async_engine(
        database_url,
        echo=False,
        future=True,
    )
    
    # Create all tables first
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database tables created")
    
    # Create session factory
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False
    )
    
    # Owner users to create
    owners = [
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
        }
    ]
    
    async with AsyncSessionLocal() as session:
        try:
            for owner_data in owners:
                # Check if user exists
                result = await session.execute(
                    select(User).where(User.email == owner_data['email'])
                )
                existing_user = result.scalar_one_or_none()
                
                if existing_user:
                    # Update existing user
                    existing_user.password_hash = hash_password(owner_data['password'])
                    existing_user.full_name = owner_data['full_name']
                    existing_user.tier = owner_data['tier']
                    existing_user.is_active = True
                    existing_user.email_verified = True
                    print(f"✅ Updated owner: {owner_data['email']}")
                else:
                    # Create new user
                    user = User(
                        email=owner_data['email'],
                        password_hash=hash_password(owner_data['password']),
                        full_name=owner_data['full_name'],
                        tier=owner_data['tier'],
                        is_active=True,
                        email_verified=True
                    )
                    session.add(user)
                    print(f"✅ Created owner: {owner_data['email']}")
            
            await session.commit()
            
            # Verify users
            result = await session.execute(select(User))
            all_users = result.scalars().all()
            
            print(f"\n📊 Total users in database: {len(all_users)}")
            for user in all_users:
                print(f"   {user.email} - {user.tier} - {user.full_name}")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Error: {e}")
            raise
        finally:
            await session.close()
    
    await engine.dispose()
    
    print(f"\n🎯 Production owners created successfully!")
    print(f"🔑 Login credentials:")
    print(f"   Email: saifullahpathan49@gmail.com")
    print(f"   Email: saifullah.pathan24@sanjivani.edu.in")
    print(f"   Password: sentry@779969")
    print(f"   Tier: Enterprise (Full Access)")

if __name__ == "__main__":
    asyncio.run(create_production_owners())