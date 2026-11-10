import re
from typing import Any, Iterable

from scrapy import Spider
from scrapy.http import Response

from locations.categories import Categories, apply_category
from locations.items import Feature


class YafoKitchenUSSpider(Spider):
    name = "yafo_kitchen_us"
    item_attributes = {"brand": "YAFO Kitchen"}
    start_urls = ["https://yafokitchen.com/"]
    # The place Google resolved, stated by the map link as !3d<latitude> and
    # !4d<longitude>. The @latitude,longitude before it is the map camera,
    # shifted west on three of the four to leave room for the info panel.
    PLACE = re.compile(r"!3d(?P<lat>-?[\d.]+)!4d(?P<lon>-?[\d.]+)")
    LOCALITY = re.compile(r"^(?P<city>[^,]+),\s*(?P<state>[A-Z]{2})\s+(?P<postcode>\d{5})$")

    def parse(self, response: Response, **kwargs: Any) -> Iterable[Feature]:
        for card in response.xpath('//div[contains(@class, "section-locations")]//div[@class="fbox"]'):
            address = [text for raw in card.xpath(".//address//text()").getall() if (text := raw.strip())]
            locality = self.LOCALITY.match(address[1])
            place = self.PLACE.search(card.xpath('.//a[contains(@class, "maplink")]/@href').get())
            branch = card.xpath('.//h3[@class="name"]/text()').get().removeprefix("YAFO ")
            item = Feature(
                ref=branch,
                branch=branch,
                street_address=address[0],
                city=locality["city"],
                state=locality["state"],
                postcode=locality["postcode"],
                phone=card.xpath('.//div[@class="phonenum"]//a/text()').get(),
                lat=place["lat"],
                lon=place["lon"],
            )
            # The site gives "11 am - 9 pm" for every restaurant and names no
            # days anywhere on it, so no opening_hours is set rather than
            # assuming which days that covers.
            apply_category(Categories.RESTAURANT, item)
            item["extras"]["cuisine"] = "mediterranean;middle_eastern"
            yield item
