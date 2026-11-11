import json
import re
from typing import Any, Iterable

from scrapy.http import Request, Response

from locations.categories import Categories, apply_category
from locations.hours import OpeningHours
from locations.items import Feature
from locations.structured_data_spider import StructuredDataSpider


class SnappySaladsUSSpider(StructuredDataSpider):
    name = "snappy_salads_us"
    item_attributes = {"brand": "Snappy Salads"}
    start_urls = ["https://www.snappysalads.com/hours-and-locations/"]
    TIMES = re.compile(r"\d\s*[ap]m", re.IGNORECASE)

    def parse(self, response: Response, **kwargs: Any) -> Iterable[Request]:
        # All eight are listed here as subOrganization, but only their own pages carry a pin.
        group = json.loads(response.xpath('//script[@type="application/ld+json"]/text()').get())
        for restaurant in group["subOrganization"]:
            yield response.follow(restaurant["url"], callback=self.parse_sd)

    def post_process_item(self, item: Feature, response: Response, ld_data: dict, **kwargs: Any) -> Iterable[Feature]:
        # The name carries the city after a comma, which addr:city already states.
        item["branch"] = item.pop("name").split(",")[0]
        pin = response.xpath("//div[@data-gmaps-lat]")
        item["lat"], item["lon"] = pin.attrib["data-gmaps-lat"], pin.attrib["data-gmaps-lng"]
        # Seven of the eight state no openingHours, so the hours are read from the page, where
        # the requirement for a time also skips the dated holiday closures stated beside them.
        item["opening_hours"] = OpeningHours()
        for rule in response.xpath("//p//text()").getall():
            if self.TIMES.search(rule):
                item["opening_hours"].add_ranges_from_string(rule)
        apply_category(Categories.FAST_FOOD, item)
        item["extras"]["cuisine"] = "salad"
        yield item
