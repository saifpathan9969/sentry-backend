"""
Database session management
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool, StaticPool
import ssl

from app.core.config import settings


# Get DATABASE_URL with fallback to SQLite
database_url = getattr(settings, 'DATABASE_URL', None) or "sqlite+aiosqlite:///./pentest_brain.db"

# Ensure we have a valid database URL
if not database_url or database_url.strip() == "":
    database_url = "sqlite+aiosqlite:///./pentest_brain.db"

# Determine if using SQLite or PostgreSQL
is_sqlite = "sqlite" in database_url
is_postgres = "postgresql" in database_url
if database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    # Remove sslmode from URL as asyncpg uses ssl parameter differently
    if "sslmode=" in database_url:
        # Remove sslmode parameter from URL
        import re
        database_url = re.sub(r'[\?&]sslmode=[^&]*', '', database_url)
        # Clean up any trailing ? or &
        database_url = database_url.rstrip('?&')
elif database_url.startswith("sqlite:///"):
    # Convert SQLite URL to async format
    database_url = database_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)

# Create async engine with appropriate settings
if is_sqlite:
    # SQLite configuration with aiosqlite
    engine = create_async_engine(
        database_url,
        echo=settings.ENVIRONMENT == "development",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
elif is_postgres:
    # PostgreSQL configuration (Railway/Render compatible)
    engine = create_async_engine(
        database_url,
        echo=settings.ENVIRONMENT == "development",
        future=True,
        pool_pre_ping=True,
        poolclass=NullPool,
    )
elif is_postgres:
    # PostgreSQL configuration (Railway/Render compatible)
    engine = create_async_engine(
        database_url,
        echo=settings.ENVIRONMENT == "development",
        future=True,
        pool_pre_ping=True,
        poolclass=NullPool,
    )
else:
    # Fallback configuration
    engine = create_async_engine(
        database_url,
        echo=settings.ENVIRONMENT == "development",
        future=True,
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
