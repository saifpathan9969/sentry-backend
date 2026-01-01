"""
Subscription service for managing Stripe subscriptions
"""
import stripe
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from datetime import datetime
from typing import Optional

from app.core.config import settings
from app.models.user import User, UserTier
from app.models.subscription import Subscription, SubscriptionTier, SubscriptionStatus
from app.schemas.subscription import CheckoutSessionCreate, CheckoutSessionResponse
from fastapi import HTTPException, status

# Configure Stripe
stripe.api_key = settings.STRIPE_API_KEY


class SubscriptionService:
    """Service for subscription management"""
    
    # Stripe price IDs (these would be configured in Stripe dashboard)
    PRICE_IDS = {
        SubscriptionTier.PREMIUM: "price_premium_monthly",  # Replace with actual Stripe price ID
        SubscriptionTier.ENTERPRISE: "price_enterprise_monthly",  # Replace with actual Stripe price ID
    }
    
    @classmethod
    async def create_checkout_session(
        cls,
        db: AsyncSession,
        user: User,
        checkout_data: CheckoutSessionCreate,
    ) -> CheckoutSessionResponse:
        """
        Create a Stripe checkout session for subscription
        
        Args:
            db: Database session
            user: User creating the subscription
            checkout_data: Checkout session data
            
        Returns:
            CheckoutSessionResponse with session ID and URL
            
        Raises:
            HTTPException: If checkout session creation fails
        """
        try:
            # Get or create Stripe customer
            customer_id = await cls._get_or_create_customer(user)
            
            # Get price ID for tier
            price_id = cls.PRICE_IDS.get(checkout_data.tier)
            if not price_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid subscription tier: {checkout_data.tier}"
                )
            
            # Create checkout session
            session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=["card"],
                line_items=[
                    {
                        "price": price_id,
                        "quantity": 1,
                    }
                ],
                mode="subscription",
                success_url=checkout_data.success_url,
                cancel_url=checkout_data.cancel_url,
                metadata={
                    "user_id": str(user.id),
                    "tier": checkout_data.tier.value,
                },
            )
            
            return CheckoutSessionResponse(
                session_id=session.id,
                url=session.url,
            )
            
        except stripe.error.StripeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Stripe error: {str(e)}"
            )
    
    @classmethod
    async def get_subscription(
        cls,
        db: AsyncSession,
        user_id: UUID,
    ) -> Optional[Subscription]:
        """
        Get active subscription for user
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Subscription or None if no active subscription
        """
        query = select(Subscription).where(
            Subscription.user_id == user_id,
            Subscription.status == SubscriptionStatus.ACTIVE,
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    @classmethod
    async def cancel_subscription(
        cls,
        db: AsyncSession,
        user: User,
        immediate: bool = False,
    ) -> Subscription:
        """
        Cancel user's subscription
        
        Args:
            db: Database session
            user: User cancelling subscription
            immediate: If True, cancel immediately; if False, cancel at period end
            
        Returns:
            Updated subscription
            
        Raises:
            HTTPException: If no active subscription found
        """
        # Get active subscription
        subscription = await cls.get_subscription(db, user.id)
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active subscription found"
            )
        
        try:
            if immediate:
                # Cancel immediately in Stripe
                stripe.Subscription.delete(subscription.stripe_subscription_id)
                
                # Update database
                subscription.status = SubscriptionStatus.CANCELED
                subscription.cancel_at_period_end = False
                
                # Downgrade user to Free tier
                user.tier = UserTier.FREE
                
            else:
                # Cancel at period end in Stripe
                stripe.Subscription.modify(
                    subscription.stripe_subscription_id,
                    cancel_at_period_end=True,
                )
                
                # Update database
                subscription.cancel_at_period_end = True
            
            subscription.updated_at = datetime.utcnow()
            await db.commit()
            await db.refresh(subscription)
            
            return subscription
            
        except stripe.error.StripeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Stripe error: {str(e)}"
            )
    
    @classmethod
    async def resume_subscription(
        cls,
        db: AsyncSession,
        user: User,
    ) -> Subscription:
        """
        Resume a subscription that was set to cancel at period end
        
        Args:
            db: Database session
            user: User resuming subscription
            
        Returns:
            Updated subscription
            
        Raises:
            HTTPException: If no subscription found or not set to cancel
        """
        subscription = await cls.get_subscription(db, user.id)
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active subscription found"
            )
        
        if not subscription.cancel_at_period_end:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Subscription is not set to cancel"
            )
        
        try:
            # Resume in Stripe
            stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                cancel_at_period_end=False,
            )
            
            # Update database
            subscription.cancel_at_period_end = False
            subscription.updated_at = datetime.utcnow()
            await db.commit()
            await db.refresh(subscription)
            
            return subscription
            
        except stripe.error.StripeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Stripe error: {str(e)}"
            )
    
    @classmethod
    async def upgrade_subscription(
        cls,
        db: AsyncSession,
        user: User,
        new_tier: SubscriptionTier,
    ) -> Subscription:
        """
        Upgrade subscription to a higher tier
        
        Args:
            db: Database session
            user: User upgrading subscription
            new_tier: New subscription tier
            
        Returns:
            Updated subscription
            
        Raises:
            HTTPException: If no subscription found or invalid upgrade
        """
        subscription = await cls.get_subscription(db, user.id)
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active subscription found"
            )
        
        # Validate upgrade path
        if subscription.tier == SubscriptionTier.ENTERPRISE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Already on highest tier"
            )
        
        if new_tier == SubscriptionTier.PREMIUM and subscription.tier == SubscriptionTier.PREMIUM:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Already on Premium tier"
            )
        
        try:
            # Get new price ID
            new_price_id = cls.PRICE_IDS.get(new_tier)
            if not new_price_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid subscription tier: {new_tier}"
                )
            
            # Update subscription in Stripe
            stripe_subscription = stripe.Subscription.retrieve(
                subscription.stripe_subscription_id
            )
            
            stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                items=[{
                    "id": stripe_subscription["items"]["data"][0].id,
                    "price": new_price_id,
                }],
                proration_behavior="always_invoice",  # Charge prorated amount immediately
            )
            
            # Update database
            subscription.tier = new_tier
            subscription.updated_at = datetime.utcnow()
            
            # Update user tier
            if new_tier == SubscriptionTier.PREMIUM:
                user.tier = UserTier.PREMIUM
            elif new_tier == SubscriptionTier.ENTERPRISE:
                user.tier = UserTier.ENTERPRISE
            
            await db.commit()
            await db.refresh(subscription)
            
            return subscription
            
        except stripe.error.StripeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Stripe error: {str(e)}"
            )
    
    @classmethod
    async def downgrade_subscription(
        cls,
        db: AsyncSession,
        user: User,
        new_tier: SubscriptionTier,
    ) -> Subscription:
        """
        Downgrade subscription to a lower tier (takes effect at period end)
        
        Args:
            db: Database session
            user: User downgrading subscription
            new_tier: New subscription tier
            
        Returns:
            Updated subscription
            
        Raises:
            HTTPException: If no subscription found or invalid downgrade
        """
        subscription = await cls.get_subscription(db, user.id)
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active subscription found"
            )
        
        # Validate downgrade path
        if subscription.tier == SubscriptionTier.PREMIUM:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot downgrade from Premium tier"
            )
        
        if new_tier == SubscriptionTier.ENTERPRISE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot downgrade to Enterprise tier"
            )
        
        try:
            # Get new price ID
            new_price_id = cls.PRICE_IDS.get(new_tier)
            if not new_price_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid subscription tier: {new_tier}"
                )
            
            # Schedule downgrade in Stripe (takes effect at period end)
            stripe_subscription = stripe.Subscription.retrieve(
                subscription.stripe_subscription_id
            )
            
            stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                items=[{
                    "id": stripe_subscription["items"]["data"][0].id,
                    "price": new_price_id,
                }],
                proration_behavior="none",  # No proration for downgrades
            )
            
            # Note: Tier will be updated by webhook when period ends
            subscription.updated_at = datetime.utcnow()
            await db.commit()
            await db.refresh(subscription)
            
            return subscription
            
        except stripe.error.StripeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Stripe error: {str(e)}"
            )
    
    @classmethod
    def _get_or_create_customer(cls, user: User) -> str:
        """
        Get existing Stripe customer ID or create new customer
        
        Args:
            user: User to get/create customer for
            
        Returns:
            Stripe customer ID
        """
        # Check if user already has a Stripe customer ID
        # (This would be stored in user model or subscription)
        # For now, create a new customer
        
        customer = stripe.Customer.create(
            email=user.email,
            name=user.full_name or user.email,
            metadata={
                "user_id": str(user.id),
            },
        )
        
        return customer.id
