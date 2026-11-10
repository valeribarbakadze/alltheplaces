import json
from typing import Any, Iterable

from scrapy.http import Request, Response

from locations.categories import Categories, apply_category
from locations.items import Feature
from locations.structured_data_spider import StructuredDataSpider


class IIIForksUSSpider(StructuredDataSpider):
    name = "iii_forks_us"
    item_attributes = {"brand": "III Forks"}
    start_urls = ["https://www.3forks.com/locations/"]
    # robots.txt states Crawl-delay: 10 in the group that covers everyone, and
    # Scrapy applies none of it by itself.
    custom_settings = {"DOWNLOAD_DELAY": 10}
    # One account each for the group, linked from every restaurant's page.
    search_for_facebook = False
    search_for_twitter = False

    def parse(self, response: Response, **kwargs: Any) -> Iterable[Request]:
        # The restaurants are listed here and in no sitemap.
        graph = json.loads(
            response.xpath('//script[@type="application/ld+json"][contains(., "ItemList")]/text()').get()
        )["@graph"]
        for restaurant in next(entity for entity in graph if entity["@type"] == "ItemList")["itemListElement"]:
            yield response.follow(restaurant["url"], callback=self.parse_sd)

    def post_process_item(self, item: Feature, response: Response, ld_data: dict, **kwargs: Any) -> Iterable[Feature]:
        item["ref"] = response.url.strip("/").rsplit("/", 1)[-1]
        # Two of the four are named "III Forks" and two "III Forks Steakhouse",
        # so the structured data's name says which brand but not which
        # restaurant. The locality does, and it is the word the group's own list
        # uses for each of them, Addison included, which it calls Dallas.
        item.pop("name")
        item["branch"] = item["city"]
        apply_category(Categories.RESTAURANT, item)
        item["extras"]["cuisine"] = "steak_house"
        yield item
