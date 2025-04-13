# System Architecture

## Overview
The system consists of three main components:
1. Data Collection Service
2. Data Processing Pipeline
3. REST API Service

## Component Details

### 1. Data Collection Service
- **SERP API Integration**
  - Keyword-based queries for company/person discovery
  - Time filters (past 6-12 months)
  - Google Dorking for specific sources
- **Nitter Integration**
  - Twitter data scraping

### 2. Data Processing Pipeline
- **OpenAI Integration**
  - Entity extraction from raw data
  - Structured JSON output
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
- **Database Layer**
  - PostgreSQL with Supabase
  - Automatic 3-day refresh cycle
  - Health monitoring

## Data Flow
1. Daily scheduled tasks trigger data collection
2. Raw data stored in `/data/raw/`
3. Processing pipeline converts to structured data to store in `/data/json_inputs/`
4. Processed data stored in PostgreSQL
5. API serves processed data with caching

## API Structure
- `/api/companies` - Company search and details
- `/api/person` - Person search and profiles
- `/api/auth` - Authentication endpoints
- `/api/health` - System health check
- `/api/docs` - API documentation
- `/api/redoc` - API reference

## Scoring Algorithm
```python
Score = (0.4 * Duke Affiliation) + (0.4 * Startup Potential) + (0.2 * Content Relevance)
```

### Scoring Factors
1. **Duke Affiliation (40%)**

2. **Startup Potential (40%)**

3. **Content Relevance (20%)**