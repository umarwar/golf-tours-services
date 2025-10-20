from typing import Any, Dict, List, Optional, Tuple

from supabase import Client


SELECT_FIELDS = (
    "tournament_id,tournament_name,year,start_date,end_date,purse_amount,fedex_cup,status,"
    "previous_winner,winner_prize,tournament_url,ticket_url,course_name,city,state,country"
)


def fetch_tournaments(
    sb: Client, status_filter: Optional[str], page: int, page_size: int
) -> Tuple[List[Dict[str, Any]], Optional[int]]:
    base_query = (
        sb.table("pga_tournaments")
        .select(SELECT_FIELDS, count="exact")
        .order("start_date", desc=False)
    )
    if status_filter:
        base_query = base_query.eq("status", status_filter)

    start = (page - 1) * page_size
    end = start + page_size - 1
    # First, get total count with a minimal range to avoid 416 on out-of-bounds pages
    count_resp = base_query.range(0, 0).execute()
    total_count: Optional[int] = getattr(count_resp, "count", None)

    if total_count is not None and start >= total_count:
        # Out-of-range page: return empty slice with total
        return [], total_count

    resp = base_query.range(start, end).execute()
    return resp.data or [], (
        total_count if total_count is not None else getattr(resp, "count", None)
    )


def fetch_tournament_by_id(sb: Client, tournament_id: str) -> Optional[Dict[str, Any]]:
    resp = (
        sb.table("pga_tournaments")
        .select(SELECT_FIELDS)
        .eq("tournament_id", tournament_id)
        .limit(1)
        .execute()
    )
    rows: List[Dict[str, Any]] = resp.data or []
    return rows[0] if rows else None
