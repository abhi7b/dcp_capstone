# Data Documentation

## Data Sources

### 1. SERP API
- **Purpose**: Company and founder discovery
- **Data Types**:
  - Company information
  - Founder profiles
  - News articles
  - Press releases
- **Refresh Rate**: On-demand via API calls


### 2. Nitter (Twitter)
- **Purpose**: Social media insights
- **Data Types**:
  - Tweets
  - Profile information
  - Engagement metrics
- **Instances Used**:
  - https://nitter.net
  - https://nitter.privacydev.net
  - https://nitter.poast.org
  - https://nitter.woodland.cafe
- **Fallback Mechanism**: Automatic instance switching
- **Rate Limits**: Per instance limits

### 3. OpenAI
- **Purpose**: Data processing and analysis
- **Data Types**:
  - Entity extraction
  - Affiliation verification
  - Content summarization
- **Model**: GPT-4o-mini

## Data Processing

### 1. Collection
- Triggered by API endpoints
- Parallel processing for multiple sources
- Error handling and retries

### 2. Processing
- OpenAI-powered entity extraction
- Duke affiliation verification
- Data validation and cleaning
- Structured data conversion

### 3. Storage
- **Primary Database**: PostgreSQL (Supabase)
- **Cache**: Redis
- **Data Retention**: 
  - Processed data: Indefinite
  - Raw data: 30 days
  - Cache: 1 hour
