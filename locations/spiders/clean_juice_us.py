from typing import Any, Iterable

from scrapy.http import Response
from scrapy.spiders import SitemapSpider

from locations.categories import Categories, apply_category
from locations.items import Feature
from locations.structured_data_spider import StructuredDataSpider


class CleanJuiceUSSpider(SitemapSpider, StructuredDataSpider):
    """
    Clean Juice publishes an official SOCi-hosted location directory at
    locations.cleanjuice.com. Each detail page carries a schema.org Restaurant
    JSON-LD block. The `openingHoursSpecification` values in that block are
    template placeholders left empty by the vendor, so opening hours are read
    from the rendered hours table instead.
    """

    name = "clean_juice_us"
    item_attributes = {"brand": "Clean Juice", "brand_wikidata": "Q60775550"}
    allowed_domains = ["locations.cleanjuice.com"]
    sitemap_urls = ["https://locations.cleanjuice.com/sitemap.xml"]
    sitemap_rules = [(r"/ll/us/\w\w/[^/]+/[^/]+/$", "parse_sd")]
    wanted_types = ["Restaurant"]
    drop_attributes = {"image", "facebook", "twitter"}

    def post_process_item(self, item: Feature, response: Response, ld_data: dict, **kwargs: Any) -> Iterable[Feature]:
        if item.get("country") != "US":
            return

        item["ref"] = ld_data.get("@id")
        item["website"] = response.url
        item["branch"] = (item.pop("name", "") or "").removeprefix("Clean Juice").strip()

        if not item["opening_hours"] or not item["opening_hours"].as_opening_hours():
            item["opening_hours"] = None

        if mall := ld_data.get("containedIn"):
            # The vendor template leaves an unedited placeholder string behind.
            if "Column Header" not in mall:
                item["located_in"] = mall

        apply_category(Categories.FAST_FOOD, item)
        item["extras"]["cuisine"] = "juice"

        yield item
