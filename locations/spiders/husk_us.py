import re
from typing import Any, Iterable

from scrapy import Spider
from scrapy.http import Request, Response

from locations.categories import Categories, apply_category
from locations.google_url import extract_google_position
from locations.items import Feature


class HuskUSSpider(Spider):
    name = "husk_us"
    item_attributes = {"brand": "Husk"}
    start_urls = ["https://huskrestaurant.com/"]
    # Every Husk robots.txt opens with "Crawl-delay: 10" above its first User-agent line, where it
    # binds to no group, but the intent is plain.
    custom_settings = {"DOWNLOAD_DELAY": 10}
    # Charleston publishes no postcode.
    ADDRESS = re.compile(r"^(?P<street>.+),\s*(?P<city>[^,]+),\s*(?P<state>[A-Z]{2})(?:\s+(?P<postcode>\d{5}))?$")

    def parse(self, response: Response, **kwargs: Any) -> Iterable[Request]:
        # Each restaurant keeps a site of its own, named only from this landing page.
        yield from response.follow_all(response.xpath('//a[@class="card-link"]/@href'), self.parse_location)

    def parse_location(self, response: Response, **kwargs: Any) -> Iterable[Feature]:
        footer = response.xpath('//div[contains(@class, "footer-column") and contains(@class, "location")]')
        address = self.ADDRESS.match(footer.xpath('normalize-space(.//a[@title="Directions"])').get())
        item = Feature(
            ref=response.url,
            branch=address["city"],
            website=response.url,
            street_address=address["street"],
            city=address["city"],
            state=address["state"],
            postcode=address["postcode"],
            phone=footer.xpath('.//a[@class="footer-phone-link"]/@href').get(),
        )
        extract_google_position(item, footer)
        apply_category(Categories.RESTAURANT, item)
        item["extras"]["cuisine"] = "american"
        yield item
