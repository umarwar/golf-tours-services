from typing import Any, Dict, List, Optional, Tuple

from supabase import Client


SELECT_FIELDS = (
    "id,tournament_name,year,start_date,end_date,course_name,address,city,country,zipcode,"
    "tournament_url,ticket_url,status,tournament_id"
)


def fetch_tournaments(
    sb: Client, year: Optional[int], page: int, page_size: int
) -> Tuple[List[Dict[str, Any]], Optional[int]]:
    base = (
        sb.table("livgolf_tournaments")
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
