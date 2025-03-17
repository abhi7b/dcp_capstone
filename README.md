# Duke Capital Partners AI Scouting Platform

The DCP AI Scouting Platform is an intelligent system designed to identify, analyze, and evaluate promising companies and founders with connections to Duke University. The platform leverages advanced web scraping, natural language processing, and machine learning techniques to automate the initial stages of the investment scouting process.

## Project Overview

The DCP AI Scouting Platform automates the discovery and preliminary analysis of potential investment opportunities by:

1. **Discovering** companies and founders with Duke connections through automated web scraping
2. **Analyzing** the collected data using NLP and ML techniques
3. **Evaluating** opportunities based on configurable criteria
4. **Presenting** findings through a user-friendly web interface
5. **Storing** structured data for future reference and analysis

## System Architecture

The platform follows a modular architecture with clear separation of concerns:

```
capstone-dcp/
├── backend/           # Backend services and API
│   ├── api/           # API endpoints and handlers
│   ├── config/        # Configuration management
│   ├── nlp/           # Natural Language Processing components
│   │   ├── prompts/   # LLM prompt templates
│   │   └── services/  # Integration services
│   └── scrapers/      # Web scraping components
├── db/                # Database models and connection management
│   ├── database/      # Database connection and ORM models
│   └── schemas/       # Pydantic schemas for validation
├── frontend/          # Web interface (React)
└── output/            # Processed data output directory
```

## Data Flow Pipeline

The platform implements a comprehensive data pipeline:

1. **Data Collection** (Scrapers)
   - Web scraping of search engine results, company websites, and social media
   - Structured data extraction from various sources

2. **Data Processing** (NLP)
   - Entity recognition and information extraction
   - Sentiment analysis and content evaluation
   - Duke affiliation detection and verification

3. **Data Integration** (Services)
   - Combining data from multiple sources
   - Resolving conflicts and inconsistencies
   - Generating comprehensive profiles

4. **Data Storage** (Database)
   - Structured storage in PostgreSQL database
   - Efficient querying and retrieval
   - Data versioning and history tracking

5. **Data Presentation** (API & Frontend)
   - RESTful API for data access
   - Interactive web interface for exploration
   - Filtering, sorting, and search capabilities

## Key Components

### Backend Components

#### API (`backend/api/`)

The API layer provides RESTful endpoints for accessing and manipulating data:

- `base_endpoint.py`: Base class for all API endpoints with common functionality
- `company.py`: Endpoints for company data retrieval, search, and analysis
- `founder.py`: Endpoints for founder data retrieval, search, and analysis
- `test.py`: Test endpoints for system health checks and diagnostics
- `test_api.py`: Comprehensive test suite for API functionality

#### Configuration (`backend/config/`)

The configuration system manages application settings and environment variables:

- `config.py`: Central configuration with settings for all components
- `cache.py`: Caching system for improved performance
- `logs.py`: Logging configuration and management
- `__init__.py`: Configuration initialization and utilities

#### Natural Language Processing (`backend/nlp/`)

The NLP components analyze and process textual data:

- `base_processor.py`: Base class for all NLP processors
- `company_processor.py`: Analyzes company information
- `founder_processor.py`: Analyzes founder information
- `twitter_analyzer.py`: Analyzes Twitter content for insights
- `test_nlp.py`: Test suite for NLP components
- `prompts/`: Directory containing prompt templates for LLM interactions
- `services/`: Integration services for combining data from multiple sources

#### Web Scrapers (`backend/scrapers/`)

The scraping components gather information from various web sources:

- `base_scraper.py`: Base class for all scrapers with common functionality
- `company_scraper.py`: Gathers information about companies
- `founder_scraper.py`: Gathers information about founders
- `twitter_scraper.py`: Extracts data from Twitter profiles and tweets
- `test_scrapers.py`: Test suite for scraper components
- `test_twitter_scraper.py`: Specific tests for Twitter scraping
- `test_improved_scraper.py`: Tests for enhanced scraping capabilities

### Database Components (`db/`)

