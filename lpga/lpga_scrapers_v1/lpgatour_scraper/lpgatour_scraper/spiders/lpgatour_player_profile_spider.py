import os
import re
import json
import scrapy
from typing import Iterable
from dotenv import load_dotenv, find_dotenv
from supabase import create_client, Client


load_dotenv(find_dotenv())


class LpgatourPlayerProfileSpider(scrapy.Spider):
    name = "lpgatour_player_profile_spider"
    allowed_domains = ["lpga.com"]

    custom_settings = {
        "ROBOTSTXT_OBEY": False,
        "CONCURRENT_REQUESTS": 2,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.supabase: Client | None = None
        self._tournaments_batch: list[dict] = []
        self._batch_size_tournaments: int = 100
        self.results_dict = (
            kwargs.get("results_dict", {})
            if isinstance(kwargs.get("results_dict", {}), dict)
            else {}
        )
        self.players_processed = 0
        self.stats_upserts = 0
        self.tournaments_upserts = 0

    def start_requests(self) -> Iterable[scrapy.Request]:
        self._init_supabase()
        if not self.supabase:
            self.logger.error("Supabase not configured; aborting player profile spider")
            return

        try:
            resp = (
                self.supabase.table("lpga_unique_players")
                .select("player_id, player_url")
                .neq("player_url", None)
                .execute()
            )
            players = (resp.data or []) if hasattr(resp, "data") else []
        except Exception as e:
            self.logger.error(f"Failed to load players from view: {e}")
            return

        self.logger.info(
            f"Loaded {len(players)} unique player URLs from view (lpga_unique_players)"
        )

        headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "accept-language": "en-US,en;q=0.9",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
            "referer": "https://www.lpga.com/athletes",
        }

        ZYTE_APIKEY = os.environ.get("ZYTE_API_KEY")
        meta_proxy = {"proxy": ZYTE_APIKEY} if ZYTE_APIKEY else {}

        for p in players:
            pid = p.get("player_id")
            url = p.get("player_url") or ""
            if not pid or not url:
                continue
            results_url = url.replace("/overview", "/results")
            if not results_url.endswith("/results"):
                results_url = results_url.rstrip("/") + "/results"
            yield scrapy.Request(
                results_url,
                headers=headers,
                callback=self.parse_player_page,
                meta={"player_id": int(pid), **meta_proxy},
                dont_filter=True,
            )

    def parse_player_page(self, response):
        player_id = response.meta.get("player_id")
        text = response.text

        joined = self._extract_joined_stream(text)
        search_space = joined if joined else text

        # Prefer the last initialData block; fallback to best match
        initial_data = self._extract_last_initial_data(search_space)
        if not initial_data:
            initial_candidates = self._extract_all_initial_data(search_space)
            if not initial_candidates:
                snippet_idx = text.find("self.__next_f.push")
                snippet = (
                    text[snippet_idx : text[snippet_idx : snippet_idx + 200]]
                    if snippet_idx != -1
                    else text[:200]
                )
                self.logger.error(
                    f"initialData not found for player {player_id} (status={response.status}) url={response.url} snippet={snippet!r}"
                )
                return
            initial_data = self._select_best_initial_data(initial_candidates)

        context_item = initial_data.get("contextItem", {})
        stats_blocks = self._find_renderings_by_name(
            initial_data,
            [
                "playerStatsLine",
                "playerHighlightedStatsLine",
            ],
        )
        stats_values = self._collect_stats(stats_blocks)

        # Build stats row
        stats_row = {
            "player_id": player_id,
            "first_name": context_item.get("firstName") or None,
            "last_name": context_item.get("lastName") or None,
            "age": self._to_int(context_item.get("age")),
            "rookie_year": self._to_int(context_item.get("rookieYear")),
            "year_joined": self._to_int(context_item.get("yearJoined")),
            "country": context_item.get("country") or None,
            "country_flag": context_item.get("countryAbbr") or None,
            "starts": self._to_int(stats_values.get("starts")),
            "cuts_made": self._to_int(stats_values.get("cuts_made")),
            "top_10": self._to_int(stats_values.get("top_10_finishes")),
            "wins": self._to_int(stats_values.get("wins")),
            "low_round": self._to_int(stats_values.get("low_round")),
            "official_earnings_text": stats_values.get("official_money_valueFormat"),
            "official_earnings_amount": self._to_number(
                stats_values.get("official_money")
            ),
            "cme_points_rank": self._to_int(stats_values.get("cme_points_rank")),
            "cme_points_rank_previous": self._to_int(
                stats_values.get("cme_points_rank_previous")
            ),
            "cme_points": stats_values.get("cme_points_valueFormat")
            or self._to_string(stats_values.get("cme_points")),
            "cme_points_behind": self._to_string(stats_values.get("cme_points_behind")),
            "image_url": self._absolute(
                context_item.get("profileImage", {}).get("url")
            ),
        }

        tournaments_block = (
            self._find_renderings_by_name(initial_data, ["playerTournamentResults"])
            or []
        )
        tournaments_rows = self._collect_tournaments(tournaments_block)
        tournaments_rows = [
            dict(r, **{"player_id": player_id}) for r in tournaments_rows
        ]

        self._upsert_stats_immediate(stats_row)

        self._tournaments_batch.extend(tournaments_rows)
        if len(self._tournaments_batch) >= self._batch_size_tournaments:
            self._flush_tournaments()

        self.players_processed += 1

    def closed(self, reason):
        try:
            if self._tournaments_batch:
                self._flush_tournaments()
        except Exception:
            pass
        try:
            if isinstance(self.results_dict, dict):
                self.results_dict["players"] = int(self.players_processed or 0)
                self.results_dict["stats_upserts"] = int(self.stats_upserts or 0)
                self.results_dict["tournaments_upserts"] = int(
                    self.tournaments_upserts or 0
                )
        except Exception:
            pass
        self.logger.info(
            f"Player profile spider closed: {reason}; players_processed={self.players_processed}, "
            f"stats_upserts={self.stats_upserts}, tournaments_upserts={self.tournaments_upserts}"
        )

    def _init_supabase(self):
        if self.supabase is not None:
            return
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            self.logger.error("SUPABASE_URL or SUPABASE_KEY missing")
            return
        try:
            self.supabase = create_client(url, key)
            self.logger.info("Supabase client initialized (player profiles)")
        except Exception as e:
            self.logger.error(f"Failed to init Supabase: {e}")
            self.supabase = None

    def _upsert_stats_immediate(self, row: dict):
        if not self.supabase:
            return
        payload = [row]
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                (
                    self.supabase.table("lpga_players_stats")
                    .upsert(payload, on_conflict="player_id", returning="minimal")
                    .execute()
                )
                self.stats_upserts += 1
                return
            except Exception as e:
                if attempt == max_attempts:
                    self.logger.error(f"Immediate upsert player stats failed: {e}")
                    return
                self._backoff(attempt, "player stats (immediate)")

    def _flush_tournaments(self):
        if not self._tournaments_batch or not self.supabase:
            self._tournaments_batch = []
            return
        self.logger.info(
            f"Upserting {len(self._tournaments_batch)} player tournament rows"
        )
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                (
                    self.supabase.table("lpga_players_tournaments")
                    .upsert(
                        self._tournaments_batch,
                        on_conflict="player_id,tournament_id",
                        returning="minimal",
                    )
                    .execute()
                )
                self.tournaments_upserts += len(self._tournaments_batch)
                self._tournaments_batch = []
                return
            except Exception as e:
                if attempt == max_attempts:
                    self.logger.error(f"Upsert player tournaments failed: {e}")
                    self._tournaments_batch = []
                    return
                self._backoff(attempt, "player tournaments")

    def _backoff(self, attempt: int, label: str):
        delay = 2 * attempt
        self.logger.warning(
            f"{label} upsert attempt {attempt} failed; retrying in {delay}s"
        )
        try:
            import time

            time.sleep(delay)
        except Exception:
            pass

    def _find_renderings_by_name(
        self, initial_data: dict, names: list[str]
    ) -> list[dict]:
        results = []
        for ph in initial_data.get("placeholders", []):
            if ph.get("name") not in ("Main", "TabMain"):
                continue
            for r in ph.get("renderings", []):
                if r.get("name") in names:
                    results.append(r)
        return results

    def _collect_stats(self, blocks: list[dict]) -> dict:
        out: dict = {}
        for b in blocks:
            data = (b.get("data") or {}).get("stats") or []
            if not isinstance(data, list):
                continue
            for s in data:
                fname = s.get("fieldName")
                if not fname:
                    continue
                out[fname] = s.get("value")
                # also capture formatted text when present
                if "valueFormat" in s:
                    out[f"{fname}_valueFormat"] = s.get("valueFormat")
        return out

    def _collect_tournaments(self, blocks: list[dict]) -> list[dict]:
        rows_out: list[dict] = []
        for b in blocks:
            data = b.get("data", {})
            rows = data.get("rows", [])
            for row in rows:
                fields = row.get("fields", [])
                if not fields or len(fields) < 10:
                    continue
                # Field indices (0..9) as per user specification
                # 0 tournament (object with tournamentId, name and startDate)
                t_obj = (fields[0] or {}).get("tournament") or {}
                tournament_name = t_obj.get("name")
                start_date_iso = t_obj.get("startDate") or None
                tournament_id = t_obj.get("tournamentId")
                # 1 position
                position = (fields[1] or {}).get("valueFormat")
                # 2 to_par
                to_par = (fields[2] or {}).get("valueFormat")
                # 3 official money (value for amount, valueFormat for text)
                off_money_val = (fields[3] or {}).get("value")
                off_money_fmt = (fields[3] or {}).get("valueFormat")
                # 4-7 r1..r4
                r1 = self._to_int((fields[4] or {}).get("value"))
                r2 = self._to_int((fields[5] or {}).get("value"))
                r3 = self._to_int((fields[6] or {}).get("value"))
                r4 = self._to_int((fields[7] or {}).get("value"))
                # 8 total
                total = self._to_int((fields[8] or {}).get("value"))
                # 9 cme_points
                cme_points = self._to_float((fields[9] or {}).get("value"))

                rows_out.append(
                    {
                        "tournament_id": self._to_int(tournament_id),
                        "tournament_name": tournament_name,
                        "start_date": (start_date_iso or "").split("T")[0] or None,
                        "position": position,
                        "to_par": to_par,
                        "official_money_text": off_money_fmt,
                        "official_money_amount": self._to_int(off_money_val),
                        "r1": r1,
                        "r2": r2,
                        "r3": r3,
                        "r4": r4,
                        "total": total,
                        "cme_points": cme_points,
                    }
                )
        return rows_out

    def _extract_joined_stream(self, html: str) -> str | None:
        # Collect payloads from self.__next_f.push([1,"...payload..."]) blocks
        out_parts: list[str] = []
        marker = 'self.__next_f.push([1,"'
        start = 0
        while True:
            i = html.find(marker, start)
            if i == -1:
                break
            j = i + len(marker)
            # Find the closing "]) for this segment
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
        # Minimal unescape for common sequences
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

    def _select_best_initial_data(self, candidates: list[dict]) -> dict:
        # Prefer the candidate that includes playerTournamentResults
        def has_rendering(d: dict, name: str) -> bool:
            for ph in d.get("placeholders", []):
                for r in ph.get("renderings", []):
                    if r.get("name") == name:
                        return True
            return False

        for d in candidates:
            if has_rendering(d, "playerTournamentResults"):
                return d
        for d in candidates:
            if has_rendering(d, "playerStatsLine") or has_rendering(
                d, "playerHighlightedStatsLine"
            ):
                return d
        # fallback to last candidate
        return candidates[-1]

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

    def _absolute(self, path: str | None) -> str | None:
        if not path:
            return None
        if path.startswith("http://") or path.startswith("https://"):
            return path
        return f"https://www.lpga.com{path}"

    def _to_int(self, v):
        try:
            if v is None:
                return None
            return int(str(v))
        except Exception:
            try:
                return (
                    int(re.sub(r"[^0-9-]", "", str(v)))
                    if re.search(r"\d", str(v))
                    else None
                )
            except Exception:
                return None

    def _to_float(self, v):
        try:
            if v is None:
                return None
            return float(str(v).replace(",", ""))
        except Exception:
            return None

    def _to_number(self, v):
        # returns int if possible, else float, else None
        f = self._to_float(v)
        if f is None:
            return None
        try:
            if float(int(f)) == f:
                return int(f)
        except Exception:
            pass
        return f

    def _to_string(self, v):
        return None if v is None else str(v)
