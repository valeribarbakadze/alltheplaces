import re
from typing import Any, Iterable

from scrapy import Selector, Spider
from scrapy.http import Response

from locations.categories import Categories, apply_category
from locations.items import Feature
from locations.linked_data_parser import LinkedDataParser
from locations.user_agents import BROWSER_DEFAULT

# Store page URLs are /l/<branch-slug>/<state>/<city-slug>/<postcode>/<store-id>
STORE_URL_PATTERN = re.compile(
    r"^/l/(?P<branch>[^/]+)/(?P<state>[A-Z]{2})/(?P<city>[^/]+)/(?P<postcode>\d{5})/(?P<ref>\d+)/?$"
)

# Territories which The Home Depot lists in its US directory but which are
# separate ISO 3166-1 countries in the ATP data model.
NON_US_TERRITORIES = {"GU", "PR", "VI", "AS", "MP"}


class HomeDepotUSSpider(Spider):
    """
    The Home Depot's official store directory at
    https://www.homedepot.com/l/storeDirectory links to one page per state.
    Each state page lists every store in that state with its branch name,
    street address, city/state/postcode and phone number, and links to the
    store's own page.

    The state pages carry no coordinates or opening hours, so each store page
    is then visited for its schema.org JSON-LD. Directory-derived fields are
    kept as the fallback so a store still yields a usable POI if the store
    page structured data is missing.

    Note: homedepot.com serves HTTP 403 to datacentre IP ranges, so this
    spider requires a US residential proxy.
    """

    name = "home_depot_us"
    item_attributes = {"brand": "The Home Depot", "brand_wikidata": "Q864407"}
    allowed_domains = ["www.homedepot.com"]
    start_urls = ["https://www.homedepot.com/l/storeDirectory"]
    custom_settings = {"ROBOTSTXT_OBEY": False, "DOWNLOAD_DELAY": 1.0, "USER_AGENT": BROWSER_DEFAULT}
    requires_proxy = "US"

    def parse(self, response: Response, **kwargs: Any) -> Any:
        """Follow each state directory page linked from the top level directory."""
        for href in set(response.xpath('//a[starts-with(@href, "/l/")]/@href').getall()):
            if match := re.fullmatch(r"/l/([A-Z]{2})/?", href):
                if match.group(1) in NON_US_TERRITORIES:
                    continue
                yield response.follow(href, callback=self.parse_state)

    def parse_state(self, response: Response) -> Iterable[Any]:
        seen = set()
        for link in response.xpath('//a[starts-with(@href, "/l/")]'):
            href = link.xpath("./@href").get("")
            match = STORE_URL_PATTERN.match(href)
            if not match or match.group("ref") in seen:
                continue
            if match.group("state") in NON_US_TERRITORIES:
                continue
            seen.add(match.group("ref"))

            item = Feature()
            item["ref"] = match.group("ref")
            item["branch"] = link.xpath("normalize-space(.)").get() or match.group("branch").replace("-", " ")
            item["city"] = match.group("city").replace("-", " ")
            item["state"] = match.group("state")
            item["postcode"] = match.group("postcode")
            item["country"] = "US"
            item["website"] = response.urljoin(href)

            # The smallest ancestor containing both the store link and the
            # "City, ST 12345" line is the block holding this store's details.
            # `ancestor` is a reverse axis, so [1] is the nearest ancestor.
            row = link.xpath('./ancestor::*[contains(., "{}")][1]'.format(match.group("postcode")))
            item["street_address"] = self.extract_street_address(row, item["city"], item["state"])
            item["phone"] = self.extract_phone(row)

            apply_category(Categories.SHOP_DOITYOURSELF, item)

            yield response.follow(href, callback=self.parse_store, cb_kwargs={"item": item})

    # schema.org types seen on Home Depot store pages, most specific first.
    wanted_types = ["HardwareStore", "HomeGoodsStore", "Store", "LocalBusiness"]

    def parse_store(self, response: Response, item: Feature) -> Iterable[Feature]:
        """Enrich the directory row with coordinates and hours from JSON-LD."""
        for wanted_type in self.wanted_types:
            if ld_data := LinkedDataParser.find_linked_data(response, wanted_type):
                break
        else:
            # No structured data; the directory row alone is still a usable POI.
            yield item
            return

        ld_item = LinkedDataParser.parse_ld(ld_data)

        item["lat"] = ld_item.get("lat")
        item["lon"] = ld_item.get("lon")
        if opening_hours := ld_item.get("opening_hours"):
            if opening_hours.as_opening_hours():
                item["opening_hours"] = opening_hours

        # The directory is the more reliable source for these, so only fall
        # back to structured data where the directory row was incomplete.
        item["phone"] = item.get("phone") or ld_item.get("phone")
        item["street_address"] = item.get("street_address") or ld_item.get("street_address")

        yield item

    @staticmethod
    def extract_phone(row: Selector) -> str | None:
        if href := row.xpath('.//a[starts-with(@href, "tel:")]/@href').get():
            return href.removeprefix("tel:").strip()
        for text in row.xpath(".//text()").getall():
            if match := re.search(r"\(?\d{3}\)?[\s.-]*\d{3}[\s.-]*\d{4}", text):
                return match.group(0)
        return None

    @staticmethod
    def extract_street_address(row: Selector, city: str, state: str) -> str | None:
        """
        Rows render the street on one line and "City, ST 12345" on the next.
        Link text is skipped because the branch name and the per-department
        links ("<branch> Rentals" and friends) are not address lines, and some
        branch names begin with a number, e.g. "21st South".
        """
        city_state = "{}, {}".format(city, state).lower()
        for text in row.xpath(".//text()[not(ancestor::a)]").getall():
            text = " ".join(text.split())
            if not text or text.lower().startswith(city_state):
                continue
            if re.fullmatch(r"[A-Za-z .'-]+,\s*[A-Z]{2}\s*\d{5}(-\d{4})?", text):
                continue
            if re.fullmatch(r"[(\d)\s.+-]+", text):
                continue
            if re.search(r"\d", text):
                return text
        return None
