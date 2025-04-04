<<<<<<< HEAD
# dcp_capstone
=======
# Duke Capital Partners AI Insight Engine

An AI-powered service to identify and filter investment opportunities by focusing on new companies, startups, and their founders, with a particular emphasis on Duke alumni.

## Overview

This system collects data from search engines and Twitter (via Nitter), processes it using NLP and LLM techniques, and serves actionable insights through REST APIs and a user-friendly frontend.

## Features

- **Identify Duke-affiliated startups and founders**: Automatically detect new companies and founders with Duke affiliations
- **Surface investment opportunities**: Highlight actionable funding opportunities by analyzing web activity
- **Automate data collection and analysis**: Leverage SERP and Nitter to gather and process relevant data
- **Focus on new companies and startups**: Prioritize startups in early stages to align with DCP's investment strategy

## Project Structure

```
/duke-vc-insight-engine
├── backend/              # FastAPI backend
├── celery/               # Background tasks
├── frontend/             # Next.js frontend
├── docs/                 # Project documentation
└── tests/                # Unit and integration tests
```

## Setup Instructions

### Prerequisites

- Python 3.9+
- PostgreSQL
- Docker



## API Documentation

When running the backend, visit `http://localhost:8000/docs` for the Swagger UI documentation.
>>>>>>> ok-api
