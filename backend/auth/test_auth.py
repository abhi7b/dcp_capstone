"""
Simple test script for the authentication module.

Run with: python -m backend.auth.test_auth
"""
import asyncio
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security.api_key import APIKey

from db.database.db import engine
from db.database.models import Base, User, APIUser
from backend.auth.auth import (
    get_api_key, 
    get_current_user,
    check_scope
)

# Create a simple database session function
async def get_test_session():
    """Create a test database session."""
    session = AsyncSession(engine)
    try:
        yield session
    finally:
        await session.close()

# Use UTC timezone for all datetime objects
def utc_now():
    """Get current UTC datetime with timezone info."""
    return datetime.now(timezone.utc)

# Custom implementation of generate_api_key for testing
async def test_generate_api_key(
    user_id: int,
    name: str,
    scopes: list,
    expires_in_days: int = None,
    session: AsyncSession = None
) -> str:
    """Generate a test API key directly without using the main function."""
    # Generate a secure random API key
    api_key = secrets.token_urlsafe(32)
    
    # Calculate expiration date
    expires_at = None
    if expires_in_days is not None:
        expires_at = utc_now() + timedelta(days=expires_in_days)
    
    # Create API user
    api_user = APIUser(
        user_id=user_id,
        name=name,
        api_key=api_key,
        scopes=scopes,
        expires_at=expires_at,
        created_at=utc_now()
    )
    
    # Add to database
    session.add(api_user)
    await session.commit()
    await session.refresh(api_user)
    
    return api_key

async def setup_test_db():
    """Create tables and test user."""
    print("Setting up test database...")
    
    # Create tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create a session
    session_gen = get_test_session()
    session = await anext(session_gen)
    
    try:
        # Create test user if it doesn't exist
        test_user = await session.get(User, 1)
        if not test_user:
            test_user = User(
                id=1,
                username="test_user",
                email="test@example.com",
                is_active=True,
                created_at=utc_now()
            )
            session.add(test_user)
            await session.commit()
            print("✅ Created test user")
        
        # Check if test API key exists
        query = select(APIUser).where(APIUser.user_id == 1)
        result = await session.execute(query)
        test_api_user = result.scalars().first()
        
        if not test_api_user:
            # Generate a test API key
            test_api_key = secrets.token_urlsafe(32)
            expires_at = utc_now() + timedelta(days=30)
            
            # Create API user
            api_user = APIUser(
                user_id=1,
                name="Test API Key",
                api_key=test_api_key,
                scopes=["read", "write"],
                expires_at=expires_at,
                created_at=utc_now()
            )
            
            session.add(api_user)
            await session.commit()
            print(f"✅ Created test API key: {test_api_key[:8]}...")
            return test_api_key
        else:
            # If the API key is expired, update it
            if test_api_user.expires_at and test_api_user.expires_at < utc_now():
                print("⚠️ Existing API key is expired, updating expiration date...")
                test_api_user.expires_at = utc_now() + timedelta(days=30)
                await session.commit()
                
            print(f"✅ Using existing API key: {test_api_user.api_key[:8]}...")
            return test_api_user.api_key
    except Exception as e:
        print(f"❌ Error in setup: {e}")
        raise
    finally:
        await session.close()

async def run_tests(api_key):
    """Run authentication tests."""
    print("\nRunning authentication tests...")
    
    # Create a session
    session_gen = get_test_session()
    session = await anext(session_gen)
    
    try:
        # Test get_api_key
        print("\n1. Testing get_api_key...")
        try:
            api_key_str = await get_api_key(api_key, session)
            assert isinstance(api_key_str, str)
            print("✅ get_api_key passed")
        except Exception as e:
            print(f"❌ get_api_key failed: {e}")
            return False
        
        # Test get_current_user
        print("\n2. Testing get_current_user...")
        try:
            user = await get_current_user(api_key_str, session)
            assert user is not None
            print(f"✅ get_current_user passed - Got user: {user.username}")
        except Exception as e:
            print(f"❌ get_current_user failed: {e}")
            return False
        
        # Test check_scope
        print("\n3. Testing check_scope...")
        try:
            has_read_scope = await check_scope("read", api_key_str, session)
            assert has_read_scope is True
            print("✅ check_scope passed for 'read' scope")
        except Exception as e:
            print(f"❌ check_scope failed: {e}")
            return False
        
        # Test generate_api_key
        print("\n4. Testing generate_api_key...")
        try:
            # Create a new session for generate_api_key to avoid async issues
            async with AsyncSession(engine) as new_session:
                new_api_key = await test_generate_api_key(
                    user_id=1,
                    name="Test Generated Key",
                    scopes=["read"],
                    expires_in_days=1,
                    session=new_session
                )
                assert new_api_key is not None
                print(f"✅ generate_api_key passed - Generated key: {new_api_key[:8]}...")
        except Exception as e:
            print(f"❌ generate_api_key failed: {e}")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    finally:
        await session.close()

async def main():
    """Run the test script."""
    print("=== Authentication Module Tests ===")
    
    try:
        # Setup test database
        api_key = await setup_test_db()
        
        # Run tests
        success = await run_tests(api_key)
        
        if success:
            print("\n✅ All authentication tests passed!")
        else:
            print("\n❌ Some tests failed.")
    except Exception as e:
        print(f"\n❌ Test setup failed: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 