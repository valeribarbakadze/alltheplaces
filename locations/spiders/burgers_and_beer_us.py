import re
from typing import Any, Iterable

from scrapy.http import Response
from scrapy.spiders import SitemapSpider

from locations.categories import Categories, apply_category
from locations.hours import OpeningHours, day_range, sanitise_day
from locations.items import Feature

# The address is written as one line, and a restaurant's names its town, state
# and postcode where the corporate office's names none of them.
ADDRESS = re.compile(r"^(?P<street>.+?),\s*(?P<city>[A-Za-z .'-]+),\s*(?P<state>[A-Z]{2})\s+(?P<postcode>\d{5})$")
# A Google place link's own pin, which is the restaurant, against the @ that
# follows it, which is where the map is centred.
PIN = re.compile(r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)")
HOURS = "Opening Hours"
TIMES = re.compile(
    r"^(?P<opens>\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?)\s*[-–]\s*(?P<closes>\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?)$",
    re.IGNORECASE,
)
SHUT = re.compile(r"^closed$", re.IGNORECASE)
SPLIT = re.compile(r"\s*(?:[-–&]|and)\s*", re.IGNORECASE)


class BurgersAndBeerUSSpider(SitemapSpider):
    name = "burgers_and_beer_us"
    item_attributes = {"brand": "Burgers & Beer"}
    allowed_domains = ["www.burgersandbeer.com"]
    # The restaurants are listed on one page of the site, which is named
    # contact-5 today. The site builder names its pages, and renames them, so the
    # page is found by what it holds rather than by that name: every page in the
    # sitemap is read and the blocks are recognised by their contents. Only the
    # one page carries any.
    sitemap_urls = ["https://www.burgersandbeer.com/pages-sitemap.xml"]
    sitemap_rules = [("", "parse_page")]

    def parse_page(self, response: Response, **kwargs: Any) -> Iterable[Feature]:
        """Yield a restaurant for each block that states a full address.

        The page carries a block for each restaurant and one more for the
        corporate office, which looks the same but for its address: it states a
        street alone, where a restaurant states its town, state and postcode. The
        office also repeats one restaurant's position as its own, so taking the
        blocks as they come would put two places at one point.
        """
        for section in response.xpath("//section"):
            link = section.xpath('.//a[contains(@href, "google.com/maps")]')
            if len(link) != 1:
                continue
            if not (stated := ADDRESS.match(self.text(link))):
                continue

            item = Feature()
            item["street_address"] = stated["street"]
            item["city"] = stated["city"]
            item["state"] = stated["state"]
            item["postcode"] = stated["postcode"]
            item["country"] = "US"
            item["ref"] = re.sub(r"[^a-z0-9]+", "-", stated["city"].lower()).strip("-")
            # No website: the restaurants have no pages of their own. The only
            # link the site gives each of them is to order from a delivery
            # platform, and the page they are all listed on is one page, so
            # recording it would state the same address against all five.
            # Each block is headed with the town and the state, which the address
            # states as well.
            item["branch"] = self.text(section.xpath(".//h2[1]")).split(",")[0].strip() or None
            item["phone"] = section.xpath('.//a[starts-with(@href, "tel:")]/@href').get("").removeprefix("tel:") or None

            if pin := PIN.search(link.xpath("@href").get("")):
                item["lat"], item["lon"] = pin.groups()
            else:
                self.logger.warning(f"{item['branch']} names no position in its map link")

            item["opening_hours"] = self.hours(section, item["branch"])

            item["extras"]["cuisine"] = "burger"
            apply_category(Categories.RESTAURANT, item)

            yield item

    @staticmethod
    def text(selector: Any) -> str:
        return re.sub(r"\s+", " ", " ".join(selector.xpath(".//text()").getall())).strip()

    def hours(self, section: Any, branch: str | None) -> OpeningHours:
        """Read the days and times that follow the block's "Opening Hours".

        The days and the times they apply to are written as separate elements,
        one after the other, so the run of text is walked rather than matched
        line by line.
        """
        oh = OpeningHours()
        nodes = [text for raw in section.xpath(".//text()").getall() if (text := re.sub(r"\s+", " ", raw).strip())]
        start = next((i for i, node in enumerate(nodes) if HOURS in node), None)
        if start is None:
            self.logger.warning(f"{branch} states no hours")
            return oh

        days: list[str] = []
        for node in nodes[start + 1 :]:
            if named := [day for word in SPLIT.split(node) if (day := sanitise_day(word))]:
                days = day_range(named[0], named[-1]) if len(named) > 1 and "&" not in node else named
            elif not days:
                continue
            elif SHUT.match(node):
                for day in days:
                    oh.set_closed(day)
                days = []
            elif times := TIMES.match(node):
                for day in days:
                    oh.add_range(day, self.time(times["opens"]), self.time(times["closes"]), "%I:%M%p")
                days = []
        return oh

    @staticmethod
    def time(stated: str) -> str:
        stated = re.sub(r"[\s.]", "", stated).upper()
        return stated if ":" in stated else f"{stated[:-2]}:00{stated[-2:]}"
