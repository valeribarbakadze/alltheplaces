import json
import re
from typing import Iterable

from scrapy import Spider
from scrapy.http import Response

from locations.categories import Categories, apply_category
from locations.hours import DAYS, OpeningHours
from locations.items import Feature


class KahalaSpider(Spider):
    category = Categories.RESTAURANT
    cuisine = None

    def parse(self, response: Response) -> Iterable[Feature]:
        matches = list(re.finditer(r"Locator\.stores\[\d+\]\s*=\s*", response.text))
        if not matches:
            raise ValueError("The locator returned no store objects; check for a block or layout change")
        for match in matches:
            location = json.JSONDecoder().raw_decode(response.text[match.end() :])[0]
            if location.get("StoreStatusId") == "CS" or location.get("StatusName") == "Coming Soon":
                continue
            item = Feature(
                ref=location["StoreId"],
                website=location.get("OrderOnline") or response.url,
                street_address=location["Address"].strip().rstrip(","),
                city=location["City"],
                state=location["State"],
                postcode=location["Zip"],
                country=location.get("CountryCode") or "US",
                phone=location.get("Phone"),
                lat=location["Latitude"],
                lon=location["Longitude"],
            )
            if branch := location.get("Name"):
                if not any(character.isdigit() for character in branch):
                    item["branch"] = branch
            if location.get("StoreStatusId") == "TC" or location.get("StatusName") == "Temporary Closed":
                item["opening_hours"] = OpeningHours()
                item["opening_hours"].set_closed(DAYS)
            apply_category(self.category, item)
            if self.cuisine:
                item["extras"]["cuisine"] = self.cuisine
            yield item
