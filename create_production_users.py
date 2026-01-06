#!/usr/bin/env python3
"""
Create production users on live database
"""
import asyncio
import asyncpg
from app.core.security import hash_password
import uuid
import os

async def create_production_users():
    """Create production users on Neon PostgreSQL"""
    
    # Production database connection
    DATABASE_URL = "postgresql://neondb_owner:npg_2EA9gjUvaZry@ep-small-silence-a4op8mv6-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require"
    
    try:
        # Connect to database
        conn = await asyncpg.connect(DATABASE_URL)
        print("✅ Connected to production database")
        
        # Users to create
        users = [
            {
                "email": "saifullahpathan49@gmail.com",
                "password": "Test1234",
                "full_name": "Saifullah Pathan",
                "tier": "enterprise"
            },
            {
                "email": "saifullah.pathan24@sanjivani.edu.in", 
                "password": "Test1234",
                "full_name": "Saifullah Pathan",
                "tier": "enterprise"
            },
            {
                "email": "test@example.com",
                "password": "Test1234", 
                "full_name": "Test User",
                "tier": "free"
            }
        ]
        
        for user_data in users:
            # Check if user exists
            existing = await conn.fetchrow(
                "SELECT email FROM users WHERE email = $1", 
                user_data["email"]
            )
            
            if existing:
                print(f"⚠️  User {user_data['email']} already exists")
                continue
            
            # Hash password
            password_hash = hash_password(user_data["password"])
            user_id = str(uuid.uuid4())
            
            # Insert user
            await conn.execute("""
                INSERT INTO users (id, email, password_hash, full_name, tier, is_active, email_verified, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
            """, user_id, user_data["email"], password_hash, user_data["full_name"], 
                user_data["tier"], True, True)
            
            print(f"✅ Created user: {user_data['email']} ({user_data['tier']} tier)")
        
        # Verify users
        users_count = await conn.fetchval("SELECT COUNT(*) FROM users")
        print(f"📊 Total users in database: {users_count}")
        
        await conn.close()
        print("✅ Production users setup complete!")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(create_production_users())