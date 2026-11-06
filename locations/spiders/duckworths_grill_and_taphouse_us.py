import re
from typing import Any, Iterable

from scrapy import Spider
from scrapy.http import Response

from locations.categories import Categories, apply_category
from locations.google_url import extract_google_position
from locations.hours import DAYS, OpeningHours, day_range, sanitise_day
from locations.items import Feature

LOCATOR = "https://www.duckworths.com/locations/"
# A restaurant's own page, which the locator links to and the sitemap does not
# list. Note the singular, against the plural of the locator itself.
LOCATION = re.compile(r"^/location/[^/]+/?$")
LOCALITY = re.compile(r"^(?P<city>[A-Za-z .'-]+),\s*(?P<state>[A-Z]{2})\s+(?P<postcode>\d{5})$")
# "Sun-Wed from 11am-11pm", with the minutes left off a whole hour. The word
# between the days and the times is not required, so that dropping it does not
# cost the hours.
RULE = re.compile(
    r"^(?P<days>[A-Za-z]{3,9}(?:\s*[-–&]\s*[A-Za-z]{3,9})?)\s+(?:from\s+)?"
    r"(?P<opens>\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?)\s*[-–]\s*(?P<closes>\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?)$",
    re.IGNORECASE,
)
SPLIT = re.compile(r"\s*[-–&]\s*")


class DuckworthsGrillAndTaphouseUSSpider(Spider):
    name = "duckworths_grill_and_taphouse_us"
    # As the site names itself, in its own og:site_name: "Duckworth's | Grill &
    # Taphouse in NC".
    item_attributes = {"brand": "Duckworth's Grill & Taphouse"}
    allowed_domains = ["www.duckworths.com"]
    start_urls = [LOCATOR]

    def parse(self, response: Response, **kwargs: Any) -> Iterable[Any]:
        """Follow the restaurants the locator links to.

        The sitemap lists the locator and a beer list for each restaurant but
        none of the restaurants themselves, so the locator is what names them.
        """
        found = 0
        for url in response.xpath("//a/@href").getall():
            if not LOCATION.match(re.sub(r"^https?://[^/]+", "", url)):
                continue
            found += 1
            yield response.follow(url, callback=self.parse_location)
        if not found:
            self.logger.error("The locator linked to no restaurants, so it has changed")

    def parse_location(self, response: Response, **kwargs: Any) -> Iterable[Feature]:
        """Read the block the page heads "Hours & Location".

        Nothing is published in structured data: the page's only such block is
        an empty object. The section is read rather than the whole page,
        because the page carries the restaurant's entire menu below it and the
        menu quotes both prices and times.
        """
        intro = response.css("section#intro")
        link = intro.xpath('.//a[contains(@href, "maps.google.com")]')[:1]
        lines = [text for raw in link.xpath(".//text()").getall() if (text := re.sub(r"\s+", " ", raw).strip())]
        if len(lines) < 2 or not (stated := LOCALITY.match(lines[-1])):
            self.logger.warning(f"{response.url} states an address this cannot read: {lines!r}")
            return

        item = Feature()
        item["ref"] = response.url.rstrip("/").rsplit("/", 1)[-1]
        item["website"] = response.url
        item["street_address"] = " ".join(lines[:-1]).strip().rstrip(",")
        item["city"] = stated["city"]
        item["state"] = stated["state"]
        item["postcode"] = stated["postcode"]
        item["country"] = "US"
        item["phone"] = intro.xpath('.//a[starts-with(@href, "tel:")]/@href').get("").removeprefix("tel:") or None
        item["branch"] = self.branch(
            link.xpath("@aria-label").get() or self.text(response.xpath("//h1")), stated["city"]
        )

        # Each restaurant keeps a page of its own, where the Instagram account
        # the same block links to is the chain's and is left alone.
        item["facebook"] = intro.xpath('.//a[contains(@href, "facebook.com")]/@href').get()

        # The position comes from the map the page embeds, which is a street
        # level view: it gives the point the photograph was taken from, out on
        # the road, rather than the building itself. It is the only position
        # published - the address links to a Google place by CID, which carries
        # none.
        extract_google_position(item, response)
        if not item.get("lat"):
            self.logger.warning(f"{response.url} embeds no map, so it has no position")

        item["opening_hours"] = self.hours(intro, response.url)

        # The block also states that reservations are accepted Monday to
        # Thursday, which is not recorded: the tag for it cannot say "on four
        # days of the week", and recording a plain yes would claim three days
        # the restaurant does not.
        item["extras"]["cuisine"] = "american"
        apply_category(Categories.RESTAURANT, item)

        yield item

    @staticmethod
    def branch(stated: str, city: str) -> str | None:
        """Name the restaurant as the page heads it, where that says anything.

        Four of the five are headed in capitals, which is how the page styles
        the heading rather than how the name is written, so a heading that is
        all capitals is returned in the ordinary case. One is headed SouthPark,
        which is not, and keeps the capital it is given.

        Two of the five are headed with the town they stand in, which the
        address already states, so those are left unnamed.
        """
        stated = stated.strip()
        if stated.isupper():
            stated = stated.title()
        return stated if stated and stated.casefold() != city.casefold() else None

    def hours(self, intro: Any, url: str) -> OpeningHours:
        """Read the rules the block states beneath the address and the phone.

        Each is its own paragraph, alongside paragraphs that state no hours, so
        the rules are recognised by naming days and then times. A dash spans
        the days between the two named and an ampersand names only the pair.
        """
        oh = OpeningHours()
        for paragraph in intro.xpath(".//p"):
            if not (rule := RULE.match(self.text(paragraph))):
                continue
            named = [day for word in SPLIT.split(rule["days"]) if (day := sanitise_day(word))]
            if not named:
                continue
            spans = len(named) > 1 and "&" not in rule["days"]
            for day in day_range(named[0], named[-1]) if spans else named:
                oh.add_range(day, self.time(rule["opens"]), self.time(rule["closes"]), "%I:%M %p")

        if not oh.as_opening_hours():
            self.logger.warning(f"{url} states no hours this could read")
        elif len(set(oh.day_hours) | oh.days_closed) < len(DAYS):
            self.logger.info(f"{url} states nothing for some days of the week")
        return oh

    @staticmethod
    def text(selector: Any) -> str:
        return re.sub(r"\s+", " ", " ".join(selector.xpath(".//text()").getall())).strip()

    @staticmethod
    def time(stated: str) -> str:
        """Return "11am" or "11:30 pm" in the one shape strptime is given."""
        packed = re.sub(r"[\s.]", "", stated).upper()
        clock, meridiem = packed[:-2], packed[-2:]
        return f"{clock if ':' in clock else clock + ':00'} {meridiem}"
