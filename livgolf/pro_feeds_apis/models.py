from pydantic import BaseModel
from typing import Optional, List


class CourseModel(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    zipcode: Optional[str] = None


class TournamentModel(BaseModel):
    id: str
    name: str
    year: Optional[int] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    status: Optional[str] = None
    tournament_url: Optional[str] = None
    ticket_url: Optional[str] = None
    course: CourseModel


class TournamentsFeedResponse(BaseModel):
    tournaments: List[TournamentModel]
    page: int
    page_size: int
    has_more: bool


class TicketUrlItem(BaseModel):
    tournament_id: str
    tournament_name: str
    year: Optional[int] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    ticket_url: Optional[str] = None


class TicketUrlResponse(BaseModel):
    tickets: List[TicketUrlItem]
    page: int
    page_size: int
    has_more: bool
