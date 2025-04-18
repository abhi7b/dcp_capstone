"""
Test script for evaluating Duke affiliation query effectiveness.

This script tests different SERP queries to determine which produces
the most accurate results for Duke affiliation detection.
"""

import asyncio
import json
from typing import List, Dict, Any
import pytest
import os
import random
from datetime import datetime
from pathlib import Path

from app.utils.logger import test_logger as logger
from app.services.scraper import SERPScraper
from app.services.person_processor import PersonProcessor
from app.services.query_utils import QueryBuilder
from app.utils.config import settings

# Test dataset of people with known Duke affiliations
TEST_PEOPLE = [
    # Confirmed Duke affiliates
    {"name": "Tim Cook", "is_duke": True},
    {"name": "Grant Hill", "is_duke": True},
    {"name": "Jason Robins", "is_duke": True},
    {"name": "Aaron Chatterji", "is_duke": True},
    {"name": "Luis von Ahn", "is_duke": True},
    {"name": "Tianhao Li", "is_duke": True},
    {"name": "John Doe", "is_duke": True},
    {"name": "Adam Silver", "is_duke": True},
    {"name": "Cameron Fisher", "is_duke": True},
    {"name": "Archit Kaila", "is_duke": True},
    {"name": "Michael Mazzoleni", "is_duke": True},
    {"name": "Shyamal Hitesh Anadkat", "is_duke": True},
    {"name": "Diarra Bell", "is_duke": True},
 
    # Non-Duke affiliates
    {"name": "Elon Musk", "is_duke": False},
    {"name": "Mark Zuckerberg", "is_duke": False},
    {"name": "Jeff Bezos", "is_duke": False},
    {"name": "Bill Gates", "is_duke": False},
    {"name": "Steve Jobs", "is_duke": False},
    {"name": "Sam Altman", "is_duke": False},
    {"name": "Chungin (Roy) Lee", "is_duke": False},
    {"name": "Logan Tills", "is_duke": False},
    {"name": "Chaitanya Baweja", "is_duke": False},
    {"name": "Phill Agnew", "is_duke": False},
    {"name": "Alaa El-Nouby", "is_duke": False},
  
    # Edge cases
    {"name": "John Smith", "is_duke": True},  # Common name
    {"name": "David Duke", "is_duke": False},  # Name contains "Duke"
]

