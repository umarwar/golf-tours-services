# PGA Tour Feeds APIs

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

- GET `/pga/tournaments` — List tournaments (optional status filter, pagination)
- GET `/pga/tournaments/{tournament_id}` — Get a tournament by id
- GET `/pga/tournaments/{tournament_id}/leaderboard` — Get leaderboard rows (pagination)
- GET `/pga/tournaments/{tournament_id}/hole-statistics` — Get hole-by-hole course stats
- GET `/pga/players` — List players (pagination)
- GET `/pga/players/{player_id}/profile` — Get a player's profile

---

## Endpoint Details

#### . GET /pga/tournaments
Query params:
- `status` (optional): `UPCOMING | COMPLETED | IN_PROGRESS`
- `page` (default 1)
- `page_size` (default 20, max 200)

Response:
```json
{
  "tournaments": [
    {
      "id": "R2025464",
      "name": "Procore Championship",
      "year": 2025,
      "start_date": "2025-09-11",
      "end_date": "2025-09-14",
      "purse_amount": "$6,000,000",
      "fedex_cup": "500 pts",
      "status": "UPCOMING",
      "previous_winner": "Patton Kizzire",
      "winner_prize": "$1,080,000",
      "tournament_url": "https://www.pgatour.com/tournaments/r464",
      "ticket_url": "https://am.ticketmaster.com/pganapa",
      "course": {
        "name": "Silverado Resort (North Course)",
        "city": "Napa",
        "state": "CA",
        "country": "United States of America"
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
curl "http://localhost:8000/pga/tournaments?page=1&page_size=20"
```

#### . GET /pga/tournaments/{tournament_id}
Response: single tournament object (same shape as in list).

Example:
```bash
curl "http://localhost:8000/pga/tournaments/R2025464"
```

#### . GET /pga/tournaments/{tournament_id}/leaderboard
Returns leaderboard rows for a given tournament.

Query params:
- `page` (default 1)
- `page_size` (default 50, max 200)

Response:
```json
{
  "tournament_id": "R2025464",
  "tournament_name": "Procore Championship",
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
      "total": -19,
      "thru": "F",
      "score": "-5",
      "r1": 70,
      "r2": 68,
      "r3": 64,
      "r4": 67,
      "strokes": 269,
      "projected": null,
      "starting": "-",
      "country": "USA",
      "player_url": "https://www.pgatour.com/player/46046/scottie-scheffler"
    }
  ],
  "page": 1,
  "page_size": 50,
  "has_more": false
}
```

Example:
```bash
curl "http://localhost:8000/pga/tournaments/R2025464/leaderboard?page=1&page_size=50"
```

#### . GET /pga/tournaments/{tournament_id}/hole-statistics
Returns hole-by-hole course statistics for a tournament.

Response:
```json
{
  "tournament_id": "R2025464",
  "tournament_name": "Procore Championship",
  "start_date": "2025-09-11",
  "end_date": "2025-09-14",
  "status": "COMPLETED",
  "year": 2025,
  "course": {
    "name": "Silverado Resort (North Course)",
    "yardage": "7138",
    "par": 72,
    "record": 269,
    "fairway": "Miscellaneous",
    "design": "Robert Trent-Jones JR.",
    "established": 1966
  },
  "rounds": [
    {
      "number": 1,
      "holes": [
        {
          "number": 1,
          "par": 4,
          "yards": 436,
          "eagles": 1,
          "birdies": 27,
          "pars": 99,
          "bogeys": 15,
          "double_bogeys": 1,
          "scoring_average": 3.94,
          "avg_diff": -0.06,
          "rank": 11
        }
      ]
    }
  ]
}
```

Example:
```bash
curl "http://localhost:8000/pga/tournaments/R2025464/hole-statistics"
```


#### . GET /pga/players
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
      "height": 75,
      "weight": 200,
      "age": 29,
      "birthday": "June 21, 1996",
      "country": "United States",
      "residence": "Dallas, Texas",
      "birth_place": "Ridgewood, New Jersey",
      "family": "Wife, Meredith; Bennett",
      "college": "University of Texas",
      "turned_pro": 2018,
      "image_url": "https://pga-tour-res.cloudinary.com/image/upload/c_thumb,g_face,w_280,h_350,z_0.7/headshots_46046.jpg"
    }
  ],
  "page": 1,
  "page_size": 20,
  "has_more": true
}
```

Example:
```bash
curl "http://localhost:8000/pga/players?page=1&page_size=20"
```


#### . GET /pga/players/{player_id}/profile
Get a single player's profile with statistics.

Response:
```json
{
  "id": 46046,
  "first_name": "Scottie",
  "last_name": "Scheffler",
  "height": 75,
  "weight": 200,
  "age": 29,
  "birthday": "June 21, 1996",
  "country": "United States",
  "residence": "Dallas, Texas",
  "birth_place": "Ridgewood, New Jersey",
  "family": "Wife, Meredith; Bennett",
  "college": "University of Texas",
  "turned_pro": 2018,
  "image_url": "https://pga-tour-res.cloudinary.com/image/upload/c_thumb,g_face,w_280,h_350,z_0.7/headshots_46046.jpg",
  "statistics": {
    "events_played": 22,
    "career_wins": 19,
    "wins_current_year": 6,
    "second_place": 0,
    "third_place": 0,
    "top_10": 1,
    "top_25": 3,
    "cuts_made": 11,
    "official_money": "$8,523,672",
    "career_earnings": "$99,453,136"
  }
}
```

Example:
```bash
curl "http://localhost:8000/pga/players/46046/profile"
```

### For GCP deployment 
Run deploy.sh file

