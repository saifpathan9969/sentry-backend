"""
Tier-related schemas
"""
from pydantic import BaseModel


class TierLimits(BaseModel):
    """Tier limits information"""
    tier: str  # 'free', 'premium', or 'enterprise'
    scans_per_day: int | None  # None means unlimited
    allowed_scan_modes: list[str]
    rate_limit_per_hour: int | None  # None means unlimited
    scan_history_days: int | None  # None means unlimited
    
    class Config:
        from_attributes = True


class TierCheckResponse(BaseModel):
    """Response for tier check"""
    allowed: bool
    reason: str | None = None
    current_usage: int | None = None
    limit: int | None = None