The database layer manages data persistence and retrieval:

- `database/db.py`: Database connection management and session handling
- `database/models.py`: SQLAlchemy ORM models defining the database schema
- `schemas/`: Pydantic schemas for request/response validation

## Detailed Component Descriptions

### Scraping System

The scraping system is responsible for gathering raw data from various sources:

1. **Base Scraper**: Provides common functionality for all scrapers, including:
   - Rate limiting and throttling
   - Error handling and retry logic
   - Proxy management
   - Result caching

2. **Company Scraper**: Gathers information about companies from:
   - Search engine results
   - Company websites
   - Business directories
   - News articles

3. **Founder Scraper**: Gathers information about founders from:
   - Search engine results
   - Professional profiles
   - Academic directories
   - News articles

4. **Twitter Scraper**: Extracts data from Twitter, including:
   - Profile information
   - Recent tweets
   - Engagement metrics
   - Network connections

### NLP Processing System

The NLP system analyzes and processes the raw data:

1. **Base Processor**: Provides common functionality for all processors, including:
   - Text preprocessing
   - Entity recognition
   - Sentiment analysis
   - LLM integration

2. **Company Processor**: Analyzes company information to extract:
   - Business description and focus
   - Industry classification
   - Growth indicators
   - Duke affiliation signals

3. **Founder Processor**: Analyzes founder information to extract:
   - Educational background
   - Professional experience
   - Duke affiliation details
   - Entrepreneurial history

4. **Twitter Analyzer**: Analyzes Twitter content to determine:
   - Content themes and topics
   - Sentiment and tone
   - Engagement patterns
   - Actionability for investment scouting

### Integration Services

The integration services combine data from multiple sources:

1. **Data Integration**: Merges data from different sources to create comprehensive profiles
2. **Conflict Resolution**: Resolves inconsistencies between data sources
3. **Enrichment**: Adds derived insights and metrics to the raw data
4. **Scoring**: Calculates various scores for evaluation and ranking

### API System

The API system provides access to the processed data:

1. **Base Endpoint**: Common functionality for all endpoints, including:
   - Authentication and authorization
   - Request validation
   - Response formatting
   - Error handling

2. **Company Endpoints**: Access to company data, including:
   - Retrieval by name or ID
   - Search and filtering
   - Analysis and insights
   - Scoring and ranking

3. **Founder Endpoints**: Access to founder data, including:
   - Retrieval by name or ID
   - Search and filtering
   - Analysis and insights
   - Scoring and ranking

4. **Test Endpoints**: System health checks and diagnostics

## Database Schema

The database schema is designed to efficiently store and retrieve structured data:

1. **Company**: Stores company information
   - Basic details (name, description, industry)
   - Contact information (website, social media)
   - Financial information (funding, valuation)
   - Duke affiliation details
   - Analysis scores and metrics

2. **Founder**: Stores founder information
   - Personal details (name, bio, location)
   - Educational background
   - Professional experience
   - Duke affiliation details
   - Analysis scores and metrics

3. **CompanyFounder**: Maps the many-to-many relationship between companies and founders
4. **SERPUsage**: Tracks search engine API usage for quota management

## Scoring and Evaluation

The platform evaluates opportunities using multiple scoring dimensions:

1. **Duke Affiliation Score**: Measures the strength and relevance of Duke connections
2. **Startup Potential Score**: Evaluates the company's growth potential
3. **Content Relevance Score**: Assesses the relevance to DCP's investment focus
4. **Overall Score**: Weighted combination of individual scores

## Alignment with Project Scope

The DCP AI Scouting Platform aligns with the project scope by:

1. **Automating Discovery**: The scraping system automates the discovery of companies and founders with Duke connections, significantly reducing manual research time.

2. **Intelligent Analysis**: The NLP system provides deep insights into companies and founders, extracting relevant information from unstructured text.

3. **Objective Evaluation**: The scoring system provides consistent, objective evaluation of opportunities based on configurable criteria.

