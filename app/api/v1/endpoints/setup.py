"""
Setup endpoint for initializing production database
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.db.session import get_db
from app.models.user import User
from app.models.subscription import Subscription
from app.services.auth_service import AuthService
from app.core.config import settings

router = APIRouter()

class InitializeRequest(BaseModel):
    secret_key: str

@router.post("/initialize-database")
async def initialize_database(
    request: InitializeRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Initialize database with owner accounts
    Requires secret key for security
    """
    # Verify secret key
    if request.secret_key != settings.SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid secret key"
        )
    
    try:
        # Check if owners already exist
        existing_owners = []
        for email in settings.OWNER_EMAILS:
            result = await db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
            if user:
                existing_owners.append(email)
        
        if existing_owners:
            return {
                "status": "already_initialized",
                "message": f"Owner accounts already exist: {existing_owners}",
                "existing_owners": existing_owners
            }
        
        # Create owner accounts
        auth_service = AuthService()
        created_owners = []
        
        for email in settings.OWNER_EMAILS:
            # Create owner user
            user_data = {
                "email": email,
                "password": "sentry@779969",  # Default password
                "first_name": "Owner",
                "last_name": "Account",
                "is_active": True,
                "is_verified": True
            }
            
            user = await auth_service.create_user(db, user_data)
            
            # Create enterprise subscription
            subscription = Subscription(
                user_id=user.id,
                tier="enterprise",
                status="active",
                is_active=True
            )
            db.add(subscription)
            
            created_owners.append({
                "email": email,
                "user_id": user.id,
                "tier": "enterprise"
            })
        
        await db.commit()
        
        return {
            "status": "success",
            "message": "Database initialized successfully",
            "created_owners": created_owners,
            "login_credentials": {
                "emails": settings.OWNER_EMAILS,
                "password": "sentry@779969"
            }
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database initialization failed: {str(e)}"
        )

@router.get("/database-status")
async def database_status(db: AsyncSession = Depends(get_db)):
    """
    Check database status and existing users
    """
    try:
        # Count total users
        result = await db.execute(select(User))
        all_users = result.scalars().all()
        
        # Check owner accounts
        owner_accounts = []
        for email in settings.OWNER_EMAILS:
            result = await db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
            if user:
                # Get subscription
                sub_result = await db.execute(
                    select(Subscription).where(Subscription.user_id == user.id)
                )
                subscription = sub_result.scalar_one_or_none()
                
                owner_accounts.append({
                    "email": user.email,
                    "user_id": user.id,
                    "is_active": user.is_active,
                    "is_verified": user.is_verified,
                    "tier": subscription.tier if subscription else "none",
                    "subscription_status": subscription.status if subscription else "none"
                })
        
        return {
            "status": "success",
            "total_users": len(all_users),
            "owner_accounts": owner_accounts,
            "database_ready": len(owner_accounts) > 0
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database status check failed: {str(e)}"
        )