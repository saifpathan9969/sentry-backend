"""
Subscription-related schemas
"""
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from typing import Optional

from app.models.subscription import SubscriptionTier, SubscriptionStatus


class CheckoutSessionCreate(BaseModel):
    """Schema for creating a Stripe checkout session"""
    tier: SubscriptionTier
    success_url: str
    cancel_url: str


class CheckoutSessionResponse(BaseModel):
    """Schema for checkout session response"""
    session_id: str
    url: str


class SubscriptionResponse(BaseModel):
    """Schema for subscription response"""
    id: UUID
    user_id: UUID
    stripe_subscription_id: str
    stripe_customer_id: str
    tier: SubscriptionTier
    status: SubscriptionStatus
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class SubscriptionUpdate(BaseModel):
    """Schema for subscription update"""
    tier: Optional[SubscriptionTier] = None
    cancel_at_period_end: Optional[bool] = None


class SubscriptionCancelResponse(BaseModel):
    """Schema for subscription cancellation response"""
    message: str
    cancel_at_period_end: bool
    period_end: datetime
