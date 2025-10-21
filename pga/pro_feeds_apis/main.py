from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query

from deps import authorize_request, get_supabase_client
from models import (
    CourseInfo,
    TournamentOut,
    TournamentsResponse,
    LeaderboardResponse,
    LeaderboardRow,
    CourseStatsResponse,
    CourseStatsCourseInfo,
    CourseStatsRound,
    CourseStatsHole,
    PlayerProfile,
    PlayerStatistics,
    PlayersResponse,
    PlayerListItem,
    TicketUrlResponse,
    TicketUrlItem,
)
from services.tournaments import (
    fetch_tournaments,
    fetch_tournament_by_id,
    fetch_upcoming_ticket_urls,
)
from services.leaderboards import (
    fetch_leaderboard_rows,
    fetch_tournament_header,
    fetch_course_stats_rows,
)
from services.players import fetch_player_profile, fetch_players


app = FastAPI(title="PGA Tour Feeds API", version="1.0.0")


# List tournaments
@app.get("/pga/tournaments", response_model=TournamentsResponse)
async def list_tournaments(
    year: int = Query(description="Tournament year (e.g., 2025)"),
    status_filter: Optional[str] = Query(
        default=None, alias="status", description="UPCOMING|COMPLETED|IN_PROGRESS"
    ),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    # _: None = Depends(authorize_request),
):
    sb = get_supabase_client()
    rows, total = fetch_tournaments(sb, year, status_filter, page, page_size)

    tournaments: List[TournamentOut] = []
    for r in rows:
        tournaments.append(
            TournamentOut(
                id=r.get("tournament_id"),
                name=r.get("tournament_name", ""),
                tournament_name=r.get("tournament_name", ""),
                year=(int(r["year"]) if r.get("year") is not None else None),
                start_date=(r.get("start_date") or None),
                end_date=(r.get("end_date") or None),
                purse_amount=r.get("purse_amount"),
                fedex_cup=r.get("fedex_cup"),
                status=r.get("status"),
                previous_winner=r.get("previous_winner"),
                winner_prize=r.get("winner_prize"),
                tournament_url=r.get("tournament_url"),
                ticket_url=r.get("ticket_url"),
                course=CourseInfo(
                    name=r.get("course_name"),
                    city=r.get("city"),
                    state=r.get("state"),
                    country=r.get("country"),
                ),
            )
        )

    # Determine has_more
    if total is not None:
        has_more = (page * page_size) < total
    else:
        has_more = len(rows) == page_size

    return TournamentsResponse(
        tournaments=tournaments, page=page, page_size=page_size, has_more=has_more
    )


# Get tournament by id
@app.get("/pga/tournaments/{tournament_id}", response_model=TournamentOut)
# async def get_tournament(tournament_id: str, _: None = Depends(authorize_request)):
async def get_tournament(tournament_id: str):
    sb = get_supabase_client()
    r = fetch_tournament_by_id(sb, tournament_id)
    if not r:
        raise HTTPException(status_code=404, detail="Not found")
    return TournamentOut(
        id=r.get("tournament_id"),
        name=r.get("tournament_name", ""),
        tournament_name=r.get("tournament_name", ""),
        year=(int(r["year"]) if r.get("year") is not None else None),
        start_date=(r.get("start_date") or None),
        end_date=(r.get("end_date") or None),
        purse_amount=r.get("purse_amount"),
        fedex_cup=r.get("fedex_cup"),
        status=r.get("status"),
        previous_winner=r.get("previous_winner"),
        winner_prize=r.get("winner_prize"),
        tournament_url=r.get("tournament_url"),
        ticket_url=r.get("ticket_url"),
        course=CourseInfo(
            name=r.get("course_name"),
            city=r.get("city"),
            state=r.get("state"),
            country=r.get("country"),
        ),
    )


