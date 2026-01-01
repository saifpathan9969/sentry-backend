"""
Database session management
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool, StaticPool
import ssl

from app.core.config import settings


# Determine if using SQLite or PostgreSQL
is_sqlite = "sqlite" in settings.DATABASE_URL

# Convert DATABASE_URL to async format if needed
database_url = settings.DATABASE_URL
if database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    # Remove sslmode from URL as asyncpg uses ssl parameter differently
    if "sslmode=" in database_url:
        # Remove sslmode parameter from URL
        import re
        database_url = re.sub(r'[\?&]sslmode=[^&]*', '', database_url)
        # Clean up any trailing ? or &
        database_url = database_url.rstrip('?&')

# Create async engine with appropriate settings
if is_sqlite:
    # SQLite configuration
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.ENVIRONMENT == "development",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    # PostgreSQL configuration (Neon/Render compatible)
    # Create SSL context for secure connection
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    engine = create_async_engine(
        database_url,
        echo=settings.ENVIRONMENT == "development",
        future=True,
        pool_pre_ping=True,
        poolclass=NullPool,
        connect_args={"ssl": ssl_context},
    )

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# Alias for compatibility
async_session_maker = AsyncSessionLocal


async def get_db() -> AsyncSession:
    """
    Dependency for getting async database sessions
    
    Yields:
        AsyncSession: Database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
