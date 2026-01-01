"""
Subscription management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_active_user, get_db
from app.models.user import User
from app.models.subscription import SubscriptionTier
from app.schemas.subscription import (
    CheckoutSessionCreate,
    CheckoutSessionResponse,
    SubscriptionResponse,
    SubscriptionCancelResponse,
)
from app.services.subscription_service import SubscriptionService

router = APIRouter()


@router.post("/checkout", response_model=CheckoutSessionResponse, status_code=201)
async def create_checkout_session(
    checkout_data: CheckoutSessionCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a Stripe checkout session for subscription
    
    - Creates a Stripe checkout session
    - Redirects user to Stripe payment page
    - Returns session ID and URL
    """
    session = await SubscriptionService.create_checkout_session(
        db, current_user, checkout_data
    )
    return session


@router.get("/current", response_model=SubscriptionResponse)
async def get_current_subscription(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get current active subscription for user
    
    - Returns subscription details
    - Returns 404 if no active subscription
    """
    subscription = await SubscriptionService.get_subscription(db, current_user.id)
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )
    
    return subscription


@router.post("/cancel", response_model=SubscriptionCancelResponse)
async def cancel_subscription(
    immediate: bool = False,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Cancel current subscription
    
    - immediate=False: Cancel at period end (default)
    - immediate=True: Cancel immediately
    - Returns cancellation details
    """
    subscription = await SubscriptionService.cancel_subscription(
        db, current_user, immediate
    )
    
    message = (
        "Subscription cancelled immediately"
        if immediate
        else "Subscription will be cancelled at the end of the billing period"
    )
    
    return SubscriptionCancelResponse(
        message=message,
        cancel_at_period_end=subscription.cancel_at_period_end,
        period_end=subscription.current_period_end,
    )


@router.post("/resume", response_model=SubscriptionResponse)
async def resume_subscription(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Resume a subscription that was set to cancel at period end
    
    - Only works if subscription is set to cancel at period end
    - Returns updated subscription
    """
    subscription = await SubscriptionService.resume_subscription(db, current_user)
    return subscription


@router.post("/upgrade", response_model=SubscriptionResponse)
async def upgrade_subscription(
    new_tier: SubscriptionTier,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upgrade subscription to a higher tier
    
    - Premium → Enterprise
    - Charges prorated amount immediately
    - Takes effect immediately
    """
    subscription = await SubscriptionService.upgrade_subscription(
        db, current_user, new_tier
    )
    return subscription


@router.post("/downgrade", response_model=SubscriptionResponse)
async def downgrade_subscription(
    new_tier: SubscriptionTier,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Downgrade subscription to a lower tier
    
    - Enterprise → Premium
    - Takes effect at end of billing period
    - No immediate charge
    """
    subscription = await SubscriptionService.downgrade_subscription(
        db, current_user, new_tier
    )
    return subscription
