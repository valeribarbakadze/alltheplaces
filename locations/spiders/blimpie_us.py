from typing import Any, Iterable

from chompjs import parse_js_object
from scrapy.http import Response

from locations.categories import Categories, apply_category
from locations.items import Feature
from locations.json_blob_spider import JSONBlobSpider


class BlimpieUSSpider(JSONBlobSpider):
    """
    Blimpie is operated by Kahala Brands, which serves its official store
    locator as a series of `Locator.stores[n] = {...}` JavaScript assignments
    embedded in the HTML of https://www.blimpie.com/stores/.

    The same pattern is used by sibling Kahala brands, see taco_time_us.py and
    sweetfrog_us.py.
    """

    name = "blimpie_us"
    item_attributes = {"brand": "Blimpie", "brand_wikidata": "Q4926479"}
    start_urls = ["https://www.blimpie.com/stores/"]
    custom_settings = {"ROBOTSTXT_OBEY": False}

    def extract_json(self, response: Response) -> list[dict]:
        return [
            parse_js_object(line.split(" = ", 1)[1])
            for line in response.text.splitlines()
            if "Locator.stores[" in line and " = {" in line
        ]

    def pre_process_data(self, location: dict) -> None:
        location["street_address"] = location.pop("Address", "").strip().strip(",")
        location["ref"] = location.pop("StoreId", None)
        location["name"] = location.pop("Name", None)
        # The locator stores city names upper cased.
        if city := location.get("City"):
            location["City"] = city.title()

    def post_process_item(self, item: Feature, response: Response, location: dict, **kwargs: Any) -> Iterable[Feature]:
        # "O" = open. Coming soon and closed locations use other status codes.
        if location.get("StoreStatusId") != "O":
            return
        if location.get("CountryCode") != "US":
            return
        if location.get("Seasonal") == "Yes":
            item["extras"]["seasonal"] = "yes"

        item["branch"] = item.pop("name", None)
        item["website"] = response.urljoin("/stores/{}".format(location["ref"]))

        if location.get("Corporate") == "Yes":
            item["operator"] = "Kahala Brands"

        apply_category(Categories.FAST_FOOD, item)
        item["extras"]["cuisine"] = "sandwich"

        yield item
