# LIV Golf Scrapers v1

This 📂`livgolf_scrapers_v1` folder contains:
- A Scrapy spider that scrapes upcoming LIV Golf tournaments and upserts them into Supabase.

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