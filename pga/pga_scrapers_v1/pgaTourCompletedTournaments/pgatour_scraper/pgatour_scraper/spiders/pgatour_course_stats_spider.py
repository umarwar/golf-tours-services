import scrapy
import json
import os
from dotenv import load_dotenv

load_dotenv()


class PgatourCourseStatsSpider(scrapy.Spider):
    name = "pgatour_course_stats_spider"
    custom_settings = {
        "FEEDS": {
            "completed_tournaments_output/04_pgatour_courseStats.csv": {
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
            "https://www.pgatour.com/tournaments/2025/the-sentry/R2025016/course-stats",
            "https://www.pgatour.com/tournaments/2025/sony-open-in-hawaii/R2025006/course-stats",
            "https://www.pgatour.com/tournaments/2025/the-american-express/R2025002/course-stats",
            "https://www.pgatour.com/tournaments/2025/farmers-insurance-open/R2025004/course-stats",
            "https://www.pgatour.com/tournaments/2025/att-pebble-beach-pro-am/R2025005/course-stats",
            "https://www.pgatour.com/tournaments/2025/wm-phoenix-open/R2025003/course-stats",
            "https://www.pgatour.com/tournaments/2025/the-genesis-invitational/R2025007/course-stats",
            "https://www.pgatour.com/tournaments/2025/mexico-open-at-vidantaworld/R2025540/course-stats",
            "https://www.pgatour.com/tournaments/2025/cognizant-classic-in-the-palm-beaches/R2025010/course-stats",
            "https://www.pgatour.com/tournaments/2025/arnold-palmer-invitational-presented-by-mastercard/R2025009/course-stats",
            "https://www.pgatour.com/tournaments/2025/puerto-rico-open/R2025483/course-stats",
            "https://www.pgatour.com/tournaments/2025/the-players-championship/R2025011/course-stats",
            "https://www.pgatour.com/tournaments/2025/valspar-championship/R2025475/course-stats",
            "https://www.pgatour.com/tournaments/2025/texas-childrens-houston-open/R2025020/course-stats",
            "https://www.pgatour.com/tournaments/2025/valero-texas-open/R2025041/course-stats",
            "https://www.pgatour.com/tournaments/2025/masters-tournament/R2025014/course-stats",
            "https://www.pgatour.com/tournaments/2025/rbc-heritage/R2025012/course-stats",
            "https://www.pgatour.com/tournaments/2025/corales-puntacana-championship/R2025522/course-stats",
            "https://www.pgatour.com/tournaments/2025/zurich-classic-of-new-orleans/R2025018/course-stats",
            "https://www.pgatour.com/tournaments/2025/the-cj-cup-byron-nelson/R2025019/course-stats",
            "https://www.pgatour.com/tournaments/2025/truist-championship/R2025480/course-stats",
            "https://www.pgatour.com/tournaments/2025/oneflight-myrtle-beach-classic/R2025553/course-stats",
            "https://www.pgatour.com/tournaments/2025/pga-championship/R2025033/course-stats",
            "https://www.pgatour.com/tournaments/2025/charles-schwab-challenge/R2025021/course-stats",
            "https://www.pgatour.com/tournaments/2025/the-memorial-tournament-presented-by-workday/R2025023/course-stats",
            "https://www.pgatour.com/tournaments/2025/rbc-canadian-open/R2025032/course-stats",
            "https://www.pgatour.com/tournaments/2025/us-open/R2025026/course-stats",
            "https://www.pgatour.com/tournaments/2025/travelers-championship/R2025034/course-stats",
            "https://www.pgatour.com/tournaments/2025/rocket-classic/R2025524/course-stats",
            "https://www.pgatour.com/tournaments/2025/john-deere-classic/R2025030/course-stats",
            "https://www.pgatour.com/tournaments/2025/genesis-scottish-open/R2025541/course-stats",
            "https://www.pgatour.com/tournaments/2025/isco-championship/R2025518/course-stats",
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
