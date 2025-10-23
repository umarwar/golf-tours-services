from typing import Any, Dict, List, Optional, Tuple

from supabase import Client


def fetch_players(
    sb: Client, page: int, page_size: int
) -> Tuple[List[Dict[str, Any]], Optional[int]]:
    base = sb.table("lpga_players_stats").select(
        "player_id,first_name,last_name,age,rookie_year,year_joined,country,country_flag,image_url",
        count="exact",
    )

    start = (page - 1) * page_size
    end = start + page_size - 1

    count_resp = base.range(0, 0).execute()
    total: Optional[int] = getattr(count_resp, "count", None)
    if total is not None and start >= total:
        return [], total

    resp = base.order("player_id", desc=False).range(start, end).execute()
    return resp.data or [], total


def fetch_player_profile(sb: Client, player_id: int) -> Optional[Dict[str, Any]]:
    resp = (
        sb.table("lpga_players_stats")
        .select(
            "player_id,first_name,last_name,age,rookie_year,year_joined,country,country_flag,starts,cuts_made,top_10,wins,low_round,official_earnings_amount,cme_points_rank,cme_points,image_url"
        )
        .eq("player_id", player_id)
        .limit(1)
        .execute()
    )
    rows = resp.data or []
    if not rows:
        return None
    return rows[0]


def fetch_player_tournaments(sb: Client, player_id: int) -> List[Dict[str, Any]]:
    resp = (
        sb.table("lpga_players_tournaments")
        .select(
            "tournament_name,start_date,position,to_par,official_money_text,official_money_amount,r1,r2,r3,r4,total,cme_points"
        )
        .eq("player_id", player_id)
        .order("start_date", desc=True)
        .execute()
    )
    return resp.data or []
