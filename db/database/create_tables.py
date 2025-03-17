#!/usr/bin/env python
"""
Database table creation utility.

Creates all database tables defined in the models module in PostgreSQL.
Can also drop all tables before creating them if specified.

Note: This script is maintained for backward compatibility.
For new code, please use the consolidated db_manager.py utility.
"""
import asyncio
import sys
import argparse
from pathlib import Path

from backend.config import settings, init_logging, get_logger
from db.database.db import engine, close_db_connection
from db.database.models import Base
from sqlalchemy import text

# Initialize logging
init_logging()
logger = get_logger(__name__)

async def drop_tables():
    """Drop all database tables."""
    logger.info(f"Dropping all tables in PostgreSQL database: {settings.DATABASE_URL}")
    
    try:
        # Drop tables using SQLAlchemy's drop_all method
        async with engine.begin() as conn:
            # This will drop all tables
            await conn.run_sync(Base.metadata.drop_all)
        
        logger.info("Tables dropped successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to drop tables: {e}")
        return False

async def create_tables():
    """Create all database tables defined in the models."""
    logger.info(f"Creating tables in PostgreSQL database: {settings.DATABASE_URL}")
    
    try:
        # Create tables using SQLAlchemy's create_all method
        async with engine.begin() as conn:
            # This will create tables that don't exist yet
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Tables created successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to create tables: {e}")
        return False

async def list_tables():
    """List all tables in the PostgreSQL database."""
    try:
        async with engine.connect() as conn:
            # PostgreSQL query to get table names
            result = await conn.execute(text(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
            ))
            tables = [row[0] for row in result.fetchall()]
            
            # Log tables
            if tables:
                logger.info(f"Found {len(tables)} tables in database:")
                for table in tables:
                    logger.info(f"  - {table}")
            else:
                logger.warning("No tables found in database")
            
            return tables
    except Exception as e:
        logger.error(f"Failed to list tables: {e}")
        return []

async def main(recreate=False):
    """Create database tables and list them."""
    logger.info("Starting database table creation")
    logger.info("Note: This script is maintained for backward compatibility. "
                "For new code, please use 'python -m db.database.db_manager create' or "
                "'python -m db.database.db_manager reset'")
    
    try:
        # Drop tables if recreate is True
        if recreate:
            logger.info("Recreate mode: dropping existing tables before creating new ones")
            drop_success = await drop_tables()
            if not drop_success:
                logger.error("Failed to drop tables. Exiting.")
                return 1
        
        # Create tables
        create_success = await create_tables()
        if not create_success:
            logger.error("Failed to create tables. Exiting.")
            return 1
        
        # List created tables
        await list_tables()
        
        if recreate:
            logger.info("Database table recreation complete!")
        else:
            logger.info("Database table creation complete!")
        return 0
    finally:
        # Always close the database connection
        await close_db_connection()

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Create or recreate database tables")
    parser.add_argument(
        "--recreate", 
        action="store_true", 
        help="Drop all existing tables before creating new ones"
    )
    args = parser.parse_args()
    
    # Run the main function with the recreate flag
    exit_code = asyncio.run(main(recreate=args.recreate))
    sys.exit(exit_code)
