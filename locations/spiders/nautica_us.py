from typing import Any, Iterable

from scrapy.http import Response
from scrapy.spiders import SitemapSpider

from locations.categories import Categories, apply_category
from locations.items import Feature
from locations.structured_data_spider import StructuredDataSpider


class NauticaUSSpider(SitemapSpider, StructuredDataSpider):
    """
    Nautica's official store locator is a Yext-hosted site at
    stores.nautica.com. Detail pages expose schema.org ClothingStore data as
    microdata rather than JSON-LD; StructuredDataSpider handles both.
    """

    name = "nautica_us"
    item_attributes = {"brand": "Nautica", "brand_wikidata": "Q6981479"}
    allowed_domains = ["stores.nautica.com"]
    sitemap_urls = ["https://stores.nautica.com/sitemap.xml"]
    # State pages are /xx, city pages are /xx/city, store pages are /xx/city/address.
    sitemap_rules = [(r"https://stores\.nautica\.com/\w\w/[^/]+/[^/]+$", "parse_sd")]
    wanted_types = ["ClothingStore"]
    drop_attributes = {"image"}

    def post_process_item(self, item: Feature, response: Response, ld_data: dict, **kwargs: Any) -> Iterable[Feature]:
        if item.get("country") != "US":
            return

        # The microdata itemid is a page anchor such as
        # "https://stores.nautica.com/#52238113"; only the Yext entity ID is
        # a stable reference.
        item["ref"] = (ld_data.get("@id") or "").rpartition("#")[2] or response.url
        item["website"] = response.url
        item.pop("name", None)

        # Titles render as "Nautica <branch>, <city>, <state>".
        title = response.xpath('normalize-space(//h1[contains(@class, "Hero-title")])').get("")
        branch = title.removeprefix("Nautica").strip()
        city, state = item.get("city"), item.get("state")
        if city and state:
            branch = branch.removesuffix("{}, {}".format(city, state)).strip().strip(",")
        item["branch"] = branch or None

        apply_category(Categories.SHOP_CLOTHES, item)

        yield item
