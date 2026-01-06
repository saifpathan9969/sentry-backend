"""
Scan-related schemas
"""
from pydantic import BaseModel, field_validator
from datetime import datetime
from uuid import UUID


class ScanCreate(BaseModel):
    """Schema for creating a new scan"""
    target_url: str  # Changed from HttpUrl to str for more flexibility
    scan_mode: str = "common"
    execution_mode: str = "report_only"
    
    @field_validator('target_url')
    @classmethod
    def validate_target_url(cls, v):
        """Validate and normalize target URL"""
        if not v:
            raise ValueError("target_url is required")
        
        # Add protocol if missing
        if not v.startswith(('http://', 'https://')):
            v = f'https://{v}'
        
        # Basic URL validation
        if not any(char in v for char in ['.', ':']):
            raise ValueError("Invalid URL format")
            
        return v
    
    @field_validator('scan_mode')
    @classmethod
    def validate_scan_mode(cls, v):
        allowed_modes = ["common", "fast", "full", "stealth", "aggressive", "custom"]
        if v not in allowed_modes:
            raise ValueError(f"scan_mode must be one of {allowed_modes}")
        return v
    
    @field_validator('execution_mode')
    @classmethod
    def validate_execution_mode(cls, v):
        allowed_modes = ["report_only", "dry_run", "apply_fixes"]
        if v not in allowed_modes:
            raise ValueError(f"execution_mode must be one of {allowed_modes}")
        return v


class ScanResponse(BaseModel):
    """Schema for scan response"""
    id: UUID
    user_id: UUID
    target: str
    scan_mode: str
    execution_mode: str = "report_only"
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
