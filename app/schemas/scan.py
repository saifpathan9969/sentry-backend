"""
Scan-related schemas
"""
from pydantic import BaseModel, HttpUrl, field_validator
from datetime import datetime
from uuid import UUID


class ScanCreate(BaseModel):
    """Schema for creating a new scan"""
    target_url: HttpUrl
    scan_mode: str = "common"
    
    @field_validator('scan_mode')
    @classmethod
    def validate_scan_mode(cls, v):
        allowed_modes = ["common", "fast", "full", "stealth", "aggressive", "custom"]
        if v not in allowed_modes:
            raise ValueError(f"scan_mode must be one of {allowed_modes}")
        return v


class ScanResponse(BaseModel):
    """Schema for scan response"""
    id: UUID
    user_id: UUID
    target: str
    scan_mode: str
    status: str  # 'queued', 'running', 'completed', 'failed', 'cancelled'
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    
    # Vulnerability counts
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    
    class Config:
        from_attributes = True


class ScanListResponse(BaseModel):
    """Schema for paginated scan list"""
    scans: list[ScanResponse]
    total: int
    limit: int
    offset: int


class ScanReportResponse(BaseModel):
    """Schema for scan report"""
    scan_id: UUID
    format: str
    report: str
