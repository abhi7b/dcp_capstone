# NLP Module for DCP AI Scouting Platform

This module provides natural language processing capabilities for the DCP AI Scouting Platform, leveraging OpenAI's language models to analyze company and founder data.

## Key Components

### Core Processors

- **BaseProcessor** (`base_processor.py`): Provides common functionality including OpenAI API integration, error handling, retry logic, and response parsing.

- **CompanyProcessor** (`company_processor.py`): Analyzes company information to extract:
  - Business descriptions and focus
  - Industry classifications
  - Funding information
  - Duke affiliation signals
  - Growth indicators

- **FounderProcessor** (`founder_processor.py`): Analyzes founder information to extract:
  - Educational background
  - Professional experience
  - Duke affiliation details
  - Entrepreneurial history

- **TwitterAnalyzer** (`twitter_analyzer.py`): Analyzes Twitter content to determine:
  - Content themes and topics
  - Sentiment and engagement patterns
  - Actionable investment insights
  - Relevance to investment decisions

### Integration Services

The `services/` directory contains modules that combine data from multiple sources:

- **IntegrationService** (`services/integration.py`): Merges data from different sources to create comprehensive profiles, resolves inconsistencies, and calculates scores.

- **ScoringService** (`services/scoring.py`): Implements scoring algorithms for evaluating investment opportunities.

### Prompt Templates

The `prompts/` directory contains structured templates for OpenAI API calls:

- Company analysis prompts
- Founder analysis prompts
- Twitter content analysis prompts

## Scoring System

The NLP module evaluates opportunities using three main components:

### 1. Duke Affiliation Score (40% of total)

Measures the strength of connection to Duke University:

| Factor | Weight | Description |
|--------|--------|-------------|
| Direct Affiliation | 50% | Is the founder/employee a Duke graduate? |
| Recency | 20% | Recent graduates (within 5 years) score higher |
| Degree Relevance | 15% | Business, Engineering, CS degrees score higher |
| Role Importance | 15% | Founders, C-level executives score higher |

### 2. Startup Potential Score (40% of total)

Evaluates the business potential of the company:

| Factor | Weight | Description |
|--------|--------|-------------|
| Funding Stage | 30% | Early stage (seed, Series A) scores higher |
| Recent Funding | 25% | Funding within last 12 months scores higher |
| Industry Growth | 25% | High-growth industries score higher |
| Market Size | 20% | Larger addressable markets score higher |

### 3. Content Relevance Score (20% of total)

Assesses the relevance and actionability of available content:

| Factor | Weight | Description |
|--------|--------|-------------|
| Content Recency | 40% | Recent content (within 3 months) scores higher |
| Actionability | 40% | Mentions of seeking investment score higher |
| Source Credibility | 20% | Verified accounts, reputable sources score higher |

The final score is a weighted combination of these three components, normalized to a 0-100 scale.

## Setup and Usage

### Environment Variables

Required environment variables:

```
# OpenAI settings
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini
OPENAI_MAX_TOKENS=4000
OPENAI_TEMPERATURE=0.0

# Cache settings (optional)
CACHE_DEFAULT_TTL=3600
CACHE_COMPANY_TTL=86400
CACHE_FOUNDER_TTL=86400
```

### Basic Usage

```python
from backend.nlp.company_processor import CompanyProcessor
from backend.nlp.founder_processor import FounderProcessor
from backend.nlp.twitter_analyzer import TwitterAnalyzer
from backend.nlp.services.integration import IntegrationService

# Initialize processors
company_processor = CompanyProcessor()
founder_processor = FounderProcessor()
twitter_analyzer = TwitterAnalyzer()

# Analyze company data
company_analysis = await company_processor.analyze_company(company_text)

# Analyze founder data
founder_analysis = await founder_processor.analyze_founder(founder_text)

# Analyze Twitter data
twitter_analysis = await twitter_analyzer.analyze_tweets(twitter_data)

# Integrate data
integrated_data = await IntegrationService.process_company_data(
    company_name="Example Company",
    serp_data=serp_results,
    twitter_data=twitter_results,
    company_processor_result=company_analysis,
    twitter_analysis=twitter_insights
)

# Save to JSON
filepath = IntegrationService.save_output_to_json(integrated_data, "company_example")
```

### Testing

To test the NLP components:

```bash
python -m backend.nlp.test_nlp
```

This script provides options to test:
1. Individual processors (Company, Founder, Twitter)
2. Integration service
3. End-to-end processing flow
4. All components

## Data Processing Flow

The NLP module follows a structured data processing flow:

1. **Data Collection**
   - Web scrapers collect raw data from search engines (SERP)
   - Twitter scraper collects tweets and profile information
   - Data is stored in JSON format

2. **Data Analysis**
   - Company and founder data analyzed using OpenAI
   - Twitter content analyzed for investment insights
   - Structured JSON outputs produced

3. **Data Integration**
   - Data from different sources merged into comprehensive profiles
   - Field inconsistencies resolved
   - Scores calculated based on combined data
   - Database-ready fields prepared

4. **Output Generation**
   - Integrated data saved to JSON files
   - Database-ready fields prepared for insertion
   - Scores included for filtering and ranking

## Caching

Results are cached to improve performance and reduce API costs:
- Company analysis: 24 hours (86400 seconds)
- Founder analysis: 24 hours (86400 seconds)
- Twitter analysis: 1 hour (3600 seconds)

## Error Handling

All processors include robust error handling with:
- Fallback mechanisms for API failures
- JSON validation for proper output format
- Detailed logging for debugging

## Directory Structure

```
nlp/
├── __init__.py           # Package exports
├── base_processor.py     # Base processor with common functionality
├── company_processor.py  # Company-specific processor
├── founder_processor.py  # Founder-specific processor
├── twitter_analyzer.py   # Twitter content analyzer
├── test_nlp.py           # Testing script for NLP components
├── services/             # Shared service modules
│   ├── __init__.py       # Service exports
│   ├── social_media.py   # Social media utilities
│   ├── scoring.py        # Scoring algorithms
│   └── integration.py    # Data integration service
├── prompts/              # Prompt templates for OpenAI
│   ├── __init__.py       # Prompt exports
│   ├── company_prompts.py # Company analysis prompts
│   ├── founder_prompts.py # Founder analysis prompts
│   └── twitter_prompts.py # Twitter analysis prompts
└── README.md             # This file
```

## Database Migration

The NLP module includes scripts for generating integrated files and migrating data to the database:

### Generating Integrated Files

The `generate_integrated_files.py` script creates integrated JSON files from existing company and Twitter analysis files:

```bash
# Generate integrated files for all companies
python -m nlp.generate_integrated_files

# Generate for a specific company
python -m nlp.generate_integrated_files --company "Example Company"
```

### Migrating to Database

The `migrate_integrated_data.py` script uploads integrated data to the database:

```bash
# Migrate all integrated files to the database
python -m nlp.migrate_integrated_data

# Perform a dry run (no actual database changes)
python -m nlp.migrate_integrated_data --dry-run
```

### Running the Complete Pipeline

The `run_pipeline.py` script provides a convenient way to run the entire process:

```bash
# Run the complete pipeline for a company
python -m nlp.run_pipeline "Example Company"

# Skip specific steps
python -m nlp.run_pipeline "Example Company" --skip-processing
```

The pipeline is flexible and allows you to:
- Process new companies from scratch
- Update existing company data
- Skip steps that have already been completed
- Test the process without making database changes 