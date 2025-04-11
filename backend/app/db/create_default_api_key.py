"""
Script to create a default API key for development.
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from .models import APIKey
from ..utils.config import settings
from ..utils.logger import get_logger

logger = get_logger(__name__)

async def create_default_api_key():
    """Create a default API key for development."""
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
            # Create default API key
            api_key = APIKey(
                name="Development API Key",
                is_active=True,
                rate_limit=100  # 100 requests per minute
            )
            
            session.add(api_key)
            await session.commit()
            await session.refresh(api_key)
            
            logger.info(f"✅ Created default API key: {api_key.key}")
            logger.info("Use this key in your requests with the X-API-Key header")
            
    except Exception as e:
        logger.error(f"❌ Failed to create API key: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(create_default_api_key()) 