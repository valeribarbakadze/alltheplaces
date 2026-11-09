from typing import Any

import chompjs
from scrapy import Spider
from scrapy.http import Response

from locations.categories import Categories, Extras, apply_category, apply_yes_no
from locations.hours import OpeningHours
from locations.items import Feature


class OnTheBorderUSSpider(Spider):
    name = "on_the_border_us"
    item_attributes = {"brand": "On The Border", "brand_wikidata": "Q7091305"}
    start_urls = ["https://www.ontheborder.com/locations/"]

    SERVICES = {"dinein": Extras.INDOOR_SEATING, "delivery": Extras.DELIVERY, "pickup": Extras.TAKEAWAY}

    def parse(self, response: Response, **kwargs: Any) -> Any:
        # The locator carries its whole MapSVG database in the page.
        database = chompjs.parse_js_object(response.text.split("var mapsvg_options = ", 1)[1])
        for location in database["data_db"]["objects"]:
            details = location["post"]["acf"]
            item = Feature(
                ref=details["restaurant_number"],
                # The address as the restaurant states it, rather than the
                # plugin's geocoding of it, which differs at the airport.
                street_address=location["street_address"],
                city=location["city"],
                state=location["state_short"],
                postcode=location["zip_code"],
                phone=details["phone_number"],
                website=location["post"]["url"],
                # The pin the locator stores. The google_maps_url beside it is
                # not trustworthy: Rapid City's centres on California.
                lat=location["location"]["lat"],
                lon=location["location"]["lng"],
            )
            if location["name"].casefold() != location["city"].casefold():
                item["branch"] = location["name"]
            item["opening_hours"] = OpeningHours()
            for rule in details["hours"]:
                item["opening_hours"].add_ranges_from_string(f"{rule['day_or_day_range']} {rule['hour_range']}")
            for service in details["available_services"]:
                if extra := self.SERVICES.get(service["value"]):
                    apply_yes_no(extra, item, True)
            apply_category(Categories.RESTAURANT, item)
            yield item
