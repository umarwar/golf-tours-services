# LIV Golf Scrapers v1 and Feed API

This 📂`livgolf_scrapers_v1` folder contains both:
- A Scrapy spider that scrapes upcoming LIV Golf tournaments and upserts them into Supabase.
- A FastAPI service exposing a read-only feed endpoint for the same tournaments.

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

## Run

Run the API:
```bash
uvicorn main:app --reload
```

## API Endpoints

#### 1. POST /livgolf/scrape/tournaments
This endpoint is used to scrape the upcoming LIV tournaments

Response:
```json
{
  "message": "Tournaments scraped successfully",
  "tournaments_processed": 11
}
```

#### 2. GET /livgolf/tournaments
Returns upcoming LIV tournaments with pagination.

Query params:
- `year` (optional), e.g. `2025`
- `page` (default 1)
- `page_size` (default 20, max 200)

Response example:
```json
{
  "tournaments": [
    {
        "id": "4489667f-06ba-408c-b1c9-cdd09cb9ea48",
        "name": "Riyadh",
        "year": 2026,
        "start_date": "2026-02-05",
        "end_date": "2026-02-07",
        "status": "Upcoming",
        "tournament_url": "https://www.livgolf.com/schedule/riyadh-2026",
        "ticket_url": "https://events.livgolf.com/riyadh/#tickets",
        "course": {
            "name": "Riyadh Golf Club",
            "address": "Riyadh Golf Club, Al Aarid",
            "city": "Riyadh",
            "country": "Saudi Arabia",
            "zipcode": "Riyadh 13352"
        }
    }
  ],
  "page": 1,
  "page_size": 20,
  "has_more": true
}
```


