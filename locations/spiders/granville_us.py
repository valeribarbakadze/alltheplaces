import re
from typing import Any, Iterable

from scrapy import Spider
from scrapy.http import Response

from locations.categories import Categories, Extras, apply_category, apply_yes_no
from locations.hours import DAYS, OpeningHours, day_range, sanitise_day
from locations.items import Feature

# The restaurants are listed on the home page, which is also where the menu's
# "Contact & Locations" points.
LOCATOR = "https://www.granville.com/"
# Each restaurant is written as one line ending in the state and the postcode,
# with no comma between the street and the town: "121 N. San Fernando Boulevard
# Burbank, CA 91502".
ADDRESS = re.compile(r"^(?P<local>.+),\s*(?P<state>[A-Z]{2})\s+(?P<postcode>\d{5})$")
# "Mon - Thurs 11:30am - 9pm", with the minutes left off a whole hour.
RULE = re.compile(
    r"^(?P<days>[A-Za-z]{3,9}(?:\s*[-–&]\s*[A-Za-z]{3,9})?)\s+"
    r"(?P<opens>\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?)\s*[-–]\s*(?P<closes>\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?)$",
    re.IGNORECASE,
)
SPLIT = re.compile(r"\s*[-–&]\s*")
# What the page offers alongside the hours a restaurant keeps, which is not one.
PROMOTION = re.compile(r"happy hour|brunch", re.IGNORECASE)
NO_BOOKING = re.compile(r"\bno reservations\b", re.IGNORECASE)
# "Tel: 818-962-0858", where the number is not a link.
PHONE = re.compile(r"^Tel:\s*(?P<number>[\d\s().+-]{7,})$", re.IGNORECASE)
BOOKING = re.compile(r"\breservations\b", re.IGNORECASE)


