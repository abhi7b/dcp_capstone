# Duke Capital Partners AI Insight Engine

An AI-powered service to identify and filter investment opportunities by focusing on new companies, startups, and their founders, with a particular emphasis on Duke alumni.

## Overview

This system collects data from Serp API and Twitter (via Nitter), processes it using NLP and LLM techniques, and serves actionable insights through REST APIs and a streamlit interface.

## Key Features

- **Duke Affiliation Detection**: 
  - Identify companies and founders with Duke connections
  - Score and validate Duke affiliations
  - Track alumni in leadership positions

- **Investment Opportunity Analysis**:
  - Focus on early-stage startups (pre-seed, seed, Series A)
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
- PostgreSQL (or Supabase)
- Redis
- Streamlit (for frontend)
- Docker (optional, for containerized deployment)

### Environment Setup

1. Clone the repository:
   ```bash
   git clone [repository-url]
   cd capstone-dcp
   ```

2. Create and activate virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   ```

3. Install backend dependencies:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```bash
   # Copy example environment files
   cp .env.example .env
   cp .streamlit/secrets.toml.example .streamlit/secrets.toml
   
   # Edit .env and .streamlit/secrets.toml with your configuration
   ```

5. Configure Supabase (if using):
   - Create a new Supabase project
   - Update DATABASE_URL in .env with your Supabase connection string
   - Set up necessary database tables and schemas

### Running the Application

1. Start Redis (required for caching and background tasks):
   ```bash
   sudo service redis-server start
   ```

2. Initialize the database:
   ```bash
   cd backend
   alembic upgrade head
   ```

3. Start the backend service:
   ```bash
   # Development mode
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

4. Start the Streamlit frontend:
   ```bash
   # In a new terminal
   cd frontend
   streamlit run streamlit_app.py
   ```

### Development Workflow

1. **API Development**:
   - Backend runs on `http://localhost:8000`
   - API documentation available at `http://localhost:8000/docs`
   - Test endpoints using the interactive Swagger UI

2. **Frontend Development**:
   - Streamlit runs on `http://localhost:8501`
   - Changes to frontend code auto-reload
   - Use `.streamlit/secrets.toml` for frontend configuration



### Deployment Notes

- Ensure all environment variables are properly set in production
- Use secure API keys and secrets
- Configure proper CORS settings for production
- Set up proper logging and monitoring
- Consider using Docker Compose for containerized deployment

## API Documentation

- **Swagger UI**: `http://localhost:8000/api/docs`

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
