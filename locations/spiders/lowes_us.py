from typing import Any, Iterable

import chompjs
from scrapy.http import Response
from scrapy.spiders import SitemapSpider

from locations.categories import Categories, apply_category
from locations.hours import DAYS_FULL, OpeningHours
from locations.items import Feature
from locations.pipelines.address_clean_up import merge_address_lines
from locations.user_agents import FIREFOX_LATEST


class LowesUSSpider(SitemapSpider):
    """
    Lowe's publishes a public store-directory sitemap listing one directory
    page per US state. Each of those pages embeds the complete set of store
    records for the state in `window.__PRELOADED_STATE__`. Individual store
    detail pages return HTTP 403, so the state directory pages are the
    refresh source.

    Note: Lowe's serves HTTP 403 to datacentre IP ranges, so this spider
    requires a residential proxy.
    """

    name = "lowes_us"
    item_attributes = {"brand": "Lowe's", "brand_wikidata": "Q1373493", "country": "US"}
    allowed_domains = ["www.lowes.com"]
    sitemap_urls = ["https://www.lowes.com/sitemap/storedirectory0.xml"]
    sitemap_rules = [(r"^https://www\.lowes\.com/Lowes-Stores/", "parse_state_directory")]
    custom_settings = {"ROBOTSTXT_OBEY": False, "USER_AGENT": FIREFOX_LATEST}
    requires_proxy = True

    def parse_state_directory(self, response: Response, **kwargs: Any) -> Iterable[Feature]:
        marker = "__PRELOADED_STATE__"
        index = response.text.find(marker)
        if index < 0:
            self.logger.warning("No __PRELOADED_STATE__ found on %s", response.url)
            return
        blob_start = response.text.find("{", index)
        state = chompjs.parse_js_object(response.text[blob_start:])

        seen = set()
        for store in self.find_stores(state.get("storeDirectory", state)):
            ref = str(store.get("id") or store.get("storeNumber") or "")
            if not ref or ref in seen:
                continue
            seen.add(ref)

            item = Feature()
            item["ref"] = ref
            item["branch"] = store.get("name") or store.get("city")
            item["street_address"] = merge_address_lines([store.get("address1"), store.get("address2")])
            item["city"] = store.get("city")
            item["state"] = store.get("state")
            item["postcode"] = store.get("zip") or store.get("zipcode") or store.get("postalCode")
            item["phone"] = store.get("phone") or store.get("phoneNumber")
            item["lat"] = store.get("latitude") or store.get("lat")
            item["lon"] = store.get("longitude") or store.get("long") or store.get("lon")

            if url := store.get("url") or store.get("storeUrl"):
                item["website"] = response.urljoin(url)

            item["opening_hours"] = self.parse_hours(store.get("hours") or store.get("storeHours"))

            apply_category(Categories.SHOP_DOITYOURSELF, item)

            yield item

    @classmethod
    def find_stores(cls, node: Any) -> Iterable[dict]:
        """
        The exact nesting of `storeDirectory` varies by state page, so walk
        the structure and yield any dictionary that looks like a store record.
        """
        if isinstance(node, dict):
            has_id = any(key in node for key in ("id", "storeNumber"))
            has_address = any(key in node for key in ("address1", "city"))
            if has_id and has_address:
                yield node
                return
            for value in node.values():
                yield from cls.find_stores(value)
        elif isinstance(node, list):
            for value in node:
                yield from cls.find_stores(value)

    @staticmethod
    def parse_hours(store_hours: Any) -> OpeningHours | None:
        if not isinstance(store_hours, list):
            return None
        oh = OpeningHours()
        for weekday in store_hours:
            if not isinstance(weekday, dict):
                continue
            day_data = weekday.get("day") if isinstance(weekday.get("day"), dict) else weekday
            day = day_data.get("day") or day_data.get("name")
            open_time, close_time = day_data.get("open"), day_data.get("close")
            if not day or not open_time or not close_time:
                continue
            if day.title() not in DAYS_FULL and day[:2].title() not in ("Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"):
                continue
            open_time = ":".join(open_time.split(".")[:2])[:5]
            close_time = ":".join(close_time.split(".")[:2])[:5]
            if close_time in {"00:00", "24:00"}:
                close_time = "23:59"
            oh.add_range(day=day[:2].title(), open_time=open_time, close_time=close_time)
        return oh if oh.as_opening_hours() else None
