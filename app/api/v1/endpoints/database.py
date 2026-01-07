"""
Database management endpoints (admin only)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.api.dependencies import get_current_user, get_db
from app.models.user import User

router = APIRouter()


@router.post("/fix-schema")
async def fix_database_schema(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Fix database schema issues (Enterprise users only)
    
    This endpoint adds missing columns to existing tables
    """
    # Only allow enterprise users to run this
    if current_user.tier != "enterprise":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only enterprise users can fix database schema"
        )
    
    try:
        # Check if scans table exists
        result = await db.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='scans'"))
        table_exists = result.fetchone()
        
        if not table_exists:
            return {"error": "Scans table does not exist"}
        
        # Check current table structure
        result = await db.execute(text("PRAGMA table_info(scans)"))
        columns = result.fetchall()
        
        existing_columns = [col[1] for col in columns]
        fixes_applied = []
        
        # Add missing execution_mode column if needed
        if 'execution_mode' not in existing_columns:
            await db.execute(text("ALTER TABLE scans ADD COLUMN execution_mode VARCHAR(20) DEFAULT 'report_only'"))
            await db.commit()
            fixes_applied.append("Added execution_mode column")
        
        # Add missing report_json column if needed
        if 'report_json' not in existing_columns:
            await db.execute(text("ALTER TABLE scans ADD COLUMN report_json TEXT"))
            await db.commit()
            fixes_applied.append("Added report_json column")
        
        return {
            "message": "Database schema check completed",
            "fixes_applied": fixes_applied,
            "existing_columns": existing_columns
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fixing database schema: {str(e)}"
        )


@router.get("/schema-info")
async def get_schema_info(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get database schema information (Enterprise users only)
    """
    # Only allow enterprise users to view schema info
    if current_user.tier != "enterprise":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only enterprise users can view database schema"
        )
    
    try:
        # Get scans table info
        result = await db.execute(text("PRAGMA table_info(scans)"))
        scan_columns = result.fetchall()
        
        # Get users table info
        result = await db.execute(text("PRAGMA table_info(users)"))
        user_columns = result.fetchall()
        
        return {
            "scans_table": [{"name": col[1], "type": col[2], "nullable": not col[3]} for col in scan_columns],
            "users_table": [{"name": col[1], "type": col[2], "nullable": not col[3]} for col in user_columns],
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting schema info: {str(e)}"
        )