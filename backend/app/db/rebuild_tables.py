#!/usr/bin/env python
"""
Script to rebuild database tables with updated schema.
"""

import os
import sys
import uuid
from sqlalchemy import create_engine
from sqlalchemy.schema import DropTable
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import asyncio

# Add project root to system path for imports when running as script
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

# Custom PostgreSQL CASCADE drop
@compiles(DropTable, "postgresql")
def _compile_drop_table(element, compiler, **kwargs):
    return compiler.visit_drop_table(element) + " CASCADE"

# Import models and settings
from backend.app.db.models import Base, APIKey
from backend.app.utils.config import settings
from ..utils.logger import get_logger
from .session import engine

logger = get_logger("rebuild_tables")

async def rebuild_tables():
    """Drop and recreate all tables with updated schema."""
    try:
        # Drop all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            logger.info("Dropped all existing tables")
        
        # Create tables with updated schema
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Created tables with updated schema")
            
    except Exception as e:
        logger.error(f"Error rebuilding tables: {str(e)}")
        raise

if __name__ == "__main__":
    print("\n🔧 Duke VC Insight Engine - Database Setup")
    print("\nThis script will:")
    print("  1. DROP ALL TABLES in your Supabase database")
    print("  2. Create new tables based on your models")
    print("\n⚠️  Type 'YES' to proceed: ")
    confirm = input()
    if confirm.upper() == "YES":
        asyncio.run(rebuild_tables())
        print("\n✅ Database tables rebuilt successfully!")
    else:
        print("\n❌ Operation cancelled.") 