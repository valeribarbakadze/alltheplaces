import re
from typing import Any, Iterable

from scrapy import Request, Spider
from scrapy.http import Response

from locations.categories import Categories, Extras, apply_category, apply_yes_no
from locations.hours import OpeningHours, day_range, sanitise_day
from locations.items import Feature

LOCATOR = "https://www.copperrivergrill.com/locations.php"
# The restaurants are listed on the one page, each under a heading that names
# the town and the state.
LOCALITY = re.compile(r"^(?P<city>[A-Za-z .'-]+),\s*(?P<state>[A-Z]{2})\s+(?P<postcode>\d{5})$")
# Each restaurant embeds a map of its own, published by the merchant through
# Google My Maps. The map holds the one pin, which the page states nowhere else.
MID = re.compile(r"[?&]mid=([^&\"]+)")
KML = "https://www.google.com/maps/d/kml?mid={}&forcekml=1"
# "Sunday - Thursday: 11am - 9pm", and the minutes are left off a whole hour.
TIMES = re.compile(
    r"^(?P<opens>\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?)\s*[-–]\s*(?P<closes>\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?)$",
    re.IGNORECASE,
)
SPLIT = re.compile(r"\s*(?:[-–&]|and)\s*", re.IGNORECASE)
WIFI = re.compile(r"wi-?fi", re.IGNORECASE)


class CopperRiverGrillUSSpider(Spider):
    name = "copper_river_grill_us"
    item_attributes = {"brand": "Copper River Grill"}
    allowed_domains = ["www.copperrivergrill.com", "www.google.com"]
    start_urls = [LOCATOR]

    def parse(self, response: Response, **kwargs: Any) -> Iterable[Any]:
        """Read the block the page gives each restaurant.

        The site answers every path with its home page, so nothing can be
        learnt from a path returning 200 and the sitemap is what names the one
        page that lists the restaurants. The page lists them twice: once in
        these blocks and again in the footer, which is not used - the footer
        states a wrong area code for Nicholasville in its text and wrong
        numbers again, differently, in its links.
        """
        sections = response.css("div.mapsection")
        if not sections:
            self.logger.error("The locator holds no restaurant blocks, so the page has changed")
            return

        for section in sections:
            text = section.css("div.maptext")
            label = self.text(text.css("h2"))
            # The lines of the block itself, which are divided by breaks rather
            # than wrapped in anything.
            lines = [line for raw in text.xpath("./text()").getall() if (line := re.sub(r"\s+", " ", raw).strip())]

            stated = next(((i, m) for i, line in enumerate(lines) if (m := LOCALITY.match(line))), None)
            if not stated:
                self.logger.warning(f"{label or 'A block'} states an address this cannot read: {lines!r}")
                continue
            position, locality = stated
            # The line above the street repeats the brand, which the item
            # already carries, so it is not part of the address.
            street = [line for line in lines[:position] if line != self.item_attributes["brand"]]
            if not street:
                self.logger.warning(f"{label or 'A block'} names no street: {lines!r}")
                continue

            item = Feature()
            item["street_address"] = ", ".join(street)
            item["city"] = locality["city"]
            item["state"] = locality["state"]
            item["postcode"] = locality["postcode"]
            item["country"] = "US"
            # The page anchors each block, and its own menu links to the
            # restaurants by those anchors, so the anchor identifies one.
            item["ref"] = section.xpath('preceding-sibling::a[@class="mapanchor"][1]/@id').get() or locality["city"]
            item["website"] = f"{LOCATOR}#{item['ref']}"
            # No branch: each restaurant is headed by the town it stands in,
            # which the address states as the town.
            item["phone"] = self.text(text.css("a.restaurant_telephone")) or None

            item["opening_hours"] = self.hours(lines[position + 1 :], label)

            # The block ends with the name of the restaurant's operating
            # partner, which names a person rather than the place, so it is
            # left where it is.
            if WIFI.search(" ".join(lines)):
                apply_yes_no(Extras.WIFI, item, True)

            item["extras"]["cuisine"] = "american"
            apply_category(Categories.RESTAURANT, item)

            if not (mid := MID.search(section.css("div.map iframe::attr(src)").get("") or "")):
                self.logger.warning(f"{label} embeds no map, so it has no position")
                yield item
                continue
            yield Request(
                KML.format(mid.group(1)),
                callback=self.add_position,
                cb_kwargs={"item": item, "label": label},
            )

    def add_position(self, response: Response, item: Feature, label: str) -> Iterable[Feature]:
        """Read the one pin out of the map the restaurant embeds.

        The map is named for the restaurant it belongs to, so that name is
        checked against the block the map was embedded in: a map holding
        anything but this restaurant's single pin is passed over rather than
        guessed at, and the restaurant is recorded without a position.
        """
        response.selector.remove_namespaces()
        named = (response.xpath("//Document/name/text()").get() or "").strip()
        pins = [point for raw in response.xpath("//Placemark//coordinates/text()").getall() if (point := raw.strip())]

        if label and label not in named:
            self.logger.warning(f"{label} embeds a map named {named!r}, so whose pin it is cannot be told")
        elif len(pins) != 1:
            self.logger.warning(f"{label} embeds a map holding {len(pins)} pins, where a restaurant has one")
        else:
            lon, lat = pins[0].split(",")[:2]
            item["lat"], item["lon"] = lat, lon

        yield item

    def hours(self, lines: list[str], label: str) -> OpeningHours:
        """Read the rules the block states beneath its address.

        Each rule names its days and then its times after a colon, with a dash
        spanning the days between the two named and an ampersand naming only
        the pair - which is how "Friday & Saturday" differs from
        "Sunday - Thursday". The rules are recognised by that shape rather than
        by the heading above them, which the page wraps where the rules
        themselves are only divided by breaks.
        """
        oh = OpeningHours()
        for line in lines:
            if ":" not in line:
                continue
            stated, _, value = line.partition(":")
            named = [day for word in SPLIT.split(stated) if (day := sanitise_day(word))]
            if not named:
                continue
            if not (times := TIMES.match(value.strip())):
                self.logger.warning(f"{label} states hours this cannot read for {stated!r}: {value.strip()!r}")
                continue
            for day in day_range(named[0], named[-1]) if len(named) > 1 and "&" not in stated else named:
                oh.add_range(day, self.time(times["opens"]), self.time(times["closes"]), "%I:%M %p")

        if not oh.as_opening_hours():
            self.logger.warning(f"{label} states no hours this could read")
        return oh

    @staticmethod
    def text(selector: Any) -> str:
        return re.sub(r"\s+", " ", " ".join(selector.xpath(".//text()").getall())).strip()

    @staticmethod
    def time(stated: str) -> str:
        """Return "11am" or "9:30 pm" in the one shape strptime is given."""
        packed = re.sub(r"[\s.]", "", stated).upper()
        clock, meridiem = packed[:-2], packed[-2:]
        return f"{clock if ':' in clock else clock + ':00'} {meridiem}"
