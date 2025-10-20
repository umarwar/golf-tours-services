import os
import logging

# Scrapy/Crochet setup
os.environ["SCRAPY_SETTINGS_MODULE"] = "livgolf_scraper.livgolf_scraper.settings"
os.environ["TWISTED_REACTOR"] = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"

from fastapi import FastAPI, HTTPException, Depends, status, Header
from pydantic import BaseModel
from scrapy.crawler import CrawlerRunner
from crochet import setup, wait_for

from livgolf_scraper.livgolf_scraper.spiders.livgolf_upcoming_spider import (
    LivgolfUpcomingSpiderSpider,
)
from models import TournamentsFeedResponse, TournamentModel, CourseModel
from deps import get_supabase_client
from services.tournaments import fetch_tournaments


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
logging.getLogger("scrapy").setLevel(logging.WARNING)
logging.getLogger("twisted").setLevel(logging.WARNING)
logging.getLogger("livgolf_upcoming_spider").setLevel(logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


# Initialize crochet
setup()

app = FastAPI(title="LIV Golf Scrapers API", version="1.0.0")


class TournamentsResponse(BaseModel):
    message: str
    tournaments_processed: int


spider_results: dict = {}
runner = CrawlerRunner()


@wait_for(timeout=300.0)
def run_livgolf_upcoming():
    kwargs = {"results_dict": spider_results}
    return runner.crawl(LivgolfUpcomingSpiderSpider, **kwargs)


async def authorize_request(x_api_key: str = Header(None)):
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="API key required"
        )
    api_key_val = os.environ.get("ACCESS_KEY")
    if x_api_key != api_key_val:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key"
        )


@app.on_event("startup")
async def startup_event():
    try:
        from supabase import create_client

        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            raise Exception("SUPABASE_URL or SUPABASE_KEY not found in environment")

        supabase = create_client(url, key)
        supabase.table("livgolf_tournaments").select("tournament_id").limit(1).execute()
        logging.info("Supabase connection verified successfully (LIV)")
    except Exception as e:
        logging.error(f"Startup error: {e}", exc_info=True)
        raise


# This endpoint is used to scrape the upcoming LIV tournaments
@app.post("/livgolf/scrape/tournaments", response_model=TournamentsResponse)
# async def scrape_livgolf_tournaments(api_key: str = Depends(authorize_request)):
async def scrape_livgolf_tournaments():
    try:
        logging.info("livgolf/scrape/tournaments started")
        spider_results["tournaments"] = 0
        run_livgolf_upcoming()
        tournaments_processed = int(spider_results.get("tournaments", 0))
        if "tournaments" in spider_results:
            del spider_results["tournaments"]
        logging.info(
            f"livgolf/scrape/tournaments completed (tournaments_processed={tournaments_processed})"
        )
        return TournamentsResponse(
            message="Tournaments scraped successfully",
            tournaments_processed=tournaments_processed,
        )
    except Exception as e:
        logging.error(f"Error during LIV tournament scraping: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"LIV tournament scraping failed: {str(e)}"
        )


# This endpoint is used to get the upcoming LIV tournaments from the database
@app.get("/livgolf/tournaments", response_model=TournamentsFeedResponse)
async def get_livgolf_tournaments(
    year: int | None = None, page: int = 1, page_size: int = 20
):
    try:
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 20
        if page_size > 200:
            page_size = 200

        sb = get_supabase_client()
        rows, total = fetch_tournaments(sb, year, page, page_size)

        tournaments: list[TournamentModel] = []
        for r in rows:
            tournaments.append(
                TournamentModel(
                    id=str(r.get("id") or r.get("tournament_id")),
                    name=r.get("tournament_name", ""),
                    year=(int(r["year"]) if r.get("year") is not None else None),
                    start_date=r.get("start_date"),
                    end_date=r.get("end_date"),
                    status=r.get("status"),
                    tournament_url=r.get("tournament_url"),
                    ticket_url=r.get("ticket_url"),
                    course=CourseModel(
                        name=r.get("course_name"),
                        address=r.get("address"),
                        city=r.get("city"),
                        country=r.get("country"),
                        zipcode=r.get("zipcode"),
                    ),
                )
            )

        has_more = False
        if total is not None:
            has_more = (page * page_size) < total
        else:
            has_more = len(rows) == page_size

        return TournamentsFeedResponse(
            tournaments=tournaments,
            page=page,
            page_size=page_size,
            has_more=has_more,
        )
    except Exception as e:
        logging.error(f"Error fetching LIV tournaments: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch LIV tournaments")
