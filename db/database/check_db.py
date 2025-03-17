#!/usr/bin/env python
"""
Database connection check utility.

Verifies connection to the PostgreSQL database and lists tables.
"""
import asyncio
import sys
import os
from pathlib import Path


from backend.config import settings, init_logging, get_logger
from db.database.db import engine, test_connection, close_db_connection
from sqlalchemy import text

# Initialize logging
init_logging()
logger = get_logger(__name__)

async def list_tables():
    """List all tables in the PostgreSQL database and count rows."""
    try:
        async with engine.connect() as conn:
            # PostgreSQL query to get table names
            result = await conn.execute(text(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
            ))
            tables = [row[0] for row in result.fetchall()]
            
            if tables:
                logger.info("Tables in database:")
                for table in tables:
                    # Count rows in each table
                    try:
                        count_result = await conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                        count = count_result.scalar()
                        logger.info(f"  - {table}: {count} rows")
                    except Exception as e:
                        logger.error(f"  - {table}: Error counting rows: {e}")
            else:
                logger.warning("No tables found in database")
            
            return tables
    except Exception as e:
        logger.error(f"Failed to list tables: {e}")
        return []

async def get_connection_info():
    """Display database connection information."""
    # Get database URL from settings or environment
    url = os.environ.get("DATABASE_URL") or settings.DATABASE_URL
    
    # Mask password in URL for logging
    masked_url = url
    if "@" in url and "://" in url:
        prefix = url.split("://")[0]
        auth_part = url.split("://")[1].split("@")[0]
        if ":" in auth_part:
            user = auth_part.split(":")[0]
            masked_url = f"{prefix}://{user}:****@{url.split('@')[1]}"
    
    # Check if this is a Supabase URL
    is_supabase = "supabase.co" in url.lower()
    
    logger.info(f"Database URL: {masked_url}")
    if is_supabase:
        logger.info("Database type: Supabase PostgreSQL")
    else:
        if "postgresql" in url.lower():
            logger.info("Database type: PostgreSQL")
        else:
            logger.info(f"Database type: Unknown ({url.split('://')[0] if '://' in url else 'unknown'})")
    
    logger.info(f"Pool size: {settings.DATABASE_POOL_SIZE}")
    logger.info(f"Max overflow: {settings.DATABASE_MAX_OVERFLOW}")

async def main():
    """Check connection to database and list tables."""
    logger.info("Starting database check")
    
    try:
        # Display connection info
        await get_connection_info()
        
        # Test connection
        connection_ok = await test_connection()
        if not connection_ok:
            logger.error("Database connection failed. Exiting.")
            return 1
        
        # List tables
        await list_tables()
        
        logger.info("Database check complete!")
        return 0
    finally:
        # Always close the database connection
        await close_db_connection()

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)