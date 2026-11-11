import re
from typing import Any, Iterable

import chompjs
from scrapy import Spider
from scrapy.http import Response

from locations.categories import Categories, apply_category
from locations.dict_parser import DictParser
from locations.hours import DAYS, OpeningHours
from locations.items import Feature


class GrabbagreenUSSpider(Spider):
    name = "grabbagreen_us"
    item_attributes = {"brand": "Grabbagreen"}
    allowed_domains = ["www.grabbagreen.com"]
    # The brand's own host serves the Kahala group locator that blimpie_us and taco_time_us read from
    # their brands' hosts too. locator.kahalamgmt.com serves the same payload and disallows every
    # agent, so it is left alone.
    start_urls = ["https://www.grabbagreen.com/locator/index.php?brand=34&mode=map"]

    def parse(self, response: Response, **kwargs: Any) -> Iterable[Feature]:
        for match in re.finditer(r"Locator\.stores\[\d+\]\s*=\s*", response.text):
            location = chompjs.parse_js_object(response.text[match.end() :])
            if location["StatusName"] == "Coming Soon":
                continue

            item = DictParser.parse(location)
            item.pop("addr_full")
            item["street_address"] = location["Address"]
            # "Name" is free text: it names the shopping centre on one store and repeats the
            # street address on the other, so it is only a branch name when it holds no digits.
            name = item.pop("name")
            if name and not any(character.isdigit() for character in name):
                item["branch"] = name

            if location["StoreStatusId"] == "TC":
                # Stated closed rather than unknown, which is what set_closed is for.
                item["opening_hours"] = OpeningHours()
                item["opening_hours"].set_closed(DAYS)

            apply_category(Categories.FAST_FOOD, item)
            item["extras"]["cuisine"] = "salad"
            yield item
