import re
from typing import Any, Iterable

from scrapy import Spider
from scrapy.http import Response

from locations.categories import Categories, apply_category
from locations.hours import OpeningHours, sanitise_day
from locations.items import Feature


class TropicalTanUSSpider(Spider):
    name = "tropical_tan_us"
    item_attributes = {"brand": "Tropical Tan"}
    start_urls = ["https://www.tropical-tan.com/contact-tropical-tan"]
    LOCALITY = re.compile(r"^(?P<city>[^,]+),\s*(?P<state>[A-Z]{2})\s+(?P<postcode>\d{5})$")
    # Walton states its number across two text nodes and offers Dry Ridge's
    # address as one of its two mail links, so both are read from the text each
    # salon shows rather than from what its links point at.
    PHONE = re.compile(r"\(\d{3}\)[-\s]?\d{3}-\d{4}")
    EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
    DAYS = re.compile(r"^[A-Z]+(?:\s*-\s*[A-Z]+)?$")
    CLOSED = re.compile(r"^CLOSED\s+(?P<day>[A-Z]+)$")
    SPAN = re.compile(r"^\d{1,2}:\d{2}\s*[ap]m\s*-\s*\d{1,2}:\d{2}\s*[ap]m$", re.IGNORECASE)

    def parse(self, response: Response, **kwargs: Any) -> Iterable[Feature]:
        for salon in response.xpath('//div[contains(@class, "dmRespColsWrapper")]'):
            lines = [text for raw in salon.xpath(".//text()").getall() if (text := raw.strip())]
            lines = [line for line in lines if line != "Get Directions"]
            address = next((i for i, line in enumerate(lines) if self.LOCALITY.match(line)), None)
            if address is None:
                continue
            locality = self.LOCALITY.match(lines[address])
            blob = salon.xpath("string()").get()
            # Dry Ridge and Florence shout their names where Walton does not.
            branch = lines[0].title() if lines[0].isupper() else lines[0]
            item = Feature(
                ref=branch,
                branch=branch,
                # Walton gives its suite on a line of its own.
                street_address=" ".join(lines[1:address]),
                city=locality["city"],
                state=locality["state"],
                postcode=locality["postcode"],
                phone=self.PHONE.search(blob).group(),
                email=self.EMAIL.search(blob).group(),
            )

            item["opening_hours"] = OpeningHours()
            for i, line in enumerate(lines):
                if closed := self.CLOSED.match(line):
                    item["opening_hours"].set_closed(sanitise_day(closed["day"]))
                elif self.DAYS.match(line) and self.SPAN.match(lines[i + 1] if i + 1 < len(lines) else ""):
                    item["opening_hours"].add_ranges_from_string(f"{line} {lines[i + 1]}")

            apply_category(Categories.SHOP_BEAUTY, item)
            yield item
