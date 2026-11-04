import re
from collections import defaultdict
from datetime import datetime
from typing import Any, Iterable
from urllib.parse import unquote

from scrapy import Spider
from scrapy.http import Response

from locations.categories import Categories, apply_category
from locations.hours import OpeningHours, day_range, sanitise_day
from locations.items import Feature

# The label the locator's menu gives each restaurant: "Hobbs, NM", and for the
# one of two El Paso restaurants it still lists, "El Paso, TX (On Airway)".
LABEL = re.compile(r"^(?P<branch>.+?),\s*[A-Z]{2}\b\s*(?P<note>\(.*\))?$")
LOCALITY = re.compile(r"^(?P<city>[A-Za-z .'-]+),\s*(?P<state>[A-Z]{2})\s+(?P<postcode>\d{5})$")
# "Mon-Sun 11AM-9PM" on five of the six, spelt with an en dash on three of those.
STATED = re.compile(
    r"^(?P<days>[A-Za-z]+(?:\s*[-–]\s*[A-Za-z]+)?)\s+"
    r"(?P<opens>\d{1,2}(?::\d{2})?\s*[AP]M)\s*[-–]\s*(?P<closes>\d{1,2}(?::\d{2})?\s*[AP]M)$",
    re.IGNORECASE,
)
# "Sunday through Thursday: 11 to 8:30" on the sixth, which names no meridiem.
BARE = re.compile(
    r"^(?P<days>[A-Za-z]+(?:\s*(?:through|to|and|[-–])\s*[A-Za-z]+)?)\s*:\s*"
    r"(?P<opens>\d{1,2}(?::\d{2})?)\s+to\s+(?P<closes>\d{1,2}(?::\d{2})?)$",
    re.IGNORECASE,
)
SPLIT = re.compile(r"\s*(?:through|and|to|[-–])\s*", re.IGNORECASE)


