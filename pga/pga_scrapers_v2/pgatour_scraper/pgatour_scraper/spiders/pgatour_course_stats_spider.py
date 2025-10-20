import os
import json
import scrapy
from dotenv import load_dotenv, find_dotenv
from supabase import create_client, Client

load_dotenv(find_dotenv())


class PgatourCourseStatsSpider(scrapy.Spider):
    name = "pgatour_course_stats_spider"
    custom_settings = {
        "ROBOTSTXT_OBEY": False,
        "CONCURRENT_REQUESTS": 4,
        "DOWNLOAD_DELAY": 1,
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
        self.course_stats_processed = 0

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
            self.logger.info("Supabase client initialized (course stats)")
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
                    .select("tournament_id,tournament_url")
                    .neq("tournament_url", None)
                    .execute()
                )
                tournaments = resp.data or []
                self.logger.info(
                    f"Loaded {len(tournaments)} tournaments for course-stats"
                )
            except Exception as e:
                self.logger.error(f"Failed to load tournaments: {e}")

        if not tournaments:
            self.logger.warning("No tournaments loaded from DB; nothing to scrape")
            return

        for t in tournaments:
            base = t.get("tournament_url")
            tid = t.get("tournament_id")
            if not base or not tid:
                continue
            url = base.rstrip("/") + "/course-stats"
            yield scrapy.Request(
                url,
                headers=self.headers,
                callback=self.parse_course_stats,
                meta={
                    "tournament_id": tid,
                    "proxy": ZYTE_APIKEY,
                },
            )

    def parse_course_stats(self, response):
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
            # Find the query with the detailed course stats (has 'courses' with 'roundHoleStats')
            detailed_courses = None
            for q in queries:
                d = q.get("state", {}).get("data", {})
                if (
                    isinstance(d, dict)
                    and "courses" in d
                    and isinstance(d["courses"], list)
                    and d["courses"]
                    and "roundHoleStats" in d["courses"][0]
                ):
                    detailed_courses = d["courses"]
                    break
            if not detailed_courses:
                self.logger.error(f"No detailed course stats found for {response.url}")
                return
            for course_data in detailed_courses:
                overview = {
                    item["label"]: item
                    for item in course_data.get("courseOverview", {}).get(
                        "overview", []
                    )
                }

                def get_overview(label, key="value"):
                    return overview.get(label, {}).get(key, "")

                record = overview.get("Record", {})
                for round_stat in course_data.get("roundHoleStats", []):
                    # Only keep numbered rounds. Skip "All Rounds" and any non-numbered headers.
                    round_num_val = round_stat.get("roundNum")
                    if round_num_val is None:
                        continue
                    try:
                        round_num_int = int(round_num_val)
                    except Exception:
                        continue

                    for hole in round_stat.get("holeStats", []):
                        if hole.get("__typename", "") != "CourseHoleStats":
                            # Skip summary rows like IN/OUT/TOTAL to preserve hole ordering by numeric holes only
                            continue
                        row = self._build_row(
                            response.meta.get("tournament_id"),
                            course_data,
                            round_num_int,
                            hole,
                            get_overview,
                            record,
                        )
                        self._buffer_row(row)
        except Exception as e:
            self.logger.error(f"Error parsing course stats page {response.url}: {e}")

    def closed(self, reason):
        if getattr(self, "_batch", None):
            self._flush_batch()
        # Update results summary if provided by API caller
        try:
            if isinstance(self.results_dict, dict):
                self.results_dict["course_stats"] = self.course_stats_processed
        except Exception:
            pass

    def _to_int(self, v):
        try:
            return int(v)
        except Exception:
            return None

    def _to_float(self, v):
        try:
            return float(v)
        except Exception:
            return None

    def _build_row(
        self,
        tournament_id,
        course_data,
        round_num_int,
        hole,
        get_overview,
        record,
    ):
        course_name = course_data.get("courseName", "")
        hole_id = hole.get("courseHoleNum")
        par = self._to_int(hole.get("parValue"))
        yards = self._to_int(hole.get("yards"))

        # Parse scoringAverageDiff values like "+0.109" or "-0.025"
        avg_diff_raw = hole.get("scoringAverageDiff")
        try:
            avg_diff_val = (
                float(str(avg_diff_raw).replace("+", ""))
                if avg_diff_raw is not None
                else None
            )
        except Exception:
            avg_diff_val = None

        return {
            "tournament_id": course_data.get("tournamentId", tournament_id),
            "course_name": course_name,
            "round": self._to_int(round_num_int) or 0,
            "hole": self._to_int(hole_id) or 0,
            "par": par,
            "yards": yards,
            "scoring_average": self._to_float(hole.get("scoringAverage")),
            "avg_diff": avg_diff_val,
            "rank": self._to_int(hole.get("rank")),
            "eagles": self._to_int(hole.get("eagles")),
            "birdies": self._to_int(hole.get("birdies")),
            "pars": self._to_int(hole.get("pars")),
            "bogeys": self._to_int(hole.get("bogeys")),
            "double_bogeys": self._to_int(hole.get("doubleBogey")),
            "hole_image": hole.get("holeImage", ""),
            "course_par": self._to_int(get_overview("Par")),
            "course_yardage": get_overview("Yardage") or None,
            "course_record": self._to_int(record.get("value", "")),
            "course_fairway": get_overview("Fairway") or None,
            "course_rough": get_overview("Rough") or None,
            "course_green": get_overview("Green") or None,
            "course_established": self._to_int(get_overview("Established")),
            "course_design": get_overview("Design") or None,
        }

    def _buffer_row(self, row: dict):
        self._batch.append(row)
        self.course_stats_processed += 1
        if len(self._batch) >= self._batch_size:
            self._flush_batch()

    def _flush_batch(self):
        if self.supabase is None:
            if self._batch:
                self.logger.warning(
                    f"Supabase not initialized; dropping {len(self._batch)} course rows"
                )
                self._batch = []
            return
        if not self._batch:
            return
        try:
            # Deduplicate by composite key within the batch
            key_map = {}
            for r in self._batch:
                k = (
                    r.get("tournament_id"),
                    r.get("course_name"),
                    r.get("round"),
                    r.get("hole"),
                )
                key_map[k] = r
            rows = list(key_map.values())

            self.logger.info(f"Upserting {len(rows)} course stats rows")
            (
                self.supabase.table("pga_course_stats")
                .upsert(
                    rows,
                    on_conflict="tournament_id,course_name,round,hole",
                    returning="minimal",
                )
                .execute()
            )
            self._batch = []
        except Exception as e:
            self.logger.error(f"Failed to upsert course stats batch: {e}")
            self._batch = []
