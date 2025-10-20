import scrapy
import json
import os
from urllib.parse import urlparse
from dotenv import load_dotenv
import csv

load_dotenv()


class PgatourPlayerDetailSpider(scrapy.Spider):
    name = "pgatour_player_detail_spider"
    custom_settings = {
        "FEEDS": {
            "upcoming_tournaments_output/04_pgatour_player_details.csv": {
                "format": "csv",
                "overwrite": True,
                "encoding": "utf-8-sig",
            }
        },
        "FEED_EXPORT_FIELDS": [
            "PlayerID",
            "Name",
            "Age",
            "Birthday",
            "Country",
            "Birth place",
            "College",
            "Residence",
            "Family",
            "Turned pro",
            "Career wins",
            "Wins(2025)",
            "FedExCup Standings",
            "FedExCup Fall Standings",
            "OWGR",
            "Career Earnings",
            "Plays From",
            "Pronunciation",
            "Events Played",
            "PGA Tour wins",
            "International wins",
            "Cuts made",
            "Runner Up",
            "Third place finishes",
            "Top 5 finishes",
            "Top 10 finishes",
            "Year joined tour",
            "Official money",
            "Image URL",
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
        # urls = []
        # with open(
        #     "output/players_URLs.csv",
        #     newline="",
        #     encoding="utf-8-sig",
        # ) as csvfile:
        #     reader = csv.DictReader(csvfile)
        #     for row in reader:
        #         url = row.get("Player URL")
        #         if url:
        #             urls.append(url)
        urls = [
            "https://www.pgatour.com/player/52375/doug-ghim",
            "https://www.pgatour.com/player/57362/austin-eckroat",
            "https://www.pgatour.com/player/39977/max-homa",
            "https://www.pgatour.com/player/36326/david-lipsky",
            "https://www.pgatour.com/player/55893/sam-stevens",
            "https://www.pgatour.com/player/40162/justin-lower",
            "https://www.pgatour.com/player/39975/michael-kim",
            "https://www.pgatour.com/player/31646/emiliano-grillo",
        ]

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
            player_data = find_query_by_key("player")  # Basic bio
            overview_data = find_query_by_key("playerProfileOverview")
            career_data = find_query_by_key("playerProfileCareer")

            # Basic info
            player_bio = player_data.get("playerBio", {})
            display_name = player_data.get("displayName", "-")
            player_id = player_data.get("id", "-")
            country = player_data.get("country", "-")
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

            # Career wins and Wins(2025) (from overview)
            career_wins = "-"
            wins_2025 = "-"
            for perf in overview_data.get("performance", []):
                if perf.get("season") == "2025":
                    for stat in perf.get("stats", []):
                        if stat.get("title") == "Wins":
                            wins_2025 = stat.get("value", "-")
                if perf.get("tour") == "R":
                    for stat in perf.get("stats", []):
                        if stat.get("title") == "Wins":
                            career_wins = stat.get("career", "-")

            # Achievements (from career)
            achievements = {
                a["title"]: a["value"]
                for a in career_data.get("achievements", [])
                if "title" in a
            }

            def get_ach(title):
                return achievements.get(title, "-")

            yield {
                "PlayerID": player_id,
                "Name": display_name,
                "Age": age,
                "Birthday": birthday,
                "Country": country,
                "Birth place": (
                    f"{birth_city}, {birth_state}"
                    if birth_city != "-" or birth_state != "-"
                    else "-"
                ),
                "College": college,
                "Residence": (
                    f"{residence_city}, {residence_state}"
                    if residence_city != "-" or residence_state != "-"
                    else "-"
                ),
                "Family": family,
                "Turned pro": turned_pro,
                "Career wins": career_wins,
                "Wins(2025)": wins_2025,
                "FedExCup Standings": fedex_standings,
                "FedExCup Fall Standings": fedex_fall_standings,
                "OWGR": owgr,
                "Career Earnings": career_earnings,
                "Plays From": (
                    f"{plays_from_city}, {plays_from_state}"
                    if plays_from_city != "-" or plays_from_state != "-"
                    else "-"
                ),
                "Pronunciation": pronunciation,
                "Events Played": get_ach("Events Played"),
                "PGA Tour wins": get_ach("PGA TOUR WINS"),
                "International wins": get_ach("International Wins"),
                "Cuts made": get_ach("Cuts Made"),
                "Runner Up": get_ach("Runner Up"),
                "Third place finishes": get_ach("Third Place Finishes"),
                "Top 5 finishes": get_ach("Top 5 Finishes"),
                "Top 10 finishes": get_ach("Top 10 Finishes"),
                "Year joined tour": get_ach("Year Joined Tour"),
                "Official money": get_ach("Official Money"),
                "Image URL": image_url,
            }
        except Exception as e:
            self.logger.error(f"Error parsing player page {response.url}: {e}")
