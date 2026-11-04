import re
from typing import Any, Iterable

from scrapy.http import Response
from scrapy.spiders import SitemapSpider

from locations.categories import Categories, apply_category
from locations.hours import OpeningHours, day_range, sanitise_day
from locations.items import Feature

LOCALITY = re.compile(r"^(?P<city>[A-Za-z .'-]+),\s*(?P<state>[A-Z]{2})\s+(?P<postcode>\d{5})$")
# The five pages state their hours five ways: with and without a colon after the
# days, with and without spaces around the dash, with the days spelt in full or
# shortened, and with the minutes left off a whole hour. Several rules may share
# one paragraph, so the text is searched rather than matched line by line.
HOURS = re.compile(
    r"(?P<days>[A-Za-z]{3,9}(?:\s*-\s*[A-Za-z]{3,9})?)\s*:?\s*"
    r"(?P<opens>\d{1,2}(?::\d{2})?\s*[AP]\.?M\.?)\s*-\s*(?P<closes>\d{1,2}(?::\d{2})?\s*[AP]\.?M\.?)",
    re.IGNORECASE,
)


class ArirangHibachiSteakhouseUSSpider(SitemapSpider):
    name = "arirang_hibachi_steakhouse_us"
    # The site brands itself Arirang Hibachi Steakhouse throughout, in its site
    # name, its page titles and its logo, without the "& Sushi" the menu adds.
    item_attributes = {"brand": "Arirang Hibachi Steakhouse"}
    allowed_domains = ["www.partyonthegrill.com"]
    sitemap_urls = ["https://www.partyonthegrill.com/sitemap.xml"]
    sitemap_rules = [(r"/location/", "parse_location")]

    def parse_location(self, response: Response, **kwargs: Any) -> Iterable[Feature]:
        """Read the block the page heads "Hours & Location".

        Nothing is published in structured data: the page's only such block is
        empty. The section is read rather than the whole page because the page
        quotes times elsewhere, in what the party packages run to.
        """
        intro = response.css("section#intro")
        address = intro.xpath('.//a[contains(@href, "google.com/maps")]')
        lines = [text for raw in address.xpath(".//text()").getall() if (text := re.sub(r"\s+", " ", raw).strip())]
        if len(lines) < 2 or not (locality := LOCALITY.match(lines[-1])):
            self.logger.warning(f"{response.url} states an address this cannot read: {lines!r}")
            return

        item = Feature()
        item["ref"] = response.url.rstrip("/").rsplit("/", 1)[-1]
        item["website"] = response.url
        item["street_address"] = " ".join(lines[:-1]).strip().rstrip(",")
        item["city"] = locality["city"]
        item["state"] = locality["state"]
        item["postcode"] = locality["postcode"]
        item["country"] = "US"
        # Each restaurant is named for the place it stands in, which the page
        # titles ahead of the first bar. Two of the five stand in a town the slug
        # of their page names differently, so the title is what is read.
        item["branch"] = (response.xpath("//title/text()").get("").split("|")[0].split(",")[0].strip()) or None

        # The restaurant's own number is the one beside the address. A second,
        # different number follows for parties of ten or more at three of the five.
        item["phone"] = (
            address.xpath('./ancestor::p[1]//a[starts-with(@href, "tel:")]/@href').get("").removeprefix("tel:") or None
        )

        # No position: the address links to a Google search for itself, which
        # names no point, and nothing else on the page publishes one.
        item["opening_hours"] = self.hours(intro, response.url)

        item["extras"]["cuisine"] = "japanese;sushi"
        apply_category(Categories.RESTAURANT, item)

        yield item

    def hours(self, intro: Any, url: str) -> OpeningHours:
        oh = OpeningHours()
        text = re.sub(r"\s+", " ", " ".join(intro.xpath(".//text()").getall()))
        for stated in HOURS.finditer(text):
            named = [day for word in stated["days"].split("-") if (day := sanitise_day(word))]
            # The expression reaches back over whatever precedes a time, so a
            # phrase that is not a day simply yields none and is passed over.
            if not named:
                continue
            for day in day_range(named[0], named[-1]) if len(named) > 1 else named:
                oh.add_range(day, self.time(stated["opens"]), self.time(stated["closes"]), "%I:%M%p")
        if not oh.as_opening_hours():
            self.logger.warning(f"{url} states no hours this could read")
        return oh

    @staticmethod
    def time(stated: str) -> str:
        """Return "3 PM" or "10:30 PM" in the one shape strptime is given."""
        stated = re.sub(r"[\s.]", "", stated).upper()
        return stated if ":" in stated else f"{stated[:-2]}:00{stated[-2:]}"
