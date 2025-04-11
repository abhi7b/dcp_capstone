#!/usr/bin/env python
"""
Script to manage database tables.
Options:
1. Rebuild existing tables (drop and recreate)
2. Create fresh tables (only if they don't exist)
"""

import os
import sys
import asyncio
from sqlalchemy import inspect
from sqlalchemy.schema import DropTable
from sqlalchemy.ext.compiler import compiles
from ..utils.logger import db_logger as logger
from . import models
from .session import engine, sync_engine

# Add project root to system path for imports when running as script
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

# Custom PostgreSQL CASCADE drop
@compiles(DropTable, "postgresql")
def _compile_drop_table(element, compiler, **kwargs):
    return compiler.visit_drop_table(element) + " CASCADE"

def check_tables_exist_sync():
    """Check if any tables already exist in the database."""
    inspector = inspect(sync_engine)
    existing_tables = inspector.get_table_names()
    return len(existing_tables) > 0

async def rebuild_tables():
    """Drop and recreate all tables with updated schema."""
    try:
        # Drop all tables
        async with engine.begin() as conn:
            await conn.run_sync(models.Base.metadata.drop_all)
            logger.info("Dropped all existing tables")
        
        # Create tables with updated schema
        async with engine.begin() as conn:
            await conn.run_sync(models.Base.metadata.create_all)
            logger.info("Created tables with updated schema")
            
    except Exception as e:
        logger.error(f"Error rebuilding tables: {str(e)}")
        raise

async def create_fresh_tables():
    """Create tables only if they don't exist."""
    try:
        tables_exist = check_tables_exist_sync()
        if tables_exist:
            logger.warning("Tables already exist. Use rebuild option to recreate them.")
            return False
            
        # Create tables with updated schema
        async with engine.begin() as conn:
            await conn.run_sync(models.Base.metadata.create_all)
            logger.info("Created fresh tables")
            return True
            
    except Exception as e:
        logger.error(f"Error creating fresh tables: {str(e)}")
        raise

def print_menu():
    print("\nDuke VC Insight Engine - Database Setup")
    print("\nChoose an option:")
    print("1. Rebuild existing tables (DROP and recreate)")
    print("2. Create fresh tables (only if they don't exist)")
    print("3. Exit")
    return input("\nEnter your choice (1-3): ")

if __name__ == "__main__":
    while True:
        choice = print_menu()
        
        if choice == "1":
            print("\nWARNING: This will DROP ALL TABLES in your database")
            print("Type 'YES' to proceed with rebuilding tables: ")
            confirm = input()
            if confirm.upper() == "YES":
                asyncio.run(rebuild_tables())
                print("\nDatabase tables rebuilt successfully!")
            else:
                print("\nOperation cancelled.")
                
        elif choice == "2":
            print("\nCreating fresh tables (if they don't exist)...")
            success = asyncio.run(create_fresh_tables())
            if success:
                print("\nFresh tables created successfully!")
            else:
                print("\nTables already exist. Use option 1 to rebuild them.")
                
        elif choice == "3":
            print("\nExiting...")
            break
            
        else:
            print("\nInvalid choice. Please try again.")
            
        input("\nPress Enter to continue...") 