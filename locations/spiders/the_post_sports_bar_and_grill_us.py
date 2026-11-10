import json
import re
from typing import Any, Iterable

from scrapy import Spider
from scrapy.http import Response

from locations.categories import Categories, apply_category
from locations.hours import OpeningHours, sanitise_day
from locations.items import Feature


class ThePostSportsBarAndGrillUSSpider(Spider):
    name = "the_post_sports_bar_and_grill_us"
    item_attributes = {"brand": "The Post Sports Bar & Grill"}
    start_urls = ["https://thepostsportsbar.com/locations/"]
    # robots.txt opens with "Crawl-delay: 10" above its first User-agent line,
    # where it belongs to no group and so is not enforced. Honoured anyway.
    custom_settings = {"DOWNLOAD_DELAY": 10}
    LOCALITY = re.compile(r"^(?P<city>[^,]+),\s*(?P<state>[A-Z]{2})\s+(?P<postcode>\d{5})$")

    def parse(self, response: Response, **kwargs: Any) -> Iterable[Feature]:
        for location in response.xpath('//div[@class="tracking-location-item"]'):
            street, locality = location.attrib["data-address"].split("<br>")
            address = self.LOCALITY.match(locality.strip())
            item = Feature(
                ref=location.attrib["data-location"],
                branch=location.attrib["data-location"],
                street_address=street.strip(),
                city=address["city"],
                state=address["state"],
                postcode=address["postcode"],
                phone=location.attrib["data-phone"],
                lat=location.attrib["data-lat"],
                lon=location.attrib["data-lng"],
                facebook=location.attrib["data-facebook"],
            )

            # The page's own structured data closes an hour later on Friday and
            # Saturday, but it describes only two of the four restaurants, so
            # these times are read as the maintained ones.
            item["opening_hours"] = OpeningHours()
            for day, span in json.loads(location.attrib["data-hours"]).items():
                opens, closes = span.split(" - ")
                item["opening_hours"].add_range(sanitise_day(day), opens, closes, time_format="%I%p")

            apply_category(Categories.RESTAURANT, item)
            item["extras"]["cuisine"] = "american"
            yield item
