#!/usr/bin/env python
"""
Database schema check utility.

Checks the actual schema of the PostgreSQL database tables.
"""
import asyncio
import sys
from pathlib import Path


from backend.config import settings, init_logging, get_logger
from db.database.db import engine, close_db_connection
from sqlalchemy import text

# Initialize logging
init_logging()
logger = get_logger(__name__)

async def get_table_columns(table_name):
    """Get the columns for a specific table."""
    try:
        async with engine.connect() as conn:
            # PostgreSQL query to get column names
            result = await conn.execute(text(
                f"SELECT column_name, data_type FROM information_schema.columns "
                f"WHERE table_name = '{table_name}' ORDER BY ordinal_position"
            ))
            columns = [(row[0], row[1]) for row in result.fetchall()]
            
            if columns:
                logger.info(f"Columns in table '{table_name}':")
                for col_name, col_type in columns:
                    logger.info(f"  - {col_name} ({col_type})")
            else:
                logger.warning(f"No columns found for table '{table_name}'")
            
            return columns
    except Exception as e:
        logger.error(f"Failed to get columns for table '{table_name}': {e}")
        return []

async def main():
    """Check the database schema."""
    logger.info("Starting database schema check")
    
    try:
        # Get list of tables
        async with engine.connect() as conn:
            result = await conn.execute(text(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
            ))
            tables = [row[0] for row in result.fetchall()]
        
        # Check columns for each table
        for table in tables:
            await get_table_columns(table)
        
        logger.info("Database schema check complete!")
        return 0
    finally:
        # Always close the database connection
        await close_db_connection()

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 