from typing import Any, Iterable

from scrapy import Selector, Spider
from scrapy.http import JsonRequest, Response

from locations.categories import Categories, apply_category
from locations.dict_parser import DictParser
from locations.hours import DAYS_EN, OpeningHours
from locations.items import Feature
from locations.pipelines.address_clean_up import merge_address_lines
from locations.user_agents import BROWSER_DEFAULT


class BuildABearUSSpider(Spider):
    """
    Build-A-Bear Workshop runs on Salesforce Commerce Cloud (Demandware). The
    locator calls the standard `Stores-FindStores` controller, which accepts a
    latitude/longitude and a radius in miles. A single national-radius query
    from the centre of the contiguous US returns every store in one response.
    """

    name = "build_a_bear_us"
    item_attributes = {"brand": "Build-A-Bear Workshop", "brand_wikidata": "Q1002992"}
    allowed_domains = ["www.buildabear.com"]
    custom_settings = {"ROBOTSTXT_OBEY": False, "USER_AGENT": BROWSER_DEFAULT}
    requires_proxy = True

    start_urls = [
        "https://www.buildabear.com/on/demandware.store/Sites-buildabear-us-Site/default/Stores-FindStores?format=json&lat=39&long=-98&radius=2500"
    ]

    async def start(self) -> Any:
        for url in self.start_urls:
            yield JsonRequest(url=url)

    def parse(self, response: Response, **kwargs: Any) -> Iterable[Feature]:
        for location in response.json().get("stores", []):
            if location.get("countryCode") != "US":
                continue

            item = DictParser.parse(location)
            item["ref"] = location.get("ID")
            item["branch"] = location.get("name")
            item.pop("name", None)
            item["street_address"] = merge_address_lines([location.get("address1"), location.get("address2")])
            item["postcode"] = location.get("postalCode")
            item["state"] = location.get("stateCode")
            item["country"] = location.get("countryCode")
            item["website"] = "https://www.buildabear.com/stores?StoreID={}".format(item["ref"])

            item["opening_hours"] = self.parse_hours(location.get("storeHours"))

            apply_category(Categories.SHOP_TOYS, item)

            yield item

    @staticmethod
    def parse_hours(store_hours: str | None) -> OpeningHours:
        oh = OpeningHours()
        if not store_hours:
            return oh
        for row in Selector(text=store_hours).xpath('//*[contains(@class, "hours-row")]'):
            days = row.xpath('.//*[contains(@class, "store-hours-day")]/text()').get("")
            times = row.xpath('.//*[contains(@class, "store-hours-time")]/text()').get("")
            oh.add_ranges_from_string("{} {}".format(days.strip(), times.strip()), days=DAYS_EN)
        if not oh.as_opening_hours():
            oh.add_ranges_from_string(" ".join(Selector(text=store_hours).xpath("//text()").getall()))
        return oh
