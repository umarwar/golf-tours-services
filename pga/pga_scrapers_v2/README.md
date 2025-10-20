# PGA Tour Scrapers API

FastAPI wrapper for PGA Tour tournament scrapers with Supabase database integration.

## Create a virtual environment:
```bash
python -m venv myenv
myenv\Scripts\activate
```

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

## Add .env file
```bash
ZYTE_API_KEY=your_zyte_api_key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

## API Endpoints

### Authentication
All endpoints require an bearer token in the header:
```
Authorization: Bearer <BEARER_TOKEN>
```

### Available Endpoints

- `POST /pga/scrape/tournaments` - Scrape upcoming and completed tournaments
- `POST /pga/scrape/leaderboards` - Scrape tournament leaderboards
- `POST /pga/scrape/players` - Scrape player details (takes 15-20 minutes)
- `POST /pga/scrape/course-stats` - Scrape course statistics


### For GCP deployment 
Run deploy.sh file

