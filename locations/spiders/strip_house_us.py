import json
from typing import Any, Iterable

from scrapy.http import Request, Response

from locations.categories import Categories, apply_category
from locations.hours import OpeningHours
from locations.items import Feature
from locations.structured_data_spider import StructuredDataSpider


class StripHouseUSSpider(StructuredDataSpider):
    name = "strip_house_us"
    item_attributes = {"brand": "Strip House"}
    start_urls = ["https://www.striphouse.com/locations/"]
    name_is_branch = True
    # One brand-wide account each, linked from the footer of every page.
    search_for_facebook = False
    search_for_twitter = False

    def parse(self, response: Response, **kwargs: Any) -> Iterable[Request]:
        group = json.loads(response.xpath('//script[@type="application/ld+json"]/text()').get())
        for venue in group["subOrganization"]:
            yield response.follow(venue["url"], callback=self.parse_sd)

    def post_process_item(self, item: Feature, response: Response, ld_data: dict, **kwargs: Any) -> Iterable[Feature]:
        item["ref"] = response.url.rsplit("/", 2)[-2]
        # The structured data stamps one stale set of times on every venue, so
        # the weekly hours shown on the page are read instead. Dated holiday
        # hours sit under a heading, which closes this paragraph before them.
        item["opening_hours"] = OpeningHours()
        for rule in response.xpath(
            '//section[@id="intro"]//p[a[starts-with(@href, "tel:")]]/following-sibling::p[1]//text()'
        ).getall():
            item["opening_hours"].add_ranges_from_string(rule)

        pin = response.xpath("//div[@data-gmaps-lat]")
        item["lat"], item["lon"] = pin.attrib["data-gmaps-lat"], pin.attrib["data-gmaps-lng"]

        apply_category(Categories.RESTAURANT, item)
        item["extras"]["cuisine"] = "steak_house"
        yield item
