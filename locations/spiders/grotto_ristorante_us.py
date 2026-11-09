import json
import re
from typing import Any, Iterable

from scrapy.http import Response

from locations.categories import Categories, apply_category
from locations.hours import OpeningHours
from locations.items import Feature
from locations.structured_data_spider import StructuredDataSpider


class GrottoRistoranteUSSpider(StructuredDataSpider):
    name = "grotto_ristorante_us"
    item_attributes = {"brand": "Grotto Ristorante"}
    start_urls = ["https://www.grottorestaurants.com/locations/"]
    wanted_types = ["FoodEstablishment"]
    name_is_branch = True
    search_for_email = False
    search_for_twitter = False
    search_for_facebook = False

    # A rule names its days and then its times. The promotions beside them lead
    # with their own name, "Happy Hour" or "Brunch", and the holiday hours
    # beneath them lead with a date, so neither shape matches.
    RULE = re.compile(r"^[A-Za-z]{3,9}(?:\s*-\s*[A-Za-z]{3,9})?:\s*(?=.*(?:\d|closed))", re.IGNORECASE)
    # One branch reads "Houston, TX (Galleria)", so the state is not always last.
    STATE = re.compile(r",\s*[A-Z]{2}\b")

    def parse(self, response: Response, **kwargs: Any) -> Any:
        # The locator states each restaurant as a subOrganization of the group.
        # That is the list the site keeps: its sitemap names only two of the
        # four, and its description claims three more that it does not publish.
        group = json.loads(response.xpath('//script[@type="application/ld+json"]/text()').get())
        for restaurant in group["subOrganization"]:
            yield response.follow(restaurant["url"], callback=self.parse_sd)

    def post_process_item(self, item: Feature, response: Response, ld_data: dict, **kwargs: Any) -> Iterable[Feature]:
        # The structured data makes its @id the ref, which is this page's URL.
        item["ref"] = response.url.rsplit("/", 2)[-2]
        item["branch"] = self.STATE.sub("", item["branch"])
        location = response.xpath("//div[@data-gmaps-lat]")
        item["lat"], item["lon"] = location.attrib["data-gmaps-lat"], location.attrib["data-gmaps-lng"]
        item["opening_hours"] = OpeningHours()
        item["opening_hours"].add_ranges_from_string(
            " ".join(
                line
                for text in response.xpath('//section[contains(@class, "c-intro")]//text()').getall()
                if self.RULE.match(line := re.sub(r"[\s ]+", " ", text).strip())
            )
        )
        apply_category(Categories.RESTAURANT, item)
        item["extras"]["cuisine"] = ld_data["servesCuisine"].lower()
        yield item
