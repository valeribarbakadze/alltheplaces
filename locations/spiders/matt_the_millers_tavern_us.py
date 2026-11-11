from typing import Any, Iterable

from scrapy.http import Response
from scrapy.spiders import SitemapSpider

from locations.categories import Categories, apply_category
from locations.items import Feature
from locations.structured_data_spider import StructuredDataSpider


class MattTheMillersTavernUSSpider(SitemapSpider, StructuredDataSpider):
    name = "matt_the_millers_tavern_us"
    item_attributes = {"brand": "Matt the Miller's Tavern Steakhouse"}
    sitemap_urls = ["https://mtmtavern.com/sitemap_index.xml"]
    # Each restaurant repeats its Restaurant block on every page beneath it, so only the top of
    # each tree is read; the other pages at that level state no Restaurant.
    sitemap_rules = [(r"^https://mtmtavern\.com/[^/]+/$", "parse_sd")]
    # One account for the brand, linked from the footer of every page.
    search_for_facebook = False

    def post_process_item(self, item: Feature, response: Response, ld_data: dict, **kwargs: Any) -> Iterable[Feature]:
        item.pop("name")
        item["branch"] = item["city"]
        apply_category(Categories.RESTAURANT, item)
        item["extras"]["cuisine"] = "steak_house"
        yield item
