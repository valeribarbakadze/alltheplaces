from typing import Iterable

from scrapy.http import TextResponse
from scrapy.spiders import SitemapSpider

from locations.categories import Categories, apply_category
from locations.items import Feature
from locations.structured_data_spider import StructuredDataSpider


class TomAndCheeUSSpider(SitemapSpider, StructuredDataSpider):
    name = "tom_and_chee_us"
    # As the restaurants' own structured data names the brand, and its parent
    # organisation with it.
    item_attributes = {"brand": "Tom & Chee"}
    allowed_domains = ["locations.tomandchee.com"]
    # The locator the site itself uses, run by SOCi. The site's own menu links
    # to /ky, /oh and /ok, all three of which answer 404, and tomandchee.com
    # publishes no sitemap.
    sitemap_urls = ["https://locations.tomandchee.com/sitemap.xml"]
    # A restaurant's page is one segment ending in twelve hex characters. The
    # state and town directories above them - /oh, /oh/mason - are not, and the
    # captured slug is what the item is referenced by.
    sitemap_rules = [(r"/([^/]+-[0-9a-f]{12})$", "parse_sd")]
    wanted_types = ["Restaurant"]
    # Every page states the parent company's address, contact@goldstarchili.com,
    # and the chain's own accounts rather than a restaurant's, so none of those
    # are collected. The image in the structured data is each restaurant's own
    # and is kept.
    search_for_email = False
    search_for_twitter = False
    search_for_facebook = False
    search_for_instagram = False

    def post_process_item(self, item: Feature, response: TextResponse, ld_data: dict, **kwargs) -> Iterable[Feature]:
        # The structured data gives its @id, which is the page's whole address,
        # where the slug alone identifies the restaurant. One of the five
        # carries an "e121" in front of its state, which is the locator's own
        # doing and is kept, the slug being what the locator calls it.
        item["ref"] = response.url.rstrip("/").rsplit("/", 1)[-1]

        # Four restaurants are named for the town they stand in, which the
        # address states as the town, so those carry no branch. The fifth is
        # named "Gold Star + Tom & Chee": it trades alongside Gold Star Chili,
        # the parent company's own chain, and that is worth keeping.
        if named := item.pop("name", None):
            item["branch"] = named if named.casefold() != (item.get("city") or "").casefold() else None

        hours = item.get("opening_hours")
        if not (hours and hours.as_opening_hours()):
            # The restaurant inside Kings Island states every day of the week
            # closed, the amusement park being shut for the winter. It is a
            # restaurant that exists, so it is collected, but with no hours
            # rather than seven closed days, which would read as permanent.
            self.logger.warning(f"{item['ref']} states no hours it is open, so it may be shut for the season")
            item["opening_hours"] = None

        item["extras"]["cuisine"] = "sandwich"
        apply_category(Categories.RESTAURANT, item)

        yield item
