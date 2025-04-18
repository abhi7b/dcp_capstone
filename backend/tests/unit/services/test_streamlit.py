import pytest
import os
import json
import shutil
from pathlib import Path
from app.services.scraper import SERPScraper
from app.services.nlp_processor import NLPProcessor
from app.services.nitter import NitterScraper
from app.services.nitter_nlp import NitterNLP
from app.services.founder_scorer import FounderScorer
from app.utils.storage import StorageService
from app.utils.config import settings
from app.services.person_processor import PersonProcessor
from app.db.session import get_db
from app.db.models import Company, Person, company_person_association
from app.db.crud import get_company_by_name, create_company, update_company
from app.db import person_crud
from app.services.redis import redis_service
from app.db.migrate_json_to_db import migrate_json_to_db, process_company_data, process_person_data, process_company_people
from sqlalchemy import select

# --- Test Data Setup ---
@pytest.fixture
def stripe_serp_data():
    """Load the Stripe SERP data from the provided JSON file."""
    with open("app/data/raw/serp_company_stripe.json", "r") as f:
        return json.load(f)

@pytest.fixture
def stripe_founder_serp_data():
    """Load the Stripe founder SERP data from the provided JSON file."""
    with open("app/data/raw/serp_person_patrick_collison.json", "r") as f:
        return json.load(f)

@pytest.fixture
def cameo_serp_data():
    """Load the Cameo SERP data from the provided JSON file."""
    with open("app/data/raw/serp_company_Cameo.json", "r") as f:
        return json.load(f)

@pytest.fixture
def steven_galanis_serp_data():
    """Load the Steven Galanis SERP data from the provided JSON file."""
    with open("app/data/raw/serp_person_Steven_Galanis.json", "r") as f:
        return json.load(f)

@pytest.fixture
def martin_blencowe_serp_data():
    """Load the Martin Blencowe SERP data from the provided JSON file."""
    with open("app/data/raw/serp_person_Martin_Blencowe.json", "r") as f:
        return json.load(f)

@pytest.fixture
def storage():
    """Create a real storage service instance."""
    return StorageService()

@pytest.fixture
def scraper(cameo_serp_data, steven_galanis_serp_data, martin_blencowe_serp_data):
    """Create a SERP scraper that returns the Cameo and founder data."""
    scraper = SERPScraper()
    
    # Patch company search to return Cameo data
    async def mock_search_company(x):
        if x == "Cameo":
            return cameo_serp_data
        return None
    
    # Patch founder search to return appropriate founder data based on name
    async def mock_search_founder(x):
        if "Steven Galanis" in x:
            return steven_galanis_serp_data
        elif "Martin Blencowe" in x:
            return martin_blencowe_serp_data
        return None
    
    scraper.search_company = mock_search_company
    scraper.search_founder = mock_search_founder
    return scraper

@pytest.fixture
def nitter_scraper():
    """Create a real Nitter scraper instance."""
    return NitterScraper()

@pytest.fixture
def nitter_nlp():
    """Create a real Nitter NLP processor instance."""
    return NitterNLP()

@pytest.fixture
def founder_scorer():
    """Create a real founder scorer instance."""
    return FounderScorer()

@pytest.fixture
def person_processor():
    """Create a real person processor instance."""
    return PersonProcessor()

@pytest.fixture
def nlp_processor():
    """Create a real NLP processor instance."""
    return NLPProcessor()

@pytest.fixture
async def db():
    """Create a database session."""
    async for session in get_db():
        yield session

@pytest.fixture
def test_data_dir():
    """Create a test data directory structure."""
    base_dir = Path(__file__).parent.parent.parent
    test_data = {
        "raw": base_dir / "data" / "raw",
        "processed": base_dir / "data" / "processed",
        "final": base_dir / "data" / "final",
        "json_inputs": base_dir / "data" / "json_inputs"
    }
    
    # Create directories
    for dir_path in test_data.values():
        dir_path.mkdir(parents=True, exist_ok=True)
    
    yield test_data
    
    # Cleanup after test
    #for dir_path in test_data.values():
    #    if dir_path.exists():
    #        shutil.rmtree(dir_path)

