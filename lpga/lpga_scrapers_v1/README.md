# LPGA Tour Scrapers API

FastAPI wrapper for LPGA Tour tournament scrapers with Supabase database integration.

## Create a virtual environment:
```bash
python -m venv myenv
myenv\Scripts\activate
```

## Installation

Install dependencies:
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

- `POST /lpga/scrape/tournaments` - Scrape upcoming and completed LPGA tournaments
- `POST /lpga/scrape/leaderboards` - Scrape LPGA tournament leaderboards
- `POST /lpga/scrape/players` - Scrape player details (takes 15-20 minutes)

### For GCP deployment 
Run deploy.sh file