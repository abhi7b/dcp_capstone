# Setup Guide

## Prerequisites

### System Requirements
- Python 3.9+
- PostgreSQL (or Supabase)
- Redis
- Git
- Virtual environment (recommended)

### API Keys Required
- OpenAI API key
- SERP API key
- Twitter API keys (optional)
- Custom API key for authentication

## Installation Steps

### 1. Clone Repository
```bash
git clone [repository-url]
cd capstone-dcp
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Configuration

#### Backend (.env)
```bash
cp .env.example .env
# Edit .env with your configuration
```

Required environment variables:
- `DATABASE_URL`: PostgreSQL/Supabase connection string
- `OPENAI_API_KEY`: OpenAI API key
- `SERPAPI_KEY`: SERP API key
- `API_SECRET_KEY`: Custom API key for authentication
- `REDIS_URL`: Redis connection string

#### Frontend (.streamlit/secrets.toml)
```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit .streamlit/secrets.toml with your configuration
```

Required secrets:
- `api_base_url`: Backend API URL
- `api_key`: Authentication API key

### 5. Database Setup

#### Using Supabase
1. Create a new Supabase project
2. Get the connection string
3. Update `DATABASE_URL` in `.env`
4. Run migrations:
```bash
cd backend
alembic upgrade head
```

### 6. Start Services

#### Redis
```bash
# Using system service
sudo service redis-server start

# Or using Docker
docker run -d -p 6379:6379 redis
```

#### Backend
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend
```bash
streamlit run streamlit_app.py
```

## Verification

### 1. Check API Health
```bash
curl http://localhost:8000/api/health
```

### 2. Test Frontend
- Open browser to `http://localhost:8501`
- Verify API connection
- Test search functionality

### 3. Verify Database
```bash
python backend/check_db.py
```

### 4. Check API Keys
```bash
python backend/check_api_keys.py
```

## Troubleshooting

### Common Issues

1. **Database Connection**
   - Verify connection string
   - Check database permissions
   - Ensure database is running

2. **API Authentication**
   - Verify API keys
   - Check environment variables
   - Test API endpoints

3. **Redis Connection**
   - Verify Redis is running
   - Check connection string
   - Test Redis commands

4. **Frontend Issues**
   - Check API base URL
   - Verify API key
   - Clear browser cache

### Support
- Check error logs
- Review documentation
- Contact development team 