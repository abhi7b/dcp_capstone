from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from ..utils.config import settings
from ..utils.logger import db_logger

# Create async engine for SQLAlchemy
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # Set to True for debugging
    future=True,
    pool_pre_ping=True  # Basic connection health check
)

# Create sync engine for migrations and scripts
sync_engine = create_engine(
    settings.DATABASE_URL.replace("asyncpg", "psycopg2"),
    echo=False,
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
    """Dependency for getting async database session"""
    db = async_session()
    try:
        db_logger.debug("Creating new database session")
        yield db
    except Exception as e:
        db_logger.error(f"Database session error: {str(e)}")
        await db.rollback()
        raise
    finally:
        db_logger.debug("Closing database session")
        await db.close()

def get_sync_db():
    """Function for getting sync database session"""
    db = sync_session()
    try:
        db_logger.debug("Creating new sync database session")
        yield db
    except Exception as e:
        db_logger.error(f"Database session error: {str(e)}")
        db.rollback()
        raise
    finally:
        db_logger.debug("Closing sync database session")
        db.close()

# Initialize database (for use in scripts)
def init_db():
    """Initialize database tables"""
    from .models import Base
    
    db_logger.info("Creating database tables")
    Base.metadata.create_all(bind=sync_engine)
    db_logger.info("Database tables created")

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
        db_logger.error(f"Database connection error: {str(e)}")
        return False 