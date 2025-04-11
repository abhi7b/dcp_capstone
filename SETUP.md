# Duke Capital Partners Project Setup Guide

## Step 1: Install Prerequisites

### 1.1 Install Python and Git
```bash
# Check Python version (should be 3.8 or higher)
python --version

# Install Git if not already installed
# On macOS:
brew install git
# On Linux:
sudo apt-get install git
# On Windows: Download from https://git-scm.com/downloads
```

### 1.2 Install Redis
```bash
# On macOS:
brew install redis
brew services start redis

# On Linux:
sudo apt-get install redis-server
sudo service redis-server start

# On Windows: Download from https://github.com/microsoftarchive/redis/releases
```

## Step 2: Clone and Setup Project

### 2.1 Clone Repository
```bash
git clone <repository-url>
cd capstone-dcp
```

### 2.2 Create Virtual Environment
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
.\venv\Scripts\activate
```

### 2.3 Install Dependencies
```bash
pip install -r requirements.txt
```

## Step 3: Configure Environment

### 3.1 Create .env File
```bash
# Create .env file
touch .env
```

### 3.2 Add Environment Variables
Edit `.env` file with these values:
```bash
# Supabase Database URL
DATABASE_URL=postgresql+asyncpg://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres

# API Keys
SERPAPI_KEY=your_serpapi_key_here
OPENAI_API_KEY=your_openai_key_here

# Application settings
ENVIRONMENT=development
DEV_API_KEY=7d0e4d15-898c-4138-ab42-154ef90f6e18

# Redis configuration
REDIS_URL=redis://localhost:6379/0
```

## Step 4: Setup Supabase

### 4.1 Create Supabase Project
1. Go to https://supabase.com
2. Create a new project
3. Get your project URL and anon key from Project Settings > API
4. Update your `.env` file with the Supabase credentials

### 4.2 Initialize Database Tables
```bash
# Run the table setup script
python -m app.db.rebuild_tables

# Choose option 2 to create fresh tables
```

## Step 5: Verify Setup

### 5.1 Check Redis
```bash
# Check Redis is running
redis-cli ping  # Should return "PONG"
```

### 5.2 Start Application
```bash
# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5.3 Test Installation
```bash
# Test health endpoint
curl http://localhost:8000/health
```

## Step 6: Access Documentation

Once the server is running, access:
- API Documentation: http://localhost:8000/docs

## Troubleshooting

### API Key Issues
- Verify `.env` has `ENVIRONMENT=development`
- Check API key in request matches `DEV_API_KEY`
- Ensure Redis is running
