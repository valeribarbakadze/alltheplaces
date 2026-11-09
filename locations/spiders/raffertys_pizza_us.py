import re
from typing import Any

from scrapy.http import Response
from scrapy.spiders import SitemapSpider

from locations.categories import Categories, apply_category
from locations.hours import OpeningHours
from locations.items import Feature


class RaffertysPizzaUSSpider(SitemapSpider):
    name = "raffertys_pizza_us"
    item_attributes = {"brand": "Rafferty's Pizza"}
    sitemap_urls = ["https://www.raffertyspizza.com/sitemap.xml"]
    sitemap_rules = [(r"/location/", "parse_location")]

    LOCALITY = re.compile(r"^(?P<city>[^,]+),\s*(?P<state>[A-Z]{2})\s+(?P<postcode>\d{5})$")

    def parse_location(self, response: Response, **kwargs: Any) -> Any:
        item = Feature(
            ref=response.url.rstrip("/").rsplit("/", 1)[-1],
            website=response.url,
            phone=response.xpath('//a[starts-with(@href, "tel:")]/@href').get(),
        )
        address = self.block(response, "Info")
        locality = self.LOCALITY.match(address[-1])
        item["street_address"] = address[-2]
        item["city"], item["state"] = locality["city"], locality["state"]
        item["postcode"] = locality["postcode"]
        branch = response.xpath("//h1/text()").get("").strip()
        if branch.casefold() != item["city"].casefold():
            item["branch"] = branch
        item["opening_hours"] = OpeningHours()
        for rule in self.block(response, "Hours"):
            item["opening_hours"].add_ranges_from_string(rule)
        apply_category(Categories.RESTAURANT, item)
        item["extras"]["cuisine"] = "pizza"
        yield item

    @staticmethod
    def block(response: Response, heading: str) -> list[str]:
        # The page labels these two blocks, and Webflow generates their class
        # names, so the heading is what they are found by.
        block = response.xpath(f'//h3[normalize-space(text()) = "{heading}"]/following-sibling::div[1]')
        return [text for raw in block.xpath(".//text()").getall() if (text := raw.strip())]
