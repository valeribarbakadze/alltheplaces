from typing import Iterable

from scrapy import FormRequest, Spider
from scrapy.http import Response

from locations.categories import Categories, apply_category
from locations.items import Feature


class PizzaShoppeUSSpider(Spider):
    name = "pizza_shoppe_us"
    item_attributes = {"brand": "Pizza Shoppe"}
    allowed_domains = ["pizzashoppe.com"]
    start_urls = ["https://pizzashoppe.com/locations/"]

    def parse(self, response: Response) -> Iterable[FormRequest]:
        if not response.xpath('//script[contains(text(), "store_locator_options")]'):
            raise ValueError("The store locator configuration is missing")
        yield FormRequest(
            "https://pizzashoppe.com/wp-admin/admin-ajax.php",
            formdata={"action": "get_all_stores", "lat": "", "lng": ""},
            callback=self.parse_locations,
        )

    def parse_locations(self, response: Response) -> Iterable[Feature]:
        data = response.json()
        if not isinstance(data, dict) or not data:
            raise ValueError("The store feed returned no locations")
        for location in data.values():
            item = Feature(
                ref=location["ID"],
                branch=location["na"],
                street_address=location["st"],
                city=location["ct"].strip(),
                state=location["rg"],
                postcode=location["zp"],
                country="US",
                phone=location.get("te"),
                website=location["gu"],
                lat=location["lat"],
                lon=location["lng"],
            )
            apply_category(Categories.RESTAURANT, item)
            item["extras"]["cuisine"] = "pizza"
            yield item
