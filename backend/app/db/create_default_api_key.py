"""
Script to create a default API key for development

Run this script to create a default API key for development to test the API.

"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select  # Import select
import uuid # Import uuid

from .models import APIKey
from ..utils.config import settings
from ..utils.logger import get_logger

logger = get_logger(__name__)

async def create_default_api_key():
    """Create or retrieve the default API key for development."""
    dev_key_name = "Development API Key"
    try:
        # Create async engine
        engine = create_async_engine(
            settings.DATABASE_URL,
            echo=settings.SQL_ECHO,
            pool_pre_ping=True
        )
        
        # Create async session
        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        
        async with async_session() as session:
            # Check if the key already exists by name
            result = await session.execute(select(APIKey).where(APIKey.name == dev_key_name))
            existing_key = result.scalar_one_or_none()

            if existing_key:
                logger.info(f"Default API key '{dev_key_name}' already exists with key: {existing_key.key}")
                dev_key_value = existing_key.key
            else:
                # Generate a new key and create the entry
                new_key_value = str(uuid.uuid4())
                api_key = APIKey(
                    key=new_key_value, # Use newly generated key
                    name=dev_key_name,
                    is_active=True,
                    rate_limit=100  # 100 requests per minute
                )
                
                session.add(api_key)
                await session.commit()
                await session.refresh(api_key)
                
                logger.info(f"Created default API key '{dev_key_name}' with key: {api_key.key}")
                dev_key_value = api_key.key
            
            logger.info(f"To use this key, set the DEV_API_KEY environment variable:")
            logger.info(f"  export DEV_API_KEY={dev_key_value}")
            logger.info(f"Or add DEV_API_KEY={dev_key_value} to your .env file")
            
    except Exception as e:
        logger.error(f"Failed to process default API key: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(create_default_api_key()) 