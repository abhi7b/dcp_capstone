#!/usr/bin/env python
"""
Database Rebuild Script

This script drops all existing tables and recreates them based on the models.
It also creates a default API key for development.
"""

import os
import sys
import uuid
from sqlalchemy import create_engine
from sqlalchemy.schema import DropTable
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

# Add project root to system path for imports when running as script
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

# Custom PostgreSQL CASCADE drop
@compiles(DropTable, "postgresql")
def _compile_drop_table(element, compiler, **kwargs):
    return compiler.visit_drop_table(element) + " CASCADE"

# Import models and settings
from backend.app.db.models import Base, APIKey
from backend.app.utils.config import settings

def rebuild_tables():
    """Rebuild all database tables and create an API key"""
    # Create a sync engine for database operations
    db_url = settings.DATABASE_URL.replace("asyncpg", "psycopg2")
    engine = create_engine(db_url)
    
    print(f"Connected to database.")
    
    # Drop all existing tables
    print("Dropping all existing tables...")
    Base.metadata.drop_all(engine)
    
    # Create new tables based on models
    print("Creating new tables...")
    Base.metadata.create_all(engine)
    
    print("Database tables rebuilt successfully!")
    
    # Create a new API key
    print("Creating default API key...")
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Generate a new API key
        api_key = str(uuid.uuid4())
        
        # Create new API key record
        new_key = APIKey(
            key=api_key,
            name="Development API Key",
            is_active=True,
            rate_limit=1000
        )
        
        # Add to database and commit
        session.add(new_key)
        session.commit()
        
        print(f"API Key created: {api_key}")
        
    except Exception as e:
        session.rollback()
        print(f"Error creating API key: {str(e)}")
    finally:
        session.close()

if __name__ == "__main__":
    print("\n🔧 Duke VC Insight Engine - Database Setup\n")
    print("This script will:")
    print("  1. DROP ALL TABLES in your Supabase database")
    print("  2. Create new tables based on your models")
    print("  3. Generate a default API key\n")
    
    confirm = input("⚠️  Type 'YES' to proceed: ")
    if confirm.upper() == "YES":
        rebuild_tables()
    else:
        print("Operation cancelled.") 