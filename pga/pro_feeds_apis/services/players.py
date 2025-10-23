from typing import Any, Dict, List, Optional, Tuple


def fetch_player_profile(sb, player_id: int) -> Optional[Dict[str, Any]]:
    resp = (
        sb.table("pga_players")
        .select(
            "player_id,first_name,last_name,height,weight,age,birthday,country,country_flag,residence,birth_place,family,college,turned_pro_year,cuts_made,events_played,career_wins,wins_current_year,runner_up,third_place,top_10,top_25,official_money,career_earnings,image_url"
        )
        .eq("player_id", player_id)
        .limit(1)
        .execute()
    )
    rows = resp.data or []
    if not rows:
        return None
    r = rows[0]
    return r


def fetch_players(
    sb, page: int, page_size: int
) -> Tuple[List[Dict[str, Any]], Optional[int]]:
    count_resp = (
        sb.table("pga_players").select("player_id", count="exact").range(0, 0).execute()
    )
    total = getattr(count_resp, "count", None)

    start = (page - 1) * page_size
    end = start + page_size - 1
    if total is not None and start >= total:
        return [], total

    resp = (
        sb.table("pga_players")
        .select(
            "player_id,first_name,last_name,height,weight,age,birthday,country,country_flag,residence,birth_place,family,college,turned_pro_year,image_url"
        )
        .order("player_id", desc=False)
        .range(start, end)
        .execute()
    )

    return resp.data or [], total
