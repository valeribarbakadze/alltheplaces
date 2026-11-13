import re
from typing import Iterable
from urllib.parse import urlsplit

from scrapy import Request, Spider
from scrapy.http import Response

from locations.categories import Categories, apply_category
from locations.items import Feature


class GoferIceCreamUSSpider(Spider):
    name = "gofer_ice_cream_us"
    item_attributes = {"brand": "Gofer Ice Cream"}
    allowed_domains = ["gofericecream.com"]
    start_urls = ["https://gofericecream.com/locations/"]

    def parse(self, response: Response) -> Iterable[Request]:
        links = set(response.css('a[href*="gofericecream.com/project/"]::attr(href)').getall())
        if not links:
            raise ValueError("No ice cream shop links found")
        yield from response.follow_all(sorted(links), callback=self.parse_location)

    def parse_location(self, response: Response) -> Iterable[Feature]:
        headings = [heading.xpath("normalize-space(.)").get() for heading in response.css("h1, h2")]
        street = next((text for text in headings if re.match(r"^\d+\s", text)), None)
        locality = next(
            (match for text in headings if (match := re.fullmatch(r"(.+),\s*([A-Z]{2})\.?\s*(\d{5})", text))), None
        )
        if not street or not locality:
            raise ValueError("The shop's address headings are missing")
        item = Feature(
            ref=urlsplit(response.url).path.rstrip("/").split("/")[-1],
            street_address=street,
            city=locality[1],
            state=locality[2],
            postcode=locality[3],
            country="US",
            website=response.url,
            phone=response.css('a[href^="tel:"]::attr(href)').get(),
        )
        # The Cos Cob and Darien pages reuse the same embedded map. Keep the
        # published address, but omit map coordinates until the source is fixed.
        apply_category(Categories.ICE_CREAM, item)
        yield item
