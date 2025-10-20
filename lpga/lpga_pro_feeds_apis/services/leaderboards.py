from typing import Any, Dict, List, Optional, Tuple

from supabase import Client


LB_SELECT = "player_id,first_name,last_name,position,to_par,r1,r2,r3,r4,strokes,points,prize_money,country_abbr,player_url"


def fetch_leaderboard_rows(
    sb: Client, tournament_id: str, page: int, page_size: int
) -> Tuple[List[Dict[str, Any]], Optional[int]]:
    base = (
        sb.table("lpga_tournament_leaderboards")
        .select(LB_SELECT, count="exact")
        .eq("tournament_id", tournament_id)
        .order("position", desc=False)
    )

    start = (page - 1) * page_size
    end = start + page_size - 1

    count_resp = base.range(0, 0).execute()
    total_count: Optional[int] = getattr(count_resp, "count", None)
    if total_count is not None and start >= total_count:
        return [], total_count

    resp = base.range(start, end).execute()
    return resp.data or [], (
        total_count if total_count is not None else getattr(resp, "count", None)
    )


TRN_SELECT = "tournament_id,name,start_date,end_date,is_complete,year"


def fetch_tournament_header(sb: Client, tournament_id: str) -> Optional[Dict[str, Any]]:
    resp = (
        sb.table("lpga_tournaments")
        .select(TRN_SELECT)
        .eq("tournament_id", tournament_id)
        .limit(1)
        .execute()
    )
    rows: List[Dict[str, Any]] = resp.data or []
    return rows[0] if rows else None
