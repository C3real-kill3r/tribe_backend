"""
Database session management with async SQLAlchemy.
"""
import asyncio
import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.exc import OperationalError

from app.core.config import settings

logger = logging.getLogger(__name__)

# Log database connection info (without credentials)
def _mask_database_url(url: str) -> str:
    """Mask database URL for logging (hide password)."""
    if "@" in url:
        parts = url.split("@")
        if len(parts) == 2:
            # Mask the user:password part
            auth_part = parts[0]
            if "://" in auth_part:
                scheme_part = auth_part.split("://")[0] + "://"
                user_pass = auth_part.split("://")[1]
                if ":" in user_pass:
                    user = user_pass.split(":")[0]
                    masked = f"{scheme_part}{user}:***@{parts[1]}"
                    return masked
    return url

# Create async engine with connection pooling
# Use database_url_async to ensure asyncpg driver is used
database_url = settings.database_url_async
logger.info(f"Connecting to database: {_mask_database_url(database_url)}")

engine = create_async_engine(
    database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_pre_ping=True,  # Verify connections before using them
    pool_recycle=3600,  # Recycle connections every hour
    connect_args={
        "server_settings": {
            "application_name": settings.app_name,
        },
    },
    echo=settings.debug,
    future=True
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# Base class for declarative models
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session.
    
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


async def init_db() -> None:
    """
    Initialize database tables with retry logic.
    
    Retries connection with exponential backoff to handle cases where
    the database might not be immediately available (e.g., during deployment).
    """
    max_retries = 5
    base_delay = 2  # seconds
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Attempting to connect to database (attempt {attempt + 1}/{max_retries})...")
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database connection successful and tables initialized.")
            return
        except (OperationalError, ConnectionRefusedError, OSError) as e:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)  # Exponential backoff
                logger.warning(
                    f"Database connection failed (attempt {attempt + 1}/{max_retries}): {str(e)}. "
                    f"Retrying in {delay} seconds..."
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    f"Failed to connect to database after {max_retries} attempts. "
                    f"Last error: {str(e)}"
                )
                raise
        except Exception as e:
            logger.error(f"Unexpected error during database initialization: {str(e)}")
            raise


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()

