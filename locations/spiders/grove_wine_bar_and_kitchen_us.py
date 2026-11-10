import re
from typing import Any, Iterable

from scrapy import Spider
from scrapy.http import Request, Response

from locations.categories import Categories, apply_category
from locations.hours import OpeningHours
from locations.items import Feature


class GroveWineBarAndKitchenUSSpider(Spider):
    name = "grove_wine_bar_and_kitchen_us"
    item_attributes = {"brand": "Grove Wine Bar & Kitchen"}
    allowed_domains = ["grovewinebar.com"]
    start_urls = ["https://www.grovewinebar.com/"]
    # The destination Google states as !1d<longitude>!2d<latitude>. The
    # @latitude,longitude earlier in the same link is the map camera at zoom
    # 12, which sits up to 6 km from the restaurant.
    PIN = re.compile(r"!1d(?P<lon>-?[\d.]+)!2d(?P<lat>-?[\d.]+)")
    LOCALITY = re.compile(r"^(?P<city>[^,]+),\s*(?P<state>[A-Z]{2})\s+(?P<postcode>\d{5})$")
    # Trading hours are stated times first and days second, which the parser
    # reads the other way round. Brunch, happy hour, a holiday opening and the
    # closed dates each lead with a label instead, so none of them match.
    RULE = re.compile(r"^(?P<times>\d.*[ap]m)\s+(?P<days>[A-Za-z][A-Za-z\s-]*)$", re.IGNORECASE)

    def parse(self, response: Response, **kwargs: Any) -> Iterable[Request]:
        for card in response.xpath('//div[@data-q_id="#locations"]//div[contains(@class, "vc_col-sm-3")]'):
            pin = self.PIN.search(card.xpath('.//a[contains(@href, "/maps/dir/")]/@href').get())
            yield response.follow(
                card.xpath('.//a[contains(., "See menus & hours")]/@href').get(),
                callback=self.parse_location,
                cb_kwargs={"lat": pin["lat"], "lon": pin["lon"]},
            )

    def parse_location(self, response: Response, lat: str, lon: str) -> Iterable[Feature]:
        slug = response.url.rstrip("/").rsplit("/", 1)[-1]
        address = [
            text
            for raw in response.xpath('//p[a[contains(text(), "Get directions")]]//text()').getall()
            if (text := raw.strip())
        ]
        locality = self.LOCALITY.match(address[1])
        item = Feature(
            ref=slug,
            branch=slug.replace("-", " ").title(),
            website=response.url,
            lat=lat,
            lon=lon,
            street_address=address[0],
            city=locality["city"],
            state=locality["state"],
            postcode=locality["postcode"],
            phone=address[2],
        )

        item["opening_hours"] = OpeningHours()
        for paragraph in response.xpath(
            '//h3[normalize-space(.) = "Hours"]/ancestor::div[contains(@class, "wpb_wrapper")][1]//p'
        ):
            if rule := self.RULE.match(re.sub(r"\s+", " ", paragraph.xpath("string()").get()).strip()):
                item["opening_hours"].add_ranges_from_string(f"{rule['days']} {rule['times']}")

        apply_category(Categories.RESTAURANT, item)
        yield item
