import json
from typing import Iterable
from urllib.parse import urlsplit

from scrapy import Spider
from scrapy.http import Response

from locations.categories import Categories, apply_category
from locations.items import Feature


class ToastSpider(Spider):
    cuisine = None

    def parse(self, response: Response) -> Iterable[Feature]:
        script = response.xpath('//script[contains(text(), "window.__APOLLO_STATE__ =")]/text()').get()
        if not script:
            raise ValueError("Toast location state is missing; check for a block or layout change")
        state = json.JSONDecoder().raw_decode(script.split("window.__APOLLO_STATE__ =", 1)[1].lstrip())[0]
        locations = [value for key, value in state.items() if key.startswith("RestaurantLocation:")]
        if not locations:
            raise ValueError("Toast returned no restaurant locations")
        path = "/online/" if urlsplit(response.url).hostname == "order.toasttab.com" else "/order/"
        for location in locations:
            if location.get("country") != "US":
                continue
            item = Feature(
                ref=location["id"],
                branch=location["name"].strip(),
                street_address=" ".join(filter(None, [location.get("address1"), location.get("address2")])),
                city=location.get("city"),
                state=location.get("state") or location.get("administrativeArea"),
                postcode=location.get("zipcode"),
                country=location["country"],
                phone=location.get("phoneNumber"),
                lat=location.get("lat"),
                lon=location.get("long"),
                website=response.urljoin(path + location["shortUrl"]),
            )
            # These schedules describe ordering windows, not necessarily dining hours.
            apply_category(Categories.RESTAURANT, item)
            if self.cuisine:
                item["extras"]["cuisine"] = self.cuisine
            yield item
