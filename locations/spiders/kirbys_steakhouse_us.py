import re
from typing import Any
from urllib.parse import urlparse

from scrapy import Spider
from scrapy.http import Response

from locations.categories import Categories, apply_category
from locations.hours import OpeningHours, sanitise_day
from locations.items import Feature


class KirbysSteakhouseUSSpider(Spider):
    name = "kirbys_steakhouse_us"
    item_attributes = {"brand": "Kirby's Steakhouse"}
    start_urls = ["https://kirbyssteakhouse.com/"]

    ADDRESS = re.compile(r"^(?P<local>.+?),\s*(?P<state>[A-Za-z][A-Za-z ]*?)\s+(?P<postcode>\d{5})$")
    PHONE = re.compile(r"^\(?\d{3}\)?[\s.-]*\d{3}[\s.-]*\d{4}$")
    EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
    # A rule names its days and then a time. The bar, the happy hour and the
    # cigar lounge put no day before their colon, so they never match.
    RULE = re.compile(r"^(?P<days>[A-Za-z][A-Za-z.&\s–—-]*?):\s*(?P<times>\d.*)$")
    # A label names a room and nothing else. WinStar states the Mickey Mantle
    # Lounge's hours beside the dining room's, so only rooms the brand is
    # named in, and rules under no label at all, are the restaurant's.
    LABEL = re.compile(r"^(?P<label>[A-Za-z][A-Za-z'’\s&]*?):\s*$")
    # A range whose opening time carries no am or pm takes the closing one's:
    # every one of these is written "5 - 9pm", meaning the evening.
    BARE = re.compile(r"(\d{1,2}(?::\d{2})?)\s*[–—-]\s*(\d{1,2}(?::\d{2})?)\s*([ap])\.?m\.?", re.IGNORECASE)

    def parse(self, response: Response, **kwargs: Any) -> Any:
        # The Locations menu. Its remaining entry is a different brand of the
        # same group, on a domain of its own.
        for url in response.xpath('//li[a[normalize-space(text()) = "Locations"]]//ul//a/@href').getall():
            if urlparse(url).hostname == urlparse(response.url).hostname:
                yield response.follow(url, callback=self.parse_restaurant)

    def parse_restaurant(self, response: Response, **kwargs: Any) -> Any:
        place = response.xpath("//title/text()").get().split("|")[0].strip()
        lines = [
            text
            for raw in response.xpath("//body//text()[not(ancestor::script)][not(ancestor::style)]").getall()
            if (text := re.sub(r"[\s ]+", " ", raw).strip())
        ]
        # Everything from here down is this restaurant's own. Above it the page
        # carries a demo reservation widget with a New York address and number.
        contact = lines.index("Contact Info")
        item = Feature(ref=response.url.rsplit("/", 2)[-2], website=response.url)
        item["phone"] = next((line for line in lines[contact:] if self.PHONE.match(line)), None)
        item["email"] = next((line for line in lines[contact:] if self.EMAIL.match(line)), None)
        self.set_address(item, next(line for line in lines[contact:] if self.ADDRESS.match(line)), place)
        item["opening_hours"] = self.read_hours(lines[:contact])
        apply_category(Categories.RESTAURANT, item)
        item["extras"]["cuisine"] = "steak_house"
        yield item

    def set_address(self, item: Feature, address: str, place: str) -> None:
        match = self.ADDRESS.match(address)
        item["addr_full"] = address
        item["postcode"] = match["postcode"]
        # The state pipeline matches a code as given and a name in title case.
        item["state"] = match["state"] if len(match["state"]) == 2 else match["state"].title()
        # Nothing divides the street from the town, so they are only separated
        # where the page's own title names a town the address ends with. WinStar
        # is named for its casino instead, and keeps that as its branch.
        if match["local"].casefold().endswith(place.casefold()):
            item["street_address"] = match["local"][: -len(place)].strip().rstrip(",")
            item["city"] = place
        else:
            item["branch"] = place

    def read_hours(self, lines: list[str]) -> OpeningHours:
        hours = OpeningHours()
        wanted = True
        for line in lines:
            if (label := self.LABEL.match(line)) and not self.days(label["label"]):
                wanted = "kirby" in label["label"].casefold()
            elif (rule := self.RULE.match(line)) and wanted and self.days(rule["days"]):
                # "&" is not one of the shared delimiters, and left as it is
                # "Fri & Sat" reads as Saturday alone.
                rewritten = self.BARE.sub(r"\1\3m - \2\3m", line).replace(".", "").replace(" & ", " and ")
                hours.add_ranges_from_string(rewritten)
        return hours

    @staticmethod
    def days(value: str) -> bool:
        parts = [part.strip() for part in re.split(r"\s*(?:&|and|–|—|-|to)\s*", value.replace(".", ""))]
        return all(sanitise_day(part) for part in parts if part)
