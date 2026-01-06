"""
Database session management - SQLite only for production
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings


# Use SQLite for all environments (production ready)
database_url = "sqlite+aiosqlite:///./pentest_brain.db"

# Create async engine with SQLite configuration
engine = create_async_engine(
    database_url,
    echo=settings.ENVIRONMENT == "development",
    future=True,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
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
