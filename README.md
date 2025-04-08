# Duke Capital Partners AI Insight Engine

An AI-powered service to identify and filter investment opportunities by focusing on new companies, startups, and their founders, with a particular emphasis on Duke alumni.

## Overview

This system collects data from search engines and Twitter (via Nitter), processes it using NLP and LLM techniques, and serves actionable insights through REST APIs and a user-friendly frontend.

## Key Features

- **Duke Affiliation Detection**: 
  - Identify companies and founders with Duke connections
  - Score and validate Duke affiliations
  - Track alumni in leadership positions

- **Investment Opportunity Analysis**:
  - Focus on early-stage startups (pre-seed, seed, Series A)
  - Monitor funding announcements and growth signals
  - Score companies based on relevance and potential

- **Automated Data Pipeline**:
  - SERP API integration for web data collection
  - Nitter integration for Twitter insights
  - OpenAI-powered entity extraction and analysis
  - Automated daily updates and scoring

## Project Structure

```
capstone-dcp/
├── backend/                # FastAPI Backend Service
│   ├── app/
│   │   ├── db/             # Database models and CRUD
│   │   ├── routes/         # API endpoints
│   │   ├── services/       # Core services (SERP, NLP, etc.)
│   │   ├── tasks/          # Background tasks
│   │   └── utils/          # Helper utilities
│   ├── tests/              # Test suite
│   └── requirements.txt    # Python dependencies
├── docs/                   # Project documentation
└── frontend/               # Streamlit frontend
```

## Backend Services

### 1. Data Collection Service
- SERP API integration for company/founder discovery
- Nitter scraping for Twitter data
- Rate limiting and quota management
- Raw data storage in structured format

### 2. Data Processing Pipeline
- OpenAI-powered entity extraction
- Duke affiliation verification
- Company and founder scoring
- Data validation and enrichment

### 3. REST API Service
- Company and founder search endpoints
- OAuth-secured access
- Rate limiting (100 requests/minute)
- Redis caching for performance

## Setup Instructions

### Prerequisites
- Python 3.9+
- PostgreSQL
- Redis
- Docker (optional)

### Environment Setup
1. Clone the repository

2. Create and activate virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

### Running the Backend

1. Start PostgreSQL and Redis:
   ```bash
   # Using Docker (optional)
   docker-compose up -d postgres redis
   ```

2. Run database migrations:
   ```bash
   alembic upgrade head
   ```

3. Start the FastAPI server:
   ```bash
   uvicorn app.main:app --reload
   ```


## API Documentation

- **Swagger UI**: `http://localhost:8000/api/docs`
- **ReDoc**: `http://localhost:8000/api/redoc`

### Key Endpoints

- `GET /api/company?name={name}`: Search for company
- `GET /api/founder?name={name}`: Search for founder
- `GET /api/health`: Service health check

## Data Flow

1. **Data Collection**:
   - Scraping of new companies/founders
   - Real-time searches via API endpoints
   - Twitter data enrichment

2. **Processing**:
   - Entity extraction and validation
   - Duke affiliation verification
   - Scoring and classification

3. **Storage**:
   - PostgreSQL for structured data
   - Redis for caching and rate limiting
   - File system for raw data storage

