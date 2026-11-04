import re
from collections import defaultdict
from typing import Any, Iterable

from scrapy.http import Response
from scrapy.spiders import SitemapSpider

from locations.categories import Categories, apply_category
from locations.items import Feature
from locations.structured_data_spider import StructuredDataSpider

# Each restaurant is named for the chain and, in brackets, the neighbourhood or
# plaza it stands in: "Felipe's Mexican Taqueria (Mid City)". The two in Florida
# append the town after the brackets, which the address states already.
BRANCH = re.compile(r"\(([^)]+)\)")


class FelipesMexicanTaqueriaUSSpider(SitemapSpider, StructuredDataSpider):
    name = "felipes_mexican_taqueria_us"
    item_attributes = {"brand": "Felipe's Mexican Taqueria"}
    allowed_domains = ["felipestaqueria.com"]
    sitemap_urls = ["https://felipestaqueria.com/sitemap_index.xml"]
    # A restaurant is two segments below /locations/. The same sitemap carries the
    # locator, a page per state and an sms-contest page under each restaurant,
    # which the anchored rule leaves out.
    sitemap_rules = [(r"/locations/[^/]+/[^/]+/$", "parse_sd")]
    wanted_types = ["Restaurant"]
    # The page carries the chain's own account rather than each restaurant's, the
    # same value on all six.
    search_for_facebook = False

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # Branches by the position they publish, to find any position published
        # for more than one of them.
        self.positions: dict[tuple, list[str]] = defaultdict(list)

    def post_process_item(self, item: Feature, response: Response, ld_data: dict, **kwargs: Any) -> Iterable[Feature]:
        name = item.pop("name", None) or ""
        item["branch"] = match.group(1).strip() if (match := BRANCH.search(name)) else None
        item["ref"] = response.url.rstrip("/").rsplit("/", 1)[-1]

        # The photographs are the chain's delivery-platform gallery rather than
        # pictures of any one restaurant.
        item.pop("image", None)

        # servesCuisine mixes the two kitchens with "Group Friendly" and
        # "Exclusive to Eats", which describe the delivery listing rather than the
        # food, so only the kitchens are kept.
        item["extras"]["cuisine"] = "mexican;tex-mex"
        apply_category(Categories.RESTAURANT, item)

        if item.get("lat") and item.get("lon"):
            self.positions[(item["lat"], item["lon"])].append(item["branch"] or item["ref"])

        yield item

    def closed(self, reason: str) -> None:
        """Report any position the locator publishes for more than one restaurant.

        Two restaurants standing at one point is a contradiction in what the
        locator states, and it cannot be resolved from the page: the position is
        right for at most one of them and there is nothing to say which. Both are
        published as stated rather than dropped, since dropping both would discard
        a position that is correct, and this records the contradiction so it is not
        silent.
        """
        for position, branches in self.positions.items():
            if len(branches) > 1:
                self.logger.warning(
                    "{} are all published at {}, so the position is wrong for all but one of them".format(
                        ", ".join(sorted(branches)), position
                    )
                )