class CattleBaronUSSpider(Spider):
    name = "cattle_baron_us"
    item_attributes = {"brand": "Cattle Baron"}
    allowed_domains = ["www.cattlebaron.com"]
    start_urls = ["https://www.cattlebaron.com/"]
    # robots.txt asks for three seconds between requests, which is slower than
    # this project's default of one.
    custom_settings = {"DOWNLOAD_DELAY": 3}

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # Towns by the postcode they publish, to find a postcode given to two of them.
        self.postcodes: dict[str, set[str]] = defaultdict(set)

    def parse(self, response: Response, **kwargs: Any) -> Iterable[Any]:
        """Follow the restaurants named in the menu's Locations submenu.

        The pages sit at the top level under slugs of town and street, among
        pages for job adverts and anniversary posts that begin with a town's name
        in the same way, so the sitemap cannot tell them apart. The submenu names
        exactly the restaurants the chain is trading, each labelled with its town.
        """
        found = 0
        for link in response.xpath('//li[a[normalize-space()="Locations"]]//a[contains(@class, "sub-item")]'):
            if not (url := link.xpath("@href").get()):
                continue
            label = re.sub(r"\s+", " ", " ".join(link.xpath(".//text()").getall())).strip()
            found += 1
            yield response.follow(url, callback=self.parse_location, cb_kwargs={"label": label})
        if not found:
            self.logger.error("The Locations submenu named no restaurants, so the locator has changed")

    def parse_location(self, response: Response, label: str) -> Iterable[Feature]:
        """Read the block of address and hours the page states.

        The block is written into one of the page builder's text widgets, as a
        paragraph on five of the six pages and as a heading on the sixth, so the
        widget is what is read rather than any one tag. The line naming the town,
        state and postcode is the anchor: the street stands on the line before it
        and the hours on the line after.
        """
        lines = [
            text
            for raw in response.xpath('//div[contains(@class, "elementor-widget-text-editor")]//text()').getall()
            if (text := re.sub(r"\s+", " ", raw).strip()) and text not in {"-", "–"}
        ]

        for position, line in enumerate(lines):
            if locality := LOCALITY.match(line):
                break
        else:
            self.logger.warning(f"{response.url} states no address, so this restaurant is not published")
            return

        item = Feature()
        item["ref"] = response.url.rstrip("/").rsplit("/", 1)[-1]
        item["website"] = response.url
        item["branch"] = self.branch(label)
        item["street_address"] = lines[position - 1] if position else None
        item["city"] = locality["city"]
        item["state"] = locality["state"]
        item["postcode"] = locality["postcode"]
        item["country"] = "US"
        # One of the six writes its number with an encoded space, "(575)%20522-7533".
        telephone = response.xpath('//a[starts-with(@href, "tel:")]/@href').get("").removeprefix("tel:")
        item["phone"] = unquote(telephone) or None

        item["opening_hours"] = self.hours(lines[position + 1 :], response)

        # No position: the page's only map is an embed that searches Google for
        # the restaurant by name rather than naming a point.
        apply_category(Categories.RESTAURANT, item)
        item["extras"]["cuisine"] = "steak_house"

        self.postcodes[item["postcode"]].add(item["city"])

        yield item

    @staticmethod
    def branch(label: str) -> str | None:
        """Return the restaurant's name without the state the address states."""
        if not (match := LABEL.match(label)):
            return label or None
        return " ".join(part for part in (match["branch"], match["note"]) if part).strip()

    def hours(self, lines: list[str], response: Response) -> OpeningHours:
        oh = OpeningHours()
        for line in lines:
            if line.startswith("("):
                # The note that follows says the hours may change without notice.
                break
            if stated := STATED.match(line):
                self.add(oh, stated["days"], stated["opens"], stated["closes"])
            elif bare := BARE.match(line):
                # Neither time names a meridiem: "11 to 8:30". Read as the day it
                # describes, opening in the morning and closing in the evening,
                # which is the only reading in which the range runs forwards.
                opens, closes = self.meridiem(bare["opens"], bare["closes"])
                self.add(oh, bare["days"], opens, closes)
                self.logger.info(f"{response.url} names no am or pm, so {line!r} is read as {opens}-{closes}")
            elif any(sanitise_day(word) for word in SPLIT.split(line)[:1]):
                self.logger.warning(f"{response.url} states hours this cannot read: {line!r}")
        return oh

    @staticmethod
    def meridiem(opens: str, closes: str) -> tuple[str, str]:
        def hour(time: str) -> float:
            parts = time.split(":")
            return int(parts[0]) + (int(parts[1]) / 60 if len(parts) > 1 else 0)

        return f"{opens}AM", f"{closes}{'PM' if hour(closes) <= hour(opens) else 'AM'}"

    @staticmethod
    def normalise(time: str) -> str:
        """Return "11AM" or "8:30 pm" as a time of day.

        The minutes are left off whenever they are zero, so the format depends on
        the value rather than on the page.
        """
        time = re.sub(r"[\s.]", "", time).upper()
        return datetime.strptime(time, "%I:%M%p" if ":" in time else "%I%p").strftime("%H:%M")

    @classmethod
    def add(cls, oh: OpeningHours, days: str, opens: str, closes: str) -> None:
        """Apply one stated range to the days it names.

        How the days are joined says whether they are a span or a pair: "Mon-Sun"
        and "Sunday through Thursday" name every day between the two, while
        "Friday and Saturday" names only those two.
        """
        named = [day for word in SPLIT.split(days) if (day := sanitise_day(word))]
        if not named:
            return
        if len(named) > 1 and not re.search(r"\band\b", days, re.IGNORECASE):
            named = day_range(named[0], named[-1])
        for day in named:
            oh.add_range(day, cls.normalise(opens), cls.normalise(closes))

    def closed(self, reason: str) -> None:
        """Report a postcode the locator gives to two different towns.

        Two towns cannot share one, so it is wrong for at least one of them, and
        the page gives nothing to say which. Both are published as stated.
        """
        for postcode, cities in self.postcodes.items():
            if len(cities) > 1:
                self.logger.warning(
                    "{} are both published in {}, which belongs to one town at most".format(
                        " and ".join(sorted(cities)), postcode
                    )
                )
