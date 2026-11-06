import json
import re
from typing import Any, Iterable

from scrapy.http import TextResponse

from locations.categories import Categories, Extras, apply_category, apply_yes_no
from locations.hours import DAYS_FULL, OpeningHours, sanitise_day
from locations.items import Feature
from locations.json_blob_spider import JSONBlobSpider

# The page is built with Next.js, which sends the data for what it renders as a
# run of JSON string literals pushed onto one array.
FLIGHT = re.compile(r"self\.__next_f\.push\(\[\s*1\s*,\s*(\"(?:[^\"\\]|\\.)*\")")
HOLDS = re.compile(r'"locations":(\[)')
# "Chicago (Prudential Plaza)": the town, and then what the restaurant is known
# by within it.
WITHIN = re.compile(r"^(?P<city>[^(]+?)\s*\((?P<branch>[^)]+)\)$")
OPEN = "open"


class WildberryCafeUSSpider(JSONBlobSpider):
    name = "wildberry_cafe_us"
    # As the site titles itself. Its own map embeds search Google for
    # "Wildberry Pancakes & Cafe", and its prose calls it Wildberry Café.
    item_attributes = {"brand": "Wildberry Pancakes and Cafe"}
    allowed_domains = ["wildberrycafe.com"]
    start_urls = ["https://wildberrycafe.com/locations"]

    def extract_json(self, response: TextResponse) -> list[dict]:
        """Read the restaurants out of the data the page was rendered from.

        There is nothing else to read them from: the site publishes no sitemap
        and no structured data, and robots.txt answers 404 - a plain one from
        the site's own application rather than anything standing in its way, so
        nothing is asked of a crawler.

        The payload arrives as JSON string literals pushed one after another,
        which are joined back together and searched for the array the locator
        was given. The array is taken whole, by counting brackets, because it
        sits in the middle of a much larger structure.
        """
        payload = "".join(json.loads(chunk) for chunk in FLIGHT.findall(response.text))
        for found in HOLDS.finditer(payload):
            if not (blob := self.enclosed(payload, found.start(1))):
                continue
            try:
                locations = json.loads(blob)
            except ValueError:
                continue
            if locations and all(isinstance(one, dict) and "latitude" in one for one in locations):
                return locations

        self.logger.error("The page holds no restaurants, so what it is built from has changed")
        return []

    @staticmethod
    def enclosed(text: str, start: int) -> str | None:
        """Return the array beginning at start, counting its brackets.

        Strings are stepped over rather than counted, since a bracket inside
        one would otherwise close the array early.
        """
        depth = 0
        quoted = False
        escaped = False
        for position in range(start, len(text)):
            character = text[position]
            if quoted:
                if escaped:
                    escaped = False
                elif character == "\\":
                    escaped = True
                elif character == '"':
                    quoted = False
                continue
            if character == '"':
                quoted = True
            elif character == "[":
                depth += 1
            elif character == "]":
                depth -= 1
                if depth == 0:
                    return text[start : position + 1]
        return None

    def post_process_item(
        self, item: Feature, response: TextResponse, location: dict, **kwargs: Any
    ) -> Iterable[Feature]:
        if (stated := location.get("status")) != OPEN:
            self.logger.warning(f"{location.get('slug')} states its status as {stated!r}, so it is not collected")
            return

        # The slug names the restaurant where the identifier it is keyed by is
        # a bare UUID.
        item["ref"] = location["slug"]
        # The street is given on its own, with the town, state and postcode
        # beside it, so it is the street address rather than the whole of one.
        item["street_address"] = item.pop("addr_full", None)
        item["country"] = "US"
        item["website"] = response.urljoin(f"/locations/{location['slug']}")
        item["branch"] = self.branch(item.pop("name", None), item.get("city"))

        item["opening_hours"] = self.hours(location)

        # Each restaurant publishes a delivery link of its own, and four of the
        # five publish somewhere to book. The fifth simply offers no booking
        # link, which is not the same as stating that it takes no bookings, so
        # nothing is recorded against it. The links to order ahead are left
        # alone: ordering online says nothing certain about collecting in
        # person.
        if location.get("delivery_links"):
            apply_yes_no(Extras.DELIVERY, item, True)
        if location.get("reservation_links"):
            apply_yes_no(Extras.RESERVATION, item, True)

        item["extras"]["cuisine"] = "breakfast"
        apply_category(Categories.RESTAURANT, item)

        yield item

    @staticmethod
    def branch(named: str | None, city: str | None) -> str | None:
        """Name the restaurant by what sets it apart from the town it is in.

        Two of the five are named for the town and what stands within it,
        "Chicago (Water Tower Place)", where the town is already recorded as
        the town. The other three are named for the town alone, and carry no
        branch rather than repeating it.
        """
        if not named:
            return None
        if (within := WITHIN.match(named)) and within["city"].casefold() == (city or "").casefold():
            return within["branch"].strip()
        return named if named.casefold() != (city or "").casefold() else None

    def hours(self, location: dict) -> OpeningHours:
        """Read the days of the one set of hours the restaurant publishes.

        A set may be labelled, for a particular service rather than for the
        restaurant, so only an unlabelled set is read. Dated exceptions are
        published separately, as special_hours, and are left there: they name
        single days such as Christmas and would be wrong by next year.
        """
        oh = OpeningHours()
        sets = [one for one in (location.get("hours") or []) if not one.get("label")]
        if len(sets) != 1:
            self.logger.warning(
                f"{location.get('slug')} publishes {len(sets)} unlabelled sets of hours, where it has one"
            )

        for one in sets:
            for stated in one.get("days") or []:
                if not (day := sanitise_day(stated.get("day"))):
                    self.logger.warning(f"{location.get('slug')} names a day this cannot read: {stated.get('day')!r}")
                    continue
                if stated.get("closed24Hours"):
                    oh.set_closed(day)
                elif stated.get("open24Hours"):
                    oh.add_range(day, "00:00", "24:00")
                elif stated.get("openTime") and stated.get("closeTime"):
                    oh.add_range(day, stated["openTime"], stated["closeTime"])

        if not oh.as_opening_hours():
            self.logger.warning(f"{location.get('slug')} publishes no hours this could read")
        elif len(set(oh.day_hours) | oh.days_closed) < len(DAYS_FULL):
            self.logger.info(f"{location.get('slug')} states nothing for some days of the week")
        return oh
