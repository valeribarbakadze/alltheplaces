import re
from typing import Any, AsyncIterator, Iterable

from scrapy.http import Request, Response

from locations.categories import Categories, apply_category
from locations.country_utils import CountryUtils
from locations.items import Feature
from locations.structured_data_spider import StructuredDataSpider


class DogtopiaUSSpider(StructuredDataSpider):
    """
    Every Dogtopia franchise runs as its own WordPress multisite child at
    https://www.dogtopia.com/<slug>/, and each child registers its own
    `page-sitemap.xml` in the root sitemap index. Those slugs are the complete
    official list of locations. Each location home page carries a schema.org
    LocalBusiness JSON-LD block.
    """

    name = "dogtopia_us"
    item_attributes = {"brand": "Dogtopia", "brand_wikidata": "Q112037444"}
    allowed_domains = ["www.dogtopia.com"]
    wanted_types = ["LocalBusiness"]
    drop_attributes = {"image", "facebook", "twitter"}

    # Slugs in the sitemap index which are the corporate site, not a location.
    not_a_location = {"blog", "news", "franchise", "franchising", "careers", "about", "locations"}

    country_utils = CountryUtils()

    async def start(self) -> AsyncIterator[Request]:
        yield Request(url="https://www.dogtopia.com/sitemap_index.xml", callback=self.parse_sitemap_index)

    def parse_sitemap_index(self, response: Response) -> Iterable[Request]:
        slugs = set(re.findall(r"https://www\.dogtopia\.com/([^/]+)/page-sitemap\.xml", response.text))
        for slug in sorted(slugs - self.not_a_location):
            yield Request(url=f"https://www.dogtopia.com/{slug}/", callback=self.parse_sd)

    def post_process_item(self, item: Feature, response: Response, ld_data: dict, **kwargs: Any) -> Iterable[Feature]:
        # Dogtopia also franchises in Canada. The JSON-LD spells countries out
        # in full ("United States"), so normalise before comparing.
        item["country"] = self.country_utils.to_iso_alpha2_country_code(item.get("country"))
        if item["country"] != "US":
            return

        item["ref"] = response.url.rstrip("/").rsplit("/", 1)[-1]
        item["website"] = response.url
        item["branch"] = (item.pop("name", "") or "").removeprefix("Dogtopia of").strip()

        apply_category(Categories.ANIMAL_BOARDING, item)

        yield item
