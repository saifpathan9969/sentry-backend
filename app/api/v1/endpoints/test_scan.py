"""
Test scan endpoints for debugging
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db
from app.models.user import User
from app.models.scan import Scan
from app.schemas.scan import ScanCreate
import uuid
from datetime import datetime

router = APIRouter()


@router.post("/test-create")
async def test_scan_creation(
    scan_data: ScanCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Test scan creation without worker (Enterprise users only)
    """
    # Only allow enterprise users
    if current_user.tier != "enterprise":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only enterprise users can test scan creation"
        )
    
    try:
        # Create scan directly without service layer
        scan = Scan(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            target=str(scan_data.target_url),
            scan_mode=scan_data.scan_mode,
            execution_mode=scan_data.execution_mode,
            status='queued',
            created_at=datetime.utcnow(),
        )
        
        db.add(scan)
        await db.commit()
        await db.refresh(scan)
        
        return {
            "message": "Test scan created successfully",
            "scan": {
                "id": scan.id,
                "target": scan.target,
                "scan_mode": scan.scan_mode,
                "execution_mode": scan.execution_mode,
                "status": scan.status,
                "user_id": scan.user_id,
                "created_at": scan.created_at.isoformat() if scan.created_at else None
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating test scan: {str(e)}"
        )


@router.get("/debug-info")
async def get_debug_info(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get debug information (Enterprise users only)
    """
    # Only allow enterprise users
    if current_user.tier != "enterprise":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only enterprise users can view debug info"
        )
    
    try:
        from app.core.config import settings
        
        return {
            "user": {
                "id": current_user.id,
                "email": current_user.email,
                "tier": current_user.tier,
                "is_active": current_user.is_active
            },
            "environment": {
                "environment": settings.ENVIRONMENT,
                "database_url": settings.DATABASE_URL[:50] + "..." if len(settings.DATABASE_URL) > 50 else settings.DATABASE_URL,
            },
            "message": "Debug info retrieved successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting debug info: {str(e)}"
        )