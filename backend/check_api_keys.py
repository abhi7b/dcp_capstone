import asyncio
from app.db.session import async_session
from sqlalchemy import select
from app.db.models import APIKey

async def check_api_keys():
    async with async_session() as db:
        result = await db.execute(select(APIKey))
        print('API Keys in database:')
        for key in result.scalars():
            print(f'- {key.key} (active: {key.is_active})')

if __name__ == '__main__':
    asyncio.run(check_api_keys()) 