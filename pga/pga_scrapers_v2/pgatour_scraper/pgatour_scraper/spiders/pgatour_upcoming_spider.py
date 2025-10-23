import os
import re
import json
import scrapy
from datetime import datetime, date
from dotenv import load_dotenv, find_dotenv
from supabase import create_client, Client

load_dotenv(find_dotenv())


def slugify(name):
    # Lowercase, replace spaces with hyphens, remove non-alphanumeric except hyphens
    return re.sub(r"[^a-z0-9-]", "", name.lower().replace(" ", "-"))


class PgatourUpcomingSpider(scrapy.Spider):
    name = "pgatour_upcoming_spider"
    start_urls = ["https://www.pgatour.com/schedule"]
    custom_settings = {
        "ROBOTSTXT_OBEY": False,
        "CONCURRENT_REQUESTS": 4,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._batch_size = 100
        self._batch = []
        self.supabase = None
        self.results_dict = kwargs.get("results_dict", {})
        self.tournaments_processed = 0
        self.headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "en-US,en;q=0.9",
            "cache-control": "max-age=0",
            "sec-ch-ua": '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        }

    def _init_supabase(self):
        """Initialize supabase client once. Safe to call multiple times."""
        if getattr(self, "supabase", None) is not None:
            return

        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")

        if not url or not key:
            self.logger.error(
                "SUPABASE_URL or SUPABASE_KEY missing; Supabase client won't be initialized."
            )
            self.supabase = None
            return

        try:
            self.supabase = create_client(url, key)
            self.logger.info("Supabase client initialized; ready to upsert.")
        except Exception as e:
            self.supabase = None
            self.logger.error(
                f"Failed to initialize Supabase client: {e}", exc_info=True
            )

    def start_requests(self):
        self._init_supabase()

        ZYTE_APIKEY = os.environ.get("ZYTE_API_KEY")

        for url in self.start_urls:
            yield scrapy.Request(
                url,
                headers=self.headers,
                callback=self.parse,
                meta={
                    "proxy": ZYTE_APIKEY,
                },
                dont_filter=True,
            )

    def closed(self, reason):
        # Called by Scrapy when the spider closes; flush any remaining rows
        if getattr(self, "_batch", None):
            self.logger.info("Spider closing — flushing final batch")
            self._flush_batch()
        # Update results dictionary for API response
        try:
            if isinstance(self.results_dict, dict):
                self.results_dict["tournaments"] = self.tournaments_processed
        except Exception:
            pass
        self.logger.info(
            f"Spider closed: {reason}. Processed {self.tournaments_processed} tournaments."
        )

    def parse(self, response):
        # Extract JSON data from the __NEXT_DATA__ script tag
        script_content = response.xpath('//script[@id="__NEXT_DATA__"]/text()').get()

        if not script_content:
            self.logger.error("Could not find __NEXT_DATA__ script tag!")
            return

        try:
            data = json.loads(script_content)

            # Navigate to the schedule data
            schedule_data = (
                data.get("props", {})
                .get("pageProps", {})
                .get("dehydratedState", {})
                .get("queries", [])
            )

            # Find the schedule query that contains tournament data
            schedule_query = None
            for query in schedule_data:
                if query.get("queryKey", []) and query["queryKey"][0] == "schedule":
                    schedule_query = query
                    break

            if not schedule_query:
                self.logger.error("Could not find schedule data in JSON!")
                return

            # Extract all tournaments
            tournaments = (
                schedule_query.get("state", {}).get("data", {}).get("tournaments", [])
            )

            self.logger.info(f"Found {len(tournaments)} tournaments")

            # Process all tournaments
            for tournament in tournaments:
                try:
                    # Extract tournament details
                    tournament_name = tournament.get("name", "")
                    display_date = tournament.get("displayDate", "")
                    tournament_id = tournament.get("tournamentId", "")
                    status = tournament.get("status", "")
                    year_value = tournament.get("year", None)
                    month = tournament.get("month", None)

                    try:
                        year_int = int(year_value) if year_value is not None else None
                    except Exception:
                        year_int = None

                    course_data = tournament.get("courseData", {})
                    course = course_data.get("name", "")
                    city = course_data.get("city", "")
                    state = course_data.get("stateCode", "")
                    country = course_data.get("country", "")

                    location_parts = [part for part in [city, state, country] if part]
                    location = ", ".join(location_parts)

                    purse = tournament.get("purse", "")
                    standings = tournament.get("standings", {})
                    fedexcup = standings.get("value", "")

                    champions = tournament.get("champions", [])
                    previous_winner = (
                        champions[0].get("displayName", "") if champions else ""
                    )
                    winner_prize = tournament.get("championEarnings", "")

                    ticketing = tournament.get("ticketing", {})
                    ticket_url = ticketing.get("ticketsUrl", "")

                    # Extract or construct tournament URL
                    tournament_url = f"https://www.pgatour.com/tournaments/{year_int}/{slugify(tournament_name)}/{tournament_id}"

                    # Build tournament logo URL
                    tournament_logo = self._build_logo_url(tournament_id)

                    self.logger.info(
                        f"Extracted tournament: {tournament_name} - Status: {status} - URL: {tournament_url}"
                    )

                    start_date_str, end_date_str = self._parse_date_range(
                        display_date, year_int
                    )
                    row = {
                        "tournament_id": tournament_id,
                        "tournament_name": tournament_name,
                        "year": year_int,
                        "month": month,
                        "start_date": start_date_str,
                        "end_date": end_date_str,
                        "course_name": course,
                        "location": location,
                        "city": city,
                        "state": state,
                        "country": country,
                        "purse_amount": purse,
                        "fedex_cup": fedexcup,
                        "previous_winner": previous_winner,
                        "winner_prize": winner_prize,
                        "tournament_url": tournament_url,
                        "ticket_url": ticket_url,
                        "status": status,
                        "tournament_logo": tournament_logo,
                    }

                    # Buffer and flush in batches
                    self._batch.append(row)
                    self.tournaments_processed += 1
                    if len(self._batch) >= self._batch_size:
                        self._flush_batch()

                except Exception as e:
                    self.logger.error(
                        f"Error processing tournament: {e}", exc_info=True
                    )
                    continue

        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing JSON: {e}")
            return
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            return

    def _parse_date_range(
        self, date_text: str, year_int: int | None
    ) -> tuple[str | None, str | None]:
        """
        Parse strings like "Jul 3 - 6" or "Aug 29 - Sep 1" or "Jul 6" into ISO dates.
        Returns (start_date, end_date) as YYYY-MM-DD strings or (None, None) if unavailable.
        """
        if not date_text or not year_int:
            return None, None

        try:
            parts = date_text.replace("\u2013", "-").replace("\u2014", "-")
            parts = parts.replace("–", "-").replace("—", "-")
            # patterns
            # 1) "Jul 3 - 6"
            m = re.match(
                r"^(?P<mon1>[A-Za-z]{3})\s+(?P<d1>\d{1,2})\s*-\s*(?P<d2>\d{1,2})$",
                parts,
            )
            if m:
                mon1 = m.group("mon1")
                d1 = int(m.group("d1"))
                d2 = int(m.group("d2"))
                month1 = datetime.strptime(mon1, "%b").month
                start_dt = date(year_int, month1, d1)
                end_dt = date(year_int, month1, d2)
                return start_dt.isoformat(), end_dt.isoformat()

            # 2) "Aug 29 - Sep 1"
            m = re.match(
                r"^(?P<mon1>[A-Za-z]{3})\s+(?P<d1>\d{1,2})\s*-\s*(?P<mon2>[A-Za-z]{3})\s+(?P<d2>\d{1,2})$",
                parts,
            )
            if m:
                mon1 = m.group("mon1")
                mon2 = m.group("mon2")
                d1 = int(m.group("d1"))
                d2 = int(m.group("d2"))
                month1 = datetime.strptime(mon1, "%b").month
                month2 = datetime.strptime(mon2, "%b").month
                start_dt = date(year_int, month1, d1)
                # When crossing year boundary (rare for schedule year), handle Dec->Jan
                end_year = year_int + 1 if month2 < month1 else year_int
                end_dt = date(end_year, month2, d2)
                return start_dt.isoformat(), end_dt.isoformat()

            # 3) "Jul 6"
            m = re.match(r"^(?P<mon1>[A-Za-z]{3})\s+(?P<d1>\d{1,2})$", parts)
            if m:
                mon1 = m.group("mon1")
                d1 = int(m.group("d1"))
                month1 = datetime.strptime(mon1, "%b").month
                start_dt = date(year_int, month1, d1)
                return start_dt.isoformat(), start_dt.isoformat()

        except Exception as e:
            self.logger.warning(f"Failed to parse date range '{date_text}': {e}")

        return None, None

    def _build_logo_url(self, tournament_id: str) -> str:
        """
        Build tournament logo URL from tournament ID.
        Example: R2025554 -> https://res.cloudinary.com/pgatour-prod/d_tournaments:logos:R000.png/tournaments/logos/R554.png
        """
        if not tournament_id:
            return ""

        try:
            tournament_code = tournament_id.replace("R2025", "R")

            # Build the Cloudinary URL
            base_url = "https://res.cloudinary.com/pgatour-prod"
            fallback = "d_tournaments:logos:R000.png"
            logo_path = f"tournaments/logos/{tournament_code}"

            return f"{base_url}/{fallback}/{logo_path}.png"
        except Exception as e:
            self.logger.warning(
                f"Failed to build logo URL for tournament {tournament_id}: {e}"
            )
            return ""

    def _flush_batch(self):
        if not getattr(self, "supabase", None):
            self.logger.warning(
                "Supabase client not initialized; skipping upsert (batch size %d)."
                % len(self._batch)
            )
            self._batch = []
            return

        if not self._batch:
            return

        try:
            self.logger.info(f"Upserting {len(self._batch)} rows to Supabase")
            resp = (
                self.supabase.table("pga_tournaments")
                .upsert(self._batch, on_conflict="tournament_id", returning="minimal")
                .execute()
            )
            self.logger.info(f"Supabase upsert response: {resp}")
            self._batch = []
        except Exception as e:
            self.logger.error(f"Error upserting batch to Supabase: {e}")
            self._batch = []