# --- Test Functions ---
@pytest.mark.asyncio
async def test_company_search_pipeline(cameo_serp_data, storage, scraper, nitter_scraper, nitter_nlp, founder_scorer, person_processor, nlp_processor, db):
    """Test the company search pipeline exactly as used by the Streamlit app."""
    # Test data
    company_name = "Cameo"
    force_refresh = True  # Set to True to test full pipeline
    
    try:
        # Layer 1: Check Redis cache
        cache_key = f"company:{company_name.lower()}"
        cached_data = await redis_service.get(cache_key)
        if cached_data and not force_refresh:
            assert cached_data is not None
            assert "name" in cached_data
            assert "people" in cached_data
            return
        
        # Layer 2: Check database
        db_company = await get_company_by_name(db, company_name)
        if db_company and not force_refresh:
            # Get associated people
            result = await db.execute(
                select(Person)
                .join(company_person_association)
                .where(company_person_association.c.company_id == db_company.id)
            )
            people = result.scalars().all()
            
            # Create response dictionary
            company_dict = {
                "id": db_company.id,
                "name": db_company.name,
                "duke_affiliation_status": db_company.duke_affiliation_status,
                "relevance_score": db_company.relevance_score,
                "summary": db_company.summary,
                "investors": db_company.investors,
                "funding_stage": db_company.funding_stage,
                "industry": db_company.industry,
                "founded": db_company.founded,
                "location": db_company.location,
                "twitter_handle": db_company.twitter_handle,
                "linkedin_handle": db_company.linkedin_handle,
                "twitter_summary": db_company.twitter_summary,
                "source_links": db_company.source_links,
                "people": [
                    {
                        "name": p.name,
                        "title": p.title
                    }
                    for p in people
                ]
            }
            
            # Cache the database result
            await redis_service.set(cache_key, company_dict, expire=3600)
            return
        
        # Layer 3: Scrape and process new data
        # Scrape company data
        raw_serp_data = await scraper.search_company(company_name)
        assert raw_serp_data == cameo_serp_data
        assert "organic_results" in raw_serp_data
        
        # Save raw SERP data
        serp_file_path = Path(storage.save_raw_data(raw_serp_data, "serp_company", company_name))
        assert serp_file_path.exists()
        
        # Process with NLP pipeline
        processed_data = await nlp_processor.process_company(raw_serp_data)
        assert processed_data is not None
        assert "name" in processed_data
        assert "people" in processed_data
        
        # Verify intermediate data was saved
        clean_company_name = storage._clean_filename(company_name)
        intermediate_path = Path(storage.get_file_path(f"company_{clean_company_name}", "intermediate_extraction", settings.PROCESSED_DATA_DIR))
        assert intermediate_path.exists()
        
        intermediate_data = storage.load_data(f"company_{clean_company_name}", "intermediate_extraction", settings.PROCESSED_DATA_DIR)
        assert intermediate_data is not None
        assert "name" in intermediate_data
        assert "people" in intermediate_data
        
        # Process company Twitter data if handle exists
        if processed_data.get("twitter_handle"):
            nitter_results = await nitter_scraper.get_raw_tweets(processed_data["twitter_handle"])
            assert nitter_results is not None
            assert not nitter_results.get("twitter_unavailable", True)
            assert "raw_tweets" in nitter_results
            
            # Save raw Twitter data
            nitter_file_path = Path(storage.save_raw_data(nitter_results, "nitter", company_name))
            assert nitter_file_path.exists()
            
            # Analyze tweets
            summary, urgency_score = await nitter_nlp.analyze_tweets(nitter_results["raw_tweets"])
            processed_data["twitter_summary"] = summary
            processed_data["twitter_urgency_score"] = urgency_score
            
            # Save Twitter analysis
            nitter_analysis = {
                "summary": summary,
                "urgency_score": urgency_score
            }
            analysis_file_path = Path(storage.save_processed_data(nitter_analysis, "nitter_analysis", company_name))
            assert analysis_file_path.exists()
        
        # Check if company exists
        existing_company = await get_company_by_name(db, company_name)
        if existing_company:
            # Update existing company
            company = await update_company(db, existing_company.id, processed_data)
        else:
            # Create new company
            company = await create_company(db, processed_data)
        
        assert company is not None
        
        # Process each person associated with the company
        fully_processed_people = []
        for person_info in processed_data.get("people", []):
            person_name = person_info.get("name")
            if person_name:
                # Process person data
                person_data = await person_processor.process_person(person_name, raw_serp_data)
                assert person_data is not None
                
                # Process person's Twitter data if handle exists
                if person_data.get("twitter_handle"):
                    person_nitter_results = await nitter_scraper.get_raw_tweets(person_data["twitter_handle"])
                    if person_nitter_results and not person_nitter_results.get("twitter_unavailable", True):
                        person_summary, person_urgency_score = await nitter_nlp.analyze_tweets(person_nitter_results["raw_tweets"])
                        person_data["twitter_summary"] = person_summary
                        person_data["twitter_urgency_score"] = person_urgency_score
                        
                        # Save person's Twitter analysis
                        person_nitter_analysis = {
                            "summary": person_summary,
                            "urgency_score": person_urgency_score
                        }
                        person_analysis_path = Path(storage.save_processed_data(person_nitter_analysis, "nitter_analysis", person_name))
                        assert person_analysis_path.exists()
                
                # Calculate person's relevance score
                person_data["relevance_score"] = founder_scorer.calculate_relevance_score(
                    person_data=person_data,
                    twitter_urgency_score=person_data.get("twitter_urgency_score")
                )
                
                # Save person data
                person_file_path = Path(storage.save_final_data(person_data, "person", person_name))
                assert person_file_path.exists()
                
                # Create or update person in database
                person = await person_crud.create_person(db=db, person=person_data)
                assert person is not None
                
                # Associate person with company
                await process_company_people(company, [person_data], db)
                
                # Add to fully processed people list
                fully_processed_people.append(person_data)
        
        # Get associated people after processing
        result = await db.execute(
            select(Person)
            .join(company_person_association)
            .where(company_person_association.c.company_id == company.id)
        )
        people = result.scalars().all()
        
        # Prepare data for caching
        company_dict = {c.name: getattr(company, c.name) for c in company.__table__.columns}
        company_dict['people'] = [
            {
                "name": p.name,
                "title": p.title
            }
            for p in people
        ]
        
        # Save final company data
        final_company_path = Path(storage.save_final_data(company_dict, "company", company_name))
        assert final_company_path.exists()
        
        # Verify final company data
        final_company_data = storage.load_data("company", company_name, settings.JSON_INPUTS_DIR)
        assert final_company_data is not None
        assert final_company_data.get("name") == company_name
        assert "people" in final_company_data
        assert "twitter_summary" in final_company_data
        assert "relevance_score" in final_company_data
        
        # Cache the result
        await redis_service.set(cache_key, company_dict, expire=3600)
        
    except Exception as e:
        pytest.fail(f"Company search pipeline failed: {str(e)}")

