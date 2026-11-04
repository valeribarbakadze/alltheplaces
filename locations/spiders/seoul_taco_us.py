from typing import Any, Iterable

from scrapy.http import Response
from scrapy.spiders import SitemapSpider

from locations.categories import Categories, apply_category
from locations.items import Feature
from locations.structured_data_spider import StructuredDataSpider

BRAND = "Seoul Taco"


class SeoulTacoUSSpider(SitemapSpider, StructuredDataSpider):
    name = "seoul_taco_us"
    item_attributes = {"brand": BRAND}
    sitemap_urls = ["https://seoultaco.com/sitemap.xml"]
    sitemap_rules = [(r"/location-[\w-]+$", "parse_sd")]
    wanted_types = ["Restaurant"]
    # Both carry the chain's own accounts rather than each restaurant's, the same
    # value on all six pages.
    search_for_twitter = False
    search_for_facebook = False

    def post_process_item(self, item: Feature, response: Response, ld_data: dict, **kwargs: Any) -> Iterable[Feature]:
        # The structured data addresses each restaurant as /locations/<slug>, which
        # answers 404. The page it is published on is /location-<slug>.
        item["website"] = response.url
        item["ref"] = response.url.rsplit("/", 1)[-1].removeprefix("location-")

        # Each is named for the chain and its neighbourhood together, so the
        # neighbourhood alone is the branch.
        item["branch"] = (item.pop("name", None) or "").removeprefix(BRAND).strip()

        # servesCuisine states the fusion and "Street Food" alongside the two
        # kitchens, which are the part that maps onto a cuisine tag.
        item["extras"]["cuisine"] = "korean;mexican"
        apply_category(Categories.FAST_FOOD, item)

        # The hours each page states in its structured data are the ones read. The
        # table rendered on the page disagrees with them and cannot be trusted: one
        # restaurant's table marks every day closed while its structured data gives
        # a full week, and another's has a Friday running from 11am to 12:59pm.
        #
        # A page that states fewer days than it trades is the site's own omission,
        # which this records rather than fills in, and says so, because an
        # incomplete week is otherwise indistinguishable from a quiet one.
        if (stated := self.days_stated(ld_data)) < 7:
            self.logger.warning(
                f"{item['branch']} publishes hours for {stated} of 7 days, so its hours may be incomplete"
            )

        yield item

    @staticmethod
    def days_stated(ld_data: dict) -> int:
        days = set()
        for rule in ld_data.get("openingHoursSpecification") or []:
            day = rule.get("dayOfWeek")
            days.update(day if isinstance(day, list) else [day])
        return len(days)