class GranvilleUSSpider(Spider):
    name = "granville_us"
    item_attributes = {"brand": "GRANVILLE"}
    allowed_domains = ["www.granville.com"]
    start_urls = [LOCATOR]

    def parse(self, response: Response, **kwargs: Any) -> Iterable[Feature]:
        """Read the pair of blocks the page gives each restaurant.

        The page is built with Wix, which writes each restaurant as two blocks
        in a row: one holding nothing but a heading, and the next holding the
        hours, the address, the phone and the email. They are paired by that
        order rather than by any name, and a pair is only taken when the second
        block states an address.

        The sitemap lists eight pages and none of them is a locator; the menu's
        "Contact & Locations" points back at this page.
        """
        blocks = response.xpath('//div[@data-testid="richTextElement"]')
        found = 0
        for position, block in enumerate(blocks):
            heading = self.text(block.xpath(".//h2"))
            # A heading block holds a heading and nothing else.
            if not heading or self.text(block) != heading or position + 1 >= len(blocks):
                continue
            detail = blocks[position + 1]
            lines = self.lines(detail)
            stated = next(((i, m) for i, line in enumerate(lines) if (m := ADDRESS.match(line))), None)
            if not stated:
                continue

            found += 1
            at, address = stated
            # Four of the five write the street and the town on one line. The
            # fifth gives the street a line of its own, so where the line
            # states the town alone the street is the line above it.
            street, city = self.split(address["local"], heading)
            if not city and self.slug(address["local"]) == self.slug(heading):
                street, city = (lines[at - 1] if at else ""), address["local"]
            if not city or not street:
                self.logger.warning(f"{heading} states an address this cannot read: {lines[max(0, at - 1) : at + 1]!r}")
                continue

            item = Feature()
            item["ref"] = self.slug(heading)
            item["street_address"] = street
            item["city"] = city
            item["state"] = address["state"]
            item["postcode"] = address["postcode"]
            item["country"] = "US"
            # No branch: each restaurant is headed with the town it stands in,
            # which the address states as the town. No website either: the
            # restaurants have no pages, and the only page there is lists all
            # five.
            # Four of the five link their number. The fifth writes it as plain
            # text, so the line it heads "Tel:" is read where there is no link.
            item["phone"] = detail.xpath('.//a[starts-with(@href, "tel:")]/@href').get("").removeprefix("tel:") or None
            if not item["phone"]:
                item["phone"] = next((m["number"].strip() for line in lines if (m := PHONE.match(line))), None)
            if not item["phone"]:
                self.logger.warning(f"{heading} states no phone number this could read")
            item["email"] = (
                detail.xpath('.//a[starts-with(@href, "mailto:")]/@href').get("").removeprefix("mailto:") or None
            )

            # No position. Every one of the blocks links its first line to one
            # Google place - the Burbank restaurant's - so the link in a block
            # says nothing about the restaurant the block is for, and taking it
            # would put all five at one point. Three blocks carry a second link
            # of their own, but those name a map centred at zoom 15 rather than
            # a pin, and a page whose links are pasted about is not one to read
            # a position from.
            item["opening_hours"] = self.hours(lines[at + 1 :] + lines[:at], heading)

            # Four of the five take bookings and the fifth states that it does
            # not, so what each states is recorded.
            if NO_BOOKING.search(" ".join(lines)):
                # Stated outright - "No Reservations. First-Come,
                # First-Served" - rather than merely left unsaid, so the no is
                # recorded as such.
                apply_yes_no(Extras.RESERVATION, item, False, apply_positive_only=False)
            elif BOOKING.search(" ".join(lines)):
                apply_yes_no(Extras.RESERVATION, item, True)

            apply_category(Categories.RESTAURANT, item)

            yield item

        if not found:
            self.logger.error("The page holds no restaurant blocks, so it has changed")

    @classmethod
    def text(cls, selector: Any) -> str:
        """Join the text of a block without putting anything between its parts.

        Wix breaks a line across several spans wherever its styling changes, so
        "11136 Magnolia Blvd" is written as "11136 Magnolia Blv" and then "d".
        Joining those with a space would spell the street wrongly, and three of
        the five addresses are broken this way.
        """
        return cls.clean("".join(selector.xpath(".//text()").getall()))

    @staticmethod
    def clean(value: str) -> str:
        # The page is littered with zero width spaces, which it uses for
        # vertical spacing.
        return re.sub(r"[\s ​]+", " ", value).strip()

    @classmethod
    def lines(cls, block: Any) -> list[str]:
        """Return the block's own lines, each joined without a separator."""
        found = []
        for line in block.xpath(".//p | .//li"):
            if line.root.tag == "li" and line.xpath(".//p"):
                continue
            if text := cls.text(line):
                found.append(text)
        return found

    @staticmethod
    def slug(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")

    @classmethod
    def split(cls, local: str, heading: str) -> tuple[str, str | None]:
        """Divide "121 N. San Fernando Boulevard Burbank" into street and town.

        The heading says which town it is, so the words at the end of the line
        that spell that town are the town and what stands before them is the
        street. Matching from the end matters: one stands on Magnolia Boulevard
        in North Hollywood, and the town is two words.
        """
        words = local.split()
        for count in range(1, min(4, len(words))):
            if cls.slug(" ".join(words[-count:])) == cls.slug(heading):
                return " ".join(words[:-count]), " ".join(words[-count:])
        return local, None

    def hours(self, lines: list[str], heading: str) -> OpeningHours:
        """Read the rules among the block's lines.

        A rule names days and then times, which is how it is told from the
        address, the phone and what the restaurant says about bookings. The
        page also offers a happy hour and a weekend brunch, which are not the
        hours a restaurant keeps and are left out.
        """
        oh = OpeningHours()
        for line in lines:
            if PROMOTION.search(line) or not (rule := RULE.match(line)):
                continue
            named = [day for word in SPLIT.split(rule["days"]) if (day := sanitise_day(word))]
            if not named:
                continue
            spans = len(named) > 1 and "&" not in rule["days"]
            for day in day_range(named[0], named[-1]) if spans else named:
                oh.add_range(day, self.time(rule["opens"]), self.time(rule["closes"]), "%I:%M %p")

        if not oh.as_opening_hours():
            self.logger.warning(f"{heading} states no hours this could read")
        elif len(set(oh.day_hours) | oh.days_closed) < len(DAYS):
            self.logger.info(f"{heading} states nothing for some days of the week")
        return oh

    @staticmethod
    def time(stated: str) -> str:
        """Return "9pm" or "11:30am" in the one shape strptime is given."""
        packed = re.sub(r"[\s.]", "", stated).upper()
        clock, meridiem = packed[:-2], packed[-2:]
        return f"{clock if ':' in clock else clock + ':00'} {meridiem}"
