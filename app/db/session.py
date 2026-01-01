"""
Database session management
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool, StaticPool

from app.core.config import settings


# Determine if using SQLite or PostgreSQL
is_sqlite = "sqlite" in settings.DATABASE_URL

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
    # PostgreSQL configuration
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.ENVIRONMENT == "development",
        future=True,
        pool_pre_ping=True,
        poolclass=NullPool,
        connect_args={
            "prepared_statement_cache_size": 0,
        }
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
