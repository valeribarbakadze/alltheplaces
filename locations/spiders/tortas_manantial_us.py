from typing import Iterable

from scrapy.http import TextResponse

from locations.categories import Categories, apply_category
from locations.items import Feature
from locations.storefinders.agile_store_locator import AgileStoreLocatorSpider


class TortasManantialUSSpider(AgileStoreLocatorSpider):
    name = "tortas_manantial_us"
    item_attributes = {"brand": "Tortas Manantial"}
    allowed_domains = ["tortasmanantial.com"]

    def post_process_item(self, item: Feature, response: TextResponse, feature: dict) -> Iterable[Feature]:
        item["branch"] = item.pop("name").split(" - ", 1)[1]
        # One company address shared by all four shops.
        item.pop("email")
        apply_category(Categories.RESTAURANT, item)
        item["extras"]["cuisine"] = "mexican"
        yield item
