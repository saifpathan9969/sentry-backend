"""
Admin endpoints for owner account management
"""
from fastapi import APIRouter, HTTPException
from sqlalchemy import select, update
from app.db.session import AsyncSessionLocal
from app.models.user import User
from passlib.context import CryptContext

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@router.post("/reset-owner-passwords")
async def reset_owner_passwords():
    """
    Reset owner account passwords to Sentry@779969
    This is a temporary endpoint for production setup
    """
    owner_emails = [
        "saifullahpathan49@gmail.com",
        "saifullah.pathan24@sanjivani.edu.in"
    ]
    
    correct_password = "Sentry@779969"
    hashed_password = pwd_context.hash(correct_password)
    
    async with AsyncSessionLocal() as db:
        try:
            results = []
            for email in owner_emails:
                # Update password for existing user
                result = await db.execute(
                    update(User)
                    .where(User.email == email)
                    .values(
                        password_hash=hashed_password,
                        tier="enterprise",
                        is_active=True,
                        email_verified=True
                    )
                )
                
                if result.rowcount > 0:
                    results.append(f"✅ Password reset for: {email}")
                else:
                    results.append(f"❌ User not found: {email}")
            
            await db.commit()
            
            return {
                "success": True,
                "message": "Owner passwords reset successfully",
                "results": results,
                "password": correct_password
            }
            
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Error resetting passwords: {str(e)}")