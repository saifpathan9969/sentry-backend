"""
Scan management endpoints
"""
from fastapi import APIRouter, Depends, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.api.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.scan import (
    ScanCreate,
    ScanResponse,
    ScanListResponse,
    ScanReportResponse,
)
from app.services.scan_service import ScanService

router = APIRouter()


@router.post("/", response_model=ScanResponse, status_code=201)
async def create_scan(
    scan_data: ScanCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new security scan
    
    - Validates tier-based access (scan limits and mode restrictions)
    - Creates scan with "queued" status
    - Enqueues scan for background processing
    """
    scan = await ScanService.create_scan(db, current_user, scan_data)
    return scan


@router.get("/", response_model=ScanListResponse)
async def list_scans(
    limit: int = Query(50, ge=1, le=100, description="Number of scans to return"),
    offset: int = Query(0, ge=0, description="Number of scans to skip"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all scans for the current user
    
    - Returns scans ordered by creation date (newest first)
    - Supports pagination
    - Applies tier-based retention filtering
    """
    scans, total = await ScanService.list_scans(
        db, current_user.id, current_user.tier, limit, offset
    )
    
    return ScanListResponse(
        scans=scans,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{scan_id}", response_model=ScanResponse)
async def get_scan(
    scan_id: UUID = Path(..., description="Scan ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get details of a specific scan
    
    - Returns scan metadata and vulnerability counts
    - Only accessible by scan owner
    """
    scan = await ScanService.get_scan(db, scan_id, current_user.id)
    return scan


@router.delete("/{scan_id}", status_code=204)
async def delete_scan(
    scan_id: UUID = Path(..., description="Scan ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a scan and its associated reports
    
    - Only accessible by scan owner
    - Permanently removes scan data
    """
    await ScanService.delete_scan(db, scan_id, current_user.id)
    return None


@router.get("/{scan_id}/report", response_model=ScanReportResponse)
async def get_scan_report(
    scan_id: UUID = Path(..., description="Scan ID"),
    format: str = Query("json", pattern="^(json|text)$", description="Report format"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get scan report in JSON or TEXT format
    
    - Only available for completed scans
    - Only accessible by scan owner
    """
    report = await ScanService.get_scan_report(db, scan_id, current_user.id, format)
    
    return ScanReportResponse(
        scan_id=scan_id,
        format=format,
        report=report,
    )


@router.post("/{scan_id}/cancel", response_model=ScanResponse)
async def cancel_scan(
    scan_id: UUID = Path(..., description="Scan ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Cancel a queued or running scan
    
    - Only works for scans in "queued" or "running" status
    - Only accessible by scan owner
    """
    scan = await ScanService.cancel_scan(db, scan_id, current_user.id)
    return scan
