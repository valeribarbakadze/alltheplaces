import re
from typing import Any, Iterable

from scrapy import Selector, Spider
from scrapy.http import Request, Response

from locations.categories import Categories, apply_category
from locations.hours import DAYS, NAMED_DAY_RANGES_EN, OpeningHours
from locations.items import Feature


class PietrosPizzaUSSpider(Spider):
    name = "pietros_pizza_us"
    item_attributes = {"brand": "Pietro's Pizza"}
    start_urls = ["https://pietrosrestaurants.com/locations/"]
    # robots.txt asks for twenty seconds between requests, in the group that
    # covers everyone, and Scrapy applies none of it by itself.
    custom_settings = {"DOWNLOAD_DELAY": 20}
    ADDRESS = re.compile(r"^(?P<street>.+),\s*(?P<city>[^,]+),\s*(?P<state>[A-Z]{2})\s+(?P<postcode>\d{5})$")
    # Hood River states "Everyday", which the parser's own table of named day
    # ranges does not hold, and which it then drops in silence.
    NAMED_DAYS = NAMED_DAY_RANGES_EN | {"Everyday": DAYS}

    def parse(self, response: Response, **kwargs: Any) -> Iterable[Request]:
        # The closed Beaverton restaurant and the corporate office each keep a
        # page under /locations/, and this list offers neither.
        yield from response.follow_all(
            response.xpath('//a[normalize-space(.) = "View Location"]/@href'), callback=self.parse_location
        )

    def parse_location(self, response: Response, **kwargs: Any) -> Iterable[Feature]:
        phone = self.block(response, "Phone")
        address = self.ADDRESS.match(self.value(self.block(response, "Location"))[0])
        item = Feature(
            ref=response.url.strip("/").rsplit("/", 1)[-1],
            branch=address["city"],
            website=response.url,
            street_address=address["street"],
            city=address["city"],
            state=address["state"],
            postcode=address["postcode"],
            # Every page lists all three restaurants' numbers in its footer.
            phone=phone.xpath('.//a[starts-with(@href, "tel:")]/@href').get(),
            email=phone.xpath('.//a[starts-with(@href, "mailto:")]/@href').get(),
        )

        # The days and the times are stated as alternating lines.
        hours = self.value(self.block(response, "Hours"))
        item["opening_hours"] = OpeningHours()
        for days, span in zip(hours[::2], hours[1::2]):
            item["opening_hours"].add_ranges_from_string(f"{days} {span}", named_day_ranges=self.NAMED_DAYS)

        # No coordinates: Milwaukie publishes only a shortened link, Hood River
        # a Google search for its address, and Salem a link whose coordinates
        # are Milwaukie's, 60 km away.
        apply_category(Categories.RESTAURANT, item)
        item["extras"]["cuisine"] = "pizza"
        yield item

    @staticmethod
    def block(response: Response, label: str) -> Selector:
        return response.xpath(
            f'//div[contains(@class, "location-page-stat")][.//p[normalize-space(text()) = "{label}"]]'
        )

    @staticmethod
    def value(block: Selector) -> list[str]:
        lines = block.xpath('.//p[not(contains(@class, "text-uppercase"))]//text()').getall()
        return [text for raw in lines if (text := raw.strip())]
