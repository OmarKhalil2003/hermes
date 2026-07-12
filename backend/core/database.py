from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.core.config import settings
from backend.core.logging import logger

# Create the async engine with production-ready connection pooling options
engine = create_async_engine(
    settings.db.async_url,
    pool_size=20,
    max_overflow=10,
    pool_recycle=3600,
    pool_pre_ping=True,
    echo=False,  # Set to True for verbose SQL logging in development if needed
)

# Configure the session factory
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession]:
    """Dependency for obtaining an asynchronous database session.

    Yields:
        AsyncSession: The database session.
    """
    async with async_session_factory() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error occurred: {e}", exc_info=True)
            raise
        finally:
            await session.close()
