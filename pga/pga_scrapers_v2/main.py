import os

os.environ["SCRAPY_SETTINGS_MODULE"] = "pgatour_scraper.settings"
os.environ["TWISTED_REACTOR"] = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"

import logging
from fastapi import FastAPI, HTTPException, Depends, status, Header
from pydantic import BaseModel
from scrapy.crawler import CrawlerRunner
from crochet import setup, wait_for
from pgatour_scraper.pgatour_scraper.spiders.pgatour_upcoming_spider import (
    PgatourUpcomingSpider,
)
from pgatour_scraper.pgatour_scraper.spiders.pgatour_leaderboard_spider import (
    PgatourLeaderboardSpider,
)
from pgatour_scraper.pgatour_scraper.spiders.pgatour_player_detail_spider import (
    PgatourPlayerDetailSpider,
)
from pgatour_scraper.pgatour_scraper.spiders.pgatour_course_stats_spider import (
    PgatourCourseStatsSpider,
)

# Configure logging early so Uvicorn shows our logs too
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

# Reduce Scrapy/Twisted noise in API logs
logging.getLogger("scrapy").setLevel(logging.WARNING)
logging.getLogger("twisted").setLevel(logging.WARNING)
logging.getLogger("pgatour_upcoming_spider").setLevel(logging.WARNING)
logging.getLogger("pgatour_leaderboard_spider").setLevel(logging.WARNING)
logging.getLogger("pgatour_player_detail_spider").setLevel(logging.WARNING)
logging.getLogger("pgatour_course_stats_spider").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

# Initialize crochet
setup()

app = FastAPI(title="PGA Tour Scrapers API", version="1.0.0")


# Response models (endpoint-specific minimal payloads)
class TournamentsResponse(BaseModel):
    message: str
    tournaments_processed: int


class LeaderboardsResponse(BaseModel):
    message: str
    leaderboard_processed: int


class PlayersResponse(BaseModel):
    message: str
    players_processed: int


class CourseStatsResponse(BaseModel):
    message: str
    course_stats_processed: int


# Global results storage
spider_results = {}

# Crawler runner
runner = CrawlerRunner()


@wait_for(timeout=100.0)
def run_upcoming_spider():
    return runner.crawl(PgatourUpcomingSpider, results_dict=spider_results)


# 30 minutes timeout for long-running scrapers
@wait_for(timeout=1800.0)
def run_leaderboard_spider():
    return runner.crawl(PgatourLeaderboardSpider, results_dict=spider_results)


@wait_for(timeout=1800.0)
def run_player_detail_spider():
    return runner.crawl(PgatourPlayerDetailSpider, results_dict=spider_results)


@wait_for(timeout=1800.0)
def run_course_stats_spider():
    return runner.crawl(PgatourCourseStatsSpider, results_dict=spider_results)


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
        # Test Supabase connection
        from supabase import create_client

        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")

        if not url or not key:
            raise Exception("SUPABASE_URL or SUPABASE_KEY not found in environment")

        supabase = create_client(url, key)
        # Test connection with a simple query
        supabase.table("pga_tournaments").select("tournament_id").limit(1).execute()
        logging.info("Supabase connection verified successfully")

    except Exception as e:
        logging.error(f"Startup error: {e}", exc_info=True)
        raise


@app.post("/pga/scrape/tournaments", response_model=TournamentsResponse)
# async def scrape_tournaments(api_key: str = Depends(authorize_request)):
async def scrape_tournaments():
    """Scrape upcoming and completed tournaments"""
    try:
        logging.info("pga/scrape/tournaments started")
        spider_results["tournaments"] = 0
        run_upcoming_spider()
        tournaments_processed = spider_results.get("tournaments", 0)
        del spider_results["tournaments"]

        logging.info(
            f"pga/scrape/tournaments completed (tournaments_processed={tournaments_processed})"
        )
        return TournamentsResponse(
            message="Tournaments scraped successfully",
            tournaments_processed=tournaments_processed,
        )
    except Exception as e:
        logging.error(f"Error during tournament scraping: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Tournament scraping failed: {str(e)}"
        )


