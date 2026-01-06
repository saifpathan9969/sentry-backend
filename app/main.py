"""
Main FastAPI application entry point
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import traceback

from app.core.config import settings
from app.api.v1.api import api_router
from app.db.session import engine
from app.db.base import Base
from app.middleware.usage_tracking import UsageTrackingMiddleware
from app.middleware.rate_limit import RateLimitMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events
    """
    # Startup
    logger.info("Starting up AI Pentest Brain Web API...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'SQLite'}")
    
    # Create database tables automatically for demo/development
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
    
    # Auto-create owner accounts if they don't exist
    await create_owner_accounts()
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI Pentest Brain Web API...")
    await engine.dispose()


async def create_owner_accounts():
    """
    Automatically create owner accounts on startup if they don't exist
    """
    try:
        from app.db.session import AsyncSessionLocal
        from app.models.user import User
        from app.models.subscription import Subscription
        from sqlalchemy import select
        from passlib.context import CryptContext
        
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        async with AsyncSessionLocal() as db:
            for email in settings.OWNER_EMAILS:
                # Check if user already exists
                result = await db.execute(select(User).where(User.email == email))
                existing_user = result.scalar_one_or_none()
                
                if not existing_user:
                    # Create owner user
                    hashed_password = pwd_context.hash("Sentry@779969")
                    user = User(
                        email=email,
                        password_hash=hashed_password,  # Correct field name
                        full_name="Owner Account",
                        is_active=True,
                        email_verified=True
                    )
                    db.add(user)
                    await db.flush()  # Get the user ID
                    
                    # Create enterprise subscription
                    subscription = Subscription(
                        user_id=user.id,
                        tier="enterprise",
                        status="active",
                        is_active=True
                    )
                    db.add(subscription)
                    
                    logger.info(f"Created owner account: {email}")
                else:
                    logger.info(f"Owner account already exists: {email}")
            
            await db.commit()
            logger.info("Owner accounts initialization complete")
            
    except Exception as e:
        logger.error(f"Failed to create owner accounts: {str(e)}")
        # Don't fail startup if owner creation fails


# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="AI-powered penetration testing platform with comprehensive vulnerability scanning",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS - Allow all origins for production (Vercel generates dynamic URLs)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting middleware (before usage tracking)
app.add_middleware(RateLimitMiddleware)

# Add usage tracking middleware
app.add_middleware(UsageTrackingMiddleware)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)


# Global exception handler for debugging
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler to log and return detailed errors in development
    """
    error_detail = str(exc)
    error_traceback = traceback.format_exc()
    
    logger.error(f"Unhandled exception: {error_detail}")
    logger.error(f"Traceback: {error_traceback}")
    
    if settings.ENVIRONMENT == "development":
        return JSONResponse(
            status_code=500,
            content={
                "detail": error_detail,
                "type": type(exc).__name__,
                "traceback": error_traceback
            }
        )
    else:
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )


@app.get("/debug/scans/{scan_id}")
async def debug_scan(scan_id: str):
    """
    Debug endpoint to check scan status
    """
    try:
        from app.db.session import async_session_maker
        from app.models.scan import Scan
        from sqlalchemy import select
        from uuid import UUID
        
        async with async_session_maker() as db:
            query = select(Scan).where(Scan.id == UUID(scan_id))
            result = await db.execute(query)
            scan = result.scalar_one_or_none()
            
            if not scan:
                return {"error": "Scan not found"}
            
            return {
                "id": str(scan.id),
                "target": scan.target,
                "status": scan.status,
                "scan_mode": scan.scan_mode,
                "execution_mode": scan.execution_mode,
                "created_at": scan.created_at.isoformat() if scan.created_at else None,
                "started_at": scan.started_at.isoformat() if scan.started_at else None,
                "completed_at": scan.completed_at.isoformat() if scan.completed_at else None,
                "vulnerabilities_found": scan.vulnerabilities_found,
                "critical_count": scan.critical_count,
                "high_count": scan.high_count,
                "medium_count": scan.medium_count,
                "low_count": scan.low_count,
                "platform_detected": scan.platform_detected,
                "confidence": scan.confidence,
                "duration_seconds": scan.duration_seconds,
                "error_message": scan.error_message,
            }
    except Exception as e:
        return {"error": str(e)}


@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT
    }


@app.get("/")
async def root():
    """
    Root endpoint
    """
    return {
        "message": "Sentry Security API",
        "version": settings.VERSION,
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
