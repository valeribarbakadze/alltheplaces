import re
from typing import Any, Iterable

from scrapy.http import Response
from scrapy.spiders import SitemapSpider

from locations.categories import Categories, apply_category
from locations.hours import OpeningHours, day_range, sanitise_day
from locations.items import Feature
from locations.linked_data_parser import LinkedDataParser

# One of the five trades under a name of its own, which the slug of its page is
# what states: the page's title template calls every location Mitchell's, while
# its text names only Columbus Fish Market.
# No brand_wikidata for the Columbus name: no Wikidata item for it could be
# verified, where the chain's own has one.
BRANDS = {
    "mitchells-fish-market": {"brand": "Mitchell's Fish Market", "brand_wikidata": "Q17022276"},
    "columbus-fish-market": {"brand": "Columbus Fish Market"},
}
# "SUN: 11:30 AM - 9:30 PM", "MON - THU: 11:00 AM - 9:30 PM".
HOURS = re.compile(
    r"^(?P<days>[A-Za-z]{3}(?:\s*-\s*[A-Za-z]{3})?)\s*:\s*"
    r"(?P<opens>\d{1,2}:\d{2}\s*[AP]M)\s*-\s*(?P<closes>\d{1,2}:\d{2}\s*[AP]M)$",
    re.IGNORECASE,
)
# The trading hours are followed by the bar's promotions and by dated holiday
# hours, both of which would otherwise be read as hours the restaurant keeps.
NOT_TRADING = re.compile(r"Happy Hour|Late Night|Holiday Hours", re.IGNORECASE)


class MitchellsFishMarketUSSpider(SitemapSpider):
    name = "mitchells_fish_market_us"
    allowed_domains = ["www.mitchellsfishmarket.com"]
    sitemap_urls = ["https://www.mitchellsfishmarket.com/sitemap.xml"]
    sitemap_rules = [(r"/location/", "parse_location")]

    def parse_location(self, response: Response, **kwargs: Any) -> Iterable[Feature]:
        if not (ld := next((n for n in LinkedDataParser.iter_linked_data(response) if self.wanted(n)), None)):
            self.logger.warning(f"{response.url} states no restaurant, so it is not published")
            return

        item = LinkedDataParser.parse_ld(ld)
        item["ref"] = slug = response.url.rstrip("/").rsplit("/", 1)[-1]
        item["website"] = response.url
        item["country"] = "US"

        # Each is named for the town it stands in and the state, which the address
        # states as well.
        item["branch"] = (item.pop("name", None) or "").split(",")[0].strip() or None

        if brand := next((attributes for prefix, attributes in BRANDS.items() if slug.startswith(prefix)), None):
            item.update(brand)
        else:
            self.logger.warning(f"{slug} is not a slug of a known brand, so this restaurant has none")

        # The picture and photo fields are published empty on every page.
        item.pop("image", None)

        # No position: the address links to a Google place by its CID, which
        # carries none, and nothing else on the page publishes one.
        item["opening_hours"] = self.hours(response)

        item["extras"]["cuisine"] = "seafood"
        apply_category(Categories.RESTAURANT, item)

        yield item

    @staticmethod
    def wanted(node: dict) -> bool:
        return isinstance(node, dict) and "FoodEstablishment" in str(node.get("@type"))

    def hours(self, response: Response) -> OpeningHours:
        oh = OpeningHours()
        for raw in response.css("section#intro p ::text").getall():
            line = re.sub(r"\s+", " ", raw).strip()
            if NOT_TRADING.search(line):
                break
            if not (stated := HOURS.match(line)):
                continue
            named = [day for word in stated["days"].split("-") if (day := sanitise_day(word))]
            if not named:
                self.logger.warning(f"{response.url} states days this cannot read: {line!r}")
                continue
            for day in day_range(named[0], named[-1]) if len(named) > 1 else named:
                oh.add_range(day, stated["opens"].replace(" ", ""), stated["closes"].replace(" ", ""), "%I:%M%p")
        return oh
