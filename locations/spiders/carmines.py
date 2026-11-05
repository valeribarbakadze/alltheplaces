import re
from typing import Any, Iterable

from scrapy.http import Response
from scrapy.spiders import SitemapSpider

from locations.categories import Categories, apply_category
from locations.hours import DAYS, OpeningHours, sanitise_day
from locations.items import Feature

# The last line of the address names the town and then either a state and a
# postcode, which is how the five in the United States write it, or a country,
# which is how the one in the Bahamas does.
US = re.compile(r"^(?P<city>[A-Za-z .'-]+),\s*(?P<state>[A-Z]{2})\s+(?P<postcode>\d{5})$")
ABROAD = re.compile(r"^(?P<city>[A-Za-z .'-]+),\s*(?P<country>[A-Za-z .'-]+)$")
# Each address links to a Google route to itself. The pin the route ends at is
# the restaurant, written longitude first; the @ that precedes it is where the
# map is centred, which is somewhere else.
PIN = re.compile(r"!1d(-?\d+\.\d+)!2d(-?\d+\.\d+)")
# "Carmine's Times Square", which is the brand and then the name of the place.
BRAND = re.compile(r"^Carmine['’]s\s*", re.IGNORECASE)
TIMES = re.compile(
    r"(?P<opens>\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?)\s*(?:[-–—]|to)\s*(?P<closes>\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?)",
    re.IGNORECASE,
)
# A restaurant that states one range for the whole week says so in words rather
# than listing the days.
EVERY_DAY = re.compile(r"seven days a week|every day|daily", re.IGNORECASE)


class CarminesSpider(SitemapSpider):
    name = "carmines"
    item_attributes = {"brand": "Carmine's"}
    # Without the www, so that both spellings are allowed: robots.txt redirects
    # one to the other and the site links to itself both ways.
    allowed_domains = ["carminesnyc.com"]
    sitemap_urls = ["https://www.carminesnyc.com/sitemap.xml"]
    # The party and catering pages repeat the restaurants' slugs under their own
    # paths, so the rule names the locations path rather than the slug.
    sitemap_rules = [(r"/locations/[^/]+/?$", "parse_location")]
    # Cloudflare answers a datacenter address with a challenge instead of the
    # page, over a robots.txt that allows every crawler but three named SEO
    # ones. Only the address's reputation is being refused, so a run from
    # elsewhere collects normally.
    requires_proxy = True

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.seen = 0

    def parse_location(self, response: Response, **kwargs: Any) -> Iterable[Feature]:
        """Read the block the page heads "Contact" and "Address".

        The page also carries a Restaurant block in structured data, which is
        not used: it contradicts the page. It states Monday 11:00 to 23:30 for
        Times Square where the page states 11:30 to 23:00, it gives a position
        some 200 metres from the one the address links to, and it has been left
        behind - its map is a goo.gl short link and it names the restaurant's
        Google+ page. The block is also missing from one of the six pages. What
        the page itself states is current, per day, and there on all six.
        """
        link = response.xpath('//h3[normalize-space()="Address"]/following-sibling::a[1]')
        lines = [text for raw in link.xpath(".//text()").getall() if (text := re.sub(r"\s+", " ", raw).strip())]

        # The address is headed with the brand and the name of the place, which
        # is a neighbourhood, a city or a resort rather than the town below it.
        # The head is read as a name only where it states one, so that a page
        # which opens straight into its street does not lose that street.
        branch = BRAND.sub("", lines[0]).strip() if lines and BRAND.match(lines[0]) else None
        street = lines[1:-1] if branch is not None else lines[:-1]
        if not street:
            self.logger.warning(f"{response.url} states an address this cannot read: {lines!r}")
            return

        item = Feature()
        item["ref"] = response.url.rstrip("/").rsplit("/", 1)[-1]
        item["website"] = response.url
        item["branch"] = branch or None
        item["street_address"] = ", ".join(street)

        if stated := US.match(lines[-1]):
            item["city"] = stated["city"]
            item["state"] = stated["state"]
            item["postcode"] = stated["postcode"]
            item["country"] = "US"
        elif stated := ABROAD.match(lines[-1]):
            item["city"] = stated["city"]
            # The country is named rather than coded, which the country code
            # pipeline turns into its two letter code.
            item["country"] = stated["country"]
        else:
            self.logger.warning(f"{response.url} ends its address with something unread: {lines[-1]!r}")
            return

        # The number the page heads "Telephone". A second paragraph may follow
        # with an extension for take out, which is the same line rather than
        # another number, so only the first paragraph is read.
        item["phone"] = (
            response.xpath(
                '//h3[normalize-space()="Contact"]/following-sibling::p[1]//a[starts-with(@href, "tel:")]/@href'
            )
            .get("")
            .removeprefix("tel:")
            or None
        )

        if pin := PIN.search(link.xpath("@href").get("") or ""):
            item["lon"], item["lat"] = pin.groups()
        else:
            self.logger.warning(f"{item['branch']} names no position in the route its address links to")

        item["opening_hours"] = self.hours(response)

        item["extras"]["cuisine"] = "italian"
        apply_category(Categories.RESTAURANT, item)

        self.seen += 1
        yield item

    def hours(self, response: Response) -> OpeningHours:
        """Read the hours, which are listed by day or else stated for the week.

        Most pages give a row per day. One states a single range for the whole
        week in words instead, so that is read when there are no rows - and only
        when the words name a range, since the same element elsewhere holds what
        a restaurant is open for rather than when.
        """
        oh = OpeningHours()
        for row in response.xpath('//div[contains(@class, "row")][div[@class="day"]]'):
            label = self.text(row.xpath('./div[@class="day"]'))
            value = self.text(row.xpath('./div[@class="hours"]'))
            if not (day := sanitise_day(label)):
                self.logger.warning(f"{response.url} names a day this cannot read: {label!r}")
                continue
            if not (times := TIMES.search(value)):
                self.logger.warning(f"{response.url} states hours this cannot read for {label}: {value!r}")
                continue
            oh.add_range(day, self.time(times["opens"]), self.time(times["closes"]), "%I:%M %p")

        if not oh.as_opening_hours():
            stated = self.text(response.xpath('//div[contains(@class, "location-hours-text")]'))
            if EVERY_DAY.search(stated) and (times := TIMES.search(stated)):
                for day in DAYS:
                    oh.add_range(day, self.time(times["opens"]), self.time(times["closes"]), "%I:%M %p")
            else:
                self.logger.warning(f"{response.url} states no hours this could read: {stated!r}")
        elif len(set(oh.day_hours) | oh.days_closed) < len(DAYS):
            self.logger.info(f"{response.url} states nothing for some days of the week")
        return oh

    @staticmethod
    def text(selector: Any) -> str:
        return re.sub(r"\s+", " ", " ".join(selector.xpath(".//text()").getall())).strip()

    @staticmethod
    def time(stated: str) -> str:
        """Return "5:30 pm", "11:30 A.M." or "5 PM" in the one shape strptime is given."""
        packed = re.sub(r"[\s.]", "", stated).upper()
        clock, meridiem = packed[:-2], packed[-2:]
        return f"{clock if ':' in clock else clock + ':00'} {meridiem}"

    def closed(self, reason: str) -> None:
        # The restaurants have pages of their own, so a page that stops being
        # listed stops being collected without anything else going wrong.
        if reason == "finished" and self.seen < 6:
            self.logger.warning(f"The sitemap listed {self.seen} restaurants, where it has listed six")
