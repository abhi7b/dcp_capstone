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
# Create .env file if it doesn't exist
touch .env
```

### 3.2 Add Environment Variables
Edit `.env` file with these values:
```dotenv
# Supabase Database URL
DATABASE_URL=postgresql+asyncpg://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres

# API Keys
SERPAPI_KEY=your_serpapi_key_here
OPENAI_API_KEY=your_openai_key_here

# Application settings
ENVIRONMENT=development
# DEV_API_KEY will be added in Step 5

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

## Step 5: Generate and Set Development API Key

Before starting the application, generate the development API key and add it to your `.env` file.

```bash
# Navigate to the backend directory if you aren't already there
cd backend

# Run the script to create/retrieve the key
python -m app.db.create_default_api_key
```

- The script will print the development API key (e.g., `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`).
- Copy this key.
- Open your `.env` file (located in the project root, `capstone-dcp/.env`).
- Add the following line, replacing `<key_from_script>` with the key you copied:
  ```dotenv
  DEV_API_KEY=<key_from_script>
  ```

## Step 6: Verify Setup (Renumbered)

### 6.1 Check Redis
```bash
# Check Redis is running
redis-cli ping  # Should return "PONG"
```

### 6.2 Start Application
```bash
# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 6.3 Test Installation
```bash
# Test health endpoint
curl http://localhost:8000/health
```

## Step 7: Access Documentation (Renumbered)

Once the server is running, access:
- API Documentation: http://localhost:8000/docs
# Removed Alternative Docs: http://localhost:8000/redoc

### Testing API Endpoints
1. Open http://localhost:8000/docs in your browser
2. Click the "Authorize" button at the top of the page
3. Enter the API key you added to your `.env` file (the one generated in Step 5).
4. Click "Authorize"
5. Navigate to the desired section (e.g., "Companies")

## Troubleshooting

### API Key Issues
- Verify `.env` has `ENVIRONMENT=development`
- Check that the `DEV_API_KEY` value in your `.env` file exists and is correct.
- Check that the API key you entered in the Swagger UI "Authorize" dialog matches the `DEV_API_KEY` in your `.env` file.
- Ensure Redis is running
- If getting "Invalid API key" error:
  1. Click the "Authorize" button in Swagger UI
  2. Re-enter the correct API key from your `.env` file.
  3. Click "Authorize"
  4. Try the request again

## License
This project is licensed under the MIT License - see the LICENSE file for details.
