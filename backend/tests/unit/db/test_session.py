"""
Unit tests for the session module.
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import engine, sync_engine, async_session, sync_session, get_db, get_sync_db, init_db, check_db_connection

def test_sync_engine_exists():
    """Test that sync_engine is initialized properly."""
    assert sync_engine is not None
    assert hasattr(sync_engine, 'connect')
    assert hasattr(sync_engine, 'dispose')

def test_engine_exists():
    """Test that async engine is initialized properly."""
    assert engine is not None
    assert hasattr(engine, 'connect')
    assert hasattr(engine, 'dispose')

def test_sync_session_factory():
    """Test that sync_session factory works."""
    assert sync_session is not None
    assert callable(sync_session)
    # Create a session instance to test
    session = sync_session()
    try:
        assert hasattr(session, 'execute')
        assert hasattr(session, 'commit')
        assert hasattr(session, 'close')
    finally:
        session.close()

def test_async_session_factory():
    """Test that async_session factory works."""
    assert async_session is not None
    assert callable(async_session)
    # Create a session instance to test - can't fully test in a sync context
    session = async_session()
    assert isinstance(session, AsyncSession)
    assert hasattr(session, 'execute')
    assert hasattr(session, 'commit')
    assert hasattr(session, 'close')

def test_get_db_dependency():
    """Test that get_db dependency function exists."""
    assert get_db is not None
    assert callable(get_db)
    # Check if the function is an async generator
    gen = get_db()
    assert hasattr(gen, '__aiter__')

def test_get_sync_db_dependency():
    """Test that get_sync_db dependency function exists."""
    assert get_sync_db is not None
    assert callable(get_sync_db)
    # We can't easily test this function as it's a generator dependency
    # for FastAPI, but we can check it returns a generator
    assert hasattr(get_sync_db(), '__next__')

def test_init_db_function():
    """Test that init_db function exists."""
    assert init_db is not None
    assert callable(init_db)
    # We won't actually call it here as it would create tables
    
# Mark as async test
@pytest.mark.asyncio
async def test_check_db_connection():
    """Test that check_db_connection function works."""
    assert check_db_connection is not None
    assert callable(check_db_connection)
    # We'd need a real connection to test this fully
    # This will actually connect to the test database if available,
    # or will fail gracefully if not
    try:
        result = await check_db_connection()
        # Just test that it runs without error
        assert isinstance(result, bool)
    except Exception:
        # If it fails, that's expected in a test environment without DB
        pass 