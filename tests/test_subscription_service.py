"""
Unit tests for subscription service
"""
import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from app.models.user import User, UserTier
from app.models.subscription import Subscription, SubscriptionTier, SubscriptionStatus
from app.schemas.subscription import CheckoutSessionCreate
from app.services.subscription_service import SubscriptionService
from fastapi import HTTPException


@pytest.mark.asyncio
class TestSubscriptionService:
    """Test suite for SubscriptionService"""
    
    @patch("app.services.subscription_service.stripe.checkout.Session.create")
    @patch("app.services.subscription_service.stripe.Customer.create")
    async def test_create_checkout_session_success(
        self,
        mock_customer_create,
        mock_session_create,
        async_db_session,
    ):
        """Test creating a checkout session successfully"""
        # Create user
        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash="hashed",
            tier=UserTier.FREE,
        )
        async_db_session.add(user)
        await async_db_session.commit()
        
        # Mock Stripe responses
        mock_customer_create.return_value = Mock(id="cus_test123")
        mock_session_create.return_value = Mock(
            id="cs_test123",
            url="https://checkout.stripe.com/test",
        )
        
        # Create checkout session
        checkout_data = CheckoutSessionCreate(
            tier=SubscriptionTier.PREMIUM,
            success_url="https://example.com/success",
            cancel_url="https://example.com/cancel",
        )
        
        result = await SubscriptionService.create_checkout_session(
            async_db_session, user, checkout_data
        )
        
        # Verify result
        assert result.session_id == "cs_test123"
        assert result.url == "https://checkout.stripe.com/test"
        
        # Verify Stripe was called
        mock_customer_create.assert_called_once()
        mock_session_create.assert_called_once()
    
    @patch("app.services.subscription_service.stripe.Customer.create")
    async def test_create_checkout_session_invalid_tier(
        self,
        mock_customer_create,
        async_db_session,
    ):
        """Test creating checkout session with invalid tier"""
        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash="hashed",
            tier=UserTier.FREE,
        )
        async_db_session.add(user)
        await async_db_session.commit()
        
        mock_customer_create.return_value = Mock(id="cus_test123")
        
        # Mock invalid tier by temporarily removing from PRICE_IDS
        original_price_ids = SubscriptionService.PRICE_IDS.copy()
        SubscriptionService.PRICE_IDS = {}
        
        checkout_data = CheckoutSessionCreate(
            tier=SubscriptionTier.PREMIUM,
            success_url="https://example.com/success",
            cancel_url="https://example.com/cancel",
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await SubscriptionService.create_checkout_session(
                async_db_session, user, checkout_data
            )
        
        assert exc_info.value.status_code == 400
        assert "Invalid subscription tier" in exc_info.value.detail
        
        # Restore PRICE_IDS
        SubscriptionService.PRICE_IDS = original_price_ids
    
    async def test_get_subscription_success(self, async_db_session):
        """Test getting active subscription"""
        # Create user
        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash="hashed",
            tier=UserTier.PREMIUM,
        )
        async_db_session.add(user)
        
        # Create subscription
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
        
        # Get subscription
        result = await SubscriptionService.get_subscription(
            async_db_session, user.id
        )
        
        assert result is not None
        assert result.id == subscription.id
        assert result.user_id == user.id
        assert result.status == SubscriptionStatus.ACTIVE
    
    async def test_get_subscription_not_found(self, async_db_session):
        """Test getting subscription when none exists"""
        user_id = uuid4()
        
        result = await SubscriptionService.get_subscription(
            async_db_session, user_id
        )
        
        assert result is None
    
    @patch("app.services.subscription_service.stripe.Subscription.delete")
    async def test_cancel_subscription_immediate(
        self,
        mock_stripe_delete,
        async_db_session,
    ):
        """Test cancelling subscription immediately"""
        # Create user
        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash="hashed",
            tier=UserTier.PREMIUM,
        )
        async_db_session.add(user)
        
        # Create subscription
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
        
        # Cancel subscription
        result = await SubscriptionService.cancel_subscription(
            async_db_session, user, immediate=True
        )
        
        # Verify result
        assert result.status == SubscriptionStatus.CANCELED
        assert result.cancel_at_period_end is False
        
        # Verify user tier downgraded
        await async_db_session.refresh(user)
        assert user.tier == UserTier.FREE
        
        # Verify Stripe was called
        mock_stripe_delete.assert_called_once_with("sub_test123")
    
    @patch("app.services.subscription_service.stripe.Subscription.modify")
    async def test_cancel_subscription_at_period_end(
        self,
        mock_stripe_modify,
        async_db_session,
    ):
        """Test cancelling subscription at period end"""
        # Create user
        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash="hashed",
            tier=UserTier.PREMIUM,
        )
        async_db_session.add(user)
        
        # Create subscription
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
        
        # Cancel subscription at period end
        result = await SubscriptionService.cancel_subscription(
            async_db_session, user, immediate=False
        )
        
        # Verify result
        assert result.status == SubscriptionStatus.ACTIVE
        assert result.cancel_at_period_end is True
        
        # Verify user tier NOT downgraded yet
        await async_db_session.refresh(user)
        assert user.tier == UserTier.PREMIUM
        
        # Verify Stripe was called
        mock_stripe_modify.assert_called_once()
    
    async def test_cancel_subscription_not_found(self, async_db_session):
        """Test cancelling subscription when none exists"""
        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash="hashed",
            tier=UserTier.FREE,
        )
        async_db_session.add(user)
        await async_db_session.commit()
        
        with pytest.raises(HTTPException) as exc_info:
            await SubscriptionService.cancel_subscription(
                async_db_session, user, immediate=False
            )
        
        assert exc_info.value.status_code == 404
        assert "No active subscription" in exc_info.value.detail
    
    @patch("app.services.subscription_service.stripe.Subscription.modify")
    async def test_resume_subscription_success(
        self,
        mock_stripe_modify,
        async_db_session,
    ):
        """Test resuming a subscription"""
        # Create user
        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash="hashed",
            tier=UserTier.PREMIUM,
        )
        async_db_session.add(user)
        
        # Create subscription set to cancel
        subscription = Subscription(
            id=uuid4(),
            user_id=user.id,
            stripe_subscription_id="sub_test123",
            stripe_customer_id="cus_test123",
            tier=SubscriptionTier.PREMIUM,
            status=SubscriptionStatus.ACTIVE,
            current_period_start=datetime.utcnow(),
            current_period_end=datetime.utcnow() + timedelta(days=30),
            cancel_at_period_end=True,
        )
        async_db_session.add(subscription)
        await async_db_session.commit()
        
        # Resume subscription
        result = await SubscriptionService.resume_subscription(
            async_db_session, user
        )
        
        # Verify result
        assert result.cancel_at_period_end is False
        
        # Verify Stripe was called
        mock_stripe_modify.assert_called_once()
    
    async def test_resume_subscription_not_set_to_cancel(self, async_db_session):
        """Test resuming subscription that's not set to cancel"""
        # Create user
        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash="hashed",
            tier=UserTier.PREMIUM,
        )
        async_db_session.add(user)
        
        # Create subscription NOT set to cancel
        subscription = Subscription(
            id=uuid4(),
            user_id=user.id,
            stripe_subscription_id="sub_test123",
            stripe_customer_id="cus_test123",
            tier=SubscriptionTier.PREMIUM,
            status=SubscriptionStatus.ACTIVE,
            current_period_start=datetime.utcnow(),
            current_period_end=datetime.utcnow() + timedelta(days=30),
            cancel_at_period_end=False,
        )
        async_db_session.add(subscription)
        await async_db_session.commit()
        
        with pytest.raises(HTTPException) as exc_info:
            await SubscriptionService.resume_subscription(
                async_db_session, user
            )
        
        assert exc_info.value.status_code == 400
        assert "not set to cancel" in exc_info.value.detail
    
    @patch("app.services.subscription_service.stripe.Subscription.retrieve")
    @patch("app.services.subscription_service.stripe.Subscription.modify")
    async def test_upgrade_subscription_success(
        self,
        mock_stripe_modify,
        mock_stripe_retrieve,
        async_db_session,
    ):
        """Test upgrading subscription"""
        # Create user
        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash="hashed",
            tier=UserTier.PREMIUM,
        )
        async_db_session.add(user)
        
        # Create Premium subscription
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
        
        # Mock Stripe response
        mock_stripe_retrieve.return_value = {
            "items": {
                "data": [Mock(id="si_test123")]
            }
        }
        
        # Upgrade to Enterprise
        result = await SubscriptionService.upgrade_subscription(
            async_db_session, user, SubscriptionTier.ENTERPRISE
        )
        
        # Verify result
        assert result.tier == SubscriptionTier.ENTERPRISE
        
        # Verify user tier upgraded
        await async_db_session.refresh(user)
        assert user.tier == UserTier.ENTERPRISE
        
        # Verify Stripe was called
        mock_stripe_retrieve.assert_called_once()
        mock_stripe_modify.assert_called_once()
    
    async def test_upgrade_subscription_already_highest_tier(self, async_db_session):
        """Test upgrading when already on highest tier"""
        # Create user
        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash="hashed",
            tier=UserTier.ENTERPRISE,
        )
        async_db_session.add(user)
        
        # Create Enterprise subscription
        subscription = Subscription(
            id=uuid4(),
            user_id=user.id,
            stripe_subscription_id="sub_test123",
            stripe_customer_id="cus_test123",
            tier=SubscriptionTier.ENTERPRISE,
            status=SubscriptionStatus.ACTIVE,
            current_period_start=datetime.utcnow(),
            current_period_end=datetime.utcnow() + timedelta(days=30),
        )
        async_db_session.add(subscription)
        await async_db_session.commit()
        
        with pytest.raises(HTTPException) as exc_info:
            await SubscriptionService.upgrade_subscription(
                async_db_session, user, SubscriptionTier.ENTERPRISE
            )
        
        assert exc_info.value.status_code == 400
        assert "highest tier" in exc_info.value.detail
    
    @patch("app.services.subscription_service.stripe.Subscription.retrieve")
    @patch("app.services.subscription_service.stripe.Subscription.modify")
    async def test_downgrade_subscription_success(
        self,
        mock_stripe_modify,
        mock_stripe_retrieve,
        async_db_session,
    ):
        """Test downgrading subscription"""
        # Create user
        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash="hashed",
            tier=UserTier.ENTERPRISE,
        )
        async_db_session.add(user)
        
        # Create Enterprise subscription
        subscription = Subscription(
            id=uuid4(),
            user_id=user.id,
            stripe_subscription_id="sub_test123",
            stripe_customer_id="cus_test123",
            tier=SubscriptionTier.ENTERPRISE,
            status=SubscriptionStatus.ACTIVE,
            current_period_start=datetime.utcnow(),
            current_period_end=datetime.utcnow() + timedelta(days=30),
        )
        async_db_session.add(subscription)
        await async_db_session.commit()
        
        # Mock Stripe response
        mock_stripe_retrieve.return_value = {
            "items": {
                "data": [Mock(id="si_test123")]
            }
        }
        
        # Downgrade to Premium
        result = await SubscriptionService.downgrade_subscription(
            async_db_session, user, SubscriptionTier.PREMIUM
        )
        
        # Verify Stripe was called
        mock_stripe_retrieve.assert_called_once()
        mock_stripe_modify.assert_called_once()
        
        # Note: Tier will be updated by webhook at period end
        # User tier should NOT change immediately
        await async_db_session.refresh(user)
        assert user.tier == UserTier.ENTERPRISE
    
    async def test_downgrade_subscription_from_premium(self, async_db_session):
        """Test downgrading from Premium tier (not allowed)"""
        # Create user
        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash="hashed",
            tier=UserTier.PREMIUM,
        )
        async_db_session.add(user)
        
        # Create Premium subscription
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
        
        with pytest.raises(HTTPException) as exc_info:
            await SubscriptionService.downgrade_subscription(
                async_db_session, user, SubscriptionTier.PREMIUM
            )
        
        assert exc_info.value.status_code == 400
        assert "Cannot downgrade from Premium" in exc_info.value.detail
