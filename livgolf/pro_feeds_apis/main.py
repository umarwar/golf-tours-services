import logging
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from deps import get_supabase_client
from services.tournaments import (
    fetch_tournaments,
    fetch_tournament_by_id,
    fetch_upcoming_ticket_urls,
)
from models import (
    TournamentsFeedResponse,
    TournamentModel,
    CourseModel,
    TicketUrlResponse,
    TicketUrlItem,
)

app = FastAPI(title="LIV Golf Feeds API", version="1.0.0")


# This endpoint is used to get the LIV tournaments from the database
@app.get("/livgolf/tournaments", response_model=TournamentsFeedResponse)
async def get_livgolf_tournaments(
    year: int = Query(description="Tournament year (e.g., 2025)"),
    status_filter: Optional[str] = Query(
        default=None, alias="status", description="UPCOMING|COMPLETED|IN_PROGRESS"
    ),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
):
    try:
        sb = get_supabase_client()
        rows, total = fetch_tournaments(sb, year, status_filter, page, page_size)

        tournaments: list[TournamentModel] = []
        for r in rows:
            tournaments.append(
                TournamentModel(
                    id=str(r.get("id") or r.get("tournament_id")),
                    name=r.get("tournament_name", ""),
                    year=(int(r["year"]) if r.get("year") is not None else None),
                    start_date=r.get("start_date"),
                    end_date=r.get("end_date"),
                    status=r.get("status"),
                    tournament_url=r.get("tournament_url"),
                    ticket_url=r.get("ticket_url"),
                    course=CourseModel(
                        name=r.get("course_name"),
                        address=r.get("address"),
                        city=r.get("city"),
                        country=r.get("country"),
                        zipcode=r.get("zipcode"),
                    ),
                )
            )

        has_more = False
        if total is not None:
            has_more = (page * page_size) < total
        else:
            has_more = len(rows) == page_size

        return TournamentsFeedResponse(
            tournaments=tournaments,
            page=page,
            page_size=page_size,
            has_more=has_more,
        )
    except Exception as e:
        logging.error(f"Error fetching LIV tournaments: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch LIV tournaments")


# Get tournament by id
@app.get("/livgolf/tournaments/{tournament_id}", response_model=TournamentModel)
async def get_tournament(tournament_id: str):
    try:
        sb = get_supabase_client()
        r = fetch_tournament_by_id(sb, tournament_id)
        if not r:
            raise HTTPException(status_code=404, detail="Not found")

        return TournamentModel(
            id=str(r.get("id") or r.get("tournament_id")),
            name=r.get("tournament_name", ""),
            year=(int(r["year"]) if r.get("year") is not None else None),
            start_date=r.get("start_date"),
            end_date=r.get("end_date"),
            status=r.get("status"),
            tournament_url=r.get("tournament_url"),
            ticket_url=r.get("ticket_url"),
            course=CourseModel(
                name=r.get("course_name"),
                address=r.get("address"),
                city=r.get("city"),
                country=r.get("country"),
                zipcode=r.get("zipcode"),
            ),
        )
    except HTTPException:
        raise
    except Exception as e:
        logging.error(
            f"Error fetching LIV tournament {tournament_id}: {e}", exc_info=True
        )
        raise HTTPException(status_code=500, detail="Failed to fetch LIV tournament")


# Get ticket URLs for upcoming tournaments
@app.get("/livgolf/tickets", response_model=TicketUrlResponse)
async def get_ticket_urls(
    year: int = Query(description="Tournament year (e.g., 2025)"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
):
    try:
        sb = get_supabase_client()
        rows, total = fetch_upcoming_ticket_urls(sb, year, page, page_size)

        ticket_urls: List[TicketUrlItem] = []
        for r in rows:
            ticket_urls.append(
                TicketUrlItem(
                    tournament_id=r.get("tournament_id"),
                    tournament_name=r.get("tournament_name", ""),
                    year=(int(r["year"]) if r.get("year") is not None else None),
                    start_date=(r.get("start_date") or None),
                    end_date=(r.get("end_date") or None),
                    ticket_url=r.get("ticket_url"),
                )
            )

        # Determine has_more
        if total is not None:
            has_more = (page * page_size) < total
        else:
            has_more = len(rows) == page_size

        return TicketUrlResponse(
            tickets=ticket_urls, page=page, page_size=page_size, has_more=has_more
        )
    except Exception as e:
        logging.error(f"Error fetching LIV ticket URLs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch LIV ticket URLs")
