import os
import re
import json
import scrapy
from datetime import datetime
import logging
from dotenv import load_dotenv, find_dotenv
from supabase import create_client, Client


load_dotenv(find_dotenv())


class LivgolfUpcomingSpiderSpider(scrapy.Spider):
    name = "livgolf_upcoming_spider"
    allowed_domains = ["livgolf.com"]

    custom_settings = {
        "ROBOTSTXT_OBEY": False,
        "CONCURRENT_REQUESTS": 4,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        self._batch_size = 100
        self._batch: list[dict] = []
        self.supabase: Client | None = None
        self.tournaments_processed = 0
        self.results_dict = (
            kwargs.get("results_dict", {})
            if isinstance(kwargs.get("results_dict", {}), dict)
            else {}
        )

    def start_requests(self):
        self._init_supabase()

        url = "https://www.livgolf.com/schedule"

        headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "accept-language": "en-US,en;q=0.9",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
            "referer": "https://www.livgolf.com/",
        }

        ZYTE_APIKEY = os.environ.get("ZYTE_API_KEY")
        meta = {"proxy": ZYTE_APIKEY} if ZYTE_APIKEY else {}

        yield scrapy.Request(
            url,
            headers=headers,
            callback=self.parse_schedule,
            meta=meta,
            dont_filter=True,
        )

    def parse_schedule(self, response):
        text = response.text

        joined = self._extract_joined_stream(text)
        search_space = joined if joined else text

        schedule = self._extract_schedule_container(search_space)
        if not schedule:
            initial_data = self._extract_last_initial_data(search_space)
            if not initial_data:
                candidates = self._extract_all_initial_data(search_space)
                initial_data = candidates[-1] if candidates else None
            if initial_data:
                schedule = self._scan_for_schedule(initial_data)
        if not schedule:
            self.logger.error(
                "scheduleListEvents not found on LIV schedule page; aborting"
            )
            return

        container = schedule.get("scheduleListEvents", {})
        upcoming = container.get("upcomingEvents", []) or []

        emitted = 0
        for event in upcoming:
            try:
                row = self._map_event_to_row(event)
                if not row:
                    continue
                self._batch.append(row)
                emitted += 1
                if len(self._batch) >= self._batch_size:
                    self._flush_batch()
            except Exception as e:
                self.logger.error(f"Error processing LIV event: {e}", exc_info=True)
                continue

        if self._batch:
            self._flush_batch()
        self.tournaments_processed += emitted
        self.logger.info(f"LIV tournaments processed: {emitted}")

    # Mapping helpers
    def _map_event_to_row(self, event: dict) -> dict | None:
        if not isinstance(event, dict):
            return None

        tournament_id = event.get("_entityId")  # UUID
        if not tournament_id:
            return None

        fields = event.get("fields", {}) or {}
        references = event.get("references", {}) or {}
        tags = event.get("tags", []) or []
        slug = event.get("slug") or ""

        year_val = None
        for t in tags:
            try:
                if t.get("externalSourceName") == "customentity.season":
                    year_val = (t.get("extraData") or {}).get("year")
            except Exception:
                continue

        country_val = None
        for t in tags:
            try:
                if t.get("externalSourceName") == "customentity.country":
                    country_val = (t.get("extraData") or {}).get("countryName")
            except Exception:
                continue

        course_title = None
        address = None
        city = None
        zipcode = None
        try:
            gc = references.get("golfCourse") or []
            if gc:
                gc0 = gc[0]
                course_title = gc0.get("fields") or None
                course_name = course_title.get("courseName") or None
                gf = gc0.get("fields") or {}
                line1 = gf.get("addressLine1") or ""
                line2 = gf.get("addressLine2") or ""
                address = (
                    ", ".join([s for s in [line1.strip(), line2.strip()] if s]) or None
                )
                city = gf.get("cityOrTown") or None
                zipcode = gf.get("postZipCode") or None
        except Exception:
            pass

        def _to_date(dts: str | None) -> str | None:
            if not dts:
                return None
            try:
                return dts.split("T")[0]
            except Exception:
                return None

        start_date = _to_date(fields.get("startDate"))
        end_date = _to_date(fields.get("endDate"))

        tournament_url = f"https://www.livgolf.com/schedule/{slug}" if slug else None
        ticket_url = None
        try:
            tickets = fields.get("ticketsCta") or {}
            ticket_url = tickets.get("url") or None
        except Exception:
            pass

        status = fields.get("status") or None

        row = {
            "tournament_id": tournament_id,
            "tournament_name": fields.get("frontendTitle")
            or event.get("title")
            or None,
            "year": year_val,
            "start_date": start_date,
            "end_date": end_date,
            "course_name": course_name,
            "address": address,
            "city": city,
            "country": country_val,
            "zipcode": zipcode,
            "tournament_url": tournament_url,
            "ticket_url": ticket_url,
            "status": status,
        }
        return row

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
            self.logger.info("Supabase client initialized for LIV upserts.")
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
            self.logger.info(f"Upserting {len(self._batch)} LIV rows to Supabase")
            max_attempts = 3
            for attempt in range(1, max_attempts + 1):
                try:
                    (
                        self.supabase.table("livgolf_tournaments")
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

    def _extract_joined_stream(self, html: str) -> str | None:
        out_parts: list[str] = []
        marker = 'self.__next_f.push([1,"'
        start = 0
        while True:
            i = html.find(marker, start)
            if i == -1:
                break
            j = i + len(marker)
            k = html.find('"])', j)
            if k == -1:
                break
            raw = html[j:k]
            out_parts.append(self._unescape_stream(raw))
            start = k + 3
        if not out_parts:
            return None
        return "".join(out_parts)

    def _unescape_stream(self, s: str) -> str:
        return (
            s.replace("\\n", "\n")
            .replace("\\t", "\t")
            .replace("\\r", "\r")
            .replace('\\"', '"')
            .replace("\\'", "'")
            .replace("\\\\", "\\")
        )

    def _extract_all_initial_data(self, text: str) -> list[dict]:
        candidates: list[dict] = []
        seen_ranges: set[tuple[int, int]] = set()
        patterns = ['"initialData":{', '\\"initialData\\":{', 'initialData":{']
        for pat in patterns:
            search_from = 0
            while True:
                idx = text.find(pat, search_from)
                if idx == -1:
                    break
                start = text.find("{", idx)
                if start == -1:
                    break
                depth = 0
                j = start
                while j < len(text):
                    ch = text[j]
                    if ch == "{":
                        depth += 1
                    elif ch == "}":
                        depth -= 1
                        if depth == 0:
                            j += 1
                            break
                    j += 1
                if (start, j) in seen_ranges:
                    search_from = j
                    continue
                raw = text[start:j]
                try:
                    data = json.loads(raw)
                    candidates.append(data)
                    seen_ranges.add((start, j))
                except Exception:
                    pass
                search_from = j
        return candidates

    def _extract_last_initial_data(self, text: str) -> dict | None:
        idx = text.rfind('"initialData":{')
        if idx == -1:
            return None
        start = text.find("{", idx)
        if start == -1:
            return None
        depth = 0
        j = start
        while j < len(text):
            ch = text[j]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    j += 1
                    break
            j += 1
        try:
            return json.loads(text[start:j])
        except Exception:
            return None

    def _scan_for_schedule(self, d: dict):
        if not isinstance(d, dict):
            return None
        if "selectedTab" in d and "scheduleListEvents" in d:
            return d
        for _, v in d.items():
            if isinstance(v, dict):
                found = self._scan_for_schedule(v)
                if found:
                    return found
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        found = self._scan_for_schedule(item)
                        if found:
                            return found
        return None

    def _extract_schedule_container(self, text: str) -> dict | None:
        key = '"selectedTab"'
        idx = text.find(key)
        while idx != -1:
            brace_start = text.rfind("{", 0, idx)
            if brace_start == -1:
                idx = text.find(key, idx + len(key))
                continue
            depth = 0
            j = brace_start
            while j < len(text):
                ch = text[j]
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        j += 1
                        break
                j += 1
            raw = text[brace_start:j]
            try:
                obj = json.loads(raw)
                if isinstance(obj, dict) and "scheduleListEvents" in obj:
                    return obj
            except Exception:
                pass
            idx = text.find(key, idx + len(key))
        return None

    def closed(self, reason):
        try:
            if getattr(self, "_batch", None):
                self.logger.info("LIV spider closing — flushing final batch")
                self._flush_batch()
        except Exception:
            pass
        try:
            if isinstance(self.results_dict, dict):
                self.results_dict["tournaments"] = int(self.tournaments_processed or 0)
        except Exception:
            pass
        self.logger.info(
            f"LIV tournaments spider closed: {reason}; processed={self.tournaments_processed}"
        )
