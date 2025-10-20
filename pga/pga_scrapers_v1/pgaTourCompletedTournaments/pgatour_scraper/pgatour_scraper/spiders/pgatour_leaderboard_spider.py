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
            "completed_tournaments_output/02_pgatour_leaderboard.csv": {
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
            "Position",
            "Total",
            "Thru",
            "Round",
            "R1",
            "R2",
            "R3",
            "R4",
            "Strokes",
            "Projected",
            "Starting",
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
            "https://www.pgatour.com/tournaments/2025/the-sentry/R2025016",
            "https://www.pgatour.com/tournaments/2025/sony-open-in-hawaii/R2025006",
            "https://www.pgatour.com/tournaments/2025/the-american-express/R2025002",
            "https://www.pgatour.com/tournaments/2025/farmers-insurance-open/R2025004",
            "https://www.pgatour.com/tournaments/2025/att-pebble-beach-pro-am/R2025005",
            "https://www.pgatour.com/tournaments/2025/wm-phoenix-open/R2025003",
            "https://www.pgatour.com/tournaments/2025/the-genesis-invitational/R2025007",
            "https://www.pgatour.com/tournaments/2025/mexico-open-at-vidantaworld/R2025540",
            "https://www.pgatour.com/tournaments/2025/cognizant-classic-in-the-palm-beaches/R2025010",
            "https://www.pgatour.com/tournaments/2025/arnold-palmer-invitational-presented-by-mastercard/R2025009",
            "https://www.pgatour.com/tournaments/2025/puerto-rico-open/R2025483",
            "https://www.pgatour.com/tournaments/2025/the-players-championship/R2025011",
            "https://www.pgatour.com/tournaments/2025/valspar-championship/R2025475",
            "https://www.pgatour.com/tournaments/2025/texas-childrens-houston-open/R2025020",
            "https://www.pgatour.com/tournaments/2025/valero-texas-open/R2025041",
            "https://www.pgatour.com/tournaments/2025/masters-tournament/R2025014",
            "https://www.pgatour.com/tournaments/2025/rbc-heritage/R2025012",
            "https://www.pgatour.com/tournaments/2025/corales-puntacana-championship/R2025522",
            "https://www.pgatour.com/tournaments/2025/zurich-classic-of-new-orleans/R2025018",
            "https://www.pgatour.com/tournaments/2025/the-cj-cup-byron-nelson/R2025019",
            "https://www.pgatour.com/tournaments/2025/truist-championship/R2025480",
            "https://www.pgatour.com/tournaments/2025/oneflight-myrtle-beach-classic/R2025553",
            "https://www.pgatour.com/tournaments/2025/pga-championship/R2025033",
            "https://www.pgatour.com/tournaments/2025/charles-schwab-challenge/R2025021",
            "https://www.pgatour.com/tournaments/2025/the-memorial-tournament-presented-by-workday/R2025023",
            "https://www.pgatour.com/tournaments/2025/rbc-canadian-open/R2025032",
            "https://www.pgatour.com/tournaments/2025/us-open/R2025026",
            "https://www.pgatour.com/tournaments/2025/travelers-championship/R2025034",
            "https://www.pgatour.com/tournaments/2025/rocket-classic/R2025524",
            "https://www.pgatour.com/tournaments/2025/john-deere-classic/R2025030",
            "https://www.pgatour.com/tournaments/2025/genesis-scottish-open/R2025541",
            "https://www.pgatour.com/tournaments/2025/isco-championship/R2025518",
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
                        "Position": scoring.get("position", "-"),
                        "Total": scoring.get("total", "-"),
                        "Thru": scoring.get("thru", "-"),
                        "Round": scoring.get("score", "-"),
                        "R1": r1,
                        "R2": r2,
                        "R3": r3,
                        "R4": r4,
                        "Strokes": scoring.get("totalStrokes", "-"),
                        "Projected": scoring.get("projected", "-"),
                        "Starting": scoring.get("official", "-"),
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
