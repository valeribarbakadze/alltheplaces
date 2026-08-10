from typing import Any, Iterable

from scrapy.http import Response
from scrapy.spiders import SitemapSpider

from locations.categories import Categories, apply_category
from locations.items import Feature
from locations.structured_data_spider import StructuredDataSpider


class JackInTheBoxSpider(SitemapSpider, StructuredDataSpider):
    """
    Jack in the Box publishes an official location sitemap at
    locations.jackinthebox.com. Each detail page carries a schema.org
    Restaurant JSON-LD block; opening/closing times use a "10:00 A.M." style
    which needs the periods stripping before parsing.
    """

    name = "jack_in_the_box"
    item_attributes = {"brand": "Jack in the Box", "brand_wikidata": "Q1538507", "country": "US"}
    allowed_domains = ["locations.jackinthebox.com"]
    sitemap_urls = ["https://locations.jackinthebox.com/sitemap.xml"]
    # Detail page paths are /<country>/<state>/<city>/<street>; restricted to
    # the US so a future non-US market cannot leak into this spider.
    sitemap_rules = [(r"com/us/\w\w/[^/]+/[^/]+$", "parse_sd")]
    json_parser = "chompjs"
    time_format = "%I:%M %p"
    drop_attributes = {"image"}

    def pre_process_data(self, ld_data: dict, **kwargs: Any) -> None:
        for rule in ld_data.get("openingHoursSpecification", []):
            rule["opens"] = rule.get("opens", "").replace(".", "")
            rule["closes"] = rule.get("closes", "").replace(".", "")

    def post_process_item(self, item: Feature, response: Response, ld_data: dict, **kwargs: Any) -> Iterable[Feature]:
        item["website"] = response.url
        item["ref"] = response.url.rstrip("/").rsplit("/", 1)[-1]
        item["branch"] = (item.pop("name", "") or "").removeprefix("Jack in the Box").strip(" -")

        apply_category(Categories.FAST_FOOD, item)
        item["extras"]["cuisine"] = "burger"

        yield item
