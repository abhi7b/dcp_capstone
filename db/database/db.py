"""
Database connection and session management.

This module provides SQLAlchemy connection management for PostgreSQL.
It handles connection pooling, session creation, and connection testing.
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from sqlalchemy import text
import os

from backend.config import settings, get_logger

# Initialize logger
logger = get_logger(__name__)

# Create async engine with proper URL
def create_db_engine():
    """
    Create and return a SQLAlchemy async engine for PostgreSQL.
    
    Uses DATABASE_URL from environment variables or settings.
    Configures connection pooling based on settings.
    """
    # Get database URL from settings or environment
    db_url = os.environ.get("DATABASE_URL") or settings.DATABASE_URL
    
    logger.info(f"Creating database engine with URL: {db_url}")
    
    try:
        return create_async_engine(
            db_url,
            pool_size=settings.DATABASE_POOL_SIZE,
            max_overflow=settings.DATABASE_MAX_OVERFLOW,
            pool_pre_ping=True,  # Verify connections before using them
            pool_recycle=3600,   # Recycle connections after 1 hour
        )
    except Exception as e:
        logger.error(f"Failed to create database engine: {e}")
        raise

# Create engine instance
engine = create_db_engine()

# Create async session factory
async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# Create declarative base
Base = declarative_base()

# Dependency to get DB session
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async DB session.
    
    Yields:
        AsyncSession: SQLAlchemy async session
        
    Example:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    async with async_session() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()

# Context manager for DB session
@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for getting async DB session.
    
    Yields:
        AsyncSession: SQLAlchemy async session
        
    Example:
        async with get_db_context() as db:
            result = await db.execute(select(Item))
            items = result.scalars().all()
    """
    async with async_session() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()

# Test database connection
async def test_connection() -> bool:
    """
    Test the database connection.
    
    Returns:
        bool: True if connection is successful, False otherwise
    """
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection test successful")
        return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False

# Close database connection
async def close_db_connection() -> None:
    """Close the database connection pool."""
    try:
        await engine.dispose()
        logger.info("Database connection closed")
    except Exception as e:
        logger.error(f"Failed to close database connection: {e}") 