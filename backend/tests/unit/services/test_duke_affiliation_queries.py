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

from app.utils.logger import test_logger as logger
from app.services.scraper import SERPScraper
from app.services.nlp_processor import NLPProcessor

# Basic list of queries to test
QUERIES = [
    '"{name}" "Duke University" alumni',
    '"{name}" "Duke University" graduate',
    '"{name}" site:duke.edu',
    '"{name}" "Duke" education',
    '"{name}" Duke University'
]

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
        self.nlp_processor = NLPProcessor()
        
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
        try:
            serp_results = await self.scraper.search(query)
            if serp_results and "organic_results" in serp_results:
                person_data = await self.nlp_processor._process_person_education({
                    "name": person["name"],
                    "title": "Test Person"
                })
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
                "query": query
            }
        
        return {
            "name": person["name"],
            "expected": person["is_duke"],
            "result": False,
            "query": query
        }
    
    async def run_test(self, selected_queries: List[str]) -> Dict[str, Any]:
        """
        Run a single test with a specific set of queries.
        
        Args:
            selected_queries: List of query templates to use
            
        Returns:
            Dictionary with test results
        """
        results = []
        for person in TEST_PEOPLE:
            # Randomly select one query from the set
            query_template = random.choice(selected_queries)
            result = await self.test_person(person, query_template)
            results.append(result)
        
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
    
    tester = TestDukeAffiliationQueries()
    
    # Run multiple tests with different query combinations
    num_tests = 5  # Number of different query combinations to test
    all_results = {}
    
    for test_num in range(1, num_tests + 1):
        # Randomly select 2-3 queries for this test
        num_queries = random.randint(2, 3)
        selected_queries = random.sample(QUERIES, num_queries)
        
        logger.info(f"\nRunning Test {test_num} with queries: {selected_queries}")
        results = await tester.run_test(selected_queries)
        
        # Save results for this test
        filename = f"duke_affiliation_test{test_num}.json"
        with open(filename, "w") as f:
            json.dump(results, f, indent=2)
        
        all_results[f"test{test_num}"] = results
        
        # Print results
        logger.info(f"\nTest {test_num} Results:")
        logger.info(f"Queries used: {selected_queries}")
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