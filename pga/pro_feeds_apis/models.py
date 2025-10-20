from typing import List, Optional
from pydantic import BaseModel


class CourseInfo(BaseModel):
    name: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None


class TournamentOut(BaseModel):
    id: str
    name: str
    year: Optional[int] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    purse_amount: Optional[str] = None
    fedex_cup: Optional[str] = None
    status: Optional[str] = None
    previous_winner: Optional[str] = None
    winner_prize: Optional[str] = None
    tournament_url: Optional[str] = None
    ticket_url: Optional[str] = None
    course: CourseInfo


class TournamentsResponse(BaseModel):
    tournaments: List[TournamentOut]
    page: int
    page_size: int
    has_more: bool


class LeaderboardRow(BaseModel):
    player_id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    position: Optional[str] = None
    total: Optional[int] = None
    thru: Optional[str] = None
    score: Optional[str] = None
    r1: Optional[int] = None
    r2: Optional[int] = None
    r3: Optional[int] = None
    r4: Optional[int] = None
    strokes: Optional[int] = None
    projected: Optional[int] = None
    starting: Optional[str] = None
    country: Optional[str] = None
    player_url: Optional[str] = None


class LeaderboardResponse(BaseModel):
    tournament_id: str
    tournament_name: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    status: Optional[str] = None
    year: Optional[int] = None
    leaderboard: List[LeaderboardRow]
    page: int
    page_size: int
    has_more: bool


class CourseStatsCourseInfo(BaseModel):
    name: Optional[str] = None
    yardage: Optional[str] = None
    par: Optional[int] = None
    record: Optional[int] = None
    fairway: Optional[str] = None
    design: Optional[str] = None
    established: Optional[int] = None


class CourseStatsHole(BaseModel):
    number: int
    par: Optional[int] = None
    yards: Optional[int] = None
    eagles: Optional[int] = None
    birdies: Optional[int] = None
    pars: Optional[int] = None
    bogeys: Optional[int] = None
    double_bogeys: Optional[int] = None
    scoring_average: Optional[float] = None
    avg_diff: Optional[float] = None
    rank: Optional[int] = None


class CourseStatsRound(BaseModel):
    number: int
    holes: List[CourseStatsHole]


class CourseStatsResponse(BaseModel):
    tournament_id: str
    tournament_name: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    status: Optional[str] = None
    year: Optional[int] = None
    course: CourseStatsCourseInfo
    rounds: List[CourseStatsRound]


class PlayerStatistics(BaseModel):
    events_played: Optional[int] = None
    career_wins: Optional[int] = None
    wins_current_year: Optional[int] = None
    second_place: Optional[int] = None
    third_place: Optional[int] = None
    top_10: Optional[int] = None
    top_25: Optional[int] = None
    cuts_made: Optional[int] = None
    official_money: Optional[str] = None
    career_earnings: Optional[str] = None


class PlayerProfile(BaseModel):
    id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    height: Optional[int] = None
    weight: Optional[int] = None
    age: Optional[int] = None
    birthday: Optional[str] = None
    country: Optional[str] = None
    residence: Optional[str] = None
    birth_place: Optional[str] = None
    family: Optional[str] = None
    college: Optional[str] = None
    turned_pro: Optional[int] = None
    image_url: Optional[str] = None
    statistics: PlayerStatistics


class PlayerListItem(BaseModel):
    id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    height: Optional[int] = None
    weight: Optional[int] = None
    age: Optional[int] = None
    birthday: Optional[str] = None
    country: Optional[str] = None
    residence: Optional[str] = None
    birth_place: Optional[str] = None
    family: Optional[str] = None
    college: Optional[str] = None
    turned_pro: Optional[int] = None
    image_url: Optional[str] = None


class PlayersResponse(BaseModel):
    players: List[PlayerListItem]
    page: int
    page_size: int
    has_more: bool
