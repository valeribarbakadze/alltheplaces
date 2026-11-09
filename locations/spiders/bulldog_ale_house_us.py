import re
from typing import Any

from scrapy import Spider
from scrapy.http import Response

from locations.categories import Categories, apply_category
from locations.hours import OpeningHours, sanitise_day
from locations.items import Feature


class BulldogAleHouseUSSpider(Spider):
    name = "bulldog_ale_house_us"
    item_attributes = {"brand": "Bulldog Ale House"}
    start_urls = ["https://www.bulldogalehouse.com/"]

    LOCALITY = re.compile(r"^(?P<city>[^,]+),\s*(?P<state>[A-Z]{2})\s+(?P<postcode>\d{5})$")
    PHONE = re.compile(r"^P:\s*(?P<phone>.+)$")

    def parse(self, response: Response, **kwargs: Any) -> Any:
        # The restaurants the site's own menu offers. Its sitemap is not the
        # list: that still carries pages for three that have closed.
        menu = response.xpath('//li[a[normalize-space(text()) = "Locations"]]//a[contains(@href, "-location/")]/@href')
        if not menu:
            self.logger.error("The Locations menu offered no restaurant, so check how the site now lists them")
        for url in menu.getall():
            yield response.follow(url, callback=self.parse_location)

    def parse_location(self, response: Response, **kwargs: Any) -> Any:
        item = Feature(ref=response.url.rsplit("/", 2)[-2].removesuffix("-location"), website=response.url)
        for paragraph in response.xpath("//p"):
            lines = [text.strip() for text in paragraph.xpath(".//text()").getall() if text.strip()]
            at = next((i for i, line in enumerate(lines) if i and self.LOCALITY.match(line)), None)
            if at is None:
                continue
            locality = self.LOCALITY.match(lines[at])
            item["street_address"] = lines[at - 1]
            item["city"], item["state"] = locality["city"], locality["state"]
            item["postcode"] = locality["postcode"]
            item["phone"] = next((match["phone"] for line in lines if (match := self.PHONE.match(line))), None)
            # "Hours:" is a heading beside the address on some of these pages
            # and a paragraph within it on others, so the rules are recognised
            # by opening with a day rather than by where they sit.
            item["opening_hours"] = OpeningHours()
            item["opening_hours"].add_ranges_from_string(
                " ".join(
                    line.strip()
                    for line in paragraph.xpath("..//text()").getall()
                    if sanitise_day(line.split(":")[0].strip())
                )
            )
            break
        else:
            self.logger.error(f"{response.url} states no address this spider can read, so check the page layout")
        # No position: the page's map embeds the address as text rather than a pin.
        apply_category(Categories.RESTAURANT, item)
        yield item