# Get leaderboard by tournament id
@app.get(
    "/pga/tournaments/{tournament_id}/leaderboard",
    response_model=LeaderboardResponse,
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
    leaderboard = [LeaderboardRow(**r) for r in rows]
    if total is not None:
        has_more = (page * page_size) < total
    else:
        has_more = len(rows) == page_size

    return LeaderboardResponse(
        tournament_id=header.get("tournament_id"),
        tournament_name=header.get("tournament_name", ""),
        start_date=header.get("start_date"),
        end_date=header.get("end_date"),
        status=header.get("status"),
        year=int(header["year"]) if header.get("year") is not None else None,
        leaderboard=leaderboard,
        page=page,
        page_size=page_size,
        has_more=has_more,
    )


# Get course stats (hole-by-hole)
@app.get(
    "/pga/tournaments/{tournament_id}/hole-statistics",
    response_model=CourseStatsResponse,
)
async def get_course_stats(
    tournament_id: str,
    # _: None = Depends(authorize_request),
):
    sb = get_supabase_client()

    header = fetch_tournament_header(sb, tournament_id)
    if not header:
        raise HTTPException(status_code=404, detail="Not found")

    rows = fetch_course_stats_rows(sb, tournament_id)
    if not rows:
        return CourseStatsResponse(
            tournament_id=header.get("tournament_id"),
            tournament_name=header.get("tournament_name", ""),
            start_date=header.get("start_date"),
            end_date=header.get("end_date"),
            status=header.get("status"),
            year=int(header["year"]) if header.get("year") is not None else None,
            course=CourseStatsCourseInfo(),
            rounds=[],
        )

    first = rows[0]
    course_info = CourseStatsCourseInfo(
        name=first.get("course_name"),
        yardage=first.get("course_yardage"),
        par=first.get("course_par"),
        record=first.get("course_record"),
        fairway=first.get("course_fairway"),
        design=first.get("course_design"),
        established=first.get("course_established"),
    )

    rounds_map: dict[int, list[CourseStatsHole]] = {}
    for r in rows:
        round_no = r.get("round")
        hole_obj = CourseStatsHole(
            number=r.get("hole"),
            par=r.get("par"),
            yards=r.get("yards"),
            eagles=r.get("eagles"),
            birdies=r.get("birdies"),
            pars=r.get("pars"),
            bogeys=r.get("bogeys"),
            double_bogeys=r.get("double_bogeys"),
            scoring_average=(
                float(r["scoring_average"])
                if r.get("scoring_average") is not None
                else None
            ),
            avg_diff=(float(r["avg_diff"]) if r.get("avg_diff") is not None else None),
            rank=r.get("rank"),
        )
        rounds_map.setdefault(round_no, []).append(hole_obj)

    rounds_out: list[CourseStatsRound] = []
    for round_no in sorted(rounds_map.keys()):
        holes_sorted = sorted(rounds_map[round_no], key=lambda h: (h.number or 0))
        rounds_out.append(CourseStatsRound(number=round_no, holes=holes_sorted))

    return CourseStatsResponse(
        tournament_id=header.get("tournament_id"),
        tournament_name=header.get("tournament_name", ""),
        start_date=header.get("start_date"),
        end_date=header.get("end_date"),
        status=header.get("status"),
        year=int(header["year"]) if header.get("year") is not None else None,
        course=course_info,
        rounds=rounds_out,
    )


# List players
@app.get("/pga/players", response_model=PlayersResponse)
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
                height=r.get("height"),
                weight=r.get("weight"),
                age=(int(r["age"]) if r.get("age") is not None else None),
                birthday=r.get("birthday"),
                country=r.get("country"),
                residence=r.get("residence"),
                birth_place=r.get("birth_place"),
                family=r.get("family"),
                college=r.get("college"),
                turned_pro=(
                    int(r["turned_pro_year"])
                    if r.get("turned_pro_year") is not None
                    else None
                ),
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


# Get player profile by player_id
@app.get("/pga/players/{player_id}/profile", response_model=PlayerProfile)
# async def get_player_profile(player_id: int, _: None = Depends(authorize_request)):
async def get_player_profile(player_id: int):
    sb = get_supabase_client()
    r = fetch_player_profile(sb, player_id)
    if not r:
        raise HTTPException(status_code=404, detail="Not found")

    stats = PlayerStatistics(
        events_played=r.get("events_played"),
        career_wins=r.get("career_wins"),
        wins_current_year=r.get("wins_current_year"),
        second_place=r.get("runner_up"),
        third_place=r.get("third_place"),
        top_10=r.get("top_10"),
        top_25=r.get("top_25"),
        cuts_made=(
            r.get("cuts_made") if r.get("cuts_made") not in ("-", "", None) else None
        ),
        official_money=r.get("official_money"),
        career_earnings=r.get("career_earnings"),
    )

    return PlayerProfile(
        id=int(r.get("player_id")),
        first_name=r.get("first_name"),
        last_name=r.get("last_name"),
        height=r.get("height"),
        weight=r.get("weight"),
        age=(int(r["age"]) if r.get("age") is not None else None),
        birthday=r.get("birthday"),
        country=r.get("country"),
        residence=r.get("residence"),
        birth_place=r.get("birth_place"),
        family=r.get("family"),
        college=r.get("college"),
        turned_pro=(
            int(r["turned_pro_year"]) if r.get("turned_pro_year") is not None else None
        ),
        image_url=r.get("image_url"),
        statistics=stats,
    )


# Get ticket URLs for upcoming tournaments
@app.get("/pga/tickets", response_model=TicketUrlResponse)
async def get_ticket_urls(
    year: int = Query(description="Tournament year (e.g., 2025)"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    # _: None = Depends(authorize_request),
):
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
