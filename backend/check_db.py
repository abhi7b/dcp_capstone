import asyncio
from app.db.session import async_session
from sqlalchemy import text

async def check_db():
    async with async_session() as db:
        # Check persons with all relevant fields
        result = await db.execute(text('''
            SELECT id, name, title, current_company, duke_affiliation_status, 
                   education, previous_companies, twitter_handle, linkedin_handle,
                   twitter_summary, source_links, relevance_score, updated_at
            FROM persons 
            WHERE name IN ('Steven Galanis', 'Devon Spinnler', 'Dario Amodei', 'Derek Carlson')
        '''))
        print("\nPersons (Detailed):")
        for row in result.fetchall():
            print("\nPerson Record:")
            print(f"ID: {row[0]}")
            print(f"Name: {row[1]}")
            print(f"Title: {row[2]}")
            print(f"Current Company: {row[3]}")
            print(f"Duke Affiliation Status: {row[4]}")
            print(f"Education: {row[5]}")
            print(f"Previous Companies: {row[6]}")
            print(f"Twitter Handle: {row[7]}")
            print(f"LinkedIn Handle: {row[8]}")
            print(f"Twitter Summary: {row[9]}")
            print(f"Source Links: {row[10]}")
            print(f"Relevance Score: {row[11]}")
            print(f"Last Updated: {row[12]}")

        # Check companies
        result = await db.execute(text('''
            SELECT id, name 
            FROM companies 
            WHERE name = 'Cameo'
        '''))
        print("\nCompanies:")
        for row in result.fetchall():
            print(row)

        # Check associations
        result = await db.execute(text('''
            SELECT company_id, person_id 
            FROM company_person_association 
            WHERE company_id = 5
        '''))
        print("\nAssociations:")
        for row in result.fetchall():
            print(row)

if __name__ == "__main__":
    asyncio.run(check_db()) 