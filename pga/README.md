# PGA Tour

PGA Tour scrapers and APIs for tournaments, players, leaderboards, and course stats.

## Project Structure

### 📁 pga_scrapers_v1
CSV-based scrapers for PGA Tour data (file outputs only).

**What it does:**
- Tournament schedules (upcoming & completed)
- Leaderboards, player details, course hole-by-hole stats
- Writes CSV/XLSX to the `completed_tournaments_output` and `upcoming_tournaments_output` folders

**Create a virtual environment:**
   ```bash
   python -m venv myenv
   myenv\Scripts\activate
   ```

**Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

**Run scrapers:**
   ```bash
   cd pga_scrapers_v1/pgatour_scraper/pgatour_scraper
   scrapy crawl pgatour_upcoming_spider
   ```

### 📁 pga_scrapers_v2
Supabase-backed scrapers with lightweight wrapper APIs.

**What it does:**
- Same data coverage as v1
- Persists to Supabase DB
- Includes simple wrapper APIs for quick access

#### Database Schema (v2)
Supabase tables populated by v2 scrapers:

- `pga_tournaments` - Tournament information
- `pga_tournament_leaderboards` - Player leaderboard data
- `pga_players` - Player profiles and statistics
- `pga_course_stats` - Course hole-by-hole statistics

**Run API:**
   ```bash
   uvicorn main:app --reload
   ```

### 📁 pro_feeds_apis
FastAPI wrapper that provides REST endpoints to access the scraped PGA Tour data.

**What it does:**
- RESTful API endpoints
- Tournament data with pagination
- Player profiles and statistics
- Leaderboard data
- Course hole-by-hole statistics


#### For details, see each folder's README.



