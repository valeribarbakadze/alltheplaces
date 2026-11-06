import html
import json
import re
from typing import Any, Iterable
from urllib.parse import urlencode

from scrapy import Request, Spider
from scrapy.http import Response

from locations.categories import Categories, apply_category
from locations.hours import DAYS, OpeningHours, day_range, sanitise_day
from locations.items import Feature

LOCATOR = "https://heavenlymassage.com/locations/"
# The spas are a post type of their own, which lists them all and is the only
# complete account of them. It carries none of their details.
CATALOGUE = "https://heavenlymassage.com/wp-json/wp/v2/wpsl_stores?per_page=100"
# What the locator itself asks for its details, and the one path under
# /wp-admin/ that robots.txt allows.
SEARCH = "https://heavenlymassage.com/wp-admin/admin-ajax.php"
# The widest the locator's own radius menu offers. Anything beyond is refused.
RADIUS = 500
SETTINGS = re.compile(r"var wpslSettings\s*=\s*(\{.*?\});", re.S)
# "Mon-Fri 9:00am - 10:00pm", "Monday - Friday 9:00am to10:00pm" - the times
# divided by a dash or by "to", which one spa writes against its closing time
# with no space before it.
RULE = re.compile(
    r"^(?P<days>[A-Za-z]{3,9}(?:\s*[-–—]\s*[A-Za-z]{3,9})?)\s+"
    r"(?P<opens>\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?)\s*(?:[-–—]|to)\s*"
    r"(?P<closes>\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?)$",
    re.IGNORECASE,
)


class HeavenlyMassageUSSpider(Spider):
    name = "heavenly_massage_us"
    item_attributes = {"brand": "Heavenly Massage"}
    allowed_domains = ["heavenlymassage.com"]
    start_urls = [LOCATOR]
    # robots.txt asks for ten seconds between requests. Three collect the lot.
    custom_settings = {"DOWNLOAD_DELAY": 10}

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.listed: dict[int, str] = {}
        self.seen: set[int] = set()

    def parse(self, response: Response, **kwargs: Any) -> Iterable[Any]:
        """Read where the locator centres its map, and start from there.

        The locator holds no spas itself: it is a WP Store Locator, which asks
        for them afterwards. Its settings say where it searches from, so the
        search begins where the site itself begins rather than at a point of
        this spider's choosing.
        """
        if not (stated := SETTINGS.search(response.text)):
            self.logger.error("The locator publishes no settings, so the page has changed")
            return
        start = json.loads(stated.group(1))["map"]["startLatLng"]
        yield Request(CATALOGUE, callback=self.parse_catalogue, cb_kwargs={"start": start})

    def parse_catalogue(self, response: Response, start: str, **kwargs: Any) -> Iterable[Any]:
        """Note every spa the site publishes, before asking for their details.

        This matters because the details come from a search within a radius,
        and the locator refuses a radius wider than its own menu offers. Every
        spa is in Illinois and well inside that, but one opened further away
        would be missed without anything going wrong, so the two lists are
        compared when the crawl closes.
        """
        self.listed = {store["id"]: store["slug"] for store in response.json()}
        if not self.listed:
            self.logger.error("The site lists no spas, so the post type has changed")
            return

        latitude, _, longitude = start.partition(",")
        query = {
            "action": "store_search",
            "lat": latitude,
            "lng": longitude,
            "search_radius": RADIUS,
            "max_results": max(100, len(self.listed)),
        }
        yield Request(f"{SEARCH}?{urlencode(query)}", callback=self.parse_stores)

    def parse_stores(self, response: Response, **kwargs: Any) -> Iterable[Feature]:
        for store in response.json():
            self.seen.add(store["id"])

            item = Feature()
            item["ref"] = str(store["id"])
            item["street_address"] = ", ".join(
                part for key in ("address", "address2") if (part := (store.get(key) or "").strip())
            )
            item["city"] = store.get("city")
            item["state"] = store.get("state")
            item["postcode"] = store.get("zip")
            # Stated as a name rather than a code, which the country code
            # pipeline resolves.
            item["country"] = store.get("country")
            item["lat"] = store.get("lat")
            item["lon"] = store.get("lng")
            item["phone"] = store.get("phone")
            item["email"] = store.get("email")
            # No website: every spa gives the chain's home page as its own.
            item["branch"] = self.branch(store.get("store"), item["city"])

            item["opening_hours"] = self.hours(store)

            apply_category(Categories.SHOP_MASSAGE, item)

            yield item

    @staticmethod
    def branch(named: str | None, city: str | None) -> str | None:
        """Name the spa by what sets it apart from the town it stands in.

        One of them is "Chicago / Goldcoast", the town and then the
        neighbourhood, where the town is already recorded as the town. The rest
        are named for their town alone and carry no branch.
        """
        if not named:
            return None
        town, _, within = named.partition("/")
        if within and town.strip().casefold() == (city or "").casefold():
            return within.strip()
        return named if named.casefold() != (city or "").casefold() else None

    @classmethod
    def lines(cls, markup: str | None) -> list[str]:
        """Return the lines of a field the site stores as HTML."""
        text = html.unescape(re.sub(r"<[^>]+>", "\n", markup or ""))
        return [line for raw in text.split("\n") if (line := re.sub(r"\s+", " ", raw).strip())]

    def hours(self, store: dict) -> OpeningHours:
        """Read the hours from whichever field the spa states them in.

        Four of the five fill in the field meant for them. The fifth leaves it
        empty and states its hours in the description instead, in words rather
        than shortened, so whichever field holds something that reads as hours
        is the one read.
        """
        oh = OpeningHours()
        for field in ("hours", "description"):
            for line in self.lines(store.get(field)):
                if not (rule := RULE.match(line)):
                    continue
                named = [day for word in re.split(r"[-–—]", rule["days"]) if (day := sanitise_day(word))]
                if not named:
                    continue
                for day in day_range(named[0], named[-1]) if len(named) > 1 else named:
                    oh.add_range(day, self.time(rule["opens"]), self.time(rule["closes"]), "%I:%M %p")
            if oh.as_opening_hours():
                return oh

        self.logger.warning(f"{store.get('store')} states no hours this could read")
        return oh

    @staticmethod
    def time(stated: str) -> str:
        """Return "9:00am" or "9am" in the one shape strptime is given."""
        packed = re.sub(r"[\s.]", "", stated).upper()
        clock, meridiem = packed[:-2], packed[-2:]
        return f"{clock if ':' in clock else clock + ':00'} {meridiem}"

    def closed(self, reason: str) -> None:
        if reason != "finished":
            return
        if missed := {self.listed[ref] for ref in set(self.listed) - self.seen}:
            self.logger.error(f"The site lists spas the search did not reach, so widen it: {sorted(missed)}")
