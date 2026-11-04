from typing import Any, Iterable

from scrapy.http import Response
from scrapy.spiders import SitemapSpider

from locations.categories import Categories, apply_category
from locations.items import Feature
from locations.structured_data_spider import StructuredDataSpider

# The chain's own site hands its locator to a subdomain, which publishes a page
# per restaurant at /<state>/<city>/<street>/ and lists them in its sitemap.
LOCATOR = "https://restaurants.thesimplegreek.com"


class TheSimpleGreekUSSpider(SitemapSpider, StructuredDataSpider):
    name = "the_simple_greek_us"
    item_attributes = {"brand": "The Simple Greek"}
    allowed_domains = ["restaurants.thesimplegreek.com"]
    sitemap_urls = [f"{LOCATOR}/sitemap_index.xml"]
    # The sitemap also carries the locator's own front page, its search page and a
    # page per state and per city, which the three path segments distinguish.
    sitemap_rules = [(r"/[a-z]{2}/[^/]+/[^/]+/$", "parse_sd")]
    wanted_types = ["FastFoodRestaurant"]
    # Both carry the chain's own accounts rather than each restaurant's, the same
    # value on all six pages.
    search_for_twitter = False
    search_for_facebook = False

    def post_process_item(self, item: Feature, response: Response, ld_data: dict, **kwargs: Any) -> Iterable[Feature]:
        # Each restaurant is named for its town, which is its branch rather than a
        # name of its own.
        item["branch"] = item.pop("name", None)
        item["ref"] = response.url.replace(LOCATOR, "").strip("/")

        # The structured data states one photograph of the brand's food against
        # every restaurant, so it says nothing about any of them. search_for_image
        # would not prevent this: it only gates the search of the page for an image
        # when the structured data supplied none.
        item.pop("image", None)

        item["extras"]["cuisine"] = "greek"
        apply_category(Categories.FAST_FOOD, item)

        yield item
