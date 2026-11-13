import re
from typing import Iterable

from scrapy import Spider
from scrapy.http import Response

from locations.categories import Categories, apply_category
from locations.items import Feature


class CoolHandLukesUSSpider(Spider):
    name = "cool_hand_lukes_us"
    item_attributes = {"brand": "Cool Hand Luke's"}
    allowed_domains = ["coolhandlukes.com"]
    start_urls = ["https://coolhandlukes.com/locations/"]

    def parse(self, response: Response) -> Iterable[Feature]:
        count = 0
        for column in response.xpath('//div[contains(@class, "kt-inside-inner-col")][h2]'):
            link = column.xpath('.//a[contains(@href, "maps")][1]')
            if not link:
                continue
            lines = [text.strip() for text in link.xpath(".//text()").getall() if text.strip()]
            locality = re.fullmatch(r"(.+),\s*([A-Z]{2})\s+(\d{5})", lines[-1]) if lines else None
            if len(lines) < 2 or not locality:
                raise ValueError("The restaurant address format has changed")
            branch = column.xpath("normalize-space(h2)").get()
            item = Feature(
                ref=re.sub(r"\W+", "-", branch.lower()).strip("-"),
                branch=branch,
                street_address=" ".join(lines[:-1]),
                city=locality[1],
                state=locality[2],
                postcode=locality[3],
                country="US",
                phone=column.css('a[href^="tel:"]::attr(href)').get(),
                website=response.url,
            )
            apply_category(Categories.RESTAURANT, item)
            item["extras"]["cuisine"] = "steak_house"
            count += 1
            yield item
        if not count:
            raise ValueError("No restaurant address blocks found")
