import re
from typing import Any, Iterable

from scrapy import Spider
from scrapy.http import Response

from locations.categories import Categories, apply_category
from locations.hours import OpeningHours
from locations.items import Feature


class FlipSideBurgerUSSpider(Spider):
    name = "flip_side_burger_us"
    item_attributes = {"brand": "Flip Side Burgers & Shakes"}
    start_urls = ["https://www.flipsideburger.com/"]
    # Hudson puts a comma between its street and city and Easton does not, so the city is read as
    # the one capitalised word before the state.
    ADDRESS = re.compile(
        r"^(?P<street>.+?),?\s+(?P<city>[A-Z][a-z]+),?\s+(?P<state>[A-Z]{2}|[A-Z][a-z]+)\s+(?P<postcode>\d{5})$"
    )
    PHONE = re.compile(r"^\d{3}-\d{3}-\d{4}$")
    TIMES = re.compile(r"\d{1,2}:\d{2}")

    def parse(self, response: Response, **kwargs: Any) -> Iterable[Feature]:
        for row in response.xpath('//div[contains(@class, "sqs-row")][.//h2]'):
            lines = [text for raw in row.xpath(".//p//text()").getall() if (text := raw.strip())]
            # The welcome text and the ordering links are headed the same way and state no address.
            addresses = [match for line in lines if (match := self.ADDRESS.match(line))]
            if not addresses:
                continue
            address = addresses[0]
            branch = row.xpath("normalize-space(.//h2)").get().title()
            item = Feature(
                ref=branch,
                branch=branch,
                street_address=address["street"],
                city=address["city"],
                state=address["state"],
                postcode=address["postcode"],
                phone=next(line for line in lines if self.PHONE.match(line)),
            )

            hours, unreadable = OpeningHours(), False
            for rule in next(line for line in lines if self.TIMES.search(line)).split("/"):
                if not rule.strip():
                    continue
                stated = hours.as_opening_hours()
                hours.add_ranges_from_string(rule)
                unreadable |= hours.as_opening_hours() == stated
            # Hudson writes "11:300pm" on its weekday rule, which the parser drops in silence.
            # Keeping the rest would state the restaurant is closed Monday to Thursday.
            if not unreadable:
                item["opening_hours"] = hours

            apply_category(Categories.RESTAURANT, item)
            item["extras"]["cuisine"] = "burger"
            yield item
