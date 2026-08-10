from typing import Any, AsyncIterator, Iterable

from scrapy import Request, Spider
from scrapy.http import JsonRequest, Response

from locations.categories import Categories, apply_category
from locations.dict_parser import DictParser
from locations.hours import OpeningHours
from locations.items import Feature


class FoodmaxxUSSpider(Spider):
    """
    FoodMaxx (Save Mart Companies) runs a Swiftly-powered Remix storefront.
    Appending `_data=root` to the store locator URL returns the raw root
    loader JSON, which contains the complete `storeList.stores` array for the
    supplied coordinates and radius. FoodMaxx only trades in California and
    Nevada, so one wide query covers the chain.
    """

    name = "foodmaxx_us"
    item_attributes = {"brand": "FoodMaxx", "brand_wikidata": "Q61894844"}
    allowed_domains = ["foodmaxx.com"]

    async def start(self) -> AsyncIterator[Request]:
        yield JsonRequest(
            url="https://foodmaxx.com/?lat=37.7749&lng=-121.4194&miles=500&showStoreLocator=true&_data=root"
        )

    def parse(self, response: Response, **kwargs: Any) -> Iterable[Feature]:
        for store in response.json().get("storeList", {}).get("stores", []):
            if store.get("location", {}).get("country") != "US":
                continue

            item = DictParser.parse(store.get("location", {}))
            item["ref"] = store.get("storeId")
            item["branch"] = (store.get("displayName") or "").title().strip()

            if phones := store.get("phoneNumbers"):
                item["phone"] = phones[0].get("value")

            item["opening_hours"] = self.parse_hours(store.get("hours", {}).get("weekly", []))

            apply_category(Categories.SHOP_SUPERMARKET, item)

            yield item

    @staticmethod
    def parse_hours(weekly: list[dict]) -> OpeningHours:
        oh = OpeningHours()
        for day_hours in weekly:
            day = day_hours.get("day")
            if not day:
                continue
            daily = day_hours.get("daily", {})
            if daily.get("type") == "OPEN_24_HOURS":
                oh.add_range(day.title(), "00:00", "23:59")
            elif daily.get("type") == "OPEN":
                open_time = daily.get("open", {}).get("open")
                close_time = daily.get("open", {}).get("close")
                if open_time and close_time:
                    if close_time.startswith("00:00"):
                        close_time = "23:59"
                    oh.add_range(day.title(), open_time[:5], close_time[:5])
        return oh
