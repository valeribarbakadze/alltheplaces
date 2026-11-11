from typing import Iterable

from scrapy.http import TextResponse

from locations.categories import Categories, apply_category
from locations.items import Feature
from locations.storefinders.agile_store_locator import AgileStoreLocatorSpider


class RemkeMarketsUSSpider(AgileStoreLocatorSpider):
    name = "remke_markets_us"
    item_attributes = {"brand": "Remke Markets"}
    allowed_domains = ["www.remkes.com"]

    def post_process_item(self, item: Feature, response: TextResponse, feature: dict) -> Iterable[Feature]:
        item["branch"] = item.pop("name")
        # Only one of the five states the page it has on this site.
        if feature["about_us"]:
            item["website"] = response.urljoin(feature["about_us"])
        apply_category(Categories.SHOP_SUPERMARKET, item)
        yield item
