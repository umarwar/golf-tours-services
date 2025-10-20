from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query

from deps import authorize_request, get_supabase_client
from models import (
    CourseInfo,
    TournamentOut,
    TournamentsResponse,
    LeaderboardResponse,
    LeaderboardRow,
    PlayersResponse,
    PlayerListItem,
    PlayerProfile,
    PlayerTournamentRow,
)
from services.tournaments import fetch_tournaments, fetch_tournament_by_id
from services.leaderboards import fetch_leaderboard_rows, fetch_tournament_header
from services.players import (
    fetch_players,
    fetch_player_profile,
    fetch_player_tournaments,
)


app = FastAPI(title="LPGA Feeds API", version="1.0.0")


@app.get("/lpga/tournaments", response_model=TournamentsResponse)
async def list_tournaments(
    year: Optional[int] = Query(default=None, description="Filter by year"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    # _: None = Depends(authorize_request),
):
    sb = get_supabase_client()
    rows, total = fetch_tournaments(sb, year, page, page_size)

    tournaments: List[TournamentOut] = []
    for r in rows:
        tournaments.append(
            TournamentOut(
                id=r.get("tournament_id"),
                name=r.get("name", ""),
                year=(int(r["year"]) if r.get("year") is not None else None),
                month=r.get("month"),
                date_range=r.get("date_range"),
                start_date=r.get("start_date"),
                end_date=r.get("end_date"),
                purse_text=r.get("purse_text"),
                purse_amount=(
                    float(r["purse_amount"])
                    if r.get("purse_amount") is not None
                    else None
                ),
                points=(int(r["points"]) if r.get("points") is not None else None),
                status=("COMPLETE" if r.get("is_complete") else "UPCOMING"),
                winners=r.get("winners"),
                tournament_url=r.get("tournament_url"),
                ticket_url=r.get("ticket_url"),
                course=CourseInfo(name=r.get("course"), location=r.get("location")),
            )
        )

    has_more = False
    if total is not None:
        has_more = (page * page_size) < total
    else:
        has_more = len(rows) == page_size

    return TournamentsResponse(
        tournaments=tournaments, page=page, page_size=page_size, has_more=has_more
    )


@app.get("/lpga/tournaments/{tournament_id}", response_model=TournamentOut)
# async def get_tournament(tournament_id: str, _: None = Depends(authorize_request)):
async def get_tournament(tournament_id: str):
    sb = get_supabase_client()
    r = fetch_tournament_by_id(sb, tournament_id)
    if not r:
        raise HTTPException(status_code=404, detail="Not found")
    return TournamentOut(
        id=r.get("tournament_id"),
        name=r.get("name", ""),
        year=(int(r["year"]) if r.get("year") is not None else None),
        month=r.get("month"),
        date_range=r.get("date_range"),
        start_date=r.get("start_date"),
        end_date=r.get("end_date"),
        purse_text=r.get("purse_text"),
        purse_amount=(
            float(r["purse_amount"]) if r.get("purse_amount") is not None else None
        ),
        points=(int(r["points"]) if r.get("points") is not None else None),
        status=("COMPLETE" if r.get("is_complete") else "UPCOMING"),
        winners=r.get("winners"),
        tournament_url=r.get("tournament_url"),
        ticket_url=r.get("ticket_url"),
        course=CourseInfo(name=r.get("course"), location=r.get("location")),
    )


@app.get(
    "/lpga/tournaments/{tournament_id}/leaderboard", response_model=LeaderboardResponse
)
async def get_leaderboard(
    tournament_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    # _: None = Depends(authorize_request),
):
    sb = get_supabase_client()

    header = fetch_tournament_header(sb, tournament_id)
    if not header:
        raise HTTPException(status_code=404, detail="Not found")

    rows, total = fetch_leaderboard_rows(sb, tournament_id, page, page_size)
    leaderboard = [
        LeaderboardRow(
            player_id=int(r.get("player_id")),
            first_name=r.get("first_name"),
            last_name=r.get("last_name"),
            position=r.get("position"),
            to_par=r.get("to_par"),
            r1=r.get("r1"),
            r2=r.get("r2"),
            r3=r.get("r3"),
            r4=r.get("r4"),
            strokes=r.get("strokes"),
            points=(float(r["points"]) if r.get("points") is not None else None),
            prize_money=r.get("prize_money"),
            country=r.get("country_abbr"),
            player_url=r.get("player_url"),
        )
        for r in rows
    ]

    has_more = False
    if total is not None:
        has_more = (page * page_size) < total
    else:
        has_more = len(rows) == page_size

    return LeaderboardResponse(
        tournament_id=header.get("tournament_id"),
        tournament_name=header.get("name", ""),
        start_date=header.get("start_date"),
        end_date=header.get("end_date"),
        status=("COMPLETE" if header.get("is_complete") else "UPCOMING"),
        year=int(header["year"]) if header.get("year") is not None else None,
        leaderboard=leaderboard,
        page=page,
        page_size=page_size,
        has_more=has_more,
    )


@app.get("/lpga/players", response_model=PlayersResponse)
async def list_players(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    # _: None = Depends(authorize_request),
):
    sb = get_supabase_client()
    rows, total = fetch_players(sb, page, page_size)

    items: list[PlayerListItem] = []
    for r in rows:
        items.append(
            PlayerListItem(
                id=int(r.get("player_id")),
                first_name=r.get("first_name"),
                last_name=r.get("last_name"),
                age=(int(r["age"]) if r.get("age") is not None else None),
                rookie_year=(
                    int(r["rookie_year"]) if r.get("rookie_year") is not None else None
                ),
                year_joined=(
                    int(r["year_joined"]) if r.get("year_joined") is not None else None
                ),
                country=r.get("country"),
                image_url=r.get("image_url"),
            )
        )

    if total is not None:
        has_more = (page * page_size) < total
    else:
        has_more = len(rows) == page_size

    return PlayersResponse(
        players=items, page=page, page_size=page_size, has_more=has_more
    )


@app.get("/lpga/players/{player_id}/profile", response_model=PlayerProfile)
# async def get_player_profile(player_id: int, _: None = Depends(authorize_request)):
async def get_player_profile(player_id: int):
    sb = get_supabase_client()
    s = fetch_player_profile(sb, player_id)
    if not s:
        raise HTTPException(status_code=404, detail="Not found")

    tournaments_rows = fetch_player_tournaments(sb, player_id)
    tournaments: list[PlayerTournamentRow] = []
    for t in tournaments_rows:
        tournaments.append(
            PlayerTournamentRow(
                tournament_name=t.get("tournament_name"),
                start_date=t.get("start_date"),
                position=t.get("position"),
                to_par=t.get("to_par"),
                official_money_text=t.get("official_money_text"),
                official_money_amount=(
                    float(t["official_money_amount"])
                    if t.get("official_money_amount") is not None
                    else None
                ),
                r1=t.get("r1"),
                r2=t.get("r2"),
                r3=t.get("r3"),
                r4=t.get("r4"),
                total=t.get("total"),
                cme_points=(
                    float(t["cme_points"]) if t.get("cme_points") is not None else None
                ),
            )
        )

    return PlayerProfile(
        id=int(s.get("player_id")),
        first_name=s.get("first_name"),
        last_name=s.get("last_name"),
        age=(int(s["age"]) if s.get("age") is not None else None),
        rookie_year=(
            int(s["rookie_year"]) if s.get("rookie_year") is not None else None
        ),
        year_joined=(
            int(s["year_joined"]) if s.get("year_joined") is not None else None
        ),
        country=s.get("country"),
        starts=s.get("starts"),
        cuts_made=s.get("cuts_made"),
        top_10=s.get("top_10"),
        wins=s.get("wins"),
        low_round=s.get("low_round"),
        official_earnings_amount=(
            float(s["official_earnings_amount"])
            if s.get("official_earnings_amount") is not None
            else None
        ),
        cme_points_rank=s.get("cme_points_rank"),
        cme_points=s.get("cme_points"),
        image_url=s.get("image_url"),
        tournaments=tournaments,
    )