@app.post("/pga/scrape/leaderboards", response_model=LeaderboardsResponse)
# async def scrape_leaderboards(api_key: str = Depends(authorize_request)):
async def scrape_leaderboards():
    """Scrape tournament leaderboards"""
    try:
        logging.info("pga/scrape/leaderboards started")
        spider_results["leaderboards"] = 0
        run_leaderboard_spider()
        leaderboard_processed = spider_results.get("leaderboards", 0)
        del spider_results["leaderboards"]

        logging.info(
            f"pga/scrape/leaderboards completed (leaderboard_processed={leaderboard_processed})"
        )
        return LeaderboardsResponse(
            message="Leaderboards scraped successfully",
            leaderboard_processed=leaderboard_processed,
        )
    except Exception as e:
        logging.error(f"Error during leaderboard scraping: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Leaderboard scraping failed: {str(e)}"
        )


@app.post("/pga/scrape/players", response_model=PlayersResponse)
# async def scrape_players(api_key: str = Depends(authorize_request)):
async def scrape_players():
    """Scrape player details (this may take 15-20 minutes)"""
    try:
        logging.info("pga/scrape/players started")
        spider_results["players"] = 0
        run_player_detail_spider()
        players_processed = spider_results.get("players", 0)
        del spider_results["players"]

        logging.info(
            f"pga/scrape/players completed (players_processed={players_processed})"
        )
        return PlayersResponse(
            message="Player details scraped successfully",
            players_processed=players_processed,
        )
    except Exception as e:
        logging.error(f"Error during player scraping: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Player scraping failed: {str(e)}")


@app.post("/pga/scrape/course-stats", response_model=CourseStatsResponse)
# async def scrape_course_stats(api_key: str = Depends(authorize_request)):
async def scrape_course_stats():
    """Scrape course statistics"""
    try:
        logging.info("pga/scrape/course-stats started")
        spider_results["course_stats"] = 0
        run_course_stats_spider()
        course_stats_processed = spider_results.get("course_stats", 0)
        del spider_results["course_stats"]

        logging.info(
            f"pga/scrape/course-stats completed (course_stats_processed={course_stats_processed})"
        )
        return CourseStatsResponse(
            message="Course statistics scraped successfully",
            course_stats_processed=course_stats_processed,
        )
    except Exception as e:
        logging.error(f"Error during course stats scraping: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Course stats scraping failed: {str(e)}"
        )


## @app.post("/scrape/all", response_model=ScraperResponse)
## async def scrape_all(api_key: str = Depends(authorize_request)):
##     """Run all scrapers in sequence (this may take 30+ minutes)"""
##     try:
##         results = {
##             "tournaments_processed": 0,
##             "players_processed": 0,
##             "course_stats_processed": 0,
##         }
##
##         # 1. Scrape tournaments first
##         logging.info("Starting tournament scraping...")
##         spider_results["tournaments"] = 0
##         run_upcoming_spider()
##         results["tournaments_processed"] = spider_results.get("tournaments", 0)
##         del spider_results["tournaments"]
##
##         # 2. Scrape leaderboards
##         logging.info("Starting leaderboard scraping...")
##         spider_results["leaderboards"] = 0
##         run_leaderboard_spider()
##         results["players_processed"] = spider_results.get("leaderboards", 0)
##         del spider_results["leaderboards"]
##
##         # 3. Scrape player details
##         logging.info("Starting player detail scraping...")
##         spider_results["players"] = 0
##         run_player_detail_spider()
##         results["players_processed"] = spider_results.get("players", 0)
##         del spider_results["players"]
##
##         # 4. Scrape course stats
##         logging.info("Starting course stats scraping...")
##         spider_results["course_stats"] = 0
##         run_course_stats_spider()
##         results["course_stats_processed"] = spider_results.get("course_stats", 0)
##         del spider_results["course_stats"]
##
##         return ScraperResponse(message="All scrapers completed successfully", **results)
##     except Exception as e:
##         logging.error(f"Error during full scraping: {e}", exc_info=True)
##         raise HTTPException(status_code=500, detail=f"Full scraping failed: {str(e)}")
