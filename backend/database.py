from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool, QueuePool
from typing import AsyncGenerator
import logging

from backend.config import settings
from backend.exceptions import DatabaseError

logger = logging.getLogger(__name__)

# Configure engine with connection pooling
engine_kwargs = {
    "echo": settings.DB_ECHO,
    "future": True,
}

# Use connection pooling for non-SQLite databases
if "sqlite" not in settings.DATABASE_URL.lower():
    engine_kwargs.update({
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        "pool_pre_ping": True,  # Verify connections before using
        "pool_recycle": 3600,  # Recycle connections after 1 hour
    })
else:
    # SQLite doesn't support connection pooling
    engine_kwargs["poolclass"] = NullPool

engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()


async def init_db() -> None:
    """
    Initialize database tables and verify connection.
    
    Raises:
        DatabaseError: If database initialization fails
    """
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialized successfully")
        
        # Verify connection
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
        logger.info("Database connection verified")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise DatabaseError(f"Database initialization failed: {str(e)}") from e


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for database sessions.
    
    Yields:
        AsyncSession: Database session
        
    Raises:
        DatabaseError: If session creation fails
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {str(e)}")
            raise DatabaseError(f"Database operation failed: {str(e)}") from e
        finally:
            await session.close()


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()
    logger.info("Database connections closed")
