from typing import Iterable
from urllib.parse import urlsplit

from scrapy import Spider
from scrapy.http import Response

from locations.categories import Categories, apply_category
from locations.items import Feature


class HashHouseAGoGoUSSpider(Spider):
    name = "hash_house_a_go_go_us"
    item_attributes = {"brand": "Hash House a Go Go"}
    allowed_domains = ["www.hashhouseagogo.com"]
    start_urls = ["https://www.hashhouseagogo.com/locations/"]

    def parse(self, response: Response) -> Iterable[Feature]:
        cards = response.css(".o-locationCard")
        if not cards:
            raise ValueError("The restaurant directory cards are missing")
        for card in cards:
            website = response.urljoin(card.css('a[href*="/location/"]::attr(href)').get())
            item = Feature(
                ref=urlsplit(website).path.rstrip("/").split("/")[-1],
                branch=card.xpath("normalize-space(.//h2)").get(),
                street_address=card.xpath('normalize-space(.//*[@itemprop="streetAddress"])').get(),
                city=card.xpath('normalize-space(.//*[@itemprop="addressLocality"])').get(),
                state=card.xpath('normalize-space(.//*[@itemprop="addressRegion"])').get(),
                postcode=card.xpath('normalize-space(.//*[@itemprop="postalCode"])').get(),
                country="US",
                phone=card.css('a[href^="tel:"]::attr(href)').get(),
                website=website,
            )
            apply_category(Categories.RESTAURANT, item)
            yield item
