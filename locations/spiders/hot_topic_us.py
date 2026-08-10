from typing import Any, AsyncIterator, Iterable

from scrapy import Request, Spider
from scrapy.http import JsonRequest, Response

from locations.categories import Categories, apply_category
from locations.dict_parser import DictParser
from locations.items import Feature
from locations.pipelines.address_clean_up import merge_address_lines
from locations.spiders.build_a_bear_us import BuildABearUSSpider
from locations.user_agents import BROWSER_DEFAULT


class HotTopicUSSpider(Spider):
    """
    Hot Topic runs on Salesforce Commerce Cloud (Demandware). The locator
    calls the standard `Stores-FindStores` controller; a single query from the
    centre of the contiguous US with a 2500 mile radius returns every store.
    """

    name = "hot_topic_us"
    item_attributes = {"brand": "Hot Topic", "brand_wikidata": "Q9294032"}
    allowed_domains = ["www.hottopic.com"]
    custom_settings = {"ROBOTSTXT_OBEY": False, "USER_AGENT": BROWSER_DEFAULT}

    async def start(self) -> AsyncIterator[Request]:
        yield JsonRequest(
            url="https://www.hottopic.com/on/demandware.store/Sites-hottopic-Site/default/Stores-FindStores"
            "?showMap=false&radius=2500&lat=39.8283&long=-98.5795&postalCode=US"
        )

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

            item["opening_hours"] = BuildABearUSSpider.parse_hours(location.get("storeHours"))

            apply_category(Categories.SHOP_CLOTHES, item)

            yield item
