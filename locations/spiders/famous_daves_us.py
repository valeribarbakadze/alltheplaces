import html
import json
import re
from typing import Any, Iterable

from scrapy import Selector, Spider
from scrapy.http import Response

from locations.categories import Categories, apply_category
from locations.hours import DAYS_EN, OpeningHours
from locations.items import Feature
from locations.pipelines.address_clean_up import merge_address_lines


class FamousDavesUSSpider(Spider):
    """
    The official Famous Dave's locations index links to one list page per
    state (US) or per city (international). Each list page embeds the full
    location records for that area in a hidden `storeList` input as escaped
    JSON.
    """

    name = "famous_daves_us"
    item_attributes = {"brand": "Famous Dave's", "brand_wikidata": "Q5433448"}
    allowed_domains = ["www.famousdaves.com"]
    start_urls = ["https://www.famousdaves.com/locations"]

    def parse(self, response: Response, **kwargs: Any) -> Any:
        seen = set()
        # International list pages use "country=canada", "country=united arab
        # emirates" and so on, so only US state pages are requested.
        for href in response.xpath('//a[contains(@href, "/Locations/List?country=usa")]/@href').getall():
            url = response.urljoin(href)
            if url in seen:
                continue
            seen.add(url)
            yield response.follow(url, callback=self.parse_store_list)

    def parse_store_list(self, response: Response) -> Iterable[Feature]:
        raw = response.xpath('//input[@id="storeList"]/@value').get()
        if not raw:
            return
        for location in json.loads(html.unescape(raw)):
            name = location.get("Name") or ""
            if "coming soon" in name.lower():
                continue
            # The locator also covers Canada and the United Arab Emirates.
            if location.get("Country") != "USA":
                continue

            item = Feature()
            item["ref"] = location.get("Id")
            item["branch"] = name.strip()
            item["lat"] = location.get("Latitude")
            item["lon"] = location.get("Longitude")
            item["street_address"] = merge_address_lines([location.get("AddressLine1")])
            item["city"] = location.get("City")
            item["state"] = location.get("StateCode") or location.get("State")
            item["postcode"] = self.extract_postcode(location.get("AddressLine2"))
            item["phone"] = location.get("PhoneNumber")
            item["extras"]["ref:famousdaves:store"] = location.get("StoreNumber")

            if slug := location.get("RestaurantUrl"):
                item["website"] = response.urljoin(f"/locations/{slug}")

            item["opening_hours"] = self.parse_hours(location.get("Hours"))

            apply_category(Categories.RESTAURANT, item)
            item["extras"]["cuisine"] = "barbecue"

            yield item

    @staticmethod
    def extract_postcode(address_line_2: str | None) -> str | None:
        """AddressLine2 is formatted "City, ST 12345"."""
        if not address_line_2:
            return None
        parts = address_line_2.strip().rsplit(" ", 1)
        if len(parts) == 2 and parts[1].replace("-", "").isdigit():
            return parts[1]
        return None

    @staticmethod
    def parse_hours(hours_html: str | None) -> OpeningHours | None:
        """
        Hours are free-text HTML entered by the franchisee, with one day range
        per <br />-separated line. Any <em> block is footnote prose (delivery
        notes, gift card terms) rather than opening hours.
        """
        if not hours_html:
            return None
        text = re.sub(r"<em>.*?</em>", "", hours_html, flags=re.S | re.I)
        text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
        lines = [
            " ".join(line.split())
            for line in " ".join(Selector(text=text).xpath("//text()").getall()).replace("\xa0", " ").splitlines()
        ]
        oh = OpeningHours()
        oh.add_ranges_from_string("; ".join(filter(None, lines)), days=DAYS_EN)
        return oh if oh.as_opening_hours() else None
