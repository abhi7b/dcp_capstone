import pytest
import os
import json
from typing import Dict, Any, Optional, Tuple


from app.services.scraper import SERPScraper
from app.services.nlp_processor import NLPProcessor
from app.services.nitter import NitterScraper
from app.services.nitter_nlp import NitterNLP
from app.services.founder_scorer import FounderScorer
from app.utils.storage import StorageService
from app.utils.config import settings
from app.services.person_processor import PersonProcessor

# --- Helper Function for Person Pipeline Steps ---

async def _test_person_pipeline_steps(
    person_name: str, 
    scraper: SERPScraper, 
    person_processor: PersonProcessor,
    nitter_scraper: NitterScraper,
    nitter_nlp: NitterNLP,
    founder_scorer: FounderScorer,
    storage: StorageService
) -> Optional[Dict[str, Any]]:
    """Runs the complete pipeline steps for a single person and verifies outputs."""
    print(f"\n--- Processing Person: {person_name} ---")
    clean_person_name = storage._clean_filename(person_name)
    
    # Get or create SERP data
    person_serp_path = storage.get_file_path("serp_person", clean_person_name, settings.RAW_DATA_DIR)
    assert person_serp_path is not None, f"Failed to get SERP path for {person_name}"
    
    if os.path.exists(person_serp_path):
        print(f"Loading existing SERP data for {person_name}...")
        serp_results = storage.load_data("serp_person", clean_person_name, settings.RAW_DATA_DIR)
    else:
        print(f"Scraping new SERP data for {person_name}...")
        serp_results = await scraper.search_founder(person_name)
        if serp_results:
            storage.save_raw_data(serp_results, "serp_person", person_name)
        else:
            print(f"Warning: Failed to get SERP data for {person_name}")
            return None
            
    assert serp_results is not None, "Failed to get SERP results"
    assert "organic_results" in serp_results, "SERP results should contain organic_results"
    assert len(serp_results["organic_results"]) > 0, "SERP results should have at least one result"
    
    # Process person through the pipeline with SERP data
    print(f"Processing person data for {person_name}...")
    person_data = await person_processor.process_person(person_name, serp_results)
    
    if not person_data or "error" in person_data:
        print(f"Warning: Person processing failed for {person_name}")
        return None

    # Verify all expected files exist and have correct structure
    # 1. Raw Data
    assert os.path.exists(person_serp_path), f"Person SERP raw data should exist at: {person_serp_path}"
    
    # Get twitter handle from processed data for Nitter verification
    twitter_handle = person_data.get("twitter_handle")
    if twitter_handle:
        nitter_path = storage.get_file_path("nitter", twitter_handle, settings.RAW_DATA_DIR)
        assert nitter_path is not None
        assert os.path.exists(nitter_path), f"Nitter raw data should exist at: {nitter_path}"
    
    # 2. Processed Data
    person_processed_path = storage.get_file_path(f"person_{clean_person_name}", "processed", settings.PROCESSED_DATA_DIR)
    assert person_processed_path is not None
    assert os.path.exists(person_processed_path), f"Processed person data should exist at: {person_processed_path}"
    
    processed_data = storage.load_data(f"person_{clean_person_name}", "processed", settings.PROCESSED_DATA_DIR)
    assert processed_data is not None
    assert "name" in processed_data
    assert "education" in processed_data
    assert "duke_affiliation_status" in processed_data
    # These should NOT be in processed data
    assert "twitter_summary" not in processed_data
    assert "relevance_score" not in processed_data
    
    # 3. Final Data
    person_final_path = storage.get_file_path("person", clean_person_name, settings.JSON_INPUTS_DIR)
    assert person_final_path is not None
    assert os.path.exists(person_final_path), f"Final person data should exist at: {person_final_path}"
    
    final_data = storage.load_data("person", clean_person_name, settings.JSON_INPUTS_DIR)
    assert final_data is not None
    assert final_data.get("name") == person_name
    assert "twitter_summary" in final_data
    assert "relevance_score" in final_data
    
    print(f"--- Completed Person: {person_name} ---")
    return final_data


# --- Test Setup ---

@pytest.fixture(autouse=True)
def setup_data_directories():
    """Create necessary data directories before tests"""
    os.makedirs(settings.RAW_DATA_DIR, exist_ok=True)
    os.makedirs(settings.PROCESSED_DATA_DIR, exist_ok=True)
    os.makedirs(settings.JSON_INPUTS_DIR, exist_ok=True)
    yield
    # No cleanup - keep files for inspection

# --- Parameterized Test Function ---