@pytest.mark.asyncio
async def test_founder_search_pipeline(cameo_serp_data, steven_galanis_serp_data, martin_blencowe_serp_data, storage, scraper, nitter_scraper, nitter_nlp, founder_scorer, person_processor, nlp_processor, db):
    """Test the founder search pipeline exactly as used by the Streamlit app."""
    # First, process the company to get founder information
    company_name = "Cameo"
    company = await process_company_data(cameo_serp_data, db)
    assert company is not None
    
    # Test both founders
    founders = [
        ("Steven Galanis", steven_galanis_serp_data),
        ("Martin Blencowe", martin_blencowe_serp_data)
    ]
    
    for founder_name, founder_serp_data in founders:
        force_refresh = True  # Set to True to test full pipeline
        
        try:
            # Layer 1: Check Redis cache
            cache_key = f"person:{founder_name}"
            cached_data = await redis_service.get(cache_key)
            if cached_data and not force_refresh:
                assert cached_data is not None
                assert "name" in cached_data
                assert "title" in cached_data
                assert "duke_affiliation_status" in cached_data
                assert "relevance_score" in cached_data
                continue
            
            # Layer 2: Check database
            person = await person_crud.get_person_by_name(db, founder_name)
            if person and not force_refresh:
                # Get associated companies
                companies_result = await db.execute(
                    select(Company)
                    .join(company_person_association)
                    .where(company_person_association.c.person_id == person.id)
                )
                companies = companies_result.scalars().all()
                
                # Prepare person data
                person_data = {
                    "id": person.id,
                    "name": person.name,
                    "title": person.title,
                    "current_company": person.current_company,
                    "education": person.education,
                    "previous_companies": person.previous_companies,
                    "twitter_handle": person.twitter_handle,
                    "linkedin_handle": person.linkedin_handle,
                    "duke_affiliation_status": person.duke_affiliation_status,
                    "relevance_score": person.relevance_score,
                    "twitter_summary": person.twitter_summary,
                    "source_links": person.source_links,
                    "created_at": person.created_at.isoformat() if person.created_at else None,
                    "updated_at": person.updated_at.isoformat() if person.updated_at else None,
                    "companies": [{"name": c.name} for c in companies]
                }
                
                # Cache the result
                await redis_service.set(cache_key, person_data, expire=3600)
                continue
            
            # Layer 3: Scrape and process new data
            # Get SERP results for the founder
            serp_results = await scraper.search_founder(founder_name)
            assert serp_results is not None
            assert "organic_results" in serp_results
            assert serp_results == founder_serp_data  # Verify we're using founder-specific data
            
            # Save raw SERP data
            serp_file_path = storage.save_raw_data(serp_results, "serp_person", founder_name)
            assert serp_file_path.exists()
            
            # Process person data
            person_data = await person_processor.process_person(founder_name, serp_results)
            assert person_data is not None
            assert "name" in person_data
            assert "title" in person_data
            
            # Save intermediate data
            intermediate_path = storage.save_processed_data(person_data, "person", f"{founder_name}_intermediate")
            assert intermediate_path.exists()
            
            # Get and process Twitter data if handle exists
            twitter_urgency_score = None
            if person_data.get("twitter_handle"):
                nitter_results = await nitter_scraper.get_raw_tweets(person_data["twitter_handle"])
                assert nitter_results is not None
                assert not nitter_results.get("twitter_unavailable", True)
                assert "raw_tweets" in nitter_results
                
                # Save raw Twitter data
                nitter_file_path = storage.save_raw_data(nitter_results, "nitter", founder_name)
                assert nitter_file_path.exists()
                
                # Analyze tweets
                summary, urgency_score = await nitter_nlp.analyze_tweets(nitter_results["raw_tweets"])
                twitter_urgency_score = urgency_score
                
                # Save Twitter analysis
                nitter_analysis = {
                    "summary": summary,
                    "urgency_score": urgency_score
                }
                analysis_file_path = storage.save_processed_data(nitter_analysis, "nitter_analysis", founder_name)
                assert analysis_file_path.exists()
                person_data["twitter_summary"] = summary
            
            # Calculate final score
            person_data["relevance_score"] = founder_scorer.calculate_relevance_score(
                person_data=person_data,
                twitter_urgency_score=twitter_urgency_score
            )
            
            # Save final data
            final_path = storage.save_final_data(person_data, "person", founder_name)
            assert final_path.exists()
            
            # Store in database
            person = await person_crud.create_person(db=db, person=person_data)
            assert person is not None
            
            # Associate person with company
            await process_company_people(company, [person_data], db)
            
            # Get associated companies
            companies_result = await db.execute(
                select(Company)
                .join(company_person_association)
                .where(company_person_association.c.person_id == person.id)
            )
            companies = companies_result.scalars().all()
            
            # Prepare person data with companies
            person_data = person.dict()
            person_data['companies'] = [{"name": c.name} for c in companies]
            
            # Cache the result
            await redis_service.set(cache_key, person_data, expire=3600)
            
        except Exception as e:
            pytest.fail(f"Founder search pipeline failed for {founder_name}: {str(e)}")

@pytest.mark.asyncio
async def test_pipeline_error_handling(storage, scraper, nitter_scraper, nitter_nlp, founder_scorer, person_processor, nlp_processor, db):
    """Test error handling in the pipeline."""
    # Test invalid company search
    async def mock_invalid_company(x):
        raise Exception("Invalid company search")
    scraper.search_company = mock_invalid_company
    
    with pytest.raises(Exception, match="Invalid company search"):
        await scraper.search_company("Invalid Company")
    
    # Test invalid founder search
    async def mock_invalid_founder(x):
        raise Exception("Invalid founder search")
    scraper.search_founder = mock_invalid_founder
    
    with pytest.raises(Exception, match="Invalid founder search"):
        await scraper.search_founder("Invalid Person")
    
    # Test database errors
    with pytest.raises(Exception):
        await get_company_by_name(db, "NonExistentCompany")
    
    # Test Redis errors
    with pytest.raises(Exception):
        await redis_service.get("invalid:key")

@pytest.mark.asyncio
async def test_migration_pipeline(cameo_serp_data, storage, scraper, nitter_scraper, nitter_nlp, founder_scorer, person_processor, nlp_processor, db, test_data_dir):
    """Test the complete migration pipeline using real components and the actual database."""
    try:
        # Save the Cameo SERP data as a test JSON file
        test_company_file = test_data_dir["json_inputs"] / "company_cameo.json"
        with open(test_company_file, "w") as f:
            json.dump(cameo_serp_data, f)
        
        # Process the company data
        company = await process_company_data(cameo_serp_data, db)
        assert company is not None
        assert company.name == "Cameo"
        
        # Verify company data in database
        db_company = await get_company_by_name(db, "Cameo")
        assert db_company is not None
        assert db_company.name == "Cameo"
        assert db_company.duke_affiliation_status is not None
        assert db_company.relevance_score is not None
        assert db_company.twitter_summary is not None if db_company.twitter_handle else True
        
        # Verify raw data was saved
        raw_data_file = test_data_dir["raw"] / "serp_company_cameo.json"
        assert raw_data_file.exists()
        
        # Process people data if available
        if "people" in cameo_serp_data:
            await process_company_people(company, cameo_serp_data["people"], db)
            
            # Verify people associations
            result = await db.execute(
                select(Person)
                .join(company_person_association)
                .where(company_person_association.c.company_id == company.id)
            )
            people = result.scalars().all()
            assert len(people) > 0
            
            # Verify each person's data
            for person in people:
                assert person.name is not None
                assert person.title is not None
                assert person.duke_affiliation_status is not None
                assert person.relevance_score is not None
                assert person.twitter_summary is not None if person.twitter_handle else True
                
                # Verify person-company association
                result = await db.execute(
                    select(company_person_association)
                    .where(company_person_association.c.person_id == person.id)
                    .where(company_person_association.c.company_id == company.id)
                )
                association = result.first()
                assert association is not None
                
                # Verify person data files were created
                person_raw_file = test_data_dir["raw"] / f"serp_person_{person.name.lower().replace(' ', '_')}.json"
                person_processed_file = test_data_dir["processed"] / f"person_{person.name.lower().replace(' ', '_')}.json"
                person_final_file = test_data_dir["final"] / f"person_{person.name.lower().replace(' ', '_')}.json"
                
                assert person_raw_file.exists()
                assert person_processed_file.exists()
                assert person_final_file.exists()
                
                # Verify Nitter data if Twitter handle exists
                if person.twitter_handle:
                    nitter_raw_file = test_data_dir["raw"] / f"nitter_{person.twitter_handle.lower()}.json"
                    nitter_analysis_file = test_data_dir["processed"] / f"nitter_analysis_{person.twitter_handle.lower()}.json"
                    assert nitter_raw_file.exists()
                    assert nitter_analysis_file.exists()
        
        # Test the complete migration function
        await migrate_json_to_db()
        
        # Verify data in Redis cache
        cache_key = f"company:cameo"
        cached_data = await redis_service.get(cache_key)
        assert cached_data is not None
        assert cached_data["name"] == "Cameo"
        assert "people" in cached_data
        assert all(p.get("duke_affiliation_status") is not None for p in cached_data["people"])
        assert all(p.get("relevance_score") is not None for p in cached_data["people"])
        
        # Verify final company data file
        company_final_file = test_data_dir["final"] / "company_cameo.json"
        assert company_final_file.exists()
        
        # Verify processed company data file
        company_processed_file = test_data_dir["processed"] / "company_cameo.json"
        assert company_processed_file.exists()
        
        # Verify Nitter data if company Twitter handle exists
        if db_company.twitter_handle:
            company_nitter_raw_file = test_data_dir["raw"] / f"nitter_{db_company.twitter_handle.lower()}.json"
            company_nitter_analysis_file = test_data_dir["processed"] / f"nitter_analysis_{db_company.twitter_handle.lower()}.json"
            assert company_nitter_raw_file.exists()
            assert company_nitter_analysis_file.exists()
        
    except Exception as e:
        pytest.fail(f"Migration pipeline test failed: {str(e)}")
