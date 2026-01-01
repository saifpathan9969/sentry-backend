"""Test registration directly"""
import asyncio
import sys
import os

# Set the working directory to backend
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, '.')

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from app.db.session import AsyncSessionLocal
from app.services.auth_service import AuthService
from app.schemas.auth import UserRegister

async def test_register():
    try:
        async with AsyncSessionLocal() as db:
            auth_service = AuthService(db)
            user_data = UserRegister(email="test_new_user@example.com", password="Test123!")
            user = await auth_service.register_user(user_data)
            print(f"User created: {user.id}, {user.email}, {user.tier}")
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_register())
