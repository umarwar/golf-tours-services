from typing import List, Optional
from pydantic import BaseModel


class CourseInfo(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None


class TournamentOut(BaseModel):
    id: str
    name: str
    year: Optional[int] = None
    month: Optional[str] = None
    date_range: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    purse_text: Optional[str] = None
    purse_amount: Optional[float] = None
    points: Optional[int] = None
    status: Optional[str] = None
    winners: Optional[str] = None
    tournament_url: Optional[str] = None
    tournament_logo: Optional[str] = None
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
    to_par: Optional[str] = None
    r1: Optional[int] = None
    r2: Optional[int] = None
    r3: Optional[int] = None
    r4: Optional[int] = None
    strokes: Optional[int] = None
    points: Optional[float] = None
    prize_money: Optional[str] = None
    country_flag: Optional[str] = None
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


class PlayerListItem(BaseModel):
    id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    age: Optional[int] = None
    rookie_year: Optional[int] = None
    year_joined: Optional[int] = None
    country: Optional[str] = None
    country_flag: Optional[str] = None
    image_url: Optional[str] = None


class PlayersResponse(BaseModel):
    players: List[PlayerListItem]
    page: int
    page_size: int
    has_more: bool


class PlayerTournamentRow(BaseModel):
    tournament_name: Optional[str] = None
    start_date: Optional[str] = None
    position: Optional[str] = None
    to_par: Optional[str] = None
    official_money_text: Optional[str] = None
    official_money_amount: Optional[float] = None
    r1: Optional[int] = None
    r2: Optional[int] = None
    r3: Optional[int] = None
    r4: Optional[int] = None
    total: Optional[int] = None
    cme_points: Optional[float] = None


class PlayerProfile(BaseModel):
    id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    age: Optional[int] = None
    rookie_year: Optional[int] = None
    year_joined: Optional[int] = None
    country: Optional[str] = None
    country_flag: Optional[str] = None
    starts: Optional[int] = None
    cuts_made: Optional[int] = None
    top_10: Optional[int] = None
    wins: Optional[int] = None
    low_round: Optional[int] = None
    official_earnings_amount: Optional[float] = None
    cme_points_rank: Optional[int] = None
    cme_points: Optional[str] = None
    image_url: Optional[str] = None
    tournaments: List[PlayerTournamentRow]


class TicketUrlItem(BaseModel):
    tournament_id: str
    tournament_name: str
    year: Optional[int] = None
    month: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    ticket_url: Optional[str] = None
    tournament_logo: Optional[str] = None


class TicketUrlResponse(BaseModel):
    tickets: List[TicketUrlItem]
    page: int
    page_size: int
    has_more: bool
