"""
Test database connection script.

This script tests the database connection using the existing session setup
from app.db.session.
"""
import asyncio
import pytest
from sqlalchemy import text

from app.db.session import check_db_connection, async_session
from app.utils.config import settings

@pytest.mark.asyncio
async def test_db_connection():
    """Test database connection and basic queries."""
    try:
        # Print database URL (masking sensitive parts)
        db_url = settings.DATABASE_URL
        masked_url = db_url.split('@')[0] + '@' + '*****'  # Mask password
        print(f"\nTesting connection to database: {masked_url}")
        
        # Test basic connection
        is_connected = await check_db_connection()
        assert is_connected, "Failed to establish database connection"
        print("Database connection successful")
        
        # Test session and queries
        async with async_session() as session:
            # Test version query
            result = await session.execute(text("SELECT version();"))
            version = result.scalar()
            print(f"Database version: {version}")
            
            # Test current database
            result = await session.execute(text("SELECT current_database();"))
            db_name = result.scalar()
            print(f"Connected to database: {db_name}")
            
            # Test current user
            result = await session.execute(text("SELECT current_user;"))
            user = result.scalar()
            print(f"Connected as user: {user}")
            
            # Test basic query
            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1, "Basic query test failed"
            print("Basic query test successful\n")
            
    except Exception as e:
        print(f"Database test failed: {str(e)}")
        raise

if __name__ == "__main__":
    # Run the test directly
    asyncio.run(test_db_connection()) 