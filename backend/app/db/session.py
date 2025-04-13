"""
Database Session Management Module

This module handles database connection and session management using SQLAlchemy.
Provides async session factory and connection pooling configuration.

Key Features:
- Async SQLAlchemy engine
- Connection pooling
- Session management
- FastAPI dependency injection
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from ..utils.config import settings
from ..utils.logger import db_logger as logger
from typing import Generator


# Create async engine for SQLAlchemy
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.SQL_ECHO,  # Set to True for debugging
    future=True,
    pool_pre_ping=True,  # Basic connection health check
    pool_size=5,
    max_overflow=10
)

# Create sync engine for migrations and scripts
sync_engine = create_engine(
    settings.DATABASE_URL.replace("asyncpg", "psycopg2"),
    echo=settings.SQL_ECHO,
    future=True,
    pool_recycle=3600  # Recycle connections after 1 hour
)

# Create session factory
async_session = sessionmaker(
    engine, 
    expire_on_commit=False, 
    class_=AsyncSession
)

# Create sync session factory
sync_session = sessionmaker(
    sync_engine,
    expire_on_commit=False
)

async def get_db():
    """
    FastAPI dependency for database sessions.
    
    Yields:
        AsyncSession: Database session
        
    Note:
        Session is automatically closed after request
    """
    db = async_session()
    try:
        logger.debug("Creating new database session")
        yield db
    except Exception as e:
        logger.error(f"Database session error: {str(e)}")
        await db.rollback()
        raise
    finally:
        logger.debug("Closing database session")
        await db.close()

def get_sync_db():
    """Function for getting sync database session"""
    db = sync_session()
    try:
        logger.debug("Creating new sync database session")
        yield db
    except Exception as e:
        logger.error(f"Database session error: {str(e)}")
        db.rollback()
        raise
    finally:
        logger.debug("Closing sync database session")
        db.close()

# Initialize database (for use in scripts)
def init_db():
    """Initialize database tables"""
    from .models import Base
    
    logger.info("Creating database tables")
    Base.metadata.create_all(bind=sync_engine)
    logger.info("Database tables created")

# Simple database health check function
async def check_db_connection():
    """Check if database connection is healthy"""
    try:
        from sqlalchemy import text
        db = async_session()
        await db.execute(text("SELECT 1"))
        await db.close()
        return True
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        return False 