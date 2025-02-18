##### database.py #####
"""
Database Configuration Module (async) using SQLAlchemy 2.0+
- Implements connection pooling
- Provides session management
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from config import settings

# asyncpg
engine = create_async_engine(
    settings.DB_URL,
    echo=True,
    future=True,
    pool_pre_ping=True  # Keep connections alive
)

# Create an async session factory
SessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autoflush=False,
    expire_on_commit=False
)

Base = declarative_base()

# Ensure `get_db()` correctly yields `AsyncSession`
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
