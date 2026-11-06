import re
from typing import Any, Iterable

from scrapy.http import Response
from scrapy.spiders import SitemapSpider

from locations.categories import Categories, apply_category
from locations.hours import DAYS, OpeningHours, day_range, sanitise_day
from locations.items import Feature

# The address is written over two lines, and one restaurant puts a comma before
# its postcode where the others do not.
ADDRESS = re.compile(r"^(?P<street>.+?),\s*(?P<city>[A-Za-z .'-]+),\s*(?P<state>[A-Z]{2}),?\s*(?P<postcode>\d{5})$")
# The page heads its contact form with the restaurant's own name.
NAMED = re.compile(r"^Contact\s+(?P<branch>.+?)\s+Restaurant$", re.IGNORECASE)
# A Google route ends at the restaurant, which it names longitude first. The @
# that precedes it is where the map is centred, which is somewhere else.
PIN = re.compile(r"!1d(-?\d+\.\d+)!2d(-?\d+\.\d+)")
TIMES = re.compile(
    r"(?P<opens>\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?)\s*[-–—]\s*(?P<closes>\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?)",
    re.IGNORECASE,
)
# "Lounge: 4:30pm - 9:30pm", "Happy Hour: 4:30pm - 6:00pm", "Dining Room: 5:00pm
# - 9:00pm": what the times belong to, where the page states it inline rather
# than as a heading.
VENUE = re.compile(r"^(?P<venue>[A-Za-z][A-Za-z &|]{1,24}?):\s*(?P<rest>.*)$")
# The dining room's hours are the restaurant's. Takeout, delivery, the lounge
# and the happy hour are not.
DINING = re.compile(r"\bdining\b", re.IGNORECASE)
PAIR = re.compile(r"&|\band\b", re.IGNORECASE)


