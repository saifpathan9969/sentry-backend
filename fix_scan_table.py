#!/usr/bin/env python3
"""
Fix the scan table schema by adding missing columns
"""
import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.session import async_session_maker
from sqlalchemy import text


async def fix_scan_table():
    """Add missing columns to the scan table"""
    print("🔧 Fixing scan table schema...")
    
    try:
        async with async_session_maker() as db:
            # Check current table structure
            result = await db.execute(text("PRAGMA table_info(scans)"))
            columns = result.fetchall()
            
            print("📋 Current scan table columns:")
            existing_columns = []
            for col in columns:
                print(f"   - {col[1]} ({col[2]})")
                existing_columns.append(col[1])
            
            # List of required columns with their definitions
            required_columns = {
                'execution_mode': "ALTER TABLE scans ADD COLUMN execution_mode VARCHAR(20) DEFAULT 'report_only'",
                'report_json': "ALTER TABLE scans ADD COLUMN report_json JSON",
            }
            
            # Add missing columns
            for column_name, alter_sql in required_columns.items():
                if column_name not in existing_columns:
                    print(f"➕ Adding missing column: {column_name}")
                    await db.execute(text(alter_sql))
                    await db.commit()
                    print(f"   ✅ Added {column_name}")
                else:
                    print(f"   ✅ Column {column_name} already exists")
            
            # Verify the fix
            result = await db.execute(text("PRAGMA table_info(scans)"))
            columns = result.fetchall()
            
            print("\n📋 Updated scan table columns:")
            for col in columns:
                print(f"   - {col[1]} ({col[2]})")
            
            print("\n🎉 Scan table schema fixed successfully!")
            
    except Exception as e:
        print(f"❌ Error fixing scan table: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(fix_scan_table())