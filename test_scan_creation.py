#!/usr/bin/env python3
"""
Test scan creation locally to debug issues
"""
import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.session import async_session_maker
from app.models.user import User
from app.models.scan import Scan
from app.services.scan_service import ScanService
from app.schemas.scan import ScanCreate
from sqlalchemy import select


async def test_scan_creation():
    """Test scan creation process"""
    print("🔍 Testing scan creation process...")
    
    try:
        async with async_session_maker() as db:
            # Get a test user
            result = await db.execute(
                select(User).where(User.email == "saifullahpathan49@gmail.com")
            )
            user = result.scalar_one_or_none()
            
            if not user:
                print("❌ Test user not found")
                return
            
            print(f"✅ Found test user: {user.email} (ID: {user.id})")
            
            # Create scan data
            scan_data = ScanCreate(
                target_url="https://httpbin.org",
                scan_mode="fast",
                execution_mode="report_only"
            )
            
            print(f"📝 Creating scan for target: {scan_data.target_url}")
            
            # Try to create scan
            scan = await ScanService.create_scan(db, user, scan_data)
            
            print(f"✅ Scan created successfully!")
            print(f"   ID: {scan.id}")
            print(f"   Target: {scan.target}")
            print(f"   Status: {scan.status}")
            print(f"   Mode: {scan.scan_mode}")
            print(f"   Execution: {scan.execution_mode}")
            
    except Exception as e:
        print(f"❌ Error creating scan: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_scan_creation())