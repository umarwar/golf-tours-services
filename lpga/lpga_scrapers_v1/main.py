import os
import logging

os.environ["SCRAPY_SETTINGS_MODULE"] = "lpgatour_scraper.settings"
os.environ["TWISTED_REACTOR"] = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"

from fastapi import FastAPI, HTTPException, Depends, status, Header
from pydantic import BaseModel
from scrapy.crawler import CrawlerRunner
from crochet import setup, wait_for

from lpgatour_scraper.lpgatour_scraper.spiders.lpgatour_upcoming_spider import (
    LpgatourUpcomingSpiderSpider,
)
from lpgatour_scraper.lpgatour_scraper.spiders.lpgatour_leaderboard_spider import (
    LpgatourLeaderboardSpider,
)
from lpgatour_scraper.lpgatour_scraper.spiders.lpgatour_player_profile_spider import (
    LpgatourPlayerProfileSpider,
)


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
logging.getLogger("scrapy").setLevel(logging.WARNING)
logging.getLogger("twisted").setLevel(logging.WARNING)
logging.getLogger("lpgatour_upcoming_spider").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


# Initialize crochet
setup()

app = FastAPI(title="LPGA Scrapers API", version="1.0.0")


class TournamentsResponse(BaseModel):
    message: str
    tournaments_processed: int


class LeaderboardsResponse(BaseModel):
    message: str
    leaderboards_processed: int


class PlayersResponse(BaseModel):
    message: str
    players_processed: int
    stats_upserts: int | None = None
    tournaments_upserts: int | None = None


spider_results: dict = {}
runner = CrawlerRunner()


@wait_for(timeout=180.0)
def run_lpga_upcoming():
    kwargs = {"results_dict": spider_results}
    return runner.crawl(LpgatourUpcomingSpiderSpider, **kwargs)


@wait_for(timeout=1800.0)
def run_lpga_leaderboards():
    kwargs = {"results_dict": spider_results}
    return runner.crawl(LpgatourLeaderboardSpider, **kwargs)


@wait_for(timeout=3600.0)
def run_lpga_players():
    kwargs = {"results_dict": spider_results}
    return runner.crawl(LpgatourPlayerProfileSpider, **kwargs)


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
        supabase.table("lpga_tournaments").select("tournament_id").limit(1).execute()
        logging.info("Supabase connection verified successfully (LPGA)")
    except Exception as e:
        logging.error(f"Startup error: {e}", exc_info=True)
        raise


@app.post("/lpga/scrape/tournaments", response_model=TournamentsResponse)
# async def scrape_lpga_tournaments(api_key: str = Depends(authorize_request)):
async def scrape_lpga_tournaments():
    try:
        logging.info("lpga/scrape/tournaments started")
        spider_results["tournaments"] = 0
        run_lpga_upcoming()
        tournaments_processed = int(spider_results.get("tournaments", 0))
        if "tournaments" in spider_results:
            del spider_results["tournaments"]
        logging.info(
            f"lpga/scrape/tournaments completed (tournaments_processed={tournaments_processed})"
        )
        return TournamentsResponse(
            message="Tournaments scraped successfully",
            tournaments_processed=tournaments_processed,
        )
    except Exception as e:
        logging.error(f"Error during LPGA tournament scraping: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"LPGA tournament scraping failed: {str(e)}"
        )


@app.post("/lpga/scrape/leaderboards", response_model=LeaderboardsResponse)
# async def scrape_lpga_leaderboards(api_key: str = Depends(authorize_request)):
async def scrape_lpga_leaderboards():
    try:
        logging.info("lpga/scrape/leaderboards started")
        spider_results["leaderboards"] = 0
        run_lpga_leaderboards()
        leaderboards_processed = int(spider_results.get("leaderboards", 0))
        if "leaderboards" in spider_results:
            del spider_results["leaderboards"]
        logging.info(
            f"lpga/scrape/leaderboards completed (leaderboards_processed={leaderboards_processed})"
        )
        return LeaderboardsResponse(
            message="Leaderboards scraped successfully",
            leaderboards_processed=leaderboards_processed,
        )
    except Exception as e:
        logging.error(f"Error during LPGA leaderboard scraping: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"LPGA leaderboard scraping failed: {str(e)}"
        )


@app.post("/lpga/scrape/players", response_model=PlayersResponse)
# async def scrape_lpga_players(api_key: str = Depends(authorize_request)):
async def scrape_lpga_players():
    try:
        logging.info("lpga/scrape/players started")
        spider_results["players"] = 0
        spider_results["stats_upserts"] = 0
        spider_results["tournaments_upserts"] = 0
        run_lpga_players()
        players_processed = int(spider_results.get("players", 0))
        stats_upserts = int(spider_results.get("stats_upserts", 0))
        tournaments_upserts = int(spider_results.get("tournaments_upserts", 0))
        for k in ["players", "stats_upserts", "tournaments_upserts"]:
            if k in spider_results:
                del spider_results[k]
        logging.info(
            f"lpga/scrape/players completed (players_processed={players_processed}, "
            f"stats_upserts={stats_upserts}, tournaments_upserts={tournaments_upserts})"
        )
        return PlayersResponse(
            message="Players scraped successfully",
            players_processed=players_processed,
            stats_upserts=stats_upserts,
            tournaments_upserts=tournaments_upserts,
        )
    except Exception as e:
        logging.error(f"Error during LPGA players scraping: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"LPGA players scraping failed: {str(e)}"
        )
