"""
Application configuration settings
"""
from pydantic_settings import BaseSettings
from typing import List, Optional
import secrets


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables
    """
    # Project metadata
    PROJECT_NAME: str = "Sentry Security"
    VERSION: str = "3.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    
    # Security
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"
    
    # Database - SQLite for production (Render compatible)
    DATABASE_URL: str = "sqlite+aiosqlite:///./pentest_brain.db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
    # CORS - Production URLs for Vercel
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3002", 
        "http://localhost:5173",
        "http://localhost:8000",
        "http://localhost",
        # Vercel production URLs
        "https://neural-brain-security.vercel.app",
        "https://neural-brain-security-git-main.vercel.app",
        "https://*.vercel.app",
    ]
    
    # Email (for verification and password reset)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAILS_FROM_EMAIL: str = "noreply@pentestbrain.ai"
    EMAILS_FROM_NAME: str = "AI Pentest Brain"
    
    # Stripe
    STRIPE_API_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    
    # Rate limiting
    RATE_LIMIT_FREE_TIER: int = 100  # requests per hour
    RATE_LIMIT_PREMIUM_TIER: int = 10000  # requests per month
    
    # Scan limits
    SCAN_LIMIT_FREE_TIER: int = 10  # scans per day
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    # CLI Tool Path
    CLI_TOOL_PATH: str = "../ai_pentest_brain_complete.py"
    
    # Owner emails - these get full enterprise access for free
    OWNER_EMAILS: List[str] = [
        "saifullahpathan49@gmail.com",
        "saifullah.pathan24@sanjivani.edu.in"
    ]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create global settings instance
settings = Settings()
