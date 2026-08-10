from typing import Any, AsyncIterator, Iterable

import chompjs
from scrapy import Request, Spider
from scrapy.http import Response

from locations.categories import Categories, apply_category
from locations.hours import DAYS_FULL, OpeningHours
from locations.items import Feature
from locations.pipelines.address_clean_up import merge_address_lines


class ShawsUSSpider(Spider):
    """
    Shaw's official local directory at local.shaws.com is a Yext Pages site.
    The directory is a three-level crawl (state list -> city list -> store),
    and each store page embeds the complete Yext entity as a `Yext.Profile`
    JavaScript object.
    """

    name = "shaws_us"
    item_attributes = {"brand": "Shaw's", "brand_wikidata": "Q578387", "country": "US"}
    allowed_domains = ["local.shaws.com"]

    async def start(self) -> AsyncIterator[Request]:
        yield Request(url="https://local.shaws.com/index.html", callback=self.parse_directory)

    def parse_directory(self, response: Response) -> Iterable[Request]:
        """State, city and store pages all use the same relative-link markup."""
        for href in response.xpath('//*[@id="main"]//a/@href | //a[contains(@class, "Directory")]/@href').getall():
            if href.startswith(("http", "#", "search", "index")):
                continue
            url = response.urljoin(href)
            if not url.startswith("https://local.shaws.com/"):
                continue
            depth = url.removeprefix("https://local.shaws.com/").removesuffix(".html").count("/")
            if depth >= 2:
                yield response.follow(url, callback=self.parse_store)
            else:
                yield response.follow(url, callback=self.parse_directory)

    def parse_store(self, response: Response, **kwargs: Any) -> Iterable[Feature]:
        marker = "Yext.Profile ="
        index = response.text.find(marker)
        if index < 0:
            return
        profile = chompjs.parse_js_object(response.text[index + len(marker) :])

        if profile.get("closed"):
            return

        address = profile.get("address") or {}
        if address.get("countryCode") != "US":
            return

        coordinate = profile.get("yextDisplayCoordinate") or profile.get("geocodedCoordinate") or {}

        item = Feature()
        item["ref"] = (profile.get("meta") or {}).get("id") or profile.get("c_parentEntityID")
        item["branch"] = profile.get("c_geomodifier") or address.get("city")
        item["street_address"] = merge_address_lines([address.get("line1"), address.get("line2"), address.get("line3")])
        item["city"] = address.get("city")
        item["state"] = address.get("region")
        item["postcode"] = address.get("postalCode")
        item["country"] = address.get("countryCode")
        item["lat"] = coordinate.get("lat")
        item["lon"] = coordinate.get("long")
        item["phone"] = (profile.get("mainPhone") or {}).get("number")
        item["website"] = profile.get("websiteUrl") or response.url
        item["facebook"] = profile.get("facebookPageUrl")

        item["opening_hours"] = self.parse_hours((profile.get("hours") or {}).get("normalHours", []))

        apply_category(Categories.SHOP_SUPERMARKET, item)

        yield item

    @staticmethod
    def parse_hours(normal_hours: list[dict]) -> OpeningHours:
        oh = OpeningHours()
        for rule in normal_hours:
            day = (rule.get("day") or "").title()
            if day not in DAYS_FULL or rule.get("isClosed"):
                continue
            for interval in rule.get("intervals", []):
                start, end = interval.get("start"), interval.get("end")
                if start is None or end is None:
                    continue
                oh.add_range(
                    day,
                    "{:04d}".format(start)[:2] + ":" + "{:04d}".format(start)[2:],
                    "{:04d}".format(end)[:2] + ":" + "{:04d}".format(end)[2:],
                )
        return oh
