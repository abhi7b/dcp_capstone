import pytest
import os
import json
from typing import Dict, Any

from app.services.scraper import SERPScraper
from app.services.nlp_processor import NLPProcessor
from app.services.nitter import NitterScraper
from app.services.nitter_nlp import NitterNLP
from app.services.company_scorer import CompanyScorer
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
async def test_complete_company_pipeline():
    """Test the complete company pipeline including SERP, Nitter, and scoring"""
    
    # Initialize all services
    scraper = SERPScraper()
    processor = NLPProcessor()
    nitter_scraper = NitterScraper()
    nitter_nlp = NitterNLP()
    company_scorer = CompanyScorer()
    storage = StorageService()
    
    # Test company
    company_name = "OpenAI"
    
    # Step 1: Get SERP results
    serp_results = await scraper.search_company(company_name)
    assert serp_results is not None
    assert "organic_results" in serp_results
    assert len(serp_results["organic_results"]) > 0
    
    # Verify raw SERP data was saved
    raw_serp_path = storage.get_file_path("serp_company", company_name, settings.RAW_DATA_DIR)
    assert raw_serp_path is not None
    assert os.path.exists(raw_serp_path)
    
    # Verify raw SERP data contents
    raw_serp_data = storage.load_data("serp_company", company_name, settings.RAW_DATA_DIR)
    assert raw_serp_data is not None
    assert "organic_results" in raw_serp_data
    assert "query_summary" in raw_serp_data
    assert len(raw_serp_data["organic_results"]) > 0
    assert isinstance(raw_serp_data["query_summary"], dict)
    
    # Step 2: Process company data
    company_data = await processor.process_company(company_name, serp_results)
    
    # Verify company data structure
    assert isinstance(company_data, dict)
    assert company_data["name"] == company_name
    assert "duke_affiliation_status" in company_data
    assert "relevance_score" in company_data
    assert "people" in company_data
    
    # Verify intermediate data was saved
    intermediate_path = storage.get_file_path("company", f"{company_name}_intermediate", settings.PROCESSED_DATA_DIR)
    assert intermediate_path is not None
    assert os.path.exists(intermediate_path)
    
    # Verify intermediate data contents
    intermediate_data = storage.load_data("company", f"{company_name}_intermediate", settings.PROCESSED_DATA_DIR)
    assert intermediate_data is not None
    assert "name" in intermediate_data
    assert "summary" in intermediate_data
    assert "founded" in intermediate_data
    assert "industry" in intermediate_data
    assert "funding_stage" in intermediate_data
    assert "investors" in intermediate_data
    assert "location" in intermediate_data
    assert "twitter_handle" in intermediate_data
    assert "linkedin_handle" in intermediate_data
    assert "source_links" in intermediate_data
    assert "people" in intermediate_data
    
    # Step 3: Get Nitter data for company
    nitter_results = await nitter_scraper.get_raw_tweets(company_name)
    assert nitter_results is not None
    assert isinstance(nitter_results, dict)
    assert "raw_tweets" in nitter_results
    assert isinstance(nitter_results["raw_tweets"], list)
    
    # Verify raw Nitter data was saved
    raw_nitter_path = storage.get_file_path("nitter", company_name, settings.RAW_DATA_DIR)
    assert raw_nitter_path is not None
    assert os.path.exists(raw_nitter_path)
    
    # Verify raw Nitter data contents
    raw_nitter_data = storage.load_data("nitter", company_name, settings.RAW_DATA_DIR)
    assert raw_nitter_data is not None
    assert "raw_tweets" in raw_nitter_data
    if len(raw_nitter_data["raw_tweets"]) > 0:
        tweet = raw_nitter_data["raw_tweets"][0]
        assert "content" in tweet
        assert "date" in tweet
    
    # Step 4: Process Nitter data with NLP
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
    storage.save_processed_data(nitter_analysis_data, "nitter_analysis", company_name)
    
    # Verify Nitter analysis was saved
    nitter_analysis_path = storage.get_file_path("nitter_analysis", company_name, settings.PROCESSED_DATA_DIR)
    assert nitter_analysis_path is not None
    assert os.path.exists(nitter_analysis_path)
    
    # Verify Nitter analysis contents
    nitter_analysis_stored = storage.load_data("nitter_analysis", company_name, settings.PROCESSED_DATA_DIR)
    assert nitter_analysis_stored is not None
    assert "summary" in nitter_analysis_stored
    assert "urgency_score" in nitter_analysis_stored
    assert isinstance(nitter_analysis_stored["urgency_score"], int)
    assert 0 <= nitter_analysis_stored["urgency_score"] <= 100
    
    # Step 5: Process people data
    people_data = company_data.get("people", [])
    assert isinstance(people_data, list)
    
    # Verify people data was saved
    people_path = storage.get_file_path("company", f"{company_name}_people", settings.PROCESSED_DATA_DIR)
    assert people_path is not None
    assert os.path.exists(people_path)
    
    # Verify people data contents
    people_data = storage.load_data("company", f"{company_name}_people", settings.PROCESSED_DATA_DIR)
    assert people_data is not None
    assert "people" in people_data
    assert isinstance(people_data["people"], list)
    if len(people_data["people"]) > 0:
        person = people_data["people"][0]
        assert "name" in person
        assert "title" in person
        assert "duke_affiliation_status" in person
        assert "education" in person
    
    # Step 6: Calculate final company score
    final_score = company_scorer.calculate_relevance_score(
        company_data=company_data,
        processed_people=people_data["people"]
    )
    assert isinstance(final_score, int)
    assert 0 <= final_score <= 100
    
    # Verify final data was saved
    final_path = storage.get_file_path("company", company_name, settings.JSON_INPUTS_DIR)
    assert final_path is not None
    assert os.path.exists(final_path)
    
    # Verify final data contents
    final_data = storage.load_data("company", company_name, settings.JSON_INPUTS_DIR)
    assert final_data is not None
    assert final_data["name"] == company_name
    assert "relevance_score" in final_data
    assert isinstance(final_data["relevance_score"], int)
    assert 0 <= final_data["relevance_score"] <= 100
    assert "duke_affiliation_status" in final_data
    assert "people" in final_data
    assert isinstance(final_data["people"], list)
    assert "twitter_summary" in final_data
    
    # Print file locations for manual review
    print("\nFiles saved for manual review:")
    print(f"Raw SERP data: {raw_serp_path}")
    print(f"Raw Nitter data: {raw_nitter_path}")
    print(f"Intermediate data: {intermediate_path}")
    print(f"Nitter analysis: {nitter_analysis_path}")
    print(f"People data: {people_path}")
    print(f"Final data: {final_path}") 