import os
import re
import json
import scrapy
from datetime import datetime
from typing import Iterable
from dotenv import load_dotenv, find_dotenv
from supabase import create_client, Client


load_dotenv(find_dotenv())


class LpgatourLeaderboardSpider(scrapy.Spider):
    name = "lpgatour_leaderboard_spider"
    allowed_domains = ["lpga.com"]

    custom_settings = {
        "ROBOTSTXT_OBEY": False,
        "CONCURRENT_REQUESTS": 2,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._batch_size = 100
        self._batch: list[dict] = []
        self.supabase: Client | None = None
        self.results_dict = (
            kwargs.get("results_dict", {})
            if isinstance(kwargs.get("results_dict", {}), dict)
            else {}
        )
        self.leaderboard_processed = 0

    def start_requests(self) -> Iterable[scrapy.Request]:
        self._init_supabase()
        if not self.supabase:
            self.logger.error("Supabase not configured; aborting leaderboard spider")
            return

        # Fetch tournaments that have a results endpoint stored
        try:
            resp = (
                self.supabase.table("lpga_tournaments")
                .select("tournament_id, leaderboard_results_url")
                .neq("leaderboard_results_url", None)
                .execute()
            )
            rows = (resp.data or []) if hasattr(resp, "data") else []
        except Exception as e:
            self.logger.error(f"Failed to fetch tournaments: {e}")
            return

        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "en-US,en;q=0.9",
            "referer": "https://www.lpga.com/tournaments",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        }

        ZYTE_APIKEY = os.environ.get("ZYTE_API_KEY")
        meta_proxy = {"proxy": ZYTE_APIKEY} if ZYTE_APIKEY else {}

        # For testing purpose
        # rows = [
        #     {
        #         "tournament_id": "LOTT-2025",
        #         "leaderboard_results_url": "https://www.lpga.com/-/tournaments/results?code=LOTT&year=2024",
        #     },
        #     {
        #         "tournament_id": "SHAN-2025",
        #         "leaderboard_results_url": "https://www.lpga.com/-/tournaments/results?code=SHAN&year=2024",
        #     },
        # ]

        for row in rows:
            tournament_id = row.get("tournament_id")
            url = row.get("leaderboard_results_url")
            if not tournament_id or not url:
                continue
            # Some tournaments will have no entries until completed; still request
            yield scrapy.Request(
                url,
                headers=headers,
                callback=self.parse_leaderboard,
                meta={"tournament_id": tournament_id, **meta_proxy},
                dont_filter=True,
            )

    def parse_leaderboard(self, response):
        tournament_id = response.meta.get("tournament_id")
        try:
            payload = json.loads(response.text)
        except Exception as e:
            self.logger.error(f"Failed to parse leaderboard JSON: {e}")
            return

        result = payload.get("result", {})
        tournament_meta = result.get("tournament", {})
        tournament_year = tournament_meta.get("year")
        entries = result.get("entries", [])
        if not entries:
            # Upcoming or no data yet; not an error
            return

        for entry in entries:
            try:
                player = entry.get("player") or {}
                player_id = player.get("playerId")
                if player_id is None:
                    continue

                scores = entry.get("scores") or []
                r1 = self._parse_smallint(scores, 0)
                r2 = self._parse_smallint(scores, 1)
                r3 = self._parse_smallint(scores, 2)
                r4 = self._parse_smallint(scores, 3)

                # player tournaments result URL only if player has a profile URL
                player_url_val = self._player_url(player)
                ptr_url = None
                if (
                    player_url_val
                    and player_id is not None
                    and tournament_year is not None
                ):
                    ptr_url = f"https://www.lpga.com/-/statistics/playertournamentresults?playerId={int(player_id)}&year={int(tournament_year)}"

                row = {
                    "tournament_id": tournament_id,
                    "year": (
                        int(tournament_year) if tournament_year is not None else None
                    ),
                    "player_id": int(player_id),
                    "first_name": player.get("firstName") or None,
                    "last_name": player.get("lastName") or None,
                    "short_name": player.get("shortName") or None,
                    "country_abbr": player.get("countryAbbr") or None,
                    "position": entry.get("position") or None,
                    "to_par": entry.get("toPar"),
                    "r1": r1,
                    "r2": r2,
                    "r3": r3,
                    "r4": r4,
                    "strokes": self._parse_int(entry.get("total")),
                    "points": self._parse_decimal(entry.get("points")),
                    "prize_money": entry.get("prizeMoney") or None,
                    "player_url": player_url_val,
                    "player_tournaments_result_url": ptr_url,
                }

                self._batch.append(row)
                self.leaderboard_processed += 1
                if len(self._batch) >= self._batch_size:
                    self._flush_batch()

            except Exception as e:
                self.logger.error(
                    f"Error processing leaderboard row: {e}", exc_info=True
                )
                continue

    def closed(self, reason):
        try:
            if getattr(self, "_batch", None):
                self.logger.info("Leaderboard spider closing — flushing final batch")
                self._flush_batch()
        except Exception:
            pass
        try:
            if isinstance(self.results_dict, dict):
                self.results_dict["leaderboards"] = int(self.leaderboard_processed or 0)
        except Exception:
            pass
        self.logger.info(f"Leaderboard spider closed: {reason}")

    # Helpers
    def _init_supabase(self):
        if getattr(self, "supabase", None) is not None:
            return
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            self.logger.warning("Supabase env not set; will skip upserts.")
            self.supabase = None
            return
        try:
            self.supabase = create_client(url, key)
            self.logger.info("Supabase client initialized for LPGA leaderboards.")
        except Exception as e:
            self.logger.error(f"Failed to init Supabase: {e}")
            self.supabase = None

    def _flush_batch(self):
        if not self._batch:
            return
        if not getattr(self, "supabase", None):
            self.logger.warning(
                f"No Supabase client; dropping leaderboard batch of {len(self._batch)}"
            )
            self._batch = []
            return
        try:
            self.logger.info(
                f"Upserting {len(self._batch)} LPGA leaderboard rows to Supabase"
            )
            max_attempts = 3
            for attempt in range(1, max_attempts + 1):
                try:
                    (
                        self.supabase.table("lpga_tournament_leaderboards")
                        .upsert(
                            self._batch,
                            on_conflict="tournament_id,player_id",
                            returning="minimal",
                        )
                        .execute()
                    )
                    break
                except Exception as up_e:
                    if attempt == max_attempts:
                        raise up_e
                    backoff_seconds = 2 * attempt
                    self.logger.warning(
                        f"Leaderboard upsert attempt {attempt} failed; retrying in {backoff_seconds}s"
                    )
                    try:
                        import time

                        time.sleep(backoff_seconds)
                    except Exception:
                        pass
        except Exception as e:
            self.logger.error(f"Supabase leaderboard upsert failed: {e}")
        finally:
            self._batch = []

    def _parse_smallint(self, scores: list[str], idx: int) -> int | None:
        try:
            if idx >= len(scores):
                return None
            val = scores[idx]
            if not val or not re.search(r"\d", str(val)):
                return None
            return int(re.sub(r"[^0-9]", "", str(val)))
        except Exception:
            return None

    def _parse_int(self, value) -> int | None:
        try:
            if value is None:
                return None
            return int(str(value))
        except Exception:
            return None

    def _parse_decimal(self, value) -> float | None:
        if not value:
            return None
        try:
            # examples: "500.000"
            return float(str(value).replace(",", ""))
        except Exception:
            return None

    def _player_url(self, player: dict) -> str | None:
        link = (
            (player.get("profileLink") or {}).get("href")
            if isinstance(player, dict)
            else None
        )
        return f"https://www.lpga.com{link}" if link else None
