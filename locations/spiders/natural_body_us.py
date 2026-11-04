from typing import Any, Iterable

from scrapy.http import Response
from scrapy.spiders import SitemapSpider

from locations.categories import Categories, apply_category
from locations.items import Feature
from locations.linked_data_parser import LinkedDataParser

LOCATOR = "https://www.naturalbody.com"
# A spa that is not trading states the same moment as its opening and its
# closing, every day of the week.
SHUT = "00:00"


class NaturalBodyUSSpider(SitemapSpider):
    name = "natural_body_us"
    item_attributes = {"brand": "Natural Body"}
    allowed_domains = ["www.naturalbody.com"]
    # The locator keeps its own sitemap, listing a page per spa and its own index.
    sitemap_urls = [f"{LOCATOR}/wpseo_locations-sitemap.xml"]
    sitemap_rules = [(r"/spa-locations/[^/]+$", "parse_location")]

    def parse_location(self, response: Response, **kwargs: Any) -> Iterable[Feature]:
        """Build the spa from the DaySpa the page states.

        The address is published as a node of its own and the spa refers to it by
        id rather than carrying it, so the reference is resolved before the block
        is read; left alone, the spa parses with no address at all.
        """
        nodes = [node for node in LinkedDataParser.iter_linked_data(response) if isinstance(node, dict)]
        if not (spa := next((node for node in nodes if "DaySpa" in str(node.get("@type"))), None)):
            self.logger.warning(f"{response.url} states no spa, so it is not published")
            return

        if isinstance(address := spa.get("address"), dict) and set(address) == {"@id"}:
            by_id = {node["@id"]: node for node in nodes if node.get("@id")}
            spa = dict(spa, address=by_id.get(address["@id"], {}))

        if self.shut(spa):
            self.logger.info(f"{spa.get('name')} states no trading hours, so it is not published")
            return

        item = LinkedDataParser.parse_ld(spa)
        item["ref"] = response.url.rstrip("/").rsplit("/", 1)[-1]
        # The spa's own url redirects to the page the sitemap lists, so the page's
        # own address is the one published.
        item["website"] = response.url
        # Each spa is named for the chain and, after a bar, the place it stands in.
        item["branch"] = (item.pop("name", None) or "").rsplit("|", 1)[-1].strip() or None

        apply_category(Categories.SHOP_BEAUTY_SPA, item)

        yield item

    @staticmethod
    def shut(spa: dict) -> bool:
        """Say whether every day the spa states opens and closes at one moment.

        Two of the seven the locator lists are not trading: one is marked a former
        location and the other is shut for a rebuilding that reopens under another
        brand. Both state 00:00 to 00:00 for all seven days, which is the machine
        readable part of saying so, where the wording differs between them.
        """
        rules = spa.get("openingHoursSpecification") or []
        return bool(rules) and all(rule.get("opens") == rule.get("closes") == SHUT for rule in rules)
