"""
Tier-based access control service
"""
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.user import User, UserTier
from app.models.scan import Scan
from app.schemas.tier import TierLimits, TierCheckResponse
from app.core.config import settings


def is_owner_email(email: str) -> bool:
    """Check if email belongs to an owner (gets full access)"""
    return email.lower() in [e.lower() for e in settings.OWNER_EMAILS]


def normalize_tier(tier) -> str:
    """Convert tier to lowercase string regardless of whether it's an enum or string"""
    if isinstance(tier, str):
        return tier.lower()
    elif hasattr(tier, 'value'):
        return tier.value.lower()
    else:
        return str(tier).lower()


class TierService:
    """Service for tier-based access control"""
    
    # Tier configuration - use string keys for consistency
    TIER_CONFIG = {
        "free": {
            "scans_per_day": settings.SCAN_LIMIT_FREE_TIER,
            "allowed_scan_modes": ["common", "fast"],
            "rate_limit_per_hour": settings.RATE_LIMIT_FREE_TIER,
            "scan_history_days": 30,
        },
        "premium": {
            "scans_per_day": None,  # Unlimited
            "allowed_scan_modes": ["common", "fast", "full", "stealth", "aggressive"],
            "rate_limit_per_hour": None,  # Unlimited (monthly limit handled separately)
            "scan_history_days": 365,
        },
        "enterprise": {
            "scans_per_day": None,  # Unlimited
            "allowed_scan_modes": ["common", "fast", "full", "stealth", "aggressive", "custom"],
            "rate_limit_per_hour": None,  # Unlimited
            "scan_history_days": None,  # Unlimited
        },
    }
    
    @classmethod
    def get_tier_limits(cls, tier, email: str = None) -> TierLimits:
        """Get limits for a specific tier (owners always get enterprise)"""
        # Normalize tier to lowercase string
        tier_str = normalize_tier(tier)
        
        # Owners always get enterprise tier limits
        if email and is_owner_email(email):
            tier_str = "enterprise"
        
        # Default to free tier if unknown
        if tier_str not in cls.TIER_CONFIG:
            tier_str = "free"
        
        config = cls.TIER_CONFIG[tier_str]
        return TierLimits(
            tier=tier_str,
            scans_per_day=config["scans_per_day"],
            allowed_scan_modes=config["allowed_scan_modes"],
            rate_limit_per_hour=config["rate_limit_per_hour"],
            scan_history_days=config["scan_history_days"],
        )
    
    @classmethod
    async def check_scan_limit(
        cls,
        db: AsyncSession,
        user: User,
    ) -> TierCheckResponse:
        """
        Check if user has reached their daily scan limit
        
        Args:
            db: Database session
            user: User to check
            
        Returns:
            TierCheckResponse with allowed status and details
        """
        # Owners always have unlimited access
        if is_owner_email(user.email):
            return TierCheckResponse(
                allowed=True,
                reason=None,
                current_usage=None,
                limit=None,
            )
        
        tier_str = normalize_tier(user.tier)
        limits = cls.get_tier_limits(tier_str, user.email)
        
        # Unlimited scans for Premium and Enterprise
        if limits.scans_per_day is None:
            return TierCheckResponse(
                allowed=True,
                reason=None,
                current_usage=None,
                limit=None,
            )
        
        # Count scans in the last 24 hours
        yesterday = datetime.utcnow() - timedelta(days=1)
        query = select(func.count(Scan.id)).where(
            Scan.user_id == user.id,
            Scan.created_at >= yesterday,
        )
        result = await db.execute(query)
        scan_count = result.scalar_one()
        
        allowed = scan_count < limits.scans_per_day
        
        return TierCheckResponse(
            allowed=allowed,
            reason=None if allowed else f"Daily scan limit reached ({limits.scans_per_day} scans per day)",
            current_usage=scan_count,
            limit=limits.scans_per_day,
        )
    
    @classmethod
    def check_scan_mode(
        cls,
        user: User,
        scan_mode: str,
    ) -> TierCheckResponse:
        """
        Check if user's tier allows the requested scan mode
        
        Args:
            user: User to check
            scan_mode: Requested scan mode
            
        Returns:
            TierCheckResponse with allowed status and details
        """
        # Owners can use any scan mode
        if is_owner_email(user.email):
            return TierCheckResponse(
                allowed=True,
                reason=None,
                current_usage=None,
                limit=None,
            )
        
        tier_str = normalize_tier(user.tier)
        limits = cls.get_tier_limits(tier_str, user.email)
        allowed = scan_mode in limits.allowed_scan_modes
        
        return TierCheckResponse(
            allowed=allowed,
            reason=None if allowed else f"Scan mode '{scan_mode}' not allowed for {tier_str} tier. Allowed modes: {', '.join(limits.allowed_scan_modes)}",
            current_usage=None,
            limit=None,
        )
    
    @classmethod
    async def check_scan_access(
        cls,
        db: AsyncSession,
        user: User,
        scan_mode: str,
    ) -> TierCheckResponse:
        """
        Comprehensive check for scan access (both limit and mode)
        
        Args:
            db: Database session
            user: User to check
            scan_mode: Requested scan mode
            
        Returns:
            TierCheckResponse with allowed status and details
        """
        # Check scan mode first (faster check)
        mode_check = cls.check_scan_mode(user, scan_mode)
        if not mode_check.allowed:
            return mode_check
        
        # Check scan limit
        limit_check = await cls.check_scan_limit(db, user)
        return limit_check
