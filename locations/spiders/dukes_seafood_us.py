import re
from typing import Any, Iterable

from scrapy.http import Response
from scrapy.spiders import SitemapSpider

from locations.categories import Categories, apply_category
from locations.items import Feature
from locations.linked_data_parser import LinkedDataParser

# Every restaurant is named for the chain and the place it stands in: "Duke's
# Seafood Green Lake". Two append what the restaurant looks out over.
BRAND = "Duke's Seafood"
TRAILING = re.compile(r"\s+(?:Waterfront)$")


class DukesSeafoodUSSpider(SitemapSpider):
    name = "dukes_seafood_us"
    item_attributes = {"brand": BRAND}
    allowed_domains = ["dukesseafood.com", "www.dukesseafood.com"]
    sitemap_urls = ["https://dukesseafood.com/sitemap_index.xml"]
    # The locator's own page is /locations/ and each restaurant one segment below
    # it, which the rule requires.
    sitemap_rules = [(r"/locations/[^/]+/$", "parse_location")]
    # The host sometimes answers a datacenter address with a SiteGround captcha
    # instead of the page, naming the address's reputation as the reason. It is
    # intermittent rather than a block: it refused a run of attempts and then
    # served twelve requests in a row, and it serves both the pages and a
    # robots.txt allowing them to an ordinary address. A proxy makes a monthly run
    # dependable; without one the spider still works, but some runs will collect
    # nothing.
    requires_proxy = True

    def parse_location(self, response: Response, **kwargs: Any) -> Iterable[Feature]:
        """Build the restaurant from the one coherent block on the page.

        Each page states itself several times over in schema.org and the copies
        disagree. Alongside the one that describes the restaurant there is a
        chain-wide Organization, a Place repeating the chain's own address under a
        misspelt region, and one or two copies that put the neighbourhood in
        addressLocality and the town in addressRegion - so "Green Lake, Seattle"
        where the postal address is "Seattle, WA". Their positions differ too, by
        several hundred metres.

        The block to read is the one that says it is this page and carries both a
        position and opening hours. That holds on all six pages and picks exactly
        one of them, which is also the only one whose region is the state.
        """
        if not (ld := self.restaurant(response)):
            self.logger.warning(f"{response.url} states no restaurant that describes this page")
            return

        item = LinkedDataParser.parse_ld(ld)
        item["ref"] = response.url.rstrip("/").rsplit("/", 1)[-1]
        item["website"] = response.url
        item["branch"] = TRAILING.sub("", (item.pop("name", None) or "").removeprefix(BRAND).strip())

        # The field is published empty on every page.
        item.pop("image", None)

        item["extras"]["cuisine"] = "seafood"
        apply_category(Categories.RESTAURANT, item)

        yield item

    @staticmethod
    def restaurant(response: Response) -> dict | None:
        page = response.url.replace("//www.", "//").rstrip("/")
        for ld in LinkedDataParser.iter_linked_data(response):
            if ld.get("@type") != "Restaurant":
                continue
            if (ld.get("url") or "").replace("//www.", "//").rstrip("/") != page:
                continue
            if ld.get("geo") and ld.get("openingHoursSpecification"):
                return ld
        return None
