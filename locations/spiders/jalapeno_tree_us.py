from typing import Any, Iterable
from urllib.parse import urlsplit

from scrapy import Request
from scrapy.http import Response

from locations.categories import Categories, apply_category
from locations.google_url import extract_google_position
from locations.items import Feature
from locations.structured_data_spider import StructuredDataSpider


class JalapenoTreeUSSpider(StructuredDataSpider):
    name = "jalapeno_tree_us"
    item_attributes = {"brand": "Jalapeno Tree"}
    allowed_domains = ["jalapenotree.com"]
    start_urls = ["https://jalapenotree.com/restaurants-locations/"]
    wanted_types = ["Restaurant"]

    def parse(self, response: Response, **kwargs: Any) -> Iterable[Request]:
        links = set(response.css('a[href*="jalapenotree.com/locations/"]::attr(href)').getall())
        if not links:
            raise ValueError("No restaurant links found in the location directory")
        yield from response.follow_all(sorted(links), callback=self.parse_sd)

    def post_process_item(self, item: Feature, response: Response, ld_data: dict, **kwargs: Any) -> Iterable[Feature]:
        item["ref"] = urlsplit(response.url).path.strip("/").split("/")[-1]
        item["phone"] = ld_data.get("telephone") or ld_data.get("address", {}).get("telephone")
        if not item.get("lat") or not item.get("lon"):
            extract_google_position(item, response)
        apply_category(Categories.RESTAURANT, item)
        item["extras"]["cuisine"] = "mexican"
        yield item
