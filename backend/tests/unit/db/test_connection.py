"""
Test database connection script.

This script tests the database connection using the existing session setup
from app.db.session.
"""
import asyncio
import pytest
from sqlalchemy import text

from app.db.session import check_db_connection, async_session
from app.utils.logger import get_logger

logger = get_logger(__name__)

@pytest.mark.asyncio
async def test_db_connection():
    """Test database connection and basic queries."""
    try:
        # Test basic connection
        is_connected = await check_db_connection()
        assert is_connected, "Failed to establish database connection"
        logger.info("✅ Basic connection test passed")
        
        # Test session and queries
        async with async_session() as session:
            # Test version query
            result = await session.execute(text("SELECT version();"))
            version = result.scalar()
            logger.info(f"Database version: {version}")
            
            # Test current database
            result = await session.execute(text("SELECT current_database();"))
            db_name = result.scalar()
            logger.info(f"Connected to database: {db_name}")
            
            # Test current user
            result = await session.execute(text("SELECT current_user;"))
            user = result.scalar()
            logger.info(f"Connected as user: {user}")
            
            logger.info("✅ All database tests passed")
            
    except Exception as e:
        logger.error(f"❌ Database test failed: {str(e)}")
        raise

if __name__ == "__main__":
    # Run the test directly
    asyncio.run(test_db_connection()) 