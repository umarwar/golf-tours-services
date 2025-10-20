# LPGA

This directory contains two components:

- **📁 lpga_scrapers_v1**: Scrapy spiders that collect LPGA data and upsert into Supabase.
  - Purpose: Fetch fresh data from LPGA JSON endpoints and streamed HTML.
  - What it does: Scrapes tournaments, leaderboards, and player profiles; writes to Supabase tables.
  - How to run: Trigger spiders via the included FastAPI app.

- **📁 lpga_pro_feeds_apis**: FastAPI service exposing read-only LPGA data from Supabase.
  - Purpose: Serve the stored data through clean, paginated REST endpoints.
  - What it does: Reads from Supabase and returns tournaments, leaderboards, and players data.
  - How to run: Trigger API via the included FastAPI app.

For detailed API and scraper documentation, visit each folder's README.

### For GCP deployment 
Run deploy.sh file
