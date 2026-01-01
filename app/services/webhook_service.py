"""
Webhook service for handling Stripe webhook events
"""
import stripe
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from datetime import datetime
from typing import Dict, Any, Optional
import logging

from app.core.config import settings
from app.models.user import User, UserTier
from app.models.subscription import Subscription, SubscriptionTier, SubscriptionStatus

logger = logging.getLogger(__name__)

# Configure Stripe
stripe.api_key = settings.STRIPE_API_KEY


class WebhookService:
    """Service for processing Stripe webhook events"""
    
    @classmethod
    def verify_webhook_signature(
        cls,
        payload: bytes,
        signature: str,
    ) -> stripe.Event:
        """
        Verify Stripe webhook signature and construct event
        
        Args:
            payload: Raw request body
            signature: Stripe signature header
            
        Returns:
            Verified Stripe event
            
        Raises:
            ValueError: If signature verification fails
        """
        try:
            event = stripe.Webhook.construct_event(
                payload,
                signature,
                settings.STRIPE_WEBHOOK_SECRET,
            )
            return event
        except ValueError as e:
            logger.error(f"Invalid webhook payload: {e}")
            raise
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid webhook signature: {e}")
            raise ValueError(f"Invalid signature: {e}")
    
    @classmethod
    async def handle_webhook_event(
        cls,
        db: AsyncSession,
        event: stripe.Event,
    ) -> Dict[str, Any]:
        """
        Handle Stripe webhook event
        
        Args:
            db: Database session
            event: Stripe event
            
        Returns:
            Dict with processing result
        """
        event_type = event["type"]
        
        logger.info(f"Processing webhook event: {event_type} (ID: {event['id']})")
        
        # Route to appropriate handler
        if event_type == "checkout.session.completed":
            return await cls._handle_checkout_completed(db, event)
        elif event_type == "customer.subscription.created":
            return await cls._handle_subscription_created(db, event)
        elif event_type == "customer.subscription.updated":
            return await cls._handle_subscription_updated(db, event)
        elif event_type == "customer.subscription.deleted":
            return await cls._handle_subscription_deleted(db, event)
        elif event_type == "invoice.payment_failed":
            return await cls._handle_payment_failed(db, event)
        else:
            logger.warning(f"Unhandled webhook event type: {event_type}")
            return {"status": "ignored", "event_type": event_type}
    
    @classmethod
    async def _handle_checkout_completed(
        cls,
        db: AsyncSession,
        event: stripe.Event,
    ) -> Dict[str, Any]:
        """
        Handle checkout.session.completed event
        
        Creates subscription record when user completes checkout
        
        Args:
            db: Database session
            event: Stripe event
            
        Returns:
            Dict with processing result
        """
        session = event["data"]["object"]
        
        # Extract metadata
        user_id = UUID(session["metadata"]["user_id"])
        tier_str = session["metadata"]["tier"]
        
        # Get subscription details
        subscription_id = session.get("subscription")
        customer_id = session.get("customer")
        
        if not subscription_id:
            logger.error("No subscription ID in checkout session")
            return {"status": "error", "message": "No subscription ID"}
        
        # Get subscription from Stripe
        stripe_subscription = stripe.Subscription.retrieve(subscription_id)
        
        # Map tier string to enum
        tier = SubscriptionTier.PREMIUM if tier_str == "premium" else SubscriptionTier.ENTERPRISE
        
        # Create subscription record
        subscription = Subscription(
            user_id=user_id,
            stripe_subscription_id=subscription_id,
            stripe_customer_id=customer_id,
            tier=tier,
            status=SubscriptionStatus.ACTIVE,
            current_period_start=datetime.fromtimestamp(stripe_subscription["current_period_start"]),
            current_period_end=datetime.fromtimestamp(stripe_subscription["current_period_end"]),
            cancel_at_period_end=False,
        )
        db.add(subscription)
        
        # Update user tier
        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        
        if user:
            if tier == SubscriptionTier.PREMIUM:
                user.tier = UserTier.PREMIUM
            elif tier == SubscriptionTier.ENTERPRISE:
                user.tier = UserTier.ENTERPRISE
            user.updated_at = datetime.utcnow()
        
        await db.commit()
        
        logger.info(f"Created subscription for user {user_id}, tier: {tier}")
        
        return {
            "status": "success",
            "event_type": "checkout.session.completed",
            "user_id": str(user_id),
            "subscription_id": subscription_id,
        }
    
    @classmethod
    async def _handle_subscription_created(
        cls,
        db: AsyncSession,
        event: stripe.Event,
    ) -> Dict[str, Any]:
        """
        Handle customer.subscription.created event
        
        Args:
            db: Database session
            event: Stripe event
            
        Returns:
            Dict with processing result
        """
        subscription_data = event["data"]["object"]
        subscription_id = subscription_data["id"]
        
        logger.info(f"Subscription created: {subscription_id}")
        
        # This is typically handled by checkout.session.completed
        # Log for audit purposes
        return {
            "status": "success",
            "event_type": "customer.subscription.created",
            "subscription_id": subscription_id,
        }
    
    @classmethod
    async def _handle_subscription_updated(
        cls,
        db: AsyncSession,
        event: stripe.Event,
    ) -> Dict[str, Any]:
        """
        Handle customer.subscription.updated event
        
        Updates subscription status, period, and tier changes
        
        Args:
            db: Database session
            event: Stripe event
            
        Returns:
            Dict with processing result
        """
        subscription_data = event["data"]["object"]
        subscription_id = subscription_data["id"]
        
        # Find subscription in database
        query = select(Subscription).where(
            Subscription.stripe_subscription_id == subscription_id
        )
        result = await db.execute(query)
        subscription = result.scalar_one_or_none()
        
        if not subscription:
            logger.warning(f"Subscription not found: {subscription_id}")
            return {"status": "error", "message": "Subscription not found"}
        
        # Update subscription details
        subscription.current_period_start = datetime.fromtimestamp(
            subscription_data["current_period_start"]
        )
        subscription.current_period_end = datetime.fromtimestamp(
            subscription_data["current_period_end"]
        )
        subscription.cancel_at_period_end = subscription_data.get("cancel_at_period_end", False)
        
        # Update status
        stripe_status = subscription_data["status"]
        if stripe_status == "active":
            subscription.status = SubscriptionStatus.ACTIVE
        elif stripe_status == "canceled":
            subscription.status = SubscriptionStatus.CANCELED
        elif stripe_status == "past_due":
            subscription.status = SubscriptionStatus.PAST_DUE
        
        subscription.updated_at = datetime.utcnow()
        
        # If subscription is canceled, downgrade user to Free tier
        if subscription.status == SubscriptionStatus.CANCELED:
            query = select(User).where(User.id == subscription.user_id)
            result = await db.execute(query)
            user = result.scalar_one_or_none()
            
            if user:
                user.tier = UserTier.FREE
                user.updated_at = datetime.utcnow()
        
        await db.commit()
        
        logger.info(f"Updated subscription {subscription_id}, status: {subscription.status}")
        
        return {
            "status": "success",
            "event_type": "customer.subscription.updated",
            "subscription_id": subscription_id,
            "new_status": subscription.status.value,
        }
    
    @classmethod
    async def _handle_subscription_deleted(
        cls,
        db: AsyncSession,
        event: stripe.Event,
    ) -> Dict[str, Any]:
        """
        Handle customer.subscription.deleted event
        
        Marks subscription as canceled and downgrades user to Free tier
        
        Args:
            db: Database session
            event: Stripe event
            
        Returns:
            Dict with processing result
        """
        subscription_data = event["data"]["object"]
        subscription_id = subscription_data["id"]
        
        # Find subscription in database
        query = select(Subscription).where(
            Subscription.stripe_subscription_id == subscription_id
        )
        result = await db.execute(query)
        subscription = result.scalar_one_or_none()
        
        if not subscription:
            logger.warning(f"Subscription not found: {subscription_id}")
            return {"status": "error", "message": "Subscription not found"}
        
        # Update subscription status
        subscription.status = SubscriptionStatus.CANCELED
        subscription.updated_at = datetime.utcnow()
        
        # Downgrade user to Free tier
        query = select(User).where(User.id == subscription.user_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        
        if user:
            user.tier = UserTier.FREE
            user.updated_at = datetime.utcnow()
        
        await db.commit()
        
        logger.info(f"Deleted subscription {subscription_id}, user downgraded to Free")
        
        return {
            "status": "success",
            "event_type": "customer.subscription.deleted",
            "subscription_id": subscription_id,
            "user_id": str(subscription.user_id),
        }
    
    @classmethod
    async def _handle_payment_failed(
        cls,
        db: AsyncSession,
        event: stripe.Event,
    ) -> Dict[str, Any]:
        """
        Handle invoice.payment_failed event
        
        Updates subscription status to past_due
        
        Args:
            db: Database session
            event: Stripe event
            
        Returns:
            Dict with processing result
        """
        invoice_data = event["data"]["object"]
        subscription_id = invoice_data.get("subscription")
        
        if not subscription_id:
            logger.warning("No subscription ID in payment failed event")
            return {"status": "error", "message": "No subscription ID"}
        
        # Find subscription in database
        query = select(Subscription).where(
            Subscription.stripe_subscription_id == subscription_id
        )
        result = await db.execute(query)
        subscription = result.scalar_one_or_none()
        
        if not subscription:
            logger.warning(f"Subscription not found: {subscription_id}")
            return {"status": "error", "message": "Subscription not found"}
        
        # Update subscription status to past_due
        subscription.status = SubscriptionStatus.PAST_DUE
        subscription.updated_at = datetime.utcnow()
        
        await db.commit()
        
        logger.warning(f"Payment failed for subscription {subscription_id}, status: PAST_DUE")
        
        return {
            "status": "success",
            "event_type": "invoice.payment_failed",
            "subscription_id": subscription_id,
            "user_id": str(subscription.user_id),
        }
