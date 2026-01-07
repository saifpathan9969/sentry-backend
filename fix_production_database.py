#!/usr/bin/env python3
"""
Fix the production database schema on Render
"""
import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.session import async_session_maker
from sqlalchemy import text


async def fix_production_database():
    """Fix production database schema"""
    print("🔧 Fixing production database schema...")
    
    try:
        async with async_session_maker() as db:
            # Check if scans table exists
            result = await db.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='scans'"))
            table_exists = result.fetchone()
            
            if not table_exists:
                print("❌ Scans table does not exist")
                return
            
            # Check current table structure
            result = await db.execute(text("PRAGMA table_info(scans)"))
            columns = result.fetchall()
            
            print("📋 Current scan table columns:")
            existing_columns = []
            for col in columns:
                print(f"   - {col[1]} ({col[2]})")
                existing_columns.append(col[1])
            
            # Add missing execution_mode column if needed
            if 'execution_mode' not in existing_columns:
                print("➕ Adding execution_mode column...")
                await db.execute(text("ALTER TABLE scans ADD COLUMN execution_mode VARCHAR(20) DEFAULT 'report_only'"))
                await db.commit()
                print("   ✅ Added execution_mode column")
            else:
                print("   ✅ execution_mode column already exists")
            
            # Add missing report_json column if needed (as JSON type for SQLite)
            if 'report_json' not in existing_columns:
                print("➕ Adding report_json column...")
                await db.execute(text("ALTER TABLE scans ADD COLUMN report_json TEXT"))
                await db.commit()
                print("   ✅ Added report_json column")
            else:
                print("   ✅ report_json column already exists")
            
            print("\n🎉 Production database schema updated successfully!")
            
    except Exception as e:
        print(f"❌ Error fixing production database: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(fix_production_database())