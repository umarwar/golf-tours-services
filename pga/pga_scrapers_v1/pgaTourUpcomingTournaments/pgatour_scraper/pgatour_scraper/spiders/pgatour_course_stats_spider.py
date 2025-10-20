import scrapy
import json
import os
from dotenv import load_dotenv

load_dotenv()


class PgatourCourseStatsSpider(scrapy.Spider):
    name = "pgatour_course_stats_spider"
    custom_settings = {
        "FEEDS": {
            "upcoming_tournaments_output/03_pgatour_courseStats.csv": {
                "format": "csv",
                "overwrite": True,
                "encoding": "utf-8-sig",
            }
        },
        "FEED_EXPORT_FIELDS": [
            "TournamentId",
            "CourseName",
            "Round",
            "Live",
            "Hole",
            "Par",
            "Yards",
            "ScoringAverage",
            "Rank",
            "Eagles",
            "Birdies",
            "Bogeys",
            "HoleImage",
            "CoursePar",
            "CourseYardage",
            "CourseRecord",
            "CourseFairway",
            "CourseRough",
            "CourseGreen",
            "CourseEstablished",
            "CourseDesign",
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
            "https://www.pgatour.com/tournaments/2025/john-deere-classic/R2025030/course-stats",
            "https://www.pgatour.com/tournaments/2025/genesis-scottish-open/R2025541/course-stats",
            "https://www.pgatour.com/tournaments/2025/isco-championship/R2025518/course-stats",
            "https://www.pgatour.com/tournaments/2025/the-open-championship/R2025100/course-stats",
            "https://www.pgatour.com/tournaments/2025/barracuda-championship/R2025472/course-stats",
            "https://www.pgatour.com/tournaments/2025/3m-open/R2025525/course-stats",
            "https://www.pgatour.com/tournaments/2025/wyndham-championship/R2025013/course-stats",
            "https://www.pgatour.com/tournaments/2025/fedex-st-jude-championship/R2025027/course-stats",
            "https://www.pgatour.com/tournaments/2025/bmw-championship/R2025028/course-stats",
            "https://www.pgatour.com/tournaments/2025/tour-championship/R2025060/course-stats",
            "https://www.pgatour.com/tournaments/2025/procore-championship/R2025464/course-stats",
            "https://www.pgatour.com/tournaments/2025/ryder-cup/R2025468/course-stats",
            "https://www.pgatour.com/tournaments/2025/sanderson-farms-championship/R2025054/course-stats",
            "https://www.pgatour.com/tournaments/2025/baycurrent-classic/R2025527/course-stats",
            "https://www.pgatour.com/tournaments/2025/bank-of-utah-championship/R2025554/course-stats",
            "https://www.pgatour.com/tournaments/2025/world-wide-technology-championship/R2025457/course-stats",
            "https://www.pgatour.com/tournaments/2025/butterfield-bermuda-championship/R2025528/course-stats",
            "https://www.pgatour.com/tournaments/2025/the-rsm-classic/R2025493/course-stats",
            "https://www.pgatour.com/tournaments/2025/hero-world-challenge/R2025478/course-stats",
            "https://www.pgatour.com/tournaments/2025/grant-thornton-invitational/R2025551/course-stats",
        ]
        for url in urls:
            yield scrapy.Request(
                url,
                headers=self.headers,
                callback=self.parse_course_stats,
                meta={
                    "tournament_url": url,
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
                    round_num = round_stat.get("roundHeader", "")
                    round_live = round_stat.get("live", "")
                    for hole in round_stat.get("holeStats", []):
                        typename = hole.get("__typename", "")
                        if typename == "CourseHoleStats":
                            yield {
                                "TournamentId": course_data.get("tournamentId", ""),
                                "CourseName": course_data.get("courseName", ""),
                                "Round": round_num,
                                "Live": round_live,
                                "Hole": hole.get("courseHoleNum", ""),
                                "Par": hole.get("parValue", ""),
                                "Yards": hole.get("yards", ""),
                                "ScoringAverage": hole.get("scoringAverage", ""),
                                "Rank": hole.get("rank", ""),
                                "Eagles": hole.get("eagles", ""),
                                "Birdies": hole.get("birdies", ""),
                                "Bogeys": hole.get("bogeys", ""),
                                "HoleImage": hole.get("holeImage", ""),
                                "CoursePar": get_overview("Par"),
                                "CourseYardage": get_overview("Yardage"),
                                "CourseRecord": record.get("value", ""),
                                "CourseFairway": get_overview("Fairway"),
                                "CourseRough": get_overview("Rough"),
                                "CourseGreen": get_overview("Green"),
                                "CourseEstablished": get_overview("Established"),
                                "CourseDesign": get_overview("Design"),
                            }
                        elif typename == "SummaryRow":
                            yield {
                                "TournamentId": course_data.get("tournamentId", ""),
                                "CourseName": course_data.get("courseName", ""),
                                "Round": round_num,
                                "Live": round_live,
                                "Hole": hole.get("rowType", ""),
                                "Par": hole.get("par", ""),
                                "Yards": hole.get("yardage", ""),
                                "ScoringAverage": hole.get("scoringAverage", ""),
                                "Rank": hole.get("rank", ""),
                                "Eagles": hole.get("eagles", ""),
                                "Birdies": hole.get("birdies", ""),
                                "Bogeys": hole.get("bogeys", ""),
                                "HoleImage": "",
                                "CoursePar": get_overview("Par"),
                                "CourseYardage": get_overview("Yardage"),
                                "CourseRecord": record.get("value", ""),
                                "CourseFairway": get_overview("Fairway"),
                                "CourseRough": get_overview("Rough"),
                                "CourseGreen": get_overview("Green"),
                                "CourseEstablished": get_overview("Established"),
                                "CourseDesign": get_overview("Design"),
                            }
        except Exception as e:
            self.logger.error(f"Error parsing course stats page {response.url}: {e}")