4. **Efficient Data Management**: The database system stores structured data for efficient retrieval and analysis, creating a valuable knowledge base.

5. **User-Friendly Interface**: The API and frontend provide easy access to the data and insights, making it accessible to investment professionals.

## Getting Started

### Prerequisites

1. Python 3.9 or higher
2. PostgreSQL database
3. Required API keys:
   - SERPAPI_KEY for web scraping
   - OPENAI_API_KEY for NLP processing

### Installation

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Fill in template `.env` file with the required environment variables:
   ```
   # API Keys
   SERPAPI_KEY=your-serpapi-key-here
   OPENAI_API_KEY=your-openai-api-key-here
   
   # Database
   DATABASE_URL=postgresql+asyncpg://username:password@host:port/database
   
   # Environment
   ENV=development
   DEBUG=true

   etc
   ```

### Running the Application

To run the backend API server:

```bash
python -m backend.app
```

The API will be available at http://localhost:8000, with documentation at http://localhost:8000/docs.

### Running Tests

To run the test suite:

```bash
python -m backend.api.test_api --all
```

## Future Enhancements

Potential future enhancements include:

1. **Advanced ML Models**: Implementing more sophisticated machine learning models for opportunity evaluation
2. **Additional Data Sources**: Integrating additional data sources for more comprehensive analysis
3. **Automated Monitoring**: Implementing automated monitoring of companies and founders for updates
4. **Portfolio Integration**: Integrating with portfolio management systems for end-to-end investment workflow
5. **Predictive Analytics**: Developing predictive models for investment outcome forecasting

## License

This project is proprietary and confidential. Unauthorized copying, transfer, or reproduction of the contents of this project is strictly prohibited.

## Getting started

To make it easy for you to get started with GitLab, here's a list of recommended next steps.

Already a pro? Just edit this README.md and make it your own. Want to make it easy? [Use the template at the bottom](#editing-this-readme)!

## Add your files

- [ ] [Create](https://docs.gitlab.com/ee/user/project/repository/web_editor.html#create-a-file) or [upload](https://docs.gitlab.com/ee/user/project/repository/web_editor.html#upload-a-file) files
- [ ] [Add files using the command line](https://docs.gitlab.com/ee/gitlab-basics/add-file.html#add-a-file-using-the-command-line) or push an existing Git repository with the following command:

```
cd existing_repo
git remote add origin https://gitlab.com/abhishekb7/capstone-dcp.git
git branch -M main
git push -uf origin main
```

## Integrate with your tools

- [ ] [Set up project integrations](https://gitlab.com/abhishekb7/capstone-dcp/-/settings/integrations)

## Collaborate with your team

- [ ] [Invite team members and collaborators](https://docs.gitlab.com/ee/user/project/members/)
- [ ] [Create a new merge request](https://docs.gitlab.com/ee/user/project/merge_requests/creating_merge_requests.html)
- [ ] [Automatically close issues from merge requests](https://docs.gitlab.com/ee/user/project/issues/managing_issues.html#closing-issues-automatically)
- [ ] [Enable merge request approvals](https://docs.gitlab.com/ee/user/project/merge_requests/approvals/)
- [ ] [Set auto-merge](https://docs.gitlab.com/ee/user/project/merge_requests/merge_when_pipeline_succeeds.html)

## Test and Deploy

Use the built-in continuous integration in GitLab.

- [ ] [Get started with GitLab CI/CD](https://docs.gitlab.com/ee/ci/quick_start/)
- [ ] [Analyze your code for known vulnerabilities with Static Application Security Testing (SAST)](https://docs.gitlab.com/ee/user/application_security/sast/)
- [ ] [Deploy to Kubernetes, Amazon EC2, or Amazon ECS using Auto Deploy](https://docs.gitlab.com/ee/topics/autodevops/requirements.html)
- [ ] [Use pull-based deployments for improved Kubernetes management](https://docs.gitlab.com/ee/user/clusters/agent/)
- [ ] [Set up protected environments](https://docs.gitlab.com/ee/ci/environments/protected_environments.html)

***
