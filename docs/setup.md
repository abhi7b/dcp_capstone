# Setup and Deployment Guide

## Development Setup

### Prerequisites
- Python 3.9+
- Docker and Docker Compose
- Node.js 16+
- API keys for:
  - SERP API
  - OpenAI
  - Supabase

### Local Development
1. Clone the repository
2. Create `.env` file with required API keys
3. Start services:
   ```bash
   docker-compose up -d
   ```
4. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Environment Variables
- Stored in .env.example

## API Documentation
- Swagger UI: `http://localhost:8000/api/docs`
- ReDoc: `http://localhost:8000/api/redoc`
- OpenAPI Schema: `http://localhost:8000/api/openapi.json`

## Health Check
- Endpoint: `http://localhost:8000/api/health`
- Checks database connection
- Shows last and next data refresh
- Displays system status

## Monitoring
- Request logging middleware
- Error tracking
- Performance metrics
- Health check endpoint

## Deployment

### Production Setup
1. Set up cloud infrastructure (AWS)
2. Configure environment variables
3. Build and push Docker images
4. Deploy using Docker Compose or Kubernetes

### CI/CD Pipeline
1. Push to main branch triggers build
2. Run tests
3. Build Docker images
4. Deploy to staging
5. Manual approval for production 