#!/usr/bin/env python3
"""
Test authentication directly without HTTP
"""
import asyncio
from app.services.auth_service import AuthService
from app.schemas.auth import UserLogin
from app.db.session import async_session_maker

async def test_auth_direct():
    """Test authentication directly"""
    
    try:
        # Test credentials
        login_data = UserLogin(
            email="test@example.com",
            password="Test1234"
        )
        
        # Create database session
        async with async_session_maker() as db:
            auth_service = AuthService(db)
            
            # Try to login
            result = await auth_service.login(login_data)
            
            print("✅ Direct authentication successful!")
            print(f"Access token: {result.access_token[:50]}...")
            print(f"Token type: {result.token_type}")
            
    except Exception as e:
        print(f"❌ Direct authentication failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_auth_direct())