import re
from typing import Iterable
from urllib.parse import urlsplit

from scrapy import Request, Spider
from scrapy.http import Response

from locations.categories import Categories, apply_category
from locations.items import Feature


class ElGauchoUSSpider(Spider):
    name = "el_gaucho_us"
    item_attributes = {"brand": "El Gaucho"}
    allowed_domains = ["elgaucho.com"]
    start_urls = ["https://elgaucho.com/"]

    def parse(self, response: Response) -> Iterable[Request]:
        links = response.xpath(
            '//nav//li[a[translate(normalize-space(.), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", '
            '"abcdefghijklmnopqrstuvwxyz")="locations"]]/ul/li/a/@href'
        ).getall()
        urls = {
            response.urljoin(link)
            for link in links
            if urlsplit(response.urljoin(link)).hostname == "elgaucho.com"
            and re.fullmatch(r"/[^/]+/", urlsplit(link).path)
        }
        if not urls:
            raise ValueError("No El Gaucho branches found in the navigation")
        yield from response.follow_all(sorted(urls), callback=self.parse_location)

    def parse_location(self, response: Response) -> Iterable[Feature]:
        ref = urlsplit(response.url).path.strip("/")
        city = ref.replace("-", " ").title()
        link = response.xpath('(//a[contains(@href, "maps")])[1]')
        address = " ".join(" ".join(link.xpath(".//text()").getall()).split())
        match = re.fullmatch(rf"(.+?)\s*[,\u2022]?\s*({re.escape(city)})\s*,?\s*([A-Z]{{2}})\s+(\d{{5}})", address)
        if not match:
            raise ValueError(f"Unrecognized branch address: {address}")
        item = Feature(
            ref=ref,
            branch=city,
            street_address=match[1].rstrip(" ,\u2022"),
            city=match[2],
            state=match[3],
            postcode=match[4],
            country="US",
            phone=response.css('a[href^="tel:"]::attr(href)').get(),
            website=response.url,
        )
        apply_category(Categories.RESTAURANT, item)
        item["extras"]["cuisine"] = "steak_house"
        yield item
