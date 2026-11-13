import re
from typing import Iterable

from scrapy import Spider
from scrapy.http import Response

from locations.categories import Categories, apply_category
from locations.items import Feature


class WillieJewellsUSSpider(Spider):
    name = "willie_jewells_us"
    item_attributes = {"brand": "Willie Jewell's Old School Bar-B-Q"}
    allowed_domains = ["williejewells.com"]
    start_urls = ["https://williejewells.com/locations/"]

    def parse(self, response: Response) -> Iterable[Feature]:
        seen = set()
        tiles = response.css(".location-tile")
        if not tiles:
            raise ValueError("The location tiles are missing")
        for tile in tiles:
            phone = tile.css('a[href^="tel:"]::attr(href)').get()
            if not phone:
                continue
            ref = re.sub(r"\D", "", phone)[-10:]
            if ref in seen:
                continue
            seen.add(ref)
            address = tile.xpath("normalize-space(.//address)").get()
            match = re.fullmatch(r"(.+),\s*([^,]+),\s*([A-Z]{2})\s+(\d{5})", address)
            if not match:
                raise ValueError(f"Unrecognized address: {address}")
            item = Feature(
                ref=ref,
                branch=tile.xpath("normalize-space(.//h2)").get(),
                street_address=match[1],
                city=match[2],
                state=match[3],
                postcode=match[4],
                country="US",
                phone=phone,
                website=response.url,
            )
            apply_category(Categories.RESTAURANT, item)
            item["extras"]["cuisine"] = "barbecue"
            yield item
