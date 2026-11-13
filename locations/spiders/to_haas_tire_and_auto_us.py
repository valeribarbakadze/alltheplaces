from typing import Any, Iterable

from scrapy import Request
from scrapy.http import Response

from locations.categories import Categories, apply_category
from locations.items import Feature
from locations.structured_data_spider import StructuredDataSpider


class ToHaasTireAndAutoUSSpider(StructuredDataSpider):
    name = "to_haas_tire_and_auto_us"
    item_attributes = {"brand": "T.O. Haas Tire & Auto"}
    allowed_domains = ["www.tohaastire.com"]
    start_urls = ["https://www.tohaastire.com/locations"]
    wanted_types = ["AutoRepair"]

    def parse(self, response: Response, **kwargs: Any) -> Iterable[Request]:
        links = set(response.css('a[href*="/locations/"][href*="/auto-repair-"]::attr(href)').getall())
        if not links:
            raise ValueError("No shop links found in the location directory")
        yield from response.follow_all(sorted(links), callback=self.parse_sd)

    def post_process_item(self, item: Feature, response: Response, ld_data: dict, **kwargs: Any) -> Iterable[Feature]:
        item["ref"] = ld_data["branchCode"]
        apply_category(Categories.SHOP_CAR_REPAIR, item)
        yield item
