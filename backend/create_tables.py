##### create_tables.py #####
"""
Creates all tables in the database.
Usage:
   python create_tables.py
"""

import asyncio
import logging
from database import engine, Base
from sqlalchemy.exc import SQLAlchemyError

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

async def recreate_tables():
    """Drops and recreates database tables asynchronously."""
    try:
        async with engine.begin() as conn:
            logging.info("Dropping existing tables...")
            await conn.run_sync(Base.metadata.drop_all)  # Drop all tables
            logging.info("Tables dropped successfully!")

            logging.info("Creating new tables...")
            await conn.run_sync(Base.metadata.create_all)  # Recreate tables
            logging.info("Tables created successfully!")
    except SQLAlchemyError as e:
        logging.error(f"Database error during table recreation: {e}")
    finally:
        await engine.dispose()  # Close the connection properly
        logging.info("Database connection closed.")

if __name__ == "__main__":
    logging.info("Running database initialization script...")
    asyncio.run(recreate_tables())
    logging.info("All tables initialized!")

