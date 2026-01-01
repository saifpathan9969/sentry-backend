"""
API Key schemas for request/response validation
"""
from pydantic import BaseModel
from datetime import datetime


class APIKeyResponse(BaseModel):
    """Schema for API key response (only shown once)"""
    api_key: str
    message: str = "Store this API key securely. It will not be shown again."


class APIKeyInfo(BaseModel):
    """Schema for API key information (without the actual key)"""
    has_api_key: bool
    created_at: datetime | None = None
    
    class Config:
        from_attributes = True