class RokaAkorUSSpider(SitemapSpider):
    name = "roka_akor_us"
    item_attributes = {"brand": "Roka Akor"}
    allowed_domains = ["rokaakor.com"]
    sitemap_urls = ["https://rokaakor.com/sitemap_index.xml"]
    # Each restaurant keeps a page for its address and hours. The bare page at
    # /<name>/ repeats them, so the one page is read.
    sitemap_rules = [(r"/location-information/$", "parse_location")]

    def parse_location(self, response: Response, **kwargs: Any) -> Iterable[Feature]:
        """Read the block the page heads "Locations" and "Hours".

        Nothing here is taken from the page's structured data, which cannot be
        relied on. Its Restaurant block holds every restaurant at once, and
        every telephone number in it ends 123-4567 - a placeholder rather than
        a number - while its addresses disagree with the pages: it puts the
        Chicago restaurant at 111 West Illinois Street where the page states
        456 N Clark St, and numbers the Old Orchard one 4905 where the page
        states 4999. Its hours are the chain's rather than each restaurant's,
        and it carries reviews and ratings besides. The page is maintained; the
        block is not.
        """
        block = response.xpath('//section[contains(@class, "side-img--map")]')
        stated = block.xpath('.//h2[normalize-space()="Locations"]/following-sibling::p[1]')
        # The lines are divided by breaks, and one restaurant ends its street
        # with a comma that the joining would double.
        lines = [line.rstrip(",") for raw in stated.xpath("./text()").getall() if (line := self.clean(raw))]
        if not (address := ADDRESS.match(", ".join(lines))):
            self.logger.warning(f"{response.url} states an address this cannot read: {lines!r}")
            return

        item = Feature()
        item["ref"] = response.url.rstrip("/").rsplit("/", 2)[-2]
        item["website"] = response.url
        item["street_address"] = address["street"]
        item["city"] = address["city"]
        item["state"] = address["state"]
        item["postcode"] = address["postcode"]
        item["country"] = "US"
        item["phone"] = block.xpath('.//a[starts-with(@href, "tel:")]/@href').get("").removeprefix("tel:") or None

        # Named for the place it stands in, which four of the five state as
        # their town as well. Only the Old Orchard one is named for something
        # other than its town, and it is the only one to carry a branch.
        named = NAMED.match(
            self.clean("".join(response.xpath('//h2[starts-with(normalize-space(), "Contact ")]//text()').getall()))
        )
        branch = named["branch"] if named else None
        item["branch"] = branch if branch and branch.casefold() != address["city"].casefold() else None

        # The position comes from the route the DIRECTIONS link ends at. The
        # map the page embeds searches Google for the address instead, which
        # names no point.
        if pin := PIN.search(block.xpath('.//a[normalize-space()="DIRECTIONS"]/@href').get("") or ""):
            item["lon"], item["lat"] = pin.groups()
        else:
            self.logger.warning(f"{item['ref']} links a route that names no position")

        item["opening_hours"] = self.hours(block, response.url)

        item["extras"]["cuisine"] = "japanese;sushi"
        apply_category(Categories.RESTAURANT, item)

        yield item

    @staticmethod
    def clean(value: str) -> str:
        return re.sub(r"[\s ]+", " ", value).strip()

    @classmethod
    def named_days(cls, stated: str) -> list[str]:
        """Read "Monday - Thursday & Sunday" as the five days it names.

        A dash spans the days between the two named and an ampersand joins what
        it stands between, so a rule may hold a span and a day at once.
        """
        found: list[str] = []
        for group in PAIR.split(stated):
            named = [day for word in re.split(r"[-–—]", group) if (day := sanitise_day(word))]
            if not named:
                continue
            found += day_range(named[0], named[-1]) if len(named) > 1 else named
        return found

    def hours(self, block: Any, url: str) -> OpeningHours:
        """Read the dining room's hours out of the five ways they are written.

        Four restaurants head each set of hours with what it is for - "Dining",
        "Dining Room", "Takeout", "Take Out & Delivery", "Happy Hour" - and
        state the days and the times beneath it, either on two lines or on one
        divided by a bullet. The happy hour comes first at one of them, so the
        headings are followed rather than the reading being stopped at the
        first that is not the dining room's.

        The fifth states the day first and then a line for each room: "Monday -
        Thursday", "Lounge: 4:30pm - 9:30pm", "Dining Room: 5:00pm - 9:00pm".
        There what the times belong to is named on the line itself, so both
        forms are read by asking of every line what it is for before what it
        says.
        """
        oh = OpeningHours()
        # None until the page heads a set of hours with something: the
        # restaurant that heads none of them states what each line is for.
        section: str | None = None
        days: list[str] = []

        for paragraph in block.xpath('.//h2[normalize-space()="Hours"]/following-sibling::p'):
            if heading := self.clean(" ".join(paragraph.xpath("./strong//text()").getall())):
                section = "dining" if DINING.search(heading) else "other"
            if section == "other":
                continue

            for raw in paragraph.xpath(".//text()").getall():
                if not (line := self.clean(raw)) or line == heading:
                    continue
                if named := VENUE.match(line):
                    if spoken := self.named_days(named["venue"]):
                        days = spoken
                        continue
                    if not DINING.search(named["venue"]):
                        continue
                    line = named["rest"]
                if not (times := TIMES.search(line)):
                    if spoken := self.named_days(line):
                        days = spoken
                    continue
                if spoken := self.named_days(line[: times.start()].strip(" •:")):
                    days = spoken
                for day in days:
                    oh.add_range(day, self.time(times["opens"]), self.time(times["closes"]), "%I:%M %p")

        if not oh.as_opening_hours():
            self.logger.warning(f"{url} states no dining hours this could read")
        elif len(set(oh.day_hours) | oh.days_closed) < len(DAYS):
            self.logger.info(f"{url} states nothing for some days of the week")
        return oh

    @staticmethod
    def time(stated: str) -> str:
        """Return "5:00 pm", "4:00 p.m." or "5pm" in the one shape strptime is given."""
        packed = re.sub(r"[\s.]", "", stated).upper()
        clock, meridiem = packed[:-2], packed[-2:]
        return f"{clock if ':' in clock else clock + ':00'} {meridiem}"
