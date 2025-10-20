import os
import scrapy
import json
import re
from urllib.parse import urljoin
from dotenv import load_dotenv

load_dotenv()


def slugify(name):
    # Lowercase, replace spaces with hyphens, remove non-alphanumeric except hyphens
    return re.sub(r"[^a-z0-9-]", "", name.lower().replace(" ", "-"))


class PgatourUpcomingSpider(scrapy.Spider):
    name = "pgatour_upcoming_spider"
    start_urls = ["https://www.pgatour.com/schedule"]
    custom_settings = {
        "ROBOTSTXT_OBEY": False,
        "CONCURRENT_REQUESTS": 4,
        "FEEDS": {
            "upcoming_tournaments_output/01_pgatour_upcoming_tournaments.csv": {
                "format": "csv",
                "overwrite": True,
                "encoding": "utf-8-sig",
            }
        },
    }
    headers = {
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

    def start_requests(self):
        ZYTE_APIKEY = os.environ.get("ZYTE_API_KEY")

        for url in self.start_urls:
            yield scrapy.Request(
                url,
                headers=self.headers,
                meta={
                    "proxy": ZYTE_APIKEY,
                },
                dont_filter=True,
            )

    def parse(self, response):
        # Extract JSON data from the __NEXT_DATA__ script tag
        script_content = response.xpath('//script[@id="__NEXT_DATA__"]/text()').get()

        if not script_content:
            self.logger.error("Could not find __NEXT_DATA__ script tag!")
            return

        try:
            # Parse the JSON data
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

            # Extract upcoming tournaments
            upcoming_tournaments = (
                schedule_query.get("state", {}).get("data", {}).get("upcoming", [])
            )

            self.logger.info(
                f"Found {len(upcoming_tournaments)} upcoming tournament months"
            )

            # Process each month's tournaments
            for month_data in upcoming_tournaments:
                month_name = month_data.get("month", "")
                year = str(month_data.get("year", ""))
                tournaments = month_data.get("tournaments", [])

                self.logger.info(
                    f"Processing {month_name} {year}: {len(tournaments)} tournaments"
                )

                for tournament in tournaments:
                    try:
                        # Extract tournament details
                        tournament_name = tournament.get("tournamentName", "")
                        date = tournament.get("date", "")
                        course = tournament.get("courseName", "")
                        tournament_id = tournament.get("id", "")

                        # Build location string
                        city = tournament.get("city", "")
                        state = tournament.get("state", "")
                        country = tournament.get("country", "")
                        location_parts = [
                            part for part in [city, state, country] if part
                        ]
                        location = ", ".join(location_parts)

                        # Extract financial and competition details
                        purse = tournament.get("purse", "")
                        fedexcup = tournament.get("tourStandingValue", "")
                        previous_winner = tournament.get("champion", "")
                        winner_prize = tournament.get("championEarnings", "")
                        ticket_url = tournament.get("ticketsURL", "")

                        # Extract or construct tournament URL
                        tournament_url = f"https://www.pgatour.com/tournaments/{year}/{slugify(tournament_name)}/{tournament_id}"

                        self.logger.info(
                            f"Extracted tournament: {tournament_name} - {date} - URL: {tournament_url}"
                        )

                        # Yield structured data
                        yield {
                            "TournamentID": tournament_id,
                            "TournamentName": tournament_name,
                            "Year": f"{month_name}-{year}",
                            "Date": date,
                            "Course": course,
                            "Location": location,
                            "Purse": purse,
                            "FedExCup": fedexcup,
                            "Previous Winner": previous_winner,
                            "Winner Prize": winner_prize,
                            "Tournament URL": tournament_url,
                            "Ticket URL": ticket_url,
                        }

                    except Exception as e:
                        self.logger.error(
                            f"Error processing tournament {tournament.get('tournamentName', 'Unknown')}: {e}"
                        )
                        continue

        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing JSON: {e}")
            return
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            return
