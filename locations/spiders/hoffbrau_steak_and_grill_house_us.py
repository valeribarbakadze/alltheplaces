import re
from typing import Any, Iterable
from urllib.parse import urlsplit

from scrapy import Spider
from scrapy.http import Response

from locations.categories import Categories, apply_category
from locations.google_url import extract_google_position
from locations.hours import OpeningHours
from locations.items import Feature


class HoffbrauSteakAndGrillHouseUSSpider(Spider):
    name = "hoffbrau_steak_and_grill_house_us"
    item_attributes = {"brand": "Hoffbrau Steak & Grill House", "brand_wikidata": "Q136534380"}
    allowed_domains = ["hoffbrausteakandgrill.com"]
    start_urls = ["https://hoffbrausteakandgrill.com/locations/"]

    def parse(self, response: Response, **kwargs: Any) -> Iterable[Feature]:
        for link in response.css('.entry-content .hoff-button a[href*="/locations/"]'):
            website = response.urljoin(link.attrib["href"])
            details = link.xpath("../../following-sibling::*[1][self::p]")
            lines = [line.strip() for line in details.xpath("text()[normalize-space()]").getall()]
            if len(lines) < 3 or not (locality := re.fullmatch(r"(.+),\s*([A-Z]{2})\s+(\d{5})", lines[1])):
                self.logger.warning("Could not parse location details for %s", website)
                continue

            item = Feature(
                ref=urlsplit(website).path.rstrip("/").rsplit("/", 1)[-1],
                branch=link.xpath("normalize-space(.)").get(),
                website=website,
                street_address=lines[0],
                city=locality[1],
                state=locality[2],
                postcode=locality[3],
                country="US",
                phone=lines[2],
            )
            extract_google_position(item, details)

            hours = OpeningHours()
            for line in lines[3:]:
                hours.add_ranges_from_string(line.replace(" & ", " and "))
            item["opening_hours"] = hours

            apply_category(Categories.RESTAURANT, item)
            item["extras"]["cuisine"] = "steak_house"
            yield item
