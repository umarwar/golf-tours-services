# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem


class DuplicatesPipeline:
    def __init__(self):
        self.urls_seen = set()

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        if adapter["tournament_url"] in self.urls_seen:
            raise DropItem(f"Duplicate tournament found: {item['tournament_url']}")
        else:
            self.urls_seen.add(adapter["tournament_url"])
            return item


class PgatourScraperPipeline:
    def process_item(self, item, spider):
        return item
