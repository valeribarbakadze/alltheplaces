import re
from typing import Any, Iterable

from scrapy import Spider
from scrapy.http import Response

from locations.categories import Categories, Extras, apply_category, apply_yes_no
from locations.google_url import extract_google_position
from locations.hours import DAYS, OpeningHours, day_range, sanitise_day
from locations.items import Feature

LOCATOR = "https://badbradsbbq.com/locations"
# A restaurant's page is one segment below the locator.
LOCATION = re.compile(r"^/locations/[^/]+/?$")
# The town, state and postcode are punctuated three ways between the five:
# "Clinton Township, MI 48035", "Livonia MI, 48152", "New Baltimore, MI, 48047".
LOCALITY = re.compile(r"^(?P<city>[A-Za-z .'-]+?)[,\s]+(?P<state>[A-Z]{2})[,\s]+(?P<postcode>\d{5})$")
# "11:00 AM - 9:00 PM", against days given as a span with a dash or a pair with
# an ampersand.
TIMES = re.compile(
    r"^(?P<opens>\d{1,2}(?::\d{2})?\s*[AP]\.?M\.?)\s*-\s*(?P<closes>\d{1,2}(?::\d{2})?\s*[AP]\.?M\.?)$",
    re.IGNORECASE,
)
SHUT = re.compile(r"^closed$", re.IGNORECASE)
# What the ribbon beneath the hours says each restaurant has. Catering is listed
# too, which is a service rather than something the place holds, so it is left.
RIBBON = {
    "dine-in": Extras.INDOOR_SEATING,
    "full bar": Extras.BAR,
    "patio": Extras.OUTDOOR_SEATING,
    "carryout": Extras.TAKEAWAY,
    "delivery": Extras.DELIVERY,
}


class BadBradsBbqUSSpider(Spider):
    name = "bad_brads_bbq_us"
    item_attributes = {"brand": "Bad Brads BBQ"}
    allowed_domains = ["badbradsbbq.com"]
    start_urls = [LOCATOR]

    def parse(self, response: Response, **kwargs: Any) -> Iterable[Any]:
        """Follow the restaurants the locator links to.

        The site answers every path with a page, so its sitemap.xml is the same
        document as sitemap_index.xml and as any other name asked for, and none of
        them list anything. The locator is what names the restaurants.

        A sixth, in Ferndale, is named in the menu as opening in the summer of
        2026, but it is plain text there rather than a link and has no page, so
        there is nothing of it to collect.
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
        block = response.css("div.location-section-1")
        address = block.xpath('.//a[contains(@href, "goo.gl") or contains(@href, "google")]')
        lines = [text for raw in address.xpath(".//text()").getall() if (text := re.sub(r"\s+", " ", raw).strip())]

        # One of the five follows its address with the crossroads it stands on, so
        # the line naming the town is found rather than assumed to be the last.
        locality = next(((i, m) for i, line in enumerate(lines) if (m := LOCALITY.match(line))), None)
        if not locality or not locality[0]:
            self.logger.warning(f"{response.url} states an address this cannot read: {lines!r}")
            return
        position, stated = locality

        item = Feature()
        item["ref"] = response.url.rstrip("/").rsplit("/", 1)[-1]
        item["website"] = response.url
        item["branch"] = re.sub(r"\s+", " ", " ".join(response.css("h2.condensed-title::text").getall())).strip()
        item["street_address"] = lines[position - 1].rstrip(",")
        item["city"] = stated["city"]
        item["state"] = stated["state"]
        item["postcode"] = stated["postcode"]
        item["country"] = "US"
        item["phone"] = block.xpath('.//a[starts-with(@href, "tel:")]/@href').get("").removeprefix("tel:") or None

        # The position comes from the map the page embeds. The address link is a
        # shortened one, which no longer redirects to anything a crawl can read.
        extract_google_position(item, response)
        if not item.get("lat"):
            self.logger.warning(f"{response.url} embeds no map, so it has no position")

        item["opening_hours"] = self.hours(response)

        # Only what the ribbon states is recorded. Its absence is not read as a
        # denial, since the ribbon need not be a complete account of the place.
        offered = {text.strip().lower() for text in response.css("#location-ribbon div::text").getall()}
        for stated_feature, tag in RIBBON.items():
            if stated_feature in offered:
                apply_yes_no(tag, item, True)

        item["extras"]["cuisine"] = "barbecue"
        apply_category(Categories.RESTAURANT, item)

        yield item

    def hours(self, response: Response) -> OpeningHours:
        oh = OpeningHours()
        for rule in response.css("ul#location-hours li"):
            label = re.sub(r"\s+", " ", " ".join(rule.xpath("./b//text() | ./strong//text()").getall())).strip()
            value = re.sub(r"\s+", " ", " ".join(rule.xpath("./text() | ./span//text()").getall())).strip(" :")
            named = [day for word in re.split(r"[-&]", label) if (day := sanitise_day(word))]
            if not named:
                self.logger.warning(f"{response.url} states days this cannot read: {label!r}")
                continue
            # A dash spans the days between the two named, an ampersand names only
            # the pair, which is how "Saturday & Sunday" differs from "Mon - Fri".
            days = day_range(named[0], named[-1]) if len(named) > 1 and "-" in label else named
            if SHUT.match(value):
                for day in days:
                    oh.set_closed(day)
            elif times := TIMES.match(value):
                for day in days:
                    oh.add_range(day, self.time(times["opens"]), self.time(times["closes"]), "%I:%M%p")
            else:
                self.logger.warning(f"{response.url} states hours this cannot read: {label!r}: {value!r}")
        if len(set(oh.day_hours) | oh.days_closed) < len(DAYS):
            self.logger.info(f"{response.url} states nothing for some days of the week")
        return oh

    @staticmethod
    def time(stated: str) -> str:
        stated = re.sub(r"[\s.]", "", stated).upper()
        return stated if ":" in stated else f"{stated[:-2]}:00{stated[-2:]}"
