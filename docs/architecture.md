# System Architecture

## Overview
The system consists of three main components:
1. Data Collection Service
2. Data Processing Pipeline
3. REST API Service with Streamlit Frontend

## Component Details

### 1. Data Collection Service
- **SERP API Integration**
  - Keyword-based queries for company/person discovery
  - Time filters (past 6-12 months)
  - Google Dorking for specific sources
- **Nitter Integration**
  - Twitter data scraping via multiple Nitter instances
  - Fallback mechanism for instance availability
  - Rate limiting and error handling

### 2. Data Processing Pipeline
- **OpenAI Integration**
  - Entity extraction from raw data
  - Structured JSON output
  - GPT-4 powered analysis
- **Affiliation Resolution**
  - Duke affiliation classification
  - Scoring based on role and evidence
  - Validation against trusted sources
- **Data Validation**
  - Schema validation
  - Deduplication
  - Quality checks

### 3. REST API Service
- **FastAPI Backend**
  - API Key authentication
  - Rate limiting per API key
  - Request logging middleware
  - Custom error handling
  - Redis caching for performance
- **Database Layer**
  - PostgreSQL with Supabase
  - Automatic refresh cycle
  - Health monitoring
- **Streamlit Frontend**
  - Interactive search interface
  - Real-time API integration
  - Data visualization
  - Configurable settings

## Data Flow
1. API endpoints trigger data collection on demand
2. Raw data processed through OpenAI pipeline
3. Processed data stored in PostgreSQL
4. API serves processed data with Redis caching
5. Streamlit frontend provides user interface

## API Structure
- `/api/company/search/{name}` - Company search
- `/api/founder/search/{name}` - Founder search
- `/api/health` - System health check
- `/api/docs` - API documentation (Swagger UI)

## Scoring Algorithm
```python
Score = (0.4 * Duke Affiliation) + (0.4 * Startup Potential) + (0.2 * Content Relevance)
```

### Scoring Factors
1. **Duke Affiliation (40%)**
   - Alumni status verification
   - Leadership position
   - Company connection strength

2. **Startup Potential (40%)**
   - Funding stage
   - Growth metrics
   - Market opportunity

3. **Content Relevance (20%)**
   - Recent activity
   - Industry alignment
   - News coverage