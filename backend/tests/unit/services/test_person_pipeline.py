import pytest
import os
import json
from typing import Dict, Any

from app.services.scraper import SERPScraper
from app.services.person_processor import PersonProcessor
from app.services.nitter import NitterScraper
from app.services.nitter_nlp import NitterNLP
from app.services.founder_scorer import FounderScorer
from app.services.query_utils import QueryBuilder
from app.utils.storage import StorageService
from app.utils.config import settings

@pytest.fixture(autouse=True)
def setup_data_directories():
    """Create necessary data directories before tests"""
    os.makedirs(settings.RAW_DATA_DIR, exist_ok=True)
    os.makedirs(settings.PROCESSED_DATA_DIR, exist_ok=True)
    os.makedirs(settings.JSON_INPUTS_DIR, exist_ok=True)
    yield
    # No cleanup - keep files for inspection

@pytest.mark.asyncio
async def test_complete_person_pipeline():
    """Test the complete person pipeline from SERP scraping to final data"""
    
    # Initialize services
    processor = PersonProcessor()
    nitter_scraper = NitterScraper()
    nitter_nlp = NitterNLP()
    founder_scorer = FounderScorer()
    storage = StorageService()
    
    # Test person
    person_name = "Sam Altman"
    
    # Load existing SERP data
    raw_serp_path = os.path.join(settings.RAW_DATA_DIR, f"serp_founder_{person_name.replace(' ', '_')}.json")
    with open(raw_serp_path, 'r') as f:
        serp_results = json.load(f)
    
    # Verify raw SERP data contents
    assert serp_results is not None
    assert "organic_results" in serp_results
    assert "query_summary" in serp_results
    assert len(serp_results["organic_results"]) > 0
    assert isinstance(serp_results["query_summary"], dict)
    
    # Extract Twitter handle from SERP results
    twitter_handle = None
    for result in serp_results["organic_results"]:
        if "twitter.com" in result["link"]:
            twitter_handle = result["link"].split("/")[-1]
            break
    assert twitter_handle == "sama"
    
    # Step 2: Get Nitter data
    nitter_results = await nitter_scraper.get_raw_tweets(twitter_handle)
    assert nitter_results is not None
    assert isinstance(nitter_results, dict)
    assert "raw_tweets" in nitter_results
    assert isinstance(nitter_results["raw_tweets"], list)
    
    # Verify raw Nitter data was saved
    raw_nitter_path = storage.get_file_path("nitter", twitter_handle, settings.RAW_DATA_DIR)
    assert raw_nitter_path is not None
    assert os.path.exists(raw_nitter_path)
    
    # Verify raw Nitter data contents
    raw_nitter_data = storage.load_data("nitter", twitter_handle, settings.RAW_DATA_DIR)
    assert raw_nitter_data is not None
    assert "raw_tweets" in raw_nitter_data
    if len(raw_nitter_data["raw_tweets"]) > 0:
        tweet = raw_nitter_data["raw_tweets"][0]
        assert "content" in tweet
        assert "date" in tweet
    
    # Step 3: Process Nitter data with NLP
    nitter_analysis = await nitter_nlp.analyze_tweets(raw_nitter_data["raw_tweets"])
    assert nitter_analysis is not None
    assert isinstance(nitter_analysis, tuple)
    assert len(nitter_analysis) == 2
    assert isinstance(nitter_analysis[0], str)  # summary
    assert isinstance(nitter_analysis[1], int)  # urgency_score
    assert 0 <= nitter_analysis[1] <= 100
    
    # Create analysis dict for storage
    nitter_analysis_data = {
        "summary": nitter_analysis[0],
        "urgency_score": nitter_analysis[1]
    }
    
    # Save Nitter analysis data
    storage.save_processed_data(nitter_analysis_data, "nitter_analysis", twitter_handle)
    
    # Verify Nitter analysis was saved
    nitter_analysis_path = storage.get_file_path("nitter_analysis", twitter_handle, settings.PROCESSED_DATA_DIR)
    assert nitter_analysis_path is not None
    assert os.path.exists(nitter_analysis_path)
    
    # Verify Nitter analysis contents
    nitter_analysis_stored = storage.load_data("nitter_analysis", twitter_handle, settings.PROCESSED_DATA_DIR)
    assert nitter_analysis_stored is not None
    assert "summary" in nitter_analysis_stored
    assert "urgency_score" in nitter_analysis_stored
    assert isinstance(nitter_analysis_stored["urgency_score"], int)
    assert 0 <= nitter_analysis_stored["urgency_score"] <= 100
    
    # Step 4: Process person data
    person_data = await processor.process_person(person_name, serp_results)
    
    # Verify person data structure
    assert "Altman" in person_data.name
    assert person_data.duke_affiliation_status in ["confirmed", "please review", "no"]
    assert isinstance(person_data.relevance_score, int)
    assert person_data.relevance_score >= 0 and person_data.relevance_score <= 100
    
    # Verify intermediate data was saved
    intermediate_path = storage.get_file_path("person", "Samuel_H_Altman", settings.PROCESSED_DATA_DIR)
    assert intermediate_path is not None
    assert os.path.exists(intermediate_path)
    
    # Verify intermediate data contents
    intermediate_data = storage.load_data("person", "Samuel_H_Altman", settings.PROCESSED_DATA_DIR)
    assert intermediate_data is not None
    assert "name" in intermediate_data
    assert "education" in intermediate_data
    assert "current_company" in intermediate_data
    assert "previous_companies" in intermediate_data
    assert "twitter_handle" in intermediate_data
    assert "linkedin_handle" in intermediate_data
    assert "source_links" in intermediate_data
    
    # Step 5: Calculate final person score
    final_score = founder_scorer.calculate_relevance_score(
        person_data=intermediate_data,
        twitter_urgency_score=nitter_analysis[1]
    )
    assert isinstance(final_score, int)
    assert 0 <= final_score <= 100
    
    # Verify final data was saved
    final_path = storage.get_file_path("person", "Samuel_H_Altman", settings.PROCESSED_DATA_DIR)
    assert final_path is not None
    assert os.path.exists(final_path)
    
    # Verify final data contents
    final_data = storage.load_data("person", "Samuel_H_Altman", settings.JSON_INPUTS_DIR)
    assert final_data is not None
    assert "Altman" in final_data["name"]
    assert "education" in final_data
    assert "current_company" in final_data
    assert "previous_companies" in final_data
    assert "twitter_summary" in final_data
    assert "relevance_score" in final_data
    assert isinstance(final_data["relevance_score"], int)
    assert 0 <= final_data["relevance_score"] <= 100
    assert "duke_affiliation_status" in final_data
    
    # Print file locations for manual review
    print("\nFiles saved for manual review:")
    print(f"Raw SERP data: {raw_serp_path}")
    print(f"Raw Nitter data: {raw_nitter_path}")
    print(f"Intermediate data: {intermediate_path}")
    print(f"Nitter analysis: {nitter_analysis_path}")
    print(f"Final data: {final_path}") 