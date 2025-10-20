import os
import re
import json
import scrapy
from urllib.parse import urlparse
from dotenv import load_dotenv, find_dotenv
from supabase import create_client, Client

load_dotenv(find_dotenv())


def slugify_name(name):
    # Lowercase, replace spaces with hyphens, remove non-alphanumeric except hyphens
    return re.sub(r"[^a-z0-9-]", "", name.lower().replace(" ", "-") if name else "")


class PgatourLeaderboardSpider(scrapy.Spider):
    name = "pgatour_leaderboard_spider"
    custom_settings = {
        "ROBOTSTXT_OBEY": False,
        "CONCURRENT_REQUESTS": 2,
        "DOWNLOAD_DELAY": 2,
    }
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-language": "en-US,en;q=0.9",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.supabase: Client | None = None
        self._batch: list[dict] = []
        self._batch_size: int = 100
        self.results_dict = kwargs.get("results_dict", {})
        self.players_processed = 0

    def _init_supabase(self):
        if self.supabase is not None:
            return
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            self.logger.error(
                "SUPABASE_URL or SUPABASE_KEY missing; cannot init Supabase"
            )
            return
        try:
            self.supabase = create_client(url, key)
            self.logger.info("Supabase client initialized (leaderboard)")
        except Exception as e:
            self.logger.error(f"Failed to init Supabase: {e}")
            self.supabase = None

    def start_requests(self):
        self._init_supabase()
        ZYTE_APIKEY = os.environ.get("ZYTE_API_KEY")

        tournaments: list[dict] = []
        if self.supabase is not None:
            try:
                resp = (
                    self.supabase.table("pga_tournaments")
                    .select("tournament_id,tournament_url,status")
                    .neq("tournament_url", None)
                    .execute()
                )
                tournaments = resp.data or []
                self.logger.info(
                    f"Loaded {len(tournaments)} tournaments from DB for leaderboard scraping"
                )
            except Exception as e:
                self.logger.error(f"Failed to load tournaments from Supabase: {e}")

        if not tournaments:
            self.logger.warning("No tournaments loaded from DB; nothing to scrape")
            return

        for t in tournaments:
            tournament_url = t.get("tournament_url")
            tournament_id = t.get("tournament_id")
            status = t.get("status")
            if not tournament_url or not tournament_id:
                continue
            url = tournament_url
            yield scrapy.Request(
                url,
                headers=self.headers,
                callback=self.parse_tournament,
                meta={
                    "tournament_url": tournament_url,
                    "tournament_id": tournament_id,
                    "status": status,
                    "proxy": ZYTE_APIKEY,
                },
            )

    def parse_tournament(self, response):
        script_content = response.xpath('//script[@id="__NEXT_DATA__"]/text()').get()

        tournament_id = response.meta.get(
            "tournament_id"
        ) or self.extract_tournament_id_from_url(
            response.meta.get("tournament_url", "")
        )
        if not script_content:
            self.logger.error(f"No __NEXT_DATA__ found for {response.url}")
            return
        try:
            data = json.loads(script_content)
            queries = (
                data.get("props", {})
                .get("pageProps", {})
                .get("dehydratedState", {})
                .get("queries", [])
            )
            # Find players in leaderboard
            players = None
            for q in queries:
                d = q.get("state", {}).get("data", {})
                if (
                    isinstance(d, dict)
                    and "players" in d
                    and isinstance(d["players"], list)
                ):
                    players = d["players"]
                    break
            if players and len(players) > 0:
                for p in players:
                    player = p.get("player", {})
                    scoring = p.get("scoringData", {})
                    player_id = player.get("id")
                    first_name = player.get("firstName", "")
                    last_name = player.get("lastName", "")
                    player_name = player.get("displayName", "")
                    leaderboard_sort_order = p.get("leaderboardSortOrder")
                    if not player_id:
                        continue

                    player_url = ""
                    # Prefer first/last name for URL slug; fallback to display name
                    name_for_slug = (
                        f"{first_name} {last_name}"
                        if (first_name or last_name)
                        else player_name
                    ).strip()
                    if name_for_slug:
                        player_url = f"https://www.pgatour.com/player/{player_id}/{slugify_name(name_for_slug)}"

                    rounds = scoring.get("rounds", [])

                    def as_int(val):
                        try:
                            return int(val)
                        except Exception:
                            return None

                    r1 = as_int(rounds[0]) if len(rounds) > 0 else None
                    r2 = as_int(rounds[1]) if len(rounds) > 1 else None
                    r3 = as_int(rounds[2]) if len(rounds) > 2 else None
                    r4 = as_int(rounds[3]) if len(rounds) > 3 else None

                    total = as_int(scoring.get("total"))
                    strokes = as_int(scoring.get("totalStrokes"))
                    projected = as_int(scoring.get("projected"))
                    position = scoring.get("position", None)
                    score = scoring.get("score", None)
                    thru = scoring.get("thru", None)
                    starting = str(scoring.get("official", "-") or "-")
                    country = player.get("country", None)

                    row = {
                        "tournament_id": tournament_id,
                        "player_id": as_int(player_id),
                        "first_name": first_name or None,
                        "last_name": last_name or None,
                        "leaderboard_sort_order": as_int(leaderboard_sort_order),
                        "position": position,
                        "total": total,
                        "thru": thru,
                        "score": score,
                        "r1": r1,
                        "r2": r2,
                        "r3": r3,
                        "r4": r4,
                        "strokes": strokes,
                        "projected": projected,
                        "starting": starting,
                        "country": country,
                        "player_url": player_url,
                    }

                    self._batch.append(row)
                    self.players_processed += 1
                    if len(self._batch) >= self._batch_size:
                        self._flush_batch()
                return

            self.logger.info(
                f"No leaderboard players found for {response.url}; skipping"
            )
        except Exception as e:
            self.logger.error(f"Error parsing tournament page {response.url}: {e}")

    def closed(self, reason):
        # Flush any remaining rows when spider finishes
        if getattr(self, "_batch", None):
            self.logger.info("Spider closing — flushing final batch")
            self._flush_batch()
        self.logger.info(f"Spider closed: {reason}")
        # Update results summary if provided by API caller
        try:
            if isinstance(self.results_dict, dict):
                self.results_dict["leaderboards"] = self.players_processed
        except Exception:
            pass

    def _flush_batch(self):
        if self.supabase is None:
            if self._batch:
                self.logger.warning(
                    f"Supabase not initialized; dropping {len(self._batch)} leaderboard rows"
                )
                self._batch = []
            return
        if not self._batch:
            return
        try:
            self.logger.info(f"Upserting {len(self._batch)} leaderboard rows")
            (
                self.supabase.table("pga_tournament_leaderboards")
                .upsert(
                    self._batch,
                    on_conflict="tournament_id,player_id",
                    returning="minimal",
                )
                .execute()
            )
            self._batch = []
        except Exception as e:
            self.logger.error(f"Failed to upsert leaderboard batch: {e}")

    def extract_tournament_id_from_url(self, url):
        try:
            parts = urlparse(url).path.strip("/").split("/")
            if len(parts) >= 4:
                return parts[3]
        except Exception:
            pass
        return "-"
