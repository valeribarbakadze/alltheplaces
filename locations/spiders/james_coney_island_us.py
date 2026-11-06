import re
from typing import Any, Iterable

from scrapy import Spider
from scrapy.http import Response

from locations.categories import Categories, Extras, apply_category, apply_yes_no
from locations.hours import DAYS, OpeningHours, day_range, sanitise_day
from locations.items import Feature

LOCATOR = "https://jamesconeyisland.com/locations/"
# The second line of the address. The corporate office in the footer writes its
# state out in full - "Houston, Texas 77043" - so it never matches this and is
# not taken for a restaurant.
LOCALITY = re.compile(r"^(?P<city>[A-Za-z .'-]+),\s*(?P<state>[A-Z]{2})\s+(?P<postcode>\d{5})$")
# A Google place link's own pin, against the @ that follows it, which is where
# the map is centred.
PIN = re.compile(r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)")
# "Mon - Thur: 11:00AM - 9:00PM", several to a paragraph, so the text is
# searched rather than matched line by line.
RULE = re.compile(
    r"(?P<days>[A-Za-z]{3,9}(?:\s*[-–—]\s*[A-Za-z]{3,9})?)\s*:\s*"
    r"(?P<opens>\d{1,2}(?::\d{2})?\s*[AP]\.?M\.?)\s*[-–—]\s*(?P<closes>\d{1,2}(?::\d{2})?\s*[AP]\.?M\.?)",
    re.IGNORECASE,
)
# What the link to order by states it is for. Both words are the merchant's own,
# so both are recorded; where a restaurant adds a delivery company of its own,
# that says the same thing again.
COLLECTS = re.compile(r"\bpick\s?up\b", re.IGNORECASE)
DELIVERS = re.compile(r"\bdeliver(?:y|s)\b", re.IGNORECASE)


class JamesConeyIslandUSSpider(Spider):
    name = "james_coney_island_us"
    item_attributes = {"brand": "James Coney Island", "brand_wikidata": "Q6131624"}
    allowed_domains = ["jamesconeyisland.com"]
    start_urls = [LOCATOR]

    def parse(self, response: Response, **kwargs: Any) -> Iterable[Feature]:
        """Read the block the page gives each restaurant.

        The page is built with Elementor, which wraps each restaurant in a
        block of widgets. The blocks are recognised by what they hold - one
        heading, one phone number and one address - rather than by their
        position, since the markup carries no class that names a restaurant.

        The address and the hours are written inside a paragraph nested in a
        heading, which is not allowed: the parser closes the heading and lifts
        the paragraph out beside it. So the paragraphs are what is read, and
        the headings themselves come back empty.
        """
        found = 0
        for block in response.xpath('//div[contains(@class, "elementor-widget-wrap")]'):
            stated = [
                lines
                for paragraph in block.xpath(".//p")
                if len(lines := self.lines(paragraph)) > 1 and LOCALITY.match(lines[-1])
            ]
            if len(stated) != 1 or len(block.xpath(".//h3")) != 1:
                continue
            if len(telephone := block.xpath('.//a[starts-with(@href, "tel:")]')) != 1:
                continue

            found += 1
            lines = stated[0]
            address = LOCALITY.match(lines[-1])
            named = self.text(block.xpath(".//h3"))

            item = Feature()
            item["ref"] = self.slug(named)
            item["street_address"] = " ".join(lines[:-1])
            item["city"] = address["city"]
            item["state"] = address["state"]
            item["postcode"] = address["postcode"]
            item["country"] = "US"
            item["phone"] = telephone.xpath("@href").get("").removeprefix("tel:") or None
            # The restaurants have no pages of their own; the only link each
            # gives is to order from, which is a third party's.
            #
            # The heading is recorded as the page writes it, in capitals. Four
            # of the five are places - Hollister, Meyerland, Woodlands, Humble -
            # but the fifth is NASA, for the space centre it stands near, and
            # putting the capitals into ordinary case would spell that Nasa.
            # There is nothing on the site that writes the five any other way.
            item["branch"] = named if named.casefold() != address["city"].casefold() else None

            if pin := PIN.search(block.xpath('.//a[contains(@href, "google.com/maps")]/@href').get("") or ""):
                item["lat"], item["lon"] = pin.groups()
            else:
                self.logger.warning(f"{named} links a map that names no position")

            item["opening_hours"] = self.hours(block, named)

            offered = " ".join(self.text(link) for link in block.xpath(".//a"))
            if DELIVERS.search(offered):
                apply_yes_no(Extras.DELIVERY, item, True)
            if COLLECTS.search(offered):
                apply_yes_no(Extras.TAKEAWAY, item, True)

            item["extras"]["cuisine"] = "hot_dog"
            apply_category(Categories.FAST_FOOD, item)

            yield item

        if not found:
            self.logger.error("The locator holds no restaurant blocks, so the page has changed")

    @classmethod
    def lines(cls, paragraph: Any) -> list[str]:
        return [line for raw in paragraph.xpath(".//text()").getall() if (line := cls.clean(raw))]

    @classmethod
    def text(cls, selector: Any) -> str:
        return cls.clean(" ".join(selector.xpath(".//text()").getall()))

    @staticmethod
    def clean(value: str) -> str:
        return re.sub(r"[\s ]+", " ", value).strip()

    @staticmethod
    def slug(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")

    def hours(self, block: Any, named: str) -> OpeningHours:
        """Read the rules the block states, which share one paragraph."""
        oh = OpeningHours()
        for paragraph in block.xpath(".//p"):
            for rule in RULE.finditer(self.text(paragraph)):
                spoken = [day for word in re.split(r"[-–—]", rule["days"]) if (day := sanitise_day(word))]
                if not spoken:
                    continue
                for day in day_range(spoken[0], spoken[-1]) if len(spoken) > 1 else spoken:
                    oh.add_range(day, self.time(rule["opens"]), self.time(rule["closes"]), "%I:%M %p")

        if not oh.as_opening_hours():
            self.logger.warning(f"{named} states no hours this could read")
        elif len(set(oh.day_hours) | oh.days_closed) < len(DAYS):
            self.logger.info(f"{named} states nothing for some days of the week")
        return oh

    @staticmethod
    def time(stated: str) -> str:
        """Return "11:00AM" or "11AM" in the one shape strptime is given."""
        packed = re.sub(r"[\s.]", "", stated).upper()
        clock, meridiem = packed[:-2], packed[-2:]
        return f"{clock if ':' in clock else clock + ':00'} {meridiem}"
