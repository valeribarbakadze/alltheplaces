from typing import Iterable

from scrapy.http import TextResponse

from locations.categories import Categories, apply_category
from locations.hours import DAYS_EN
from locations.items import Feature
from locations.storefinders.wp_store_locator import WPStoreLocatorSpider


class ColorMeMineUSSpider(WPStoreLocatorSpider):
    """
    Color Me Mine's official locator is the WP Store Locator WordPress plugin
    served from https://www.colormemine.com/wp-admin/admin-ajax.php. A single
    query centred on the contiguous US with a 5000 km radius returns every
    location worldwide.
    """

    name = "color_me_mine_us"
    item_attributes = {"brand": "Color Me Mine", "brand_wikidata": "Q121433027"}
    allowed_domains = ["www.colormemine.com"]
    start_urls = [
        "https://www.colormemine.com/wp-admin/admin-ajax.php?action=store_search&lat=39.8283&lng=-98.5795&max_results=500&search_radius=5000"
    ]
    days = DAYS_EN

    def post_process_item(self, item: Feature, response: TextResponse, feature: dict) -> Iterable[Feature]:
        # The locator lists franchises which have not opened yet.
        if "coming soon" in (item.get("name") or "").lower():
            return
        # The locator also covers Canada and Costa Rica.
        if feature.get("country") != "United States":
            return

        item["branch"] = item.pop("name", None)
        item["ref"] = feature.get("id")
        item["website"] = feature.get("permalink") or feature.get("url")

        apply_category(Categories.SHOP_ART, item)
        item["extras"]["craft"] = "pottery"

        yield item
