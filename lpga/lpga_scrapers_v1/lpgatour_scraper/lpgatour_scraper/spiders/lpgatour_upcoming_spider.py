import os
import re
import json
import scrapy
from datetime import datetime, date
from urllib.parse import urlencode
from dotenv import load_dotenv, find_dotenv
from supabase import create_client, Client

load_dotenv(find_dotenv())


class LpgatourUpcomingSpiderSpider(scrapy.Spider):
    name = "lpgatour_upcoming_spider"
    allowed_domains = ["lpga.com"]

    custom_settings = {
        "ROBOTSTXT_OBEY": False,
        "CONCURRENT_REQUESTS": 4,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._batch_size = 100
        self._batch: list[dict] = []
        self.supabase: Client | None = None
        # current year, upcoming state
        self.year = int(datetime.utcnow().year)
        self.results_dict = (
            kwargs.get("results_dict", {})
            if isinstance(kwargs.get("results_dict", {}), dict)
            else {}
        )
        self.tournaments_processed = 0

    def start_requests(self):
        self._init_supabase()

        base_url = "https://www.lpga.com/-/tournaments/list"
        # fetch all tournaments for current year
        query = {"state": "all", "year": self.year}
        url = f"{base_url}?{urlencode(query)}"

        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "en-US,en;q=0.9",
            "referer": "https://www.lpga.com/tournaments",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        }

        ZYTE_APIKEY = os.environ.get("ZYTE_API_KEY")
        meta = {"proxy": ZYTE_APIKEY} if ZYTE_APIKEY else {}

        yield scrapy.Request(
            url, headers=headers, callback=self.parse_api, meta=meta, dont_filter=True
        )

    def parse_api(self, response):
        try:
            payload = json.loads(response.text)
        except Exception as e:
            self.logger.error(f"Failed to parse LPGA JSON: {e}")
            return

        result = payload.get("result", {})
        months = result.get("months", [])
        tournaments_emitted = 0

        for month_block in months:
            month_label = month_block.get("month")  # e.g., "October 2025"
            month = self._month_from_label(month_label)
            tournaments = month_block.get("list", [])
            for t in tournaments:
                try:
                    tournament_code = t.get("tournamentCode") or ""
                    name = t.get("name") or ""
                    date_range = t.get("dateRange") or None
                    purse_text = t.get("purse") or None
                    points_text = t.get("points") or None
                    is_complete = bool(t.get("isComplete", False))

                    # Derivations
                    year_int = self._year_from_month(month_label)
                    start_date, end_date = self._parse_date_range(
                        date_range, month_label
                    )
                    purse_amount = self._parse_purse_amount(purse_text)
                    points = self._parse_int(points_text)
                    winners = self._get_winners_text(t)
                    # ticket_url only for upcoming tournaments
                    raw_btn_href = (t.get("buttonLink") or {}).get("href") or None
                    ticket_url = raw_btn_href if not is_complete else None
                    link_href = (t.get("link") or {}).get("href") or ""
                    tournament_url = (
                        f"https://www.lpga.com{link_href}" if link_href else None
                    )
                    logo_url = (t.get("logo") or {}).get("url") or None
                    tournament_logo = (
                        f"https://www.lpga.com{logo_url}" if logo_url else None
                    )
                    leaderboard_results_url = (
                        f"https://www.lpga.com/-/tournaments/results?code={tournament_code}&year={year_int}"
                        if tournament_code and year_int
                        else None
                    )

                    tournament_id = (
                        f"{tournament_code.strip().upper()}-{year_int}"
                        if year_int and tournament_code
                        else tournament_code or name
                    )

                    row = {
                        "tournament_id": tournament_id,
                        "tournament_code": tournament_code,
                        "name": name,
                        "month": month,
                        "year": year_int,
                        "date_range": date_range,
                        "start_date": start_date,
                        "end_date": end_date,
                        "location": t.get("location") or None,
                        "course": t.get("course") or None,
                        "purse_text": purse_text,
                        "purse_amount": purse_amount,
                        "points": points,
                        "winners": winners,
                        "ticket_url": ticket_url,
                        "is_complete": is_complete,
                        "tournament_url": tournament_url,
                        "leaderboard_results_url": leaderboard_results_url,
                        "tournament_logo": tournament_logo,
                    }

                    self._batch.append(row)
                    tournaments_emitted += 1
                    if len(self._batch) >= self._batch_size:
                        self._flush_batch()

                except Exception as e:
                    self.logger.error(
                        f"Error processing LPGA tournament: {e}", exc_info=True
                    )
                    continue

        # Flush remaining
        if self._batch:
            self._flush_batch()
        self.logger.info(f"LPGA tournaments processed: {tournaments_emitted}")
        # Track for API wrappers
        self.tournaments_processed += tournaments_emitted

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
            self.logger.info("Supabase client initialized for LPGA upserts.")
        except Exception as e:
            self.logger.error(f"Failed to init Supabase: {e}")
            self.supabase = None

    def _flush_batch(self):
        if not self._batch:
            return
        if not getattr(self, "supabase", None):
            self.logger.warning(
                f"No Supabase client; dropping batch of {len(self._batch)}"
            )
            self._batch = []
            return
        try:
            self.logger.info(f"Upserting {len(self._batch)} LPGA rows to Supabase")
            max_attempts = 3
            for attempt in range(1, max_attempts + 1):
                try:
                    (
                        self.supabase.table("lpga_tournaments")
                        .upsert(
                            self._batch,
                            on_conflict="tournament_id",
                            returning="minimal",
                        )
                        .execute()
                    )
                    break
                except Exception as up_e:
                    if attempt == max_attempts:
                        raise up_e
                    # Backoff on transient gateway errors (e.g., Cloudflare 52x)
                    backoff_seconds = 2 * attempt
                    self.logger.warning(
                        f"Upsert attempt {attempt} failed; retrying in {backoff_seconds}s"
                    )
                    try:
                        import time

                        time.sleep(backoff_seconds)
                    except Exception:
                        pass
        except Exception as e:
            self.logger.error(f"Supabase upsert failed: {e}")
        finally:
            self._batch = []

    def _year_from_month(self, month_label: str | None) -> int | None:
        if not month_label:
            return None
        m = re.search(r"(\d{4})", month_label)
        return int(m.group(1)) if m else None

    def _month_from_label(self, month_label: str | None) -> str | None:
        if not month_label:
            return None
        # Expecting formats like "October 2025" or "December 2025"
        parts = month_label.split()
        return parts[0] if parts else None

    def _parse_date_range(
        self, date_range: str | None, month_label: str | None
    ) -> tuple[str | None, str | None]:
        if not date_range or not month_label:
            return None, None
        try:
            year = self._year_from_month(month_label)
            if not year:
                return None, None
            s = (
                date_range.replace("\u2013", "-")
                .replace("\u2014", "-")
                .replace("–", "-")
                .replace("—", "-")
            )
            # Oct 1 - 4
            m = re.match(
                r"^(?P<mon1>[A-Za-z]{3})\s+(?P<d1>\d{1,2})\s*-\s*(?P<d2>\d{1,2})$", s
            )
            if m:
                mon1 = datetime.strptime(m.group("mon1"), "%b").month
                d1, d2 = int(m.group("d1")), int(m.group("d2"))
                sd = date(year, mon1, d1).isoformat()
                ed = date(year, mon1, d2).isoformat()
                return sd, ed
            # Oct 30 - Nov 2
            m = re.match(
                r"^(?P<mon1>[A-Za-z]{3})\s+(?P<d1>\d{1,2})\s*-\s*(?P<mon2>[A-Za-z]{3})\s+(?P<d2>\d{1,2})$",
                s,
            )
            if m:
                mon1 = datetime.strptime(m.group("mon1"), "%b").month
                mon2 = datetime.strptime(m.group("mon2"), "%b").month
                d1, d2 = int(m.group("d1")), int(m.group("d2"))
                end_year = year + 1 if mon2 < mon1 else year
                sd = date(year, mon1, d1).isoformat()
                ed = date(end_year, mon2, d2).isoformat()
                return sd, ed
            # Oct 6
            m = re.match(r"^(?P<mon1>[A-Za-z]{3})\s+(?P<d1>\d{1,2})$", s)
            if m:
                mon1 = datetime.strptime(m.group("mon1"), "%b").month
                d1 = int(m.group("d1"))
                sd = date(year, mon1, d1).isoformat()
                return sd, sd
        except Exception:
            return None, None
        return None, None

    def _parse_purse_amount(self, purse_text: str | None) -> float | None:
        if not purse_text:
            return None
        # Examples: "$3.00 M", "$2.10 M", "$11.00 M"
        try:
            cleaned = purse_text.replace("$", "").strip()
            m = re.match(r"^(?P<num>[0-9.,]+)\s*(?P<suffix>[KkMm])?$", cleaned)
            if not m:
                return None
            num = float(m.group("num").replace(",", ""))
            suffix = (m.group("suffix") or "").lower()
            if suffix == "m":
                return int(num * 1_000_000)
            if suffix == "k":
                return int(num * 1_000)
            return int(num)
        except Exception:
            return None

    def _parse_int(self, value: str | None) -> int | None:
        if not value:
            return None
        try:
            return (
                int(re.sub(r"[^0-9]", "", str(value)))
                if re.search(r"\d", str(value))
                else None
            )
        except Exception:
            return None

    def _get_winners_text(self, t: dict) -> str | None:
        winners = t.get("winners") or []
        if not winners:
            return None
        try:
            names = []
            for w in winners:
                name = (w or {}).get("name")
                if name:
                    names.append(str(name).strip())
            return ", ".join(names) if names else None
        except Exception:
            return None

    def closed(self, reason):
        # Defensive: ensure any remaining rows are persisted
        try:
            if getattr(self, "_batch", None):
                self.logger.info("Spider closing — flushing final batch")
                self._flush_batch()
        except Exception:
            pass
        # Report into provided results dict for API wrapper
        try:
            if isinstance(self.results_dict, dict):
                self.results_dict["tournaments"] = int(self.tournaments_processed or 0)
        except Exception:
            pass
        self.logger.info(f"Spider closed: {reason}")
