from typing import Any, Dict, List, Optional, Tuple

from supabase import Client


LB_SELECT = "player_id,first_name,last_name,position,total,thru,score,r1,r2,r3,r4,strokes,projected,starting,country,country_flag,player_url,leaderboard_sort_order"


def fetch_leaderboard_rows(
    sb: Client, tournament_id: str, page: int, page_size: int
) -> Tuple[List[Dict[str, Any]], Optional[int]]:
    base = (
        sb.table("pga_tournament_leaderboards")
        .select(LB_SELECT, count="exact")
        .eq("tournament_id", tournament_id)
        .order("leaderboard_sort_order", desc=False)
    )

    start = (page - 1) * page_size
    end = start + page_size - 1

    # Get count via minimal range to avoid out-of-bounds 416
    count_resp = base.range(0, 0).execute()
    total_count: Optional[int] = getattr(count_resp, "count", None)
    if total_count is not None and start >= total_count:
        return [], total_count

    resp = base.range(start, end).execute()
    return resp.data or [], (
        total_count if total_count is not None else getattr(resp, "count", None)
    )


TRN_SELECT = "tournament_id,tournament_name,start_date,end_date,status,year"


def fetch_tournament_header(sb: Client, tournament_id: str) -> Optional[Dict[str, Any]]:
    resp = (
        sb.table("pga_tournaments")
        .select(TRN_SELECT)
        .eq("tournament_id", tournament_id)
        .limit(1)
        .execute()
    )
    rows: List[Dict[str, Any]] = resp.data or []
    return rows[0] if rows else None


COURSE_STATS_SELECT = (
    "course_name,round,hole,par,yards,scoring_average,avg_diff,rank,"
    "eagles,birdies,pars,bogeys,double_bogeys,course_par,course_yardage,course_record,"
    "course_fairway,course_rough,course_green,course_established,course_design"
)


def fetch_course_stats_rows(sb: Client, tournament_id: str) -> List[Dict[str, Any]]:
    resp = (
        sb.table("pga_course_stats")
        .select(COURSE_STATS_SELECT)
        .eq("tournament_id", tournament_id)
        .order("round", desc=False)
        .order("hole", desc=False)
        .execute()
    )
    return resp.data or []
