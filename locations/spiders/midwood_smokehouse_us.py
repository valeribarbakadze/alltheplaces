import re
from datetime import datetime
from typing import Any, Iterable

from scrapy import Request, Spider
from scrapy.http import Response

from locations.categories import Categories, apply_category
from locations.google_url import url_to_coords
from locations.hours import OpeningHours, day_range, sanitise_day
from locations.items import Feature

LOCATOR = "https://midwoodsmokehouse.com/locations/"
# The card states the town and state together, and one of the six appends the
# postcode: "Charlotte, NC", "Raleigh, NC 27603".
LOCALITY = re.compile(r"^(?P<city>.+?),\s*(?P<state>[A-Z]{2})(?:\s+(?P<postcode>\d{5}))?$")
# "11AM-9PM" on five cards, "11 am - 9 pm" on the sixth.
TIMES = re.compile(
    r"^(?P<opens>\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?)\s*-\s*(?P<closes>\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?)$", re.IGNORECASE
)
REDIRECTS = [301, 302, 303, 307, 308]
# A Google place URL carries two positions: the viewport centre after @, and the
# place's own pin in the 3d/4d pair. They sit a couple of hundred metres apart
# here, so the pin is read first and url_to_coords, which reads the centre, is
# the fallback.
PIN = re.compile(r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)")
# The address Google echoes back in the path ends in the postcode the card omits.
GOOGLE_POSTCODE = re.compile(r"/maps/place/[^/@]*?,\+[A-Z]{2}\+(\d{5})(?:-\d{4})?")


class MidwoodSmokehouseUSSpider(Spider):
    name = "midwood_smokehouse_us"
    item_attributes = {"brand": "Midwood Smokehouse"}
    start_urls = [LOCATOR]

    @staticmethod
    def normalise(time: str) -> str:
        time = re.sub(r"[\s.]", "", time).upper()
        return datetime.strptime(time, "%I:%M%p" if ":" in time else "%I%p").strftime("%H:%M")

    def hours(self, lines: list[str]) -> OpeningHours:
        """Read the alternating day and time lines a card states.

        Each card gives its hours as a day label followed by the times that
        apply to it: "Sun-Thurs", "11AM-9PM", "Fri-Sat", "11AM-10PM". The day
        labels are written in three spellings between the six cards, which
        sanitise_day reconciles.
        """
        oh = OpeningHours()
        days: list[str] = []
        for line in lines:
            if times := TIMES.match(line):
                for day in days:
                    oh.add_range(day, self.normalise(times["opens"]), self.normalise(times["closes"]))
                days = []
            elif parsed := self.days(line):
                days = parsed
            else:
                self.logger.warning(f"Unparsed hours line: {line!r}")
        return oh

    @staticmethod
    def days(label: str) -> list[str]:
        if "-" in label:
            start, end = (sanitise_day(part) for part in label.split("-", 1))
            return day_range(start, end) if start and end else []
        return [day] if (day := sanitise_day(label)) else []

    def parse(self, response: Response, **kwargs: Any) -> Iterable[Any]:
        for card in response.css("div.details div.inside"):
            item = Feature()
            item["branch"] = (card.css("h3.name::text").get() or "").strip()
            item["ref"] = re.sub(r"[^a-z0-9]+", "-", item["branch"].lower()).strip("-")
            item["phone"] = card.css("div.phone a[href^='tel:']::text").get()
            item["country"] = "US"

            # Every street is written with a trailing full stop on four of the six.
            item["street_address"] = (card.css("div.address.add1::text").get() or "").strip().rstrip(".")
            if locality := LOCALITY.match((card.css("div.address.add2::text").get() or "").strip()):
                item["city"] = locality["city"]
                item["state"] = locality["state"]
                item["postcode"] = locality["postcode"]

            item["opening_hours"] = self.hours(
                [text.strip() for text in card.css("div.hours-info div.hours ::text").getall() if text.strip()]
            )

            apply_category(Categories.RESTAURANT, item)
            item["extras"]["cuisine"] = "barbecue"

            # No website: the restaurants have no pages of their own, and the
            # locator's structured data names the chain's home page against
            # every one of the six.
            #
            # The position and the postcode are published only through the card's
            # map link, which is shortened. dont_filter is set because two
            # restaurants sharing a link would otherwise have the second request
            # dropped as a duplicate.
            if short := card.css("div.map a::attr(href)").get():
                yield Request(
                    short,
                    method="HEAD",
                    callback=self.parse_position,
                    cb_kwargs={"item": item},
                    dont_filter=True,
                    meta={"dont_redirect": True, "handle_httpstatus_list": REDIRECTS},
                )
            else:
                self.logger.warning(f"{item['branch']} publishes no map link, so it has no position")
                yield item

    def parse_position(self, response: Response, item: Feature) -> Iterable[Feature]:
        if resolved := response.headers.get("Location", b"").decode():
            if pin := PIN.search(resolved):
                item["lat"], item["lon"] = pin.groups()
            else:
                item["lat"], item["lon"] = url_to_coords(resolved)
            if not item.get("postcode") and (postcode := GOOGLE_POSTCODE.search(resolved)):
                item["postcode"] = postcode.group(1)
        else:
            self.logger.warning(f"{item['branch']}'s map link did not resolve, so it has no position")
        yield item
