import json
from typing import Iterable
from urllib.parse import urlencode

from scrapy import Request, Spider
from scrapy.http import Response

from locations.categories import Categories, apply_category
from locations.hours import OpeningHours
from locations.items import Feature


class BodybriteCAUSSpider(Spider):
    name = "bodybrite_ca_us"
    item_attributes = {"brand": "BodyBrite"}
    allowed_domains = ["bodybriteusa.com"]
    start_urls = ["https://bodybriteusa.com/locations/"]

    def parse(self, response: Response) -> Iterable[Request]:
        script = response.xpath('//script[contains(text(), "var ASL_REMOTE =")]/text()').get()
        if not script:
            raise ValueError("The public map configuration is missing")
        config = json.JSONDecoder().raw_decode(script.split("var ASL_REMOTE =", 1)[1].lstrip())[0]
        params = {"action": "asl_load_stores", "nonce": config["nonce"], "load_all": 1, "layout": 1}
        yield Request(config["ajax_url"] + "?" + urlencode(params), callback=self.parse_locations)

    def parse_locations(self, response: Response) -> Iterable[Feature]:
        locations = response.json()
        if not isinstance(locations, list) or not locations:
            raise ValueError("The map feed returned no locations")
        for location in locations:
            item = Feature(
                ref=location["id"],
                branch=location["title"],
                street_address=location["street"],
                city=location["city"],
                state=location["state"].upper(),
                postcode=location["postal_code"],
                country=location["country"],
                lat=location["lat"],
                lon=location["lng"],
                phone=location.get("phone"),
                website=location.get("website") or self.start_urls[0],
            )
            hours = OpeningHours()
            for day, ranges in json.loads(location.get("open_hours") or "{}").items():
                if not isinstance(ranges, list):
                    continue
                for interval in ranges:
                    hours.add_ranges_from_string(f"{day} {interval}")
            item["opening_hours"] = hours
            apply_category(Categories.SHOP_BEAUTY_SPA, item)
            yield item
