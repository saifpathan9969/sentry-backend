"""
Unit tests for webhook service
"""
import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import stripe

from app.models.user import User, UserTier
from app.models.subscription import Subscription, SubscriptionTier, SubscriptionStatus
from app.services.webhook_service import WebhookService
from fastapi import HTTPException


@pytest.mark.asyncio
class TestWebhookService:
    """Test suite for WebhookService"""
    
    def test_verify_webhook_signature_success(self):
        """Test successful webhook signature verification"""
        payload = b'{"type": "test.event"}'
        signature = "test_signature"
        
        with patch("app.services.webhook_service.stripe.Webhook.construct_event") as mock_construct:
            mock_event = {"type": "test.event", "id": "evt_test123"}
            mock_construct.return_value = mock_event
            
            result = WebhookService.verify_webhook_signature(payload, signature)
            
            assert result == mock_event
            mock_construct.assert_called_once()
    
    def test_verify_webhook_signature_invalid(self):
        """Test webhook signature verification with invalid signature"""
        payload = b'{"type": "test.event"}'
        signature = "invalid_signature"
        
        with patch("app.services.webhook_service.stripe.Webhook.construct_event") as mock_construct:
            mock_construct.side_effect = stripe.error.SignatureVerificationError(
                "Invalid signature", signature
            )
            
            with pytest.raises(ValueError):
                WebhookService.verify_webhook_signature(payload, signature)
    
    def test_verify_webhook_signature_invalid_payload(self):
        """Test webhook signature verification with invalid payload"""
        payload = b'invalid json'
        signature = "test_signature"
        
        with patch("app.services.webhook_service.stripe.Webhook.construct_event") as mock_construct:
            mock_construct.side_effect = ValueError("Invalid payload")
            
            with pytest.raises(ValueError):
                WebhookService.verify_webhook_signature(payload, signature)
    
    async def test_handle_checkout_completed(self, async_db_session):
        """Test handling checkout.session.completed event"""
        # Create user
        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash="hashed",
            tier=UserTier.FREE,
        )
        async_db_session.add(user)
        await async_db_session.commit()
        
        # Mock Stripe subscription
        with patch("app.services.webhook_service.stripe.Subscription.retrieve") as mock_retrieve:
            mock_retrieve.return_value = {
                "id": "sub_test123",
                "current_period_start": int(datetime.utcnow().timestamp()),
                "current_period_end": int((datetime.utcnow() + timedelta(days=30)).timestamp()),
            }
            
            # Create event
            event = {
                "type": "checkout.session.completed",
                "id": "evt_test123",
                "data": {
                    "object": {
                        "metadata": {
                            "user_id": str(user.id),
                            "tier": "premium",
                        },
                        "subscription": "sub_test123",
                        "customer": "cus_test123",
                    }
                }
            }
            
            # Handle event
            result = await WebhookService.handle_webhook_event(async_db_session, event)
            
            assert result["status"] == "success"
            assert result["event_type"] == "checkout.session.completed"
            assert result["user_id"] == str(user.id)
            
            # Verify user tier updated
            await async_db_session.refresh(user)
            assert user.tier == UserTier.PREMIUM
    
    async def test_handle_subscription_created(self, async_db_session):
        """Test handling customer.subscription.created event"""
        event = {
            "type": "customer.subscription.created",
            "id": "evt_test123",
            "data": {
                "object": {
                    "id": "sub_test123",
                }
            }
        }
        
        result = await WebhookService.handle_webhook_event(async_db_session, event)
        
        assert result["status"] == "success"
        assert result["event_type"] == "customer.subscription.created"
    
    async def test_handle_subscription_updated(self, async_db_session):
        """Test handling customer.subscription.updated event"""
        # Create user and subscription
        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash="hashed",
            tier=UserTier.PREMIUM,
        )
        async_db_session.add(user)
        
        subscription = Subscription(
            id=uuid4(),
            user_id=user.id,
            stripe_subscription_id="sub_test123",
            stripe_customer_id="cus_test123",
            tier=SubscriptionTier.PREMIUM,
            status=SubscriptionStatus.ACTIVE,
            current_period_start=datetime.utcnow(),
            current_period_end=datetime.utcnow() + timedelta(days=30),
        )
        async_db_session.add(subscription)
        await async_db_session.commit()
        
        # Create event
        new_period_start = datetime.utcnow() + timedelta(days=30)
        new_period_end = datetime.utcnow() + timedelta(days=60)
        
        event = {
            "type": "customer.subscription.updated",
            "id": "evt_test123",
            "data": {
                "object": {
                    "id": "sub_test123",
                    "status": "active",
                    "current_period_start": int(new_period_start.timestamp()),
                    "current_period_end": int(new_period_end.timestamp()),
                    "cancel_at_period_end": False,
                }
            }
        }
        
        result = await WebhookService.handle_webhook_event(async_db_session, event)
        
        assert result["status"] == "success"
        assert result["event_type"] == "customer.subscription.updated"
        
        # Verify subscription updated
        await async_db_session.refresh(subscription)
        assert subscription.status == SubscriptionStatus.ACTIVE
    
    async def test_handle_subscription_updated_canceled(self, async_db_session):
        """Test handling subscription update with canceled status"""
        # Create user and subscription
        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash="hashed",
            tier=UserTier.PREMIUM,
        )
        async_db_session.add(user)
        
        subscription = Subscription(
            id=uuid4(),
            user_id=user.id,
            stripe_subscription_id="sub_test123",
            stripe_customer_id="cus_test123",
            tier=SubscriptionTier.PREMIUM,
            status=SubscriptionStatus.ACTIVE,
            current_period_start=datetime.utcnow(),
            current_period_end=datetime.utcnow() + timedelta(days=30),
        )
        async_db_session.add(subscription)
        await async_db_session.commit()
        
        # Create event with canceled status
        event = {
            "type": "customer.subscription.updated",
            "id": "evt_test123",
            "data": {
                "object": {
                    "id": "sub_test123",
                    "status": "canceled",
                    "current_period_start": int(datetime.utcnow().timestamp()),
                    "current_period_end": int((datetime.utcnow() + timedelta(days=30)).timestamp()),
                    "cancel_at_period_end": False,
                }
            }
        }
        
        result = await WebhookService.handle_webhook_event(async_db_session, event)
        
        assert result["status"] == "success"
        
        # Verify subscription canceled and user downgraded
        await async_db_session.refresh(subscription)
        await async_db_session.refresh(user)
        assert subscription.status == SubscriptionStatus.CANCELED
        assert user.tier == UserTier.FREE
    
    async def test_handle_subscription_deleted(self, async_db_session):
        """Test handling customer.subscription.deleted event"""
        # Create user and subscription
        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash="hashed",
            tier=UserTier.PREMIUM,
        )
        async_db_session.add(user)
        
        subscription = Subscription(
            id=uuid4(),
            user_id=user.id,
            stripe_subscription_id="sub_test123",
            stripe_customer_id="cus_test123",
            tier=SubscriptionTier.PREMIUM,
            status=SubscriptionStatus.ACTIVE,
            current_period_start=datetime.utcnow(),
            current_period_end=datetime.utcnow() + timedelta(days=30),
        )
        async_db_session.add(subscription)
        await async_db_session.commit()
        
        # Create event
        event = {
            "type": "customer.subscription.deleted",
            "id": "evt_test123",
            "data": {
                "object": {
                    "id": "sub_test123",
                }
            }
        }
        
        result = await WebhookService.handle_webhook_event(async_db_session, event)
        
        assert result["status"] == "success"
        assert result["event_type"] == "customer.subscription.deleted"
        
        # Verify subscription canceled and user downgraded
        await async_db_session.refresh(subscription)
        await async_db_session.refresh(user)
        assert subscription.status == SubscriptionStatus.CANCELED
        assert user.tier == UserTier.FREE
    
    async def test_handle_payment_failed(self, async_db_session):
        """Test handling invoice.payment_failed event"""
        # Create user and subscription
        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash="hashed",
            tier=UserTier.PREMIUM,
        )
        async_db_session.add(user)
        
        subscription = Subscription(
            id=uuid4(),
            user_id=user.id,
            stripe_subscription_id="sub_test123",
            stripe_customer_id="cus_test123",
            tier=SubscriptionTier.PREMIUM,
            status=SubscriptionStatus.ACTIVE,
            current_period_start=datetime.utcnow(),
            current_period_end=datetime.utcnow() + timedelta(days=30),
        )
        async_db_session.add(subscription)
        await async_db_session.commit()
        
        # Create event
        event = {
            "type": "invoice.payment_failed",
            "id": "evt_test123",
            "data": {
                "object": {
                    "subscription": "sub_test123",
                }
            }
        }
        
        result = await WebhookService.handle_webhook_event(async_db_session, event)
        
        assert result["status"] == "success"
        assert result["event_type"] == "invoice.payment_failed"
        
        # Verify subscription status updated to past_due
        await async_db_session.refresh(subscription)
        assert subscription.status == SubscriptionStatus.PAST_DUE
    
    async def test_handle_payment_failed_no_subscription(self, async_db_session):
        """Test handling payment failed event without subscription ID"""
        event = {
            "type": "invoice.payment_failed",
            "id": "evt_test123",
            "data": {
                "object": {
                    # No subscription field
                }
            }
        }
        
        result = await WebhookService.handle_webhook_event(async_db_session, event)
        
        assert result["status"] == "error"
        assert "No subscription ID" in result["message"]
    
    async def test_handle_unhandled_event_type(self, async_db_session):
        """Test handling unhandled event type"""
        event = {
            "type": "unknown.event.type",
            "id": "evt_test123",
            "data": {
                "object": {}
            }
        }
        
        result = await WebhookService.handle_webhook_event(async_db_session, event)
        
        assert result["status"] == "ignored"
        assert result["event_type"] == "unknown.event.type"
    
    async def test_handle_subscription_updated_not_found(self, async_db_session):
        """Test handling subscription update for non-existent subscription"""
        event = {
            "type": "customer.subscription.updated",
            "id": "evt_test123",
            "data": {
                "object": {
                    "id": "sub_nonexistent",
                    "status": "active",
                    "current_period_start": int(datetime.utcnow().timestamp()),
                    "current_period_end": int((datetime.utcnow() + timedelta(days=30)).timestamp()),
                    "cancel_at_period_end": False,
                }
            }
        }
        
        result = await WebhookService.handle_webhook_event(async_db_session, event)
        
        assert result["status"] == "error"
        assert "Subscription not found" in result["message"]
    
    async def test_handle_subscription_deleted_not_found(self, async_db_session):
        """Test handling subscription deletion for non-existent subscription"""
        event = {
            "type": "customer.subscription.deleted",
            "id": "evt_test123",
            "data": {
                "object": {
                    "id": "sub_nonexistent",
                }
            }
        }
        
        result = await WebhookService.handle_webhook_event(async_db_session, event)
        
        assert result["status"] == "error"
        assert "Subscription not found" in result["message"]
    
    async def test_handle_checkout_completed_enterprise_tier(self, async_db_session):
        """Test handling checkout completed for Enterprise tier"""
        # Create user
        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash="hashed",
            tier=UserTier.FREE,
        )
        async_db_session.add(user)
        await async_db_session.commit()
        
        # Mock Stripe subscription
        with patch("app.services.webhook_service.stripe.Subscription.retrieve") as mock_retrieve:
            mock_retrieve.return_value = {
                "id": "sub_test123",
                "current_period_start": int(datetime.utcnow().timestamp()),
                "current_period_end": int((datetime.utcnow() + timedelta(days=30)).timestamp()),
            }
            
            # Create event for Enterprise tier
            event = {
                "type": "checkout.session.completed",
                "id": "evt_test123",
                "data": {
                    "object": {
                        "metadata": {
                            "user_id": str(user.id),
                            "tier": "enterprise",
                        },
                        "subscription": "sub_test123",
                        "customer": "cus_test123",
                    }
                }
            }
            
            # Handle event
            result = await WebhookService.handle_webhook_event(async_db_session, event)
            
            assert result["status"] == "success"
            
            # Verify user tier updated to Enterprise
            await async_db_session.refresh(user)
            assert user.tier == UserTier.ENTERPRISE
