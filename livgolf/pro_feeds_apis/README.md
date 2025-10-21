# LIV Golf Feeds APIs

## Create a virtual environment:
```bash
python -m venv myenv
myenv\Scripts\activate
```

## Install
```bash
pip install -r requirements.txt
```

## Run
```bash
uvicorn main:app --reload
```

## Available Endpoints

- GET `/livgolf/tournaments` — List tournaments (year filter, optional status filter, pagination)
- GET `/livgolf/tournaments/{tournament_id}` — Get a tournament by id
- GET `/livgolf/tickets` — Get ticket URLs for upcoming tournaments

---

## Endpoint Details

#### . GET /livgolf/tournaments
Query params:
- `year` (required): Tournament year (e.g., 2025)
- `status` (optional): `UPCOMING | COMPLETED`
- `page` (default 1)
- `page_size` (default 20, max 200)

Response:
```json
{
  "tournaments": [
    {
      "id": "18e84cc9-d2f3-4de1-a0cd-956c92073cf1",
      "name": "LIV Golf Invitational Jeddah",
      "year": 2025,
      "start_date": "2025-03-15",
      "end_date": "2025-03-17",
      "status": "Upcoming",
      "tournament_url": "https://www.livgolf.com/schedule/jeddah-2025",
      "ticket_url": "https://events.livgolf.com/jeddah/#tickets",
      "course": {
        "name": "Royal Greens Golf & Country Club",
        "address": "King Abdullah Economic City",
        "city": "Jeddah",
        "country": "Saudi Arabia",
        "zipcode": "23965"
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
curl "http://localhost:8000/livgolf/tournaments?year=2025&status=UPCOMING&page=1&page_size=20"
```

#### . GET /livgolf/tournaments/{tournament_id}
Response: single tournament object (same shape as in list).

Example:
```bash
curl "http://localhost:8000/livgolf/tournaments/18e84cc9-d2f3-4de1-a0cd-956c92073cf1"
```

#### . GET /livgolf/tickets
Get ticket URLs for upcoming tournaments only.

Query params:
- `year` (required): Tournament year (e.g., 2025)
- `page` (default 1)
- `page_size` (default 20, max 200)

Response:
```json
{
  "tickets": [
    {
      "tournament_id": "18e84cc9-d2f3-4de1-a0cd-956c92073cf1",
      "tournament_name": "LIV Golf Invitational Jeddah",
      "year": 2025,
      "start_date": "2025-03-15",
      "end_date": "2025-03-17",
      "ticket_url": "https://events.livgolf.com/jeddah/#tickets"
    }
  ],
  "page": 1,
  "page_size": 20,
  "has_more": true
}
```

Example:
```bash
curl "http://localhost:8000/livgolf/tickets?year=2025&page=1&page_size=20"
```
