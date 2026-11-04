import re
from typing import Any, Iterable
from urllib.parse import urlparse

from scrapy import Spider
from scrapy.http import Response

from locations.categories import Categories, apply_category
from locations.hours import OpeningHours, day_range, sanitise_day
from locations.items import Feature

LOCATOR = "https://acmeoyster.com/acme-locations/"
LOCALITY = re.compile(r"^(?P<city>[A-Za-z .'-]+),\s*(?P<state>[A-Z]{2})\s+(?P<postcode>\d{5})$")
# "SUN – THURS: 11AM – 10PM", with an en dash between the days and between the
# times, and the minutes left off when they are zero.
HOURS = re.compile(
    r"^(?P<days>[A-Za-z]{3,6}(?:\s*[-–]\s*[A-Za-z]{3,6})?)\s*:\s*"
    r"(?P<opens>\d{1,2}(?::\d{2})?\s*[AP]M)\s*[-–]\s*(?P<closes>\d{1,2}(?::\d{2})?\s*[AP]M)$",
    re.IGNORECASE,
)
# A Google directions link states two positions: the centre the route is drawn
# around, after @, and the destination's own pin, as longitude then latitude in
# the 1d/2d pair. They are kilometres apart here, so the pin is what is read.
# url_to_coords reads the centre, which is why it is not used.
PIN = re.compile(r"!1d(-?\d+\.\d+)!2d(-?\d+\.\d+)")
# A restaurant's page is one segment below the site root.
TOP_LEVEL = re.compile(r"^/[^/]+/?$")


class AcmeOysterHouseUSSpider(Spider):
    name = "acme_oyster_house_us"
    item_attributes = {"brand": "Acme Oyster House"}
    allowed_domains = ["acmeoyster.com"]
    start_urls = [LOCATOR]
    # The host sometimes answers a datacenter address with a SiteGround captcha
    # instead of the page, while serving the pages and a robots.txt that allows
    # them to an ordinary address.
    requires_proxy = True

    def parse(self, response: Response, **kwargs: Any) -> Iterable[Any]:
        """Follow the restaurants the menu names, not the sitemap.

        The sitemap lists each restaurant twice, once under a slug of its own and
        once under one suffixed with its state, and both carry the same address
        and each declares itself canonical, so crawling the sitemap yields ten
        restaurants where there are five. The menu names each of them once.
        """
        found = 0
        for link in response.css("a.elementor-sub-item"):
            if not (url := link.xpath("@href").get()):
                continue
            # The menu holds a second submenu, for the chain's loyalty pages,
            # whose entries sit below a section of their own. A restaurant's page
            # is always at the top level, which is what tells them apart.
            if not TOP_LEVEL.match(urlparse(response.urljoin(url)).path):
                continue
            found += 1
            yield response.follow(
                url,
                callback=self.parse_location,
                cb_kwargs={"branch": re.sub(r"\s+", " ", " ".join(link.xpath(".//text()").getall())).strip()},
            )
        if not found:
            self.logger.error("The menu named no restaurants, so the locator has changed")

    def parse_location(self, response: Response, branch: str) -> Iterable[Feature]:
        """Read the block the directions link sits in.

        The page's structured data describes neither the restaurant nor the chain:
        every page carries the same record, named for the agency that built the
        site, with no address and nine-to-five hours. The block holding the
        directions link is what states the restaurant.
        """
        if not (directions := response.xpath('//a[contains(@href, "google.com/maps/dir")]')):
            self.logger.warning(f"{response.url} shows no directions link, so it is not published")
            return

        link = directions[0]
        lines = [text for raw in link.xpath(".//text()").getall() if (text := re.sub(r"\s+", " ", raw).strip())]
        if len(lines) < 2 or not (locality := LOCALITY.match(lines[-1])):
            self.logger.warning(f"{response.url} states an address this cannot read: {lines!r}")
            return

        item = Feature()
        item["ref"] = response.url.rstrip("/").rsplit("/", 1)[-1]
        item["website"] = response.url
        item["branch"] = branch or None
        # Published as the site writes them, in capitals: lower-casing them would
        # have to guess at "216 E. 24TH AVE" and at the state.
        item["street_address"] = " ".join(lines[:-1]).strip().rstrip(",")
        item["city"] = locality["city"]
        item["state"] = locality["state"]
        item["postcode"] = locality["postcode"]
        item["country"] = "US"

        if pin := PIN.search(link.xpath("@href").get("")):
            item["lon"], item["lat"] = pin.groups()
        else:
            self.logger.warning(f"{response.url} names no position in its directions link")

        block = link.xpath('ancestor::div[contains(@class, "elementor-widget-container")][1]')
        item["phone"] = (block or response).xpath('.//a[starts-with(@href, "tel:")]/@href').get("").removeprefix("tel:")
        item["opening_hours"] = self.hours(block or response, response.url)

        # No Facebook: the link beside the hours is the chain's own page, the same
        # on all five.
        item["extras"]["cuisine"] = "seafood"
        apply_category(Categories.RESTAURANT, item)

        yield item

    def hours(self, block: Any, url: str) -> OpeningHours:
        oh = OpeningHours()
        for raw in block.xpath(".//p//text() | .//p/text()").getall():
            line = re.sub(r"\s+", " ", raw).strip()
            if not (stated := HOURS.match(line)):
                continue
            named = [day for word in re.split(r"[-–]", stated["days"]) if (day := sanitise_day(word))]
            if not named:
                self.logger.warning(f"{url} states days this cannot read: {line!r}")
                continue
            for day in day_range(named[0], named[-1]) if len(named) > 1 else named:
                oh.add_range(day, self.time(stated["opens"]), self.time(stated["closes"]), "%I:%M%p")
        return oh

    @staticmethod
    def time(stated: str) -> str:
        """Return "11AM" with the minutes the strptime format expects."""
        stated = re.sub(r"\s+", "", stated).upper()
        return stated if ":" in stated else f"{stated[:-2]}:00{stated[-2:]}"
