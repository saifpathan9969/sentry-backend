"""
Subscription model
"""
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID, ENUM as PG_ENUM
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.db.base import Base


class SubscriptionTier(str, enum.Enum):
    """Subscription tier options"""
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(str, enum.Enum):
    """Subscription status options"""
    ACTIVE = "active"
    CANCELED = "canceled"
    PAST_DUE = "past_due"


class Subscription(Base):
    """
    Subscription model for paid tiers
    """
    __tablename__ = "subscriptions"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Foreign key to user
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Stripe identifiers
    stripe_subscription_id = Column(String(255), unique=True, nullable=False, index=True)
    stripe_customer_id = Column(String(255), nullable=False)
    
    # Subscription details - use PostgreSQL native enum with lowercase values
    tier = Column(
        PG_ENUM('premium', 'enterprise', name='subscription_tier', create_type=False),
        nullable=False
    )
    status = Column(
        PG_ENUM('active', 'canceled', 'past_due', name='subscription_status', create_type=False),
        default='active',
        nullable=False,
        index=True
    )
    
    # Billing period
    current_period_start = Column(DateTime, nullable=False)
    current_period_end = Column(DateTime, nullable=False)
    
    # Cancellation
    cancel_at_period_end = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="subscriptions")
    
    def __repr__(self):
        return f"<Subscription(id={self.id}, user_id={self.user_id}, tier={self.tier}, status={self.status})>"
