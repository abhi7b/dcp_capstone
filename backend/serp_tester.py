# tester for serp_scraper.py
import asyncio
from serp_scraper import DCPScraper  # Ensure this is correctly implemented

async def test_scraper():
    scraper = DCPScraper()
    results = await scraper.search_founder("Larry Page")
    await scraper.close()
    return results

loop = asyncio.get_event_loop()
print(loop.run_until_complete(test_scraper()))
