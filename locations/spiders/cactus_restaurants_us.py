from typing import Any, Iterable

from scrapy.http import Response
from scrapy.spiders import SitemapSpider

from locations.categories import Categories, apply_category
from locations.items import Feature
from locations.structured_data_spider import StructuredDataSpider


class CactusRestaurantsUSSpider(SitemapSpider, StructuredDataSpider):
    name = "cactus_restaurants_us"
    item_attributes = {"brand": "Cactus Restaurants"}
    sitemap_urls = ["https://www.cactusrestaurants.com/sitemap.xml"]
    sitemap_rules = [(r"/location/", "parse_sd")]
    name_is_branch = True
    # One brand-wide page, reached through the group's sameAs on every location.
    search_for_facebook = False

    def post_process_item(self, item: Feature, response: Response, ld_data: dict, **kwargs: Any) -> Iterable[Feature]:
        item["ref"] = response.url.rsplit("/", 1)[-1]
        item["branch"] = item["branch"].removeprefix("Cactus ")
        apply_category(Categories.RESTAURANT, item)
        item["extras"]["cuisine"] = "mexican"
        yield item
