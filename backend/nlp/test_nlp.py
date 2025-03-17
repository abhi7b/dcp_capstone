#!/usr/bin/env python3
"""
Test script for the NLP module.

This script demonstrates how to use the CompanyProcessor, FounderProcessor,
TwitterAnalyzer, and IntegrationService to analyze information about companies,
founders, and Twitter profiles.

Usage:
    python -m backend.nlp.test_nlp

Environment variables:
    None required - all configuration is loaded from .env via the config system
"""
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from backend.nlp.company_processor import CompanyProcessor
from backend.nlp.founder_processor import FounderProcessor
from backend.nlp.twitter_analyzer import TwitterAnalyzer
from backend.nlp.services.integration import IntegrationService
from backend.config.logs import LogManager
from backend.config.config import settings

# Set up logging
LogManager.setup_logging()

# Check if OpenAI API key is set in settings
if not settings.openai.API_KEY:
    print("Error: OPENAI_API_KEY is not set in the configuration.")
    print("Please add it to your .env file:")
    print("  OPENAI_API_KEY=your_openai_api_key")
    sys.exit(1)
else:
    print(f"Using OpenAI API key from settings: {settings.openai.API_KEY[:5]}...")

async def test_company_processor(company_data_path: str):
    """
    Test the CompanyProcessor with data from a file.
    
    Args:
        company_data_path: Path to a JSON file with company search results
    """
    print(f"\n{'=' * 50}")
    print(f"Testing CompanyProcessor with data from: {company_data_path}")
    print(f"{'=' * 50}")
    
    try:
        # Load the company data
        with open(company_data_path, 'r') as f:
            company_data = json.load(f)
        
        company_name = company_data.get("company_name", "Unknown Company")
        print(f"Analyzing company: {company_name}")
        
        # Create the processor
        processor = CompanyProcessor()
        
        # Prepare the text for analysis
        # Convert the results to a string for processing
        results_text = json.dumps(company_data.get("results", {}), indent=2)
        
        # Process the company data
        print("Processing company data with OpenAI...")
        analysis = await processor.analyze_company(results_text)
        
        # Print summary of analysis
        print("\nAnalysis completed!")
        
        # Save analysis to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"analysis_company_{company_name.lower().replace(' ', '_')}_{timestamp}.json"
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / filename
        
        with open(output_path, 'w') as f:
            json.dump(analysis, f, indent=2)
        
        print(f"\nAnalysis saved to {output_path}")
        return analysis
        
    except Exception as e:
        print(f"Error processing company data: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

async def test_founder_processor(founder_data_path: str):
    """
    Test the FounderProcessor with data from a file.
    
    Args:
        founder_data_path: Path to a JSON file with founder search results
    """
    print(f"\n{'=' * 50}")
    print(f"Testing FounderProcessor with data from: {founder_data_path}")
    print(f"{'=' * 50}")
    
    try:
        # Load the founder data
        with open(founder_data_path, 'r') as f:
            founder_data = json.load(f)
        
        founder_name = founder_data.get("founder_name", "Unknown Founder")
        print(f"Analyzing founder: {founder_name}")
        
        # Create the processor
        processor = FounderProcessor()
        
        # Prepare the text for analysis
        # Convert the results to a string for processing
        results_text = json.dumps(founder_data.get("results", {}), indent=2)
        
        # Process the founder data
        print("Processing founder data with OpenAI...")
        analysis = await processor.analyze_founder(results_text)
        
        # Print summary of analysis
        print("\nAnalysis completed!")
        
        # Save analysis to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"analysis_founder_{founder_name.lower().replace(' ', '_')}_{timestamp}.json"
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / filename
        
        with open(output_path, 'w') as f:
            json.dump(analysis, f, indent=2)
        
        print(f"\nAnalysis saved to {output_path}")
        return analysis
        
    except Exception as e:
        print(f"Error processing founder data: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

async def test_twitter_analyzer(twitter_data_path: str):
    """
    Test the TwitterAnalyzer with data from a file.
    
    Args:
        twitter_data_path: Path to a JSON file with Twitter profile and tweets
    """
    print(f"\n{'=' * 50}")
    print(f"Testing TwitterAnalyzer with data from: {twitter_data_path}")
    print(f"{'=' * 50}")
    
    try:
        # Load the Twitter data
        with open(twitter_data_path, 'r') as f:
            twitter_data = json.load(f)
        
        username = twitter_data.get("username", twitter_data.get("profile", {}).get("username", "unknown_user"))
        print(f"Analyzing Twitter profile: @{username}")
        
        # Check if we have valid Twitter data
        if "profile" in twitter_data and "error" in twitter_data["profile"]:
            print(f"Error in Twitter data: {twitter_data['profile']['error']}")
            print("Using sample Twitter data instead...")
            
            # Use the sample Twitter data
            sample_path = Path("output") / "sample_twitter_data.json"
            if not sample_path.exists():
                print("Creating sample Twitter data...")
                create_sample_twitter_data(sample_path)
            
            with open(sample_path, 'r') as f:
                twitter_data = json.load(f)
            
            username = twitter_data.get("profile", {}).get("username", "unknown_user")
            print(f"Using sample Twitter data for: @{username}")
        
        # Create the analyzer
        analyzer = TwitterAnalyzer()
        
        # Analyze the tweets
        print("Processing Twitter data with OpenAI...")
        analysis = await analyzer.analyze_tweets(twitter_data)
        
        # Print summary of analysis
        print("\nAnalysis completed!")
        
        # Save analysis to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"analysis_twitter_{username}_{timestamp}.json"
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / filename
        
        with open(output_path, 'w') as f:
            json.dump(analysis, f, indent=2)
        
        print(f"\nAnalysis saved to {output_path}")
        return analysis
        
    except Exception as e:
        print(f"Error processing Twitter data: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

async def test_integration_service(company_data_path: str, twitter_data_path: str):
    """
    Test the IntegrationService with data from files.
    
    Args:
        company_data_path: Path to a JSON file with company search results
        twitter_data_path: Path to a JSON file with Twitter profile and tweets
    """
    print(f"\n{'=' * 50}")
    print(f"Testing IntegrationService with company data from: {company_data_path}")
    print(f"and Twitter data from: {twitter_data_path}")
    print(f"{'=' * 50}")
    
    try:
        # Load the company data
        with open(company_data_path, 'r') as f:
            company_data = json.load(f)
        
        company_name = company_data.get("company_name", "Unknown Company")
        
        # Load the Twitter data
        with open(twitter_data_path, 'r') as f:
            twitter_data = json.load(f)
        
        # Check if we have valid Twitter data
        if "profile" in twitter_data and "error" in twitter_data["profile"]:
            print(f"Error in Twitter data: {twitter_data['profile']['error']}")
            print("Using sample Twitter data instead...")
            
            # Use the sample Twitter data
            sample_path = Path("output") / "sample_twitter_data.json"
            if not sample_path.exists():
                print("Creating sample Twitter data...")
                create_sample_twitter_data(sample_path)
            
            with open(sample_path, 'r') as f:
                twitter_data = json.load(f)
        
        # Process the company data
        company_processor = CompanyProcessor()
        results_text = json.dumps(company_data.get("results", {}), indent=2)
        company_result = await company_processor.analyze_company(results_text)
        
        # Process the Twitter data
        twitter_analyzer = TwitterAnalyzer()
        twitter_analysis = await twitter_analyzer.analyze_tweets(twitter_data)
        
        # Integrate the data
        print("Integrating data using IntegrationService...")
        integrated_data = await IntegrationService.process_company_data(
            company_name=company_name,
            serp_data=company_data.get("results", {}),
            twitter_data=twitter_data,
            company_processor_result=company_result,
            twitter_analysis=twitter_analysis
        )
        
        # Print summary of integration
        print("\nIntegration completed!")
        
        # Save integrated data to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"integrated_{company_name.lower().replace(' ', '_')}_{timestamp}.json"
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / filename
        
        with open(output_path, 'w') as f:
            json.dump(integrated_data, f, indent=2)
        
        print(f"\nIntegrated data saved to {output_path}")
        return integrated_data
        
    except Exception as e:
        print(f"Error integrating data: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def create_sample_twitter_data(filepath: Path):
    """
    Create a sample Twitter data file for testing.
    
    Args:
        filepath: Path to save the sample data
    """
    sample_twitter_data = {
        "profile": {
            "username": "elonmusk",
            "display_name": "Elon Musk",
            "bio": "Technoking of Tesla, Imperator of Mars",
            "location": "Mars",
            "followers_count": 128000000,
            "following_count": 150,
            "joined": "June 2009",
            "verified": True
        },
        "tweets": [
            {
                "date": "2023-03-01",
                "text": "AI is the future. We need to ensure it's safe and beneficial for humanity.",
                "likes": 50000,
                "retweets": 10000,
                "replies": 5000
            },
            {
                "date": "2023-03-02",
                "text": "SpaceX Starship will make life multiplanetary.",
                "likes": 75000,
                "retweets": 15000,
                "replies": 7000
            },
            {
                "date": "2023-03-03",
                "text": "Tesla's mission is to accelerate the world's transition to sustainable energy.",
                "likes": 60000,
                "retweets": 12000,
                "replies": 6000
            }
        ],
        "mentions": ["tesla", "spacex", "neuralink", "xai"],
        "hashtags": ["ai", "space", "sustainability", "technology"]
    }
    
    with open(filepath, 'w') as f:
        json.dump(sample_twitter_data, f, indent=2)

async def main():
    """Run the NLP tests."""
    # Check if output directory exists
    output_dir = Path("output")
    if not output_dir.exists():
        print("Error: output directory not found.")
        print("Creating output directory...")
        output_dir.mkdir(exist_ok=True)
    
    # Ask user which test to run
    print("\nWhich test would you like to run?")
    print("1. Test individual processors with existing files")
    print("2. Test integration service with existing files")
    
    
    choice = input("\nEnter your choice (1-2): ")
    
    if choice == "1":
        # Find the company test file
        company_files = list(output_dir.glob("company_*.json"))
        if not company_files:
            print("Error: No company test files found in the output directory.")
            return
        company_file = max(company_files, key=lambda f: f.stat().st_mtime)
        
        # Find the founder test file
        founder_files = list(output_dir.glob("founder_*.json"))
        if not founder_files:
            print("Error: No founder test files found in the output directory.")
            return
        founder_file = max(founder_files, key=lambda f: f.stat().st_mtime)
        
        # Find or create the Twitter test file
        twitter_files = list(output_dir.glob("twitter_*.json"))
        if twitter_files:
            twitter_file = max(twitter_files, key=lambda f: f.stat().st_mtime)
        else:
            # Create a sample Twitter data file
            twitter_file = output_dir / "sample_twitter_data.json"
            if not twitter_file.exists():
                print("Creating sample Twitter data...")
                create_sample_twitter_data(twitter_file)
        
        print(f"Using company file: {company_file}")
        print(f"Using founder file: {founder_file}")
        print(f"Using Twitter file: {twitter_file}")
        
        # Test the processors
        company_result = await test_company_processor(str(company_file))
        founder_result = await test_founder_processor(str(founder_file))
        twitter_result = await test_twitter_analyzer(str(twitter_file))
    
    if choice == "2":
        # Find the company test file
        company_files = list(output_dir.glob("company_*.json"))
        if not company_files:
            print("Error: No company test files found in the output directory.")
            return
        company_file = max(company_files, key=lambda f: f.stat().st_mtime)
        
        # Find or create the Twitter test file
        twitter_files = list(output_dir.glob("twitter_*.json"))
        if twitter_files:
            twitter_file = max(twitter_files, key=lambda f: f.stat().st_mtime)
        else:
            # Create a sample Twitter data file
            twitter_file = output_dir / "sample_twitter_data.json"
            if not twitter_file.exists():
                print("Creating sample Twitter data...")
                create_sample_twitter_data(twitter_file)
        
        print(f"Using company file: {company_file}")
        print(f"Using Twitter file: {twitter_file}")
        
        # Test the integration service
        await test_integration_service(str(company_file), str(twitter_file))
    
    print("\nAll tests completed!")

if __name__ == "__main__":
    asyncio.run(main()) 