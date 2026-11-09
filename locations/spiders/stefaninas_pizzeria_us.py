import re
from typing import Any

from scrapy.http import Response
from scrapy.spiders import SitemapSpider

from locations.categories import Categories, apply_category
from locations.google_url import extract_google_position
from locations.hours import OpeningHours
from locations.items import Feature


class StefaninasPizzeriaUSSpider(SitemapSpider):
    name = "stefaninas_pizzeria_us"
    item_attributes = {"brand": "Stefanina's Pizzeria"}
    sitemap_urls = ["https://stefaninas.com/wp-sitemap.xml"]
    sitemap_rules = [(r"/[^/]+-location/$", "parse_location")]

    LOCALITY = re.compile(r"^(?P<city>[^,]+),\s*(?P<state>[A-Z]{2})\s+(?P<postcode>\d{5})$")

    def parse_location(self, response: Response, **kwargs: Any) -> Any:
        item = Feature(
            ref=response.url.rstrip("/").rsplit("/", 1)[-1].removesuffix("-location"),
            website=response.url,
            phone=response.xpath('//a[starts-with(@href, "tel:")]/@href').get(),
        )
        address = self.block(response, "Address")
        locality = self.LOCALITY.match(address[-1])
        item["street_address"] = address[-2]
        item["city"], item["state"] = locality["city"], locality["state"]
        item["postcode"] = locality["postcode"]
        branch = response.xpath('//meta[@property="og:title"]/@content').get("").strip().removesuffix(" Location")
        if branch.casefold() != item["city"].casefold():
            item["branch"] = branch
        item["opening_hours"] = OpeningHours()
        for rule in self.block(response, "Order by Phone"):
            # "Noon" is not a time the parser reads, and it drops the whole rule
            # that names it, which is how two of the four lose their Sundays.
            rewritten = re.sub(r"(?i)\bnoon\b", "12pm", re.sub(r"(?i)^open\s+", "", rule))
            item["opening_hours"].add_ranges_from_string(rewritten)
        extract_google_position(item, response)
        apply_category(Categories.RESTAURANT, item)
        item["extras"]["cuisine"] = "pizza"
        yield item

    @staticmethod
    def block(response: Response, heading: str) -> list[str]:
        # Every page's footer lists all four restaurants, so each block is taken
        # from the heading standing above it rather than from the page at large.
        block = response.xpath(
            f'//h2[normalize-space(text()) = "{heading}"]'
            '/ancestor::div[contains(@class, "fusion-title")][1]'
            '/following-sibling::div[contains(@class, "fusion-text")][1]'
        )
        return [text for raw in block.xpath(".//text()").getall() if (text := re.sub(r"\s+", " ", raw).strip())]
