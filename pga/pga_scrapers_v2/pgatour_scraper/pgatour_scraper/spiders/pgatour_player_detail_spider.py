import os
import json
import scrapy
from datetime import datetime
from dotenv import load_dotenv, find_dotenv
from supabase import create_client, Client

load_dotenv(find_dotenv())


class PgatourPlayerDetailSpider(scrapy.Spider):
    name = "pgatour_player_detail_spider"
    custom_settings = {
        "ROBOTSTXT_OBEY": False,
        "CONCURRENT_REQUESTS": 4,
        "DOWNLOAD_DELAY": 1.5,
        "RETRY_TIMES": 5,
        "DOWNLOAD_TIMEOUT": 30,
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
            self.logger.info("Supabase client initialized (players)")
        except Exception as e:
            self.logger.error(f"Failed to init Supabase: {e}")
            self.supabase = None

    def start_requests(self):
        self._init_supabase()
        ZYTE_APIKEY = os.environ.get("ZYTE_API_KEY")

        if self.supabase is None:
            self.logger.error("Supabase not initialized; cannot load player URLs")
            return

        # Load distinct players from DB view (one URL per player_id)
        urls: list[str] = []
        try:
            resp = (
                self.supabase.table("unique_players")
                .select("player_id,player_url")
                .execute()
            )
            rows = resp.data or []
            for r in rows:
                u = r.get("player_url")
                if u:
                    urls.append(u)
            self.logger.info(f"Loaded {len(urls)} unique player URLs from DB view")
        except Exception as e:
            self.logger.error(f"Failed to load player URLs from DB: {e}")
            return

        for url in urls:
            yield scrapy.Request(
                url,
                headers=self.headers,
                callback=self.parse_player,
                meta={"player_url": url, "proxy": ZYTE_APIKEY},
            )

    def parse_player(self, response):
        script_content = response.xpath('//script[@id="__NEXT_DATA__"]/text()').get()
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

            # Helper to find query by key substring
            def find_query_by_key(key):
                for q in queries:
                    if key in str(q.get("queryKey", [])):
                        return q.get("state", {}).get("data", {})
                return {}

            # Extract from all relevant queries
            player_data = find_query_by_key("player")
            overview_data = find_query_by_key("playerProfileOverview")
            career_data = find_query_by_key("playerProfileCareer")

            # Basic info
            player_bio = player_data.get("playerBio", {})
            first_name_val = player_data.get("firstName", "-")
            last_name_val = player_data.get("lastName", None)
            player_id = player_data.get("id", "-")
            country = player_data.get("country", "-")
            country_flag = player_data.get("countryFlag", "-")
            age = player_bio.get("age", "-")
            birthday = player_bio.get(
                "bornAccessibilityText", player_bio.get("born", "-")
            )
            birthplace = player_bio.get("birthplace", {})
            birth_city = birthplace.get("city", "-")
            birth_state = birthplace.get("state", "-")
            college = player_bio.get("school", "-")
            residence = player_bio.get("residence", {})
            residence_city = residence.get("city", "-")
            residence_state = residence.get("state", "-")
            family = player_bio.get("family", "-")
            turned_pro = player_bio.get("turnedPro", "-")
            career_earnings = player_bio.get("careerEarnings", "-")
            plays_from = player_bio.get("playsFrom", {})
            plays_from_city = plays_from.get("city", "-")
            plays_from_state = plays_from.get("state", "-")
            pronunciation = player_bio.get("pronunciation", "-")

            # Height (inches) and Weight (pounds) as integers
            height_imperial = player_bio.get("heightImperial")
            weight_imperial = player_bio.get("weightImperial")

            # Image URL (from overview)
            image_url = overview_data.get("headshot", {}).get("image", "-")

            # FedExCup Standings, Fall Standings, OWGR (from overview)
            fedex_standings = "-"
            fedex_fall_standings = "-"
            owgr = "-"
            for standing in overview_data.get("profileStandings", []):
                if standing.get("title") == "FedExCup Standings":
                    fedex_standings = standing.get("rank", "-")
                    owgr = standing.get("owgr", "-")
                elif standing.get("title") == "FedExCup Fall Standings":
                    fedex_fall_standings = standing.get("rank", "-")

            # Performance helpers (new JSON)
            performance = overview_data.get("performance", []) or []

            def get_stat_for_season(stat_title: str) -> str | None:
                for entry in performance:
                    if entry.get("tour") == "R":
                        # Assume the list is newest-first; take first occurrence
                        for st in entry.get("stats", []) or []:
                            if st.get("title") == stat_title:
                                return st.get("value")
                return None

            def get_career_stat(stat_title: str) -> str | None:
                for entry in performance:
                    if entry.get("tour") == "R":
                        for st in entry.get("stats", []) or []:
                            if st.get("title") == stat_title:
                                return st.get("career")
                return None

            birth_place = (
                f"{birth_city}, {birth_state}"
                if birth_city != "-" or birth_state != "-"
                else None
            )
            residence_txt = (
                f"{residence_city}, {residence_state}"
                if residence_city != "-" or residence_state != "-"
                else None
            )
            plays_from_txt = (
                f"{plays_from_city}, {plays_from_state}"
                if plays_from_city != "-" or plays_from_state != "-"
                else None
            )

            def to_int_or_none(v):
                try:
                    return int(v)
                except Exception:
                    return None

            def parse_height_to_inches(text: str | None) -> int | None:
                if not text:
                    return None
                try:
                    # Formats like 6'3" or 6' 3"
                    parts = str(text).replace('"', "").replace(" ", "")
                    if "'" in parts:
                        feet, inches = parts.split("'", 1)
                        feet_i = int(feet) if feet.isdigit() else 0
                        inches_i = int(inches) if inches.isdigit() else 0
                        return feet_i * 12 + inches_i
                except Exception:
                    return None
                return None

            row = {
                "player_id": to_int_or_none(player_id),
                "first_name": first_name_val if first_name_val != "-" else None,
                "last_name": last_name_val if last_name_val not in ("-", "") else None,
                "age": to_int_or_none(age),
                "birthday": str(birthday) if birthday != "-" else None,
                "country": country if country != "-" else None,
                "country_flag": country_flag if country_flag != "-" else None,
                "birth_place": birth_place,
                "college": college if college != "-" else None,
                "residence": residence_txt,
                "family": family if family != "-" else None,
                "turned_pro_year": to_int_or_none(turned_pro),
                "career_wins": to_int_or_none(get_career_stat("Wins")) or 0,
                "wins_current_year": to_int_or_none(get_stat_for_season("Wins")) or 0,
                "fedex_cup_standings": to_int_or_none(fedex_standings),
                "fedex_cup_fall_standings": to_int_or_none(fedex_fall_standings),
                "owgr": str(owgr) if owgr != "-" else None,
                "career_earnings": career_earnings if career_earnings != "-" else None,
                "plays_from": plays_from_txt,
                "pronunciation": pronunciation if pronunciation != "-" else None,
                "events_played": to_int_or_none(get_career_stat("Events")),
                "cuts_made": get_career_stat("Cuts Made"),
                "runner_up": to_int_or_none(get_career_stat("Seconds")) or 0,
                "third_place": to_int_or_none(get_career_stat("Thirds")) or 0,
                "top_10": to_int_or_none(get_career_stat("Top 10")) or 0,
                "top_25": to_int_or_none(get_career_stat("Top 25")) or 0,
                "official_money": (
                    get_career_stat("Earnings")
                    if get_career_stat("Earnings") not in ("-", None, "")
                    else None
                ),
                "image_url": image_url if image_url != "-" else None,
                "height": parse_height_to_inches(height_imperial),
                "weight": to_int_or_none(weight_imperial),
            }

            # Buffer and upsert in batches
            self._batch.append(row)
            self.players_processed += 1
            if len(self._batch) >= self._batch_size:
                self._flush_batch()
        except Exception as e:
            self.logger.error(f"Error parsing player page {response.url}: {e}")

    def closed(self, reason):
        if getattr(self, "_batch", None):
            self._flush_batch()
        # Update results summary if provided by API caller
        try:
            if isinstance(self.results_dict, dict):
                self.results_dict["players"] = self.players_processed
        except Exception:
            pass

    def _flush_batch(self):
        if self.supabase is None:
            if self._batch:
                self.logger.warning(
                    f"Supabase not initialized; dropping {len(self._batch)} player rows"
                )
                self._batch = []
            return
        if not self._batch:
            return
        try:
            rows_by_id = {}
            for row in self._batch:
                pid = row.get("player_id")
                if pid is not None:
                    rows_by_id[pid] = row
            rows = list(rows_by_id.values())

            self.logger.info(f"Upserting {len(rows)} players")
            (
                self.supabase.table("pga_players")
                .upsert(rows, on_conflict="player_id", returning="minimal")
                .execute()
            )
            self._batch = []
        except Exception as e:
            self.logger.error(f"Failed to upsert players batch: {e}")
            self._batch = []
