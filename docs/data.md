# Data Documentation

## Database Schema

### Companies Table
```sql
CREATE TABLE companies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    founding_date DATE,
    stage VARCHAR(50),
    industry VARCHAR(100),
    website VARCHAR(255),
    twitter_handle VARCHAR(100),
    duke_affiliation_status VARCHAR(50),
    duke_affiliation_score INTEGER,
    overall_score INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Founders Table
```sql
CREATE TABLE founders (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    current_company_id INTEGER REFERENCES companies(id),
    role VARCHAR(100),
    education JSONB,
    twitter_handle VARCHAR(100),
    duke_affiliation_status VARCHAR(50),
    duke_affiliation_score INTEGER,
    overall_score INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Data Sources

### SERP API
- Company and founder discovery
- News and article scraping
- LinkedIn profile data
- Crunchbase information

### Nitter
- Twitter data scraping
- Recent activity monitoring
- Engagement metrics

## Data Processing Pipeline

### 1. Raw Data Collection
- Format: JSON

### 2. Entity Extraction
- OpenAI processing
- Extract structured data
- Validate against schema

### 3. Affiliation Resolution
- Duke connection verification
- Score calculation
- Status classification

### 4. Data Storage
- PostgreSQL for structured data
- Redis for caching

## Data Quality
- Duplicate detection
- Source verification