@pytest.mark.parametrize(
    "entity_type, entity_name",
    [
        ("company", "OpenAI"),  # Test case for company pipeline
        ("person", "Sam Altman"), # Test case for person pipeline
    ]
)
@pytest.mark.asyncio
async def test_complete_pipeline(entity_type: str, entity_name: str):
    """Test the complete pipeline for either a company or a person."""
    
    print(f"\n=== Testing Pipeline: Type='{entity_type}', Name='{entity_name}' ===")

    # Initialize relevant services
    scraper = SERPScraper()
    processor = NLPProcessor()
    person_processor = PersonProcessor()
    nitter_scraper = NitterScraper()
    nitter_nlp = NitterNLP()
    founder_scorer = FounderScorer()
    storage = StorageService()
    
    processed_people_names = [] # Store names of successfully processed people

    # --- Pipeline Execution ---
    if entity_type == "company":
        company_name = entity_name
        clean_company_name = storage._clean_filename(company_name)
        
        # Get or create SERP data
        raw_serp_path = storage.get_file_path("serp_company", clean_company_name, settings.RAW_DATA_DIR)
        assert raw_serp_path is not None, f"Failed to get SERP path for {company_name}"
        
        if os.path.exists(raw_serp_path):
            print(f"Loading existing SERP data for company {company_name}...")
            serp_results = storage.load_data("serp_company", clean_company_name, settings.RAW_DATA_DIR)
        else:
            print(f"Scraping new SERP data for company {company_name}...")
            serp_results = await scraper.search_company(company_name)
            if serp_results:
                storage.save_raw_data(serp_results, "serp_company", company_name)
            else:
                print(f"Warning: Failed to get SERP data for company {company_name}")
                pytest.fail(f"Failed to get SERP data for company {company_name}")
                
        assert serp_results is not None, "Failed to get SERP results"
        assert "organic_results" in serp_results, "SERP results should contain organic_results"
        assert len(serp_results["organic_results"]) > 0, "SERP results should have at least one result"
        
        # Process company through NLPProcessor with SERP data
        print(f"Processing company data for {company_name}...")
        company_data = await processor.process_company(serp_results)
        assert company_data is not None
        
        # Load the final company JSON to get people list
        final_company_path = storage.get_file_path("company", clean_company_name, settings.JSON_INPUTS_DIR)
        assert final_company_path is not None and os.path.exists(final_company_path), f"Final company JSON missing: {final_company_path}"
        
        final_company_json = storage.load_data("company", clean_company_name, settings.JSON_INPUTS_DIR)
        assert "people" in final_company_json
        
        # Process associated people
        for person_info in final_company_json["people"]:
            person_name = person_info.get("name")
            if person_name:
                final_person_data = await _test_person_pipeline_steps(
                    person_name, scraper, person_processor, nitter_scraper, nitter_nlp, founder_scorer, storage
                )
                if final_person_data:
                    processed_people_names.append(person_name)
        
        # Verify Nitter data exists for the company
        nitter_path = storage.get_file_path("nitter", company_data.get("twitter_handle", "").lower(), settings.RAW_DATA_DIR)
        assert nitter_path is not None and os.path.exists(nitter_path), f"Nitter data missing for company {company_name}"
        
    elif entity_type == "person":
        person_name = entity_name
        # Process single person
        final_person_data = await _test_person_pipeline_steps(
            person_name, scraper, person_processor, nitter_scraper, nitter_nlp, founder_scorer, storage
        )
        if final_person_data:
            processed_people_names.append(person_name)
        else:
            pytest.fail(f"Person pipeline failed for {person_name}")
    
    else:
        pytest.fail(f"Unknown entity_type: {entity_type}")

    # --- Verify File Structure and Contents ---
    print("\n--- Verifying Generated Files ---")

    if entity_type == "company":
        company_name = entity_name
        clean_company_name = storage._clean_filename(company_name)
        
        # Verify Company Files
        # 1. Raw Company Data
        raw_serp_path = storage.get_file_path("serp_company", clean_company_name, settings.RAW_DATA_DIR)
        assert os.path.exists(raw_serp_path), f"Company SERP raw data file missing: {raw_serp_path}"
        
        # 2. Processed Company Data
        intermediate_path = storage.get_file_path(f"company_{clean_company_name}", "intermediate_extraction", settings.PROCESSED_DATA_DIR)
        assert os.path.exists(intermediate_path), f"Company intermediate data missing: {intermediate_path}"
        
        intermediate_data = storage.load_data(f"company_{clean_company_name}", "intermediate_extraction", settings.PROCESSED_DATA_DIR)
        assert intermediate_data is not None
        assert "name" in intermediate_data
        assert "people" in intermediate_data
        
        # 3. Final Company Data
        final_company_path = storage.get_file_path("company", clean_company_name, settings.JSON_INPUTS_DIR)
        assert os.path.exists(final_company_path), f"Final company JSON missing: {final_company_path}"
        
        final_company_data = storage.load_data("company", clean_company_name, settings.JSON_INPUTS_DIR)
        assert final_company_data is not None
        assert final_company_data.get("name") == company_name
        assert "people" in final_company_data
        assert "twitter_summary" in final_company_data
        assert "relevance_score" in final_company_data

    # Verify Person Files
    assert len(processed_people_names) > 0, "No people were successfully processed."
    
    # Print File Locations
    print("\n--- Files Generated ---")
    if entity_type == "company":
        company_name = entity_name
        clean_company_name = storage._clean_filename(company_name)
        print("\nCompany Files:")
        print(f"  Raw SERP: {storage.get_file_path('serp_company', clean_company_name, settings.RAW_DATA_DIR)}")
        print(f"  Processed Intermediate: {storage.get_file_path(f'company_{clean_company_name}', 'intermediate_extraction', settings.PROCESSED_DATA_DIR)}")
        print(f"  Final JSON: {storage.get_file_path('company', clean_company_name, settings.JSON_INPUTS_DIR)}")

    print("\nPerson Files:")
    for person_name in processed_people_names:
        clean_name = storage._clean_filename(person_name)
        processed_person_temp = storage.load_data(f"person_{clean_name}", "processed", settings.PROCESSED_DATA_DIR)
        nitter_file_key = processed_person_temp.get("twitter_handle") or clean_name
        print(f"  {person_name}:")
        print(f"    Raw SERP: {storage.get_file_path('serp_person', clean_name, settings.RAW_DATA_DIR)}")
        print(f"    Raw Nitter: {storage.get_file_path('nitter', nitter_file_key, settings.RAW_DATA_DIR)}")
        print(f"    Processed Person: {storage.get_file_path(f'person_{clean_name}', 'processed', settings.PROCESSED_DATA_DIR)}")
        print(f"    Final JSON: {storage.get_file_path('person', clean_name, settings.JSON_INPUTS_DIR)}")

    print(f"\n=== Completed Test: Type='{entity_type}', Name='{entity_name}' ===") 