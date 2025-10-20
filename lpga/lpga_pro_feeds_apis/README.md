# LPGA Feeds APIs

## Create a virtual environment:
```bash
python -m venv myenv
myenv\Scripts\activate
```

## Install
```bash
pip install -r requirements.txt
```

## Add .env file
```bash
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

## Run
```bash
uvicorn main:app --reload
```

## Available Endpoints

- GET `/lpga/tournaments` — List tournaments (optional year filter, pagination)
- GET `/lpga/tournaments/{tournament_id}` — Get a tournament by id
- GET `/lpga/tournaments/{tournament_id}/leaderboard` — Get leaderboard rows (pagination)
- GET `/lpga/players` — List players (pagination)
- GET `/lpga/players/{player_id}/profile` — Get a player's profile with stats and tournaments

---

## Endpoint Details

#### . GET /lpga/tournaments
Query params:
- `year` (optional): e.g. `2025`
- `page` (default 1)
- `page_size` (default 20, max 200)

Response:
```json
{
  "tournaments": [
    {
      "id": "CAOP-2025",
      "name": "CPKC Women's Open",
      "year": 2025,
      "month": "October",
      "date_range": "Aug 21 - 24",
      "start_date": "2025-08-21",
      "end_date": "2025-08-24",
      "purse_text": "$2.75 M",
      "purse_amount": 2750000,
      "points": 500,
      "status": "UPCOMING",
      "winners": "Somi Lee, Jin Hee Im",
      "tournament_url": "https://www.lpga.com/tournaments/caop",
      "ticket_url": "https://tickets.example.com",
      "course": {
        "name": "Silverado Resort (North Course)",
        "location": "Porthcawl, Mid Glamorgan, Wales"
      }
    }
  ],
  "page": 1,
  "page_size": 20,
  "has_more": true
}
```

Example:
```bash
curl "http://localhost:8000/lpga/tournaments?page=1&page_size=20&year=2025"
```

#### . GET /lpga/tournaments/{tournament_id}
Response: single tournament object (same shape as in list).

Example:
```bash
curl "http://localhost:8000/lpga/tournaments/CAOP-2025"
```

#### . GET /lpga/tournaments/{tournament_id}/leaderboard
Returns leaderboard rows for a given tournament.

Query params:
- `page` (default 1)
- `page_size` (default 50, max 200)

Response:
```json
{
  "tournament_id": "NWRK-2025",
  "tournament_name": "Kroger Queen City Championship presented by P&G",
  "start_date": "2025-09-11",
  "end_date": "2025-09-14",
  "status": "COMPLETED",
  "year": 2025,
  "leaderboard": [
    {
      "player_id": 46046,
      "first_name": "Scottie",
      "last_name": "Scheffler",
      "position": "1",
      "to_par": "-19",
      "r1": 70,
      "r2": 68,
      "r3": 64,
      "r4": 67,
      "strokes": 269,
      "points": 500.0,
      "prize_money": "$300,000",
      "country": "USA",
      "player_url": "https://www.lpga.com/athletes/charley-hull/98215/overview"
    }
  ],
  "page": 1,
  "page_size": 50,
  "has_more": false
}
```

Example:
```bash
curl "http://localhost:8000/lpga/tournaments/NWRK-2025/leaderboard?page=1&page_size=50"
```

#### . GET /lpga/players
List players.

Query params:
- `page` (default 1)
- `page_size` (default 20, max 200)

Response:
```json
{
  "players": [
    {
      "id": 46046,
      "first_name": "Scottie",
      "last_name": "Scheffler",
      "age": 29,
      "rookie_year": 2016,
      "year_joined": 2016,
      "country": "United States",
      "image_url": "https://www.lpga.com/-/media/images/lpga/players/l/lopez/gaby/lopez_gaby_25hs_486x486.jpg"
    }
  ],
  "page": 1,
  "page_size": 20,
  "has_more": true
}
```

Example:
```bash
curl "http://localhost:8000/lpga/players?page=1&page_size=20"
```

#### . GET /lpga/players/{player_id}/profile
Get a single player's profile with statistics.

Response:
```json
{
  "id": 46046,
  "first_name": "Scottie",
  "last_name": "Scheffler",
  "age": 29,
  "rookie_year": 2016,
  "year_joined": 2016,
  "country": "United States",
  "starts": 19,
  "cuts_made": 13,
  "top_10": 5,
  "wins": 0,
  "low_round": 65,
  "official_earnings_amount": 728258,
  "cme_points_rank": 45,
  "cme_points": "663.583",
  "image_url": "https://www.lpga.com/-/media/images/lpga/players/l/lopez/gaby/lopez_gaby_25hs_486x486.jpg",
  "tournaments": [
    {
      "tournament_name": "Walmart NW Arkansas Championship presented by P&G",
      "start_date": "2025-09-19",
      "position": "T86",
      "to_par": "-1",
      "official_money_text": "$0",
      "official_money_amount": 0,
      "r1": 70,
      "r2": 0,
      "r3": 0,
      "r4": 0,
      "total": 70,
      "cme_points": 0
    }
  ]
}
```

Example:
```bash
curl "http://localhost:8000/lpga/players/46046/profile"
```