class TestDukeAffiliationQueries:
    """Test class for evaluating Duke affiliation query effectiveness."""
    
    def __init__(self):
        self.scraper = SERPScraper()
        self.person_processor = PersonProcessor()
        self.query_builder = QueryBuilder()
        # Use the data directory for test output
        self.test_output_dir = Path(settings.DATA_DIR) / "duke_affiliation_tests"
        self.test_output_dir.mkdir(parents=True, exist_ok=True)
        
    async def test_person(self, person: Dict[str, Any], query_template: str) -> Dict[str, Any]:
        """
        Test a single person with a specific query.
        
        Args:
            person: Person dictionary with name and expected affiliation
            query_template: The query template to use
            
        Returns:
            Dictionary with test results
        """
        query = query_template.format(name=person["name"])
        logger.info(f"\nTesting person: {person['name']}")
        logger.info(f"Using query: {query}")
        
        try:
            logger.info("Making SERP API call...")
            serp_results = await self.scraper.search(query)
            logger.info(f"SERP results received: {len(serp_results.get('organic_results', []))} results")
            
            if serp_results and "organic_results" in serp_results:
                logger.info("Processing with PersonProcessor...")
                person_data = await self.person_processor.process_person(person["name"], serp_results)
                logger.info(f"Person processing complete. Affiliation status: {person_data.get('duke_affiliation_status')}")
                
                return {
                    "name": person["name"],
                    "expected": person["is_duke"],
                    "result": person_data.get("duke_affiliation_status") == "confirmed",
                    "query": query
                }
        except Exception as e:
            logger.error(f"Error processing query '{query}' for {person['name']}: {str(e)}")
            return {
                "name": person["name"],
                "expected": person["is_duke"],
                "result": False,
                "query": query,
                "error": str(e)
            }
        
        return {
            "name": person["name"],
            "expected": person["is_duke"],
            "result": False,
            "query": query
        }
    
    async def run_test(self, selected_queries: List[str], test_people: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Run a single test with a specific set of queries.
        
        Args:
            selected_queries: List of query templates to use
            test_people: List of people to test
            
        Returns:
            Dictionary with test results
        """
        results = []
        logger.info(f"\nStarting test with queries: {selected_queries}")
        
        for i, person in enumerate(test_people, 1):
            logger.info(f"\nProcessing person {i}/{len(test_people)}: {person['name']}")
            # Randomly select one query from the set
            query_template = random.choice(selected_queries)
            result = await self.test_person(person, query_template)
            results.append(result)
            logger.info(f"Completed person {i}/{len(test_people)}")
        
        # Calculate metrics
        total = len(results)
        correct = sum(1 for r in results if r["result"] == r["expected"])
        accuracy = correct / total if total > 0 else 0
        
        return {
            "queries_used": selected_queries,
            "accuracy": accuracy,
            "total_people": total,
            "correct": correct,
            "results": results
        }

@pytest.mark.asyncio
async def test_query_effectiveness(caplog):
    """Main test function to evaluate query effectiveness."""
    # Set logging level to INFO to capture all output
    caplog.set_level("INFO")
    
    logger.info("Starting Duke affiliation query tests...")
    tester = TestDukeAffiliationQueries()
    
    # Get queries from QueryBuilder
    query_builder = QueryBuilder()
    duke_queries = query_builder.get_founder_queries("{name}")["duke affiliation"]
    
    # Select a random sample of 8 people (4 Duke, 4 non-Duke)
    duke_people = [p for p in TEST_PEOPLE if p["is_duke"]]
    non_duke_people = [p for p in TEST_PEOPLE if not p["is_duke"]]
    
    # Run 3 tests with different random samples
    num_tests = 3
    all_results = {}
    
    for test_num in range(1, num_tests + 1):
        logger.info(f"\nStarting Test {test_num}/{num_tests}")
        
        # Select random sample
        sample_size = 4
        test_people = (
            random.sample(duke_people, min(sample_size, len(duke_people))) +
            random.sample(non_duke_people, min(sample_size, len(non_duke_people)))
        )
        random.shuffle(test_people)
        
        logger.info(f"Selected test people: {[p['name'] for p in test_people]}")
        logger.info(f"Running test with queries: {duke_queries}")
        
        results = await tester.run_test(duke_queries, test_people)
        
        # Save results to data directory
        filename = tester.test_output_dir / f"duke_affiliation_test{test_num}.json"
        with open(filename, "w") as f:
            json.dump(results, f, indent=2)
        
        all_results[f"test{test_num}"] = results
        
        # Print results
        logger.info(f"\nTest {test_num} Results:")
        logger.info(f"Queries used: {duke_queries}")
        logger.info(f"Accuracy: {results['accuracy']:.2%}")
        logger.info(f"Correct: {results['correct']}/{results['total_people']}")
        
        # Print individual results
        logger.info("\nIndividual Results:")
        for result in results["results"]:
            status = "✓" if result["result"] == result["expected"] else "✗"
            logger.info(f"{status} {result['name']} (Expected: {'Duke' if result['expected'] else 'Non-Duke'}, Got: {'Duke' if result['result'] else 'Non-Duke'})")
    
    # Print all captured logs
    print("\n".join(caplog.messages))
    
    # Assert that at least one test achieved good accuracy
    best_accuracy = max(r["accuracy"] for r in all_results.values())
    assert best_accuracy >= 0.7, f"Best accuracy too low: {best_accuracy:.2%}" 