import re
from typing import Any, Iterable

from scrapy import Selector, Spider
from scrapy.http import Response

from locations.categories import Categories, apply_category
from locations.items import Feature
from locations.user_agents import BROWSER_DEFAULT

# Store detail URLs encode city, state, postcode and store number, e.g.
# /tsc/store_Middletown-DE-19709_1206
STORE_URL_PATTERN = re.compile(r"/tsc/store_(?P<city>.+)-(?P<state>[A-Z]{2})-(?P<postcode>\d{5})_(?P<ref>\d+)$")


class TractorSupplySpider(Spider):
    """
    Tractor Supply's official store directory lists one page per state, and
    each state page lists every store in that state with its address and
    phone number. The store detail URL itself encodes the city, state,
    postcode and official store number, which makes it the most reliable
    identifier available from the directory.

    Note: Tractor Supply serves HTTP 403 to datacentre IP ranges, so this
    spider requires a residential proxy.
    """

    name = "tractor_supply"
    item_attributes = {"brand": "Tractor Supply Company", "brand_wikidata": "Q15109925", "country": "US"}
    allowed_domains = ["slr.shop.tractorsupply.com"]
    start_urls = ["https://slr.shop.tractorsupply.com/tsc/store-locations"]
    custom_settings = {"ROBOTSTXT_OBEY": False, "DOWNLOAD_DELAY": 1.0, "USER_AGENT": BROWSER_DEFAULT}
    requires_proxy = True

    def parse(self, response: Response, **kwargs: Any) -> Any:
        for href in set(response.xpath('//a[contains(@href, "/tsc/store-locations/")]/@href').getall()):
            if href.rstrip("/").endswith("store-locations"):
                continue
            yield response.follow(href, callback=self.parse_state)

    def parse_state(self, response: Response) -> Iterable[Feature]:
        seen = set()
        for link in response.xpath('//a[contains(@href, "/tsc/store_")]'):
            href = link.xpath("./@href").get("")
            match = STORE_URL_PATTERN.search(href.split("?")[0])
            if not match or match.group("ref") in seen:
                continue
            seen.add(match.group("ref"))

            row = link.xpath("./ancestor::li[1]")
            if not row:
                row = link.xpath("./parent::*")

            item = Feature()
            item["ref"] = match.group("ref")
            item["branch"] = link.xpath("normalize-space(.)").get() or match.group("city").replace("-", " ")
            item["city"] = match.group("city").replace("-", " ")
            item["state"] = match.group("state")
            item["postcode"] = match.group("postcode")
            item["website"] = response.urljoin(href)
            item["street_address"] = self.extract_street_address(row, item["city"], item["state"])
            item["phone"] = self.extract_phone(row)

            apply_category(Categories.SHOP_AGRARIAN, item)

            yield item

    @staticmethod
    def extract_phone(row: Selector) -> str | None:
        for href in row.xpath('.//a[starts-with(@href, "tel:")]/@href').getall():
            return href.removeprefix("tel:").strip()
        return None

    @staticmethod
    def extract_street_address(row: Selector, city: str, state: str) -> str | None:
        """
        Rows render as: <branch link> <street> <newline> City, ST 12345
        <newline> <phone>. The street is the first non-empty text node that is
        not the branch name, the "City, ST ZIP" line, or a services link.
        """
        city_state = "{}, {}".format(city, state).lower()
        for text in row.xpath("./text() | ./*/text()").getall():
            text = " ".join(text.split())
            if not text or text.lower().startswith(city_state):
                continue
            if re.fullmatch(r"[A-Za-z .'-]+,\s*[A-Z]{2}\s*\d{5}(-\d{4})?", text):
                continue
            if re.search(r"\d", text):
                return text
        return None
