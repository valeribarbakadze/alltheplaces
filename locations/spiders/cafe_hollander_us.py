import re
from typing import Any, Iterable

from scrapy import Spider
from scrapy.http import Response

from locations.categories import Categories, apply_category
from locations.hours import OpeningHours, day_range, sanitise_day
from locations.items import Feature

# The address is written as one line with no comma between the street and the
# town: "2608 N Downer Ave Milwaukee, WI 53211". The comma that is there divides
# the town from the state, so that is where it is split.
STATE = re.compile(r"^(?P<local>.+),\s*(?P<state>[A-Z]{2})\s+(?P<postcode>\d{5})$")
VISIT = re.compile(r"^Visit Us\s*", re.IGNORECASE)
TIMES = re.compile(
    r"^(?P<opens>\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?)\s*[-–]\s*(?P<closes>\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?)$",
    re.IGNORECASE,
)
SPLIT = re.compile(r"\s*(?:[-–&]|and)\s*", re.IGNORECASE)
# The tabs hold one panel that is a placeholder for the choice not yet made.
EMPTY = "location-empty"


class CafeHollanderUSSpider(Spider):
    name = "cafe_hollander_us"
    item_attributes = {"brand": "Café Hollander"}
    allowed_domains = ["cafehollander.com"]
    start_urls = ["https://cafehollander.com/locations"]
    # robots.txt asks for ten seconds between requests. One page holds all five
    # restaurants, so the crawl is two requests either way.
    custom_settings = {"DOWNLOAD_DELAY": 10}

    def parse(self, response: Response, **kwargs: Any) -> Iterable[Feature]:
        """Read the tab the page gives each restaurant.

        The restaurants are panels of one set of tabs, each identified by the town
        it stands in. Nothing is published in structured data beyond the page and
        the chain, and no map is embedded, so the panel's own text is what states
        the restaurant.
        """
        for panel in response.css("div.js-tabs-panel"):
            town = panel.xpath("@id").get()
            if not town or town == EMPTY:
                continue

            link = panel.xpath('.//a[contains(@href, "google.com/maps")]')
            if not (stated := STATE.match(self.text(link))):
                self.logger.warning(f"{town} states an address this cannot read: {self.text(link)!r}")
                continue

            street, city = self.split(stated["local"], town)
            if not city:
                self.logger.warning(f"{town} is not named at the end of its address: {stated['local']!r}")
                continue

            item = Feature()
            item["ref"] = town
            item["street_address"] = street
            item["city"] = city
            item["state"] = stated["state"]
            item["postcode"] = stated["postcode"]
            item["country"] = "US"
            # Each is headed "Visit Us" and then the name it is known by, which is
            # a neighbourhood or a centre rather than the town in the address.
            item["branch"] = VISIT.sub("", self.text(panel.xpath(".//h1|.//h2|.//h3|.//h4"))).strip() or None
            item["phone"] = panel.xpath('.//a[starts-with(@href, "tel:")]/@href').get("").removeprefix("tel:") or None

            # No position: the address links to a Google route to itself, stated
            # as text, and the page embeds no map.
            item["opening_hours"] = self.hours(panel, town)

            item["extras"]["cuisine"] = "belgian"
            apply_category(Categories.RESTAURANT, item)

            yield item

    @staticmethod
    def text(selector: Any) -> str:
        return re.sub(r"\s+", " ", " ".join(selector.xpath(".//text()").getall())).strip()

    @staticmethod
    def slug(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")

    @classmethod
    def split(cls, local: str, town: str) -> tuple[str, str | None]:
        """Divide "2608 N Downer Ave Milwaukee" into the street and the town.

        The tab says which town it is, so the words at the end of the line that
        spell that town are the town and what stands before them is the street.
        Matching from the end matters: one restaurant is on Mequon Road in
        Mequon, and taking the first match would leave the street as a number.
        """
        words = local.split()
        for count in range(1, min(4, len(words))):
            if cls.slug(" ".join(words[-count:])) == town:
                return " ".join(words[:-count]), " ".join(words[-count:])
        return local, None

    def hours(self, panel: Any, town: str) -> OpeningHours:
        """Read the days and the times, which are written as separate elements.

        They alternate: "Mon – Thurs:" and then "8am – 10pm", so the panel's run
        of text is walked and each range applied to the days last named.
        """
        oh = OpeningHours()
        days: list[str] = []
        for raw in panel.xpath(".//text()").getall():
            node = re.sub(r"\s+", " ", raw).strip()
            if named := [day for word in SPLIT.split(node.rstrip(":")) if (day := sanitise_day(word))]:
                days = day_range(named[0], named[-1]) if len(named) > 1 and "&" not in node else named
            elif days and (times := TIMES.match(node)):
                for day in days:
                    oh.add_range(day, self.time(times["opens"]), self.time(times["closes"]), "%I:%M%p")
                days = []
        if not oh.as_opening_hours():
            self.logger.warning(f"{town} states no hours this could read")
        return oh

    @staticmethod
    def time(stated: str) -> str:
        stated = re.sub(r"[\s.]", "", stated).upper()
        return stated if ":" in stated else f"{stated[:-2]}:00{stated[-2:]}"
