from typing import Any, Dict, List, Optional, Tuple

from supabase import Client


SELECT_FIELDS = (
    "tournament_id,tournament_code,name,month,year,date_range,start_date,end_date,"
    "purse_text,purse_amount,points,is_complete,winners,tournament_url,ticket_url,"
    "course,location"
)


def fetch_tournaments(
    sb: Client, year: Optional[int], page: int, page_size: int
) -> Tuple[List[Dict[str, Any]], Optional[int]]:
    base = (
        sb.table("lpga_tournaments")
        .select(SELECT_FIELDS, count="exact")
        .order("start_date", desc=False)
    )
    if year is not None:
        base = base.eq("year", year)

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


def fetch_tournament_by_id(sb: Client, tournament_id: str) -> Optional[Dict[str, Any]]:
    resp = (
        sb.table("lpga_tournaments")
        .select(SELECT_FIELDS)
        .eq("tournament_id", tournament_id)
        .limit(1)
        .execute()
    )
    rows: List[Dict[str, Any]] = resp.data or []
    return rows[0] if rows else None
