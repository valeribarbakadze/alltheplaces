import re
from typing import Any, Iterable

from scrapy import Spider
from scrapy.http import Request, Response

from locations.categories import Categories, apply_category
from locations.hours import OpeningHours, sanitise_day
from locations.items import Feature


class WalnutGrillUSSpider(Spider):
    name = "walnut_grill_us"
    item_attributes = {"brand": "Walnut Grill"}
    allowed_domains = ["eatwalnut.com"]
    start_urls = ["https://eatwalnut.com/"]
    # Each restaurant keeps its own subdomain, which states its id, its name and
    # the pin on its map in script rather than in the markup.
    REF = re.compile(r"var spot_id\s*=\s*(?P<ref>\d+)")
    BRANCH = re.compile(r'"spot_name":"Walnut Grill - (?P<branch>[^"]+)"')
    PIN = re.compile(r"L\.marker\(\[\s*(?P<lat>-?[\d.]+),\s*(?P<lon>-?[\d.]+)\s*\]")

    def parse(self, response: Response, **kwargs: Any) -> Iterable[Request]:
        for url in response.xpath('//a[contains(@href, ".eatwalnut.com")]/@href').getall():
            yield response.follow(url, callback=self.parse_location)

    def parse_location(self, response: Response, **kwargs: Any) -> Iterable[Feature]:
        city, state = response.xpath('//div[@class="city-state"]/text()').get().split(",")
        pin = self.PIN.search(response.text)
        item = Feature(
            ref=self.REF.search(response.text)["ref"],
            branch=self.BRANCH.search(response.text)["branch"],
            website=response.url,
            street_address=response.xpath('//div[@class="address"]/text()').get(),
            city=city,
            state=state,
            postcode=response.xpath('//div[@class="zip"]/text()').get(),
            phone=response.xpath('//a[@id="contact_us_v3_section_phone_link"]/@href').get(),
            email=response.xpath('//div[@class="contact-us"]//a[starts-with(@href, "mailto:")]/@href').get(),
            lat=pin["lat"],
            lon=pin["lon"],
        )

        # The day lists are comma separated, which add_ranges_from_string reads
        # as the last day of each list alone, so the days are added one by one.
        hours = response.xpath('//div[@class="hours"]')
        item["opening_hours"] = OpeningHours()
        for days, times in zip(
            hours.xpath('./div[@class="days"]/text()').getall(),
            hours.xpath('./div[@class="from-to"]/text()').getall(),
        ):
            opens, closes = (time.strip() for time in times.split(" - "))
            for day in days.split(","):
                # sanitise_day strips spaces but not the newlines in this markup.
                item["opening_hours"].add_range(sanitise_day(day.strip()), opens, closes, time_format="%I:%M %p")

        apply_category(Categories.RESTAURANT, item)
        item["extras"]["cuisine"] = "american"
        yield item
