import re
from typing import Any, Iterable

from scrapy.http import Response
from scrapy.spiders import SitemapSpider

from locations.categories import Categories, apply_category
from locations.items import Feature


class MerrimansUSSpider(SitemapSpider):
    name = "merrimans_us"
    item_attributes = {"brand": "Merriman's"}
    sitemap_urls = ["https://www.merrimanshawaii.com/sitemap.xml"]
    sitemap_rules = [(r"/location/", "parse_location")]
    # The title is the one place each restaurant's own name is stated in a
    # consistent shape. Its heading reads "Merriman's Restaurant <island>
    # (<place>)" on three and reverses the two on Honolulu.
    BRANCH = re.compile(r"Merriman[’']s\s+(?P<branch>[A-Z][a-z]+)")
    TAIL = re.compile(r"(?P<state>[A-Z]{2})\s+(?P<postcode>\d{5})$")

    def parse_location(self, response: Response, **kwargs: Any) -> Iterable[Feature]:
        pin = response.xpath("//div[@data-gmaps-lat]")
        address = pin.attrib["data-gmaps-address"]
        tail = self.TAIL.search(address)
        # Poipu states Koloa on its street line and its island where the city
        # belongs, so the address is kept whole rather than broken apart.
        item = Feature(
            ref=response.url.strip("/").rsplit("/", 1)[-1],
            branch=self.BRANCH.search(response.xpath("//title/text()").get())["branch"],
            website=response.url,
            addr_full=address,
            state=tail["state"],
            postcode=tail["postcode"],
            phone=response.xpath('//a[starts-with(@href, "tel:")]/@href').get(),
            lat=pin.attrib["data-gmaps-lat"],
            lon=pin.attrib["data-gmaps-lng"],
        )
        # No opening_hours: each restaurant states its times by meal service and
        # only Maui names a day, so there is nothing to attach them to.
        apply_category(Categories.RESTAURANT, item)
        item["extras"]["cuisine"] = "hawaiian"
        yield item
