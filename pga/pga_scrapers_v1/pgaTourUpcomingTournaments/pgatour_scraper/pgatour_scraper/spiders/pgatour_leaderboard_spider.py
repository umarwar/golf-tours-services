import scrapy
import json
import csv
import os
import re
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()


def slugify_name(name):
    # Lowercase, replace spaces with hyphens, remove non-alphanumeric except hyphens
    return re.sub(r"[^a-z0-9-]", "", name.lower().replace(" ", "-") if name else "")


class PgatourLeaderboardSpider(scrapy.Spider):
    name = "pgatour_leaderboard_spider"
    custom_settings = {
        "FEEDS": {
            "upcoming_tournaments_output/02_pgatour_leaderboard.csv": {
                "format": "csv",
                "overwrite": True,
                "encoding": "utf-8-sig",
            }
        },
        "FEED_EXPORT_FIELDS": [
            "PlayerID",
            "TournamentID",
            "TournamentName",
            "All Players",
            "Past Champions",
            "Position",
            "Total",
            "Thru",
            "Score",
            "R1",
            "R2",
            "R3",
            "R4",
            "Strokes",
            "Projected",
            "Starting",
            "Country",
            "Year",
            "Player URL",
        ],
        "ROBOTSTXT_OBEY": False,
        "CONCURRENT_REQUESTS": 2,
        "DOWNLOAD_DELAY": 2,
    }
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-language": "en-US,en;q=0.9",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    }

    def start_requests(self):
        ZYTE_APIKEY = os.environ.get("ZYTE_API_KEY")

        urls = [
            "https://www.pgatour.com/tournaments/2025/john-deere-classic/R2025030",
            "https://www.pgatour.com/tournaments/2025/genesis-scottish-open/R2025541/overview",
            "https://www.pgatour.com/tournaments/2025/isco-championship/R2025518/overview",
            "https://www.pgatour.com/tournaments/2025/the-open-championship/R2025100/overview",
            "https://www.pgatour.com/tournaments/2025/barracuda-championship/R2025472/overview",
            "https://www.pgatour.com/tournaments/2025/3m-open/R2025525/overview",
            "https://www.pgatour.com/tournaments/2025/wyndham-championship/R2025013/overview",
            "https://www.pgatour.com/tournaments/2025/fedex-st-jude-championship/R2025027/overview",
            "https://www.pgatour.com/tournaments/2025/bmw-championship/R2025028/overview",
            "https://www.pgatour.com/tournaments/2025/tour-championship/R2025060/overview",
            "https://www.pgatour.com/tournaments/2025/procore-championship/R2025464/overview",
            "https://www.pgatour.com/tournaments/2025/ryder-cup/R2025468/overview",
            "https://www.pgatour.com/tournaments/2025/sanderson-farms-championship/R2025054/overview",
            "https://www.pgatour.com/tournaments/2025/baycurrent-classic/R2025527/overview",
            "https://www.pgatour.com/tournaments/2025/bank-of-utah-championship/R2025554/overview",
            "https://www.pgatour.com/tournaments/2025/world-wide-technology-championship/R2025457/overview",
            "https://www.pgatour.com/tournaments/2025/butterfield-bermuda-championship/R2025528/overview",
            "https://www.pgatour.com/tournaments/2025/the-rsm-classic/R2025493/overview",
            "https://www.pgatour.com/tournaments/2025/hero-world-challenge/R2025478/overview",
            "https://www.pgatour.com/tournaments/2025/grant-thornton-invitational/R2025551/overview",
        ]
        for url in urls:
            yield scrapy.Request(
                url,
                headers=self.headers,
                callback=self.parse_tournament,
                meta={
                    "tournament_url": url,
                    "proxy": ZYTE_APIKEY,
                },
            )

    def parse_tournament(self, response):
        script_content = response.xpath('//script[@id="__NEXT_DATA__"]/text()').get()
        tournament_name = self.extract_tournament_name_from_url(
            response.meta["tournament_url"]
        )
        tournament_id = self.extract_tournament_id_from_url(
            response.meta["tournament_url"]
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
                    player_name = player.get("displayName", "")
                    player_url = ""
                    if player_id and player_name:
                        player_url = f"https://www.pgatour.com/player/{player_id}/{slugify_name(player_name)}"
                    if not player_id:
                        continue

                    # Extract rounds data
                    rounds = scoring.get("rounds", [])
                    r1 = rounds[0] if len(rounds) > 0 and rounds[0] != "-" else "-"
                    r2 = rounds[1] if len(rounds) > 1 and rounds[1] != "-" else "-"
                    r3 = rounds[2] if len(rounds) > 2 and rounds[2] != "-" else "-"
                    r4 = rounds[3] if len(rounds) > 3 and rounds[3] != "-" else "-"

                    yield {
                        "PlayerID": player_id,
                        "TournamentID": tournament_id,
                        "TournamentName": tournament_name,
                        "All Players": player_name,
                        "Past Champions": "-",
                        "Position": scoring.get("position", "-"),
                        "Total": scoring.get("total", "-"),
                        "Thru": scoring.get("thru", "-"),
                        "Score": scoring.get("score", "-"),
                        "R1": r1,
                        "R2": r2,
                        "R3": r3,
                        "R4": r4,
                        "Strokes": scoring.get("totalStrokes", "-"),
                        "Projected": scoring.get("projected", "-"),
                        "Starting": scoring.get("official", "-"),
                        "Country": player.get("country", "-"),
                        "Year": "-",
                        "Player URL": player_url,
                    }
                return
            # If no players, look for past champions
            past_champions = None
            for q in queries:
                d = q.get("state", {}).get("data", {})
                if (
                    isinstance(d, dict)
                    and "pastChampions" in d
                    and isinstance(d["pastChampions"], list)
                ):
                    past_champions = d["pastChampions"]
                    break
            if past_champions:
                for champ in past_champions:
                    player_id = champ.get("playerId") or champ.get("id")
                    player_name = champ.get("displayName", "")
                    player_url = ""
                    if player_id and player_name:
                        player_url = f"https://www.pgatour.com/player/{player_id}/{slugify_name(player_name)}"
                    if not player_id:
                        continue

                    # Extract rounds data for past champions (if available)
                    rounds = champ.get("rounds", [])
                    r1 = rounds[0] if len(rounds) > 0 and rounds[0] != "-" else "-"
                    r2 = rounds[1] if len(rounds) > 1 and rounds[1] != "-" else "-"
                    r3 = rounds[2] if len(rounds) > 2 and rounds[2] != "-" else "-"
                    r4 = rounds[3] if len(rounds) > 3 and rounds[3] != "-" else "-"

                    yield {
                        "PlayerID": player_id,
                        "TournamentID": tournament_id,
                        "TournamentName": tournament_name,
                        "All Players": "-",
                        "Past Champions": player_name,
                        "Position": champ.get("position", "-"),
                        "Total": champ.get("total", "-"),
                        "Thru": "-",
                        "Score": champ.get("score", "-"),
                        "R1": r1,
                        "R2": r2,
                        "R3": r3,
                        "R4": r4,
                        "Strokes": champ.get("totalStrokes", "-"),
                        "Projected": "-",
                        "Starting": "-",
                        "Country": champ.get("countryCode", "-"),
                        "Year": champ.get("displaySeason", "-"),
                        "Player URL": player_url,
                    }
                return
            self.logger.warning(
                f"No players or past champions found for {response.url}"
            )
        except Exception as e:
            self.logger.error(f"Error parsing tournament page {response.url}: {e}")

    def extract_tournament_name_from_url(self, url):
        try:
            parts = urlparse(url).path.strip("/").split("/")
            if len(parts) >= 3:
                return parts[2].replace("-", " ").title()
        except Exception:
            pass
        return "-"

    def extract_tournament_id_from_url(self, url):
        try:
            parts = urlparse(url).path.strip("/").split("/")
            if len(parts) >= 4:
                return parts[3]
        except Exception:
            pass
        return "-"
