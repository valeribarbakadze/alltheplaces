import json
import re
from typing import Any, Iterable

from scrapy import Spider
from scrapy.http import Request, Response

from locations.categories import Categories, apply_category
from locations.hours import OpeningHours
from locations.items import Feature


class EuropeanStreetCafeUSSpider(Spider):
    name = "european_street_cafe_us"
    item_attributes = {"brand": "European Street Cafe"}
    start_urls = ["https://europeanstreet.com/contact"]
    # The map block writes its locality with a comma before the postcode.
    LOCALITY = re.compile(r"^(?P<city>[^,]+),\s*(?P<state>[A-Z]{2}),\s*(?P<postcode>\d{5})$")
    OPEN = re.compile(r"^Open\s+(?P<days>[A-Za-z]+)$")
    SPAN = re.compile(r"^\d{1,2}(?::\d{2})?\s*[ap]m\s*[-–]\s*\d{1,2}(?::\d{2})?\s*[ap]m$", re.IGNORECASE)

    def parse(self, response: Response, **kwargs: Any) -> Iterable[Request]:
        for link in response.xpath('//h4/a[contains(@href, "europeanstreet.com/")]'):
            yield response.follow(
                link.attrib["href"],
                callback=self.parse_location,
                cb_kwargs={"branch": link.xpath("string()").get().strip()},
            )

    def parse_location(self, response: Response, branch: str) -> Iterable[Feature]:
        # The map block states the marker and a structured address. It is also
        # the tie-breaker on the beach restaurant, which the locations list
        # places in Jacksonville where the block and the footer agree on
        # Jacksonville Beach.
        location = json.loads(
            response.xpath('//main//div[contains(@class, "sqs-block-map")]//div[@data-context]/@data-context').get()
        )["location"]
        locality = self.LOCALITY.match(location["addressLine2"])
        item = Feature(
            ref=response.url.strip("/").rsplit("/", 1)[-1],
            branch=branch,
            website=response.url,
            street_address=location["addressLine1"],
            city=locality["city"],
            state=locality["state"],
            postcode=locality["postcode"],
            # Each page repeats all three restaurants in its footer, outside main.
            phone=response.xpath('//main//a[starts-with(@href, "tel:")]/@href').get(),
            lat=location["markerLat"],
            lon=location["markerLng"],
        )

        item["opening_hours"] = OpeningHours()
        for paragraph in response.xpath("//main//p"):
            lines = [text for raw in paragraph.xpath(".//text()").getall() if (text := raw.strip())]
            if len(lines) > 1 and (days := self.OPEN.match(lines[0])) and self.SPAN.match(lines[1]):
                item["opening_hours"].add_ranges_from_string(f"{days['days']} {lines[1]}")

        apply_category(Categories.RESTAURANT, item)
        yield item
