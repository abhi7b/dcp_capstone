"""
Pytest configuration for DB tests.

This module provides fixtures for DB testing.
"""
import os
import pytest
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, Session
from app.db.models import Base
from app.db.session import get_db, get_sync_db

# Use in-memory SQLite for testing
TEST_DATABASE_URL = "sqlite+pysqlite:///:memory:"
TEST_ASYNC_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture(scope="function")
def sync_engine():
    """Create a synchronous SQLite in-memory engine for testing."""
    engine = create_engine(TEST_DATABASE_URL, echo=False, future=True)
    # Create tables
    Base.metadata.create_all(engine)
    yield engine
    # Drop tables
    Base.metadata.drop_all(engine)

@pytest.fixture(scope="function")
def async_engine():
    """Create an asynchronous SQLite in-memory engine for testing."""
    engine = create_async_engine(TEST_ASYNC_DATABASE_URL, echo=False, future=True)
    yield engine
    # Cleanup happens in db_session fixture

@pytest.fixture(scope="function")
def sync_db_session(sync_engine):
    """Create a synchronous DB session for testing."""
    connection = sync_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, expire_on_commit=False)
    
    yield session
    
    # Rollback transaction and close connection
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")
async def async_db_session(async_engine):
    """Create an asynchronous DB session for testing."""
    async with async_engine.begin() as conn:
        # Create tables
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(
        async_engine, expire_on_commit=False, class_=AsyncSession
    )
    
    async with async_session() as session:
        yield session
    
    # Drop tables
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture(scope="function")
def event_loop():
    """Create an event loop for async tests."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close() 