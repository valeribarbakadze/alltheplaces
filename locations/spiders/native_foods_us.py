import re
from typing import Any, Iterable

from scrapy import Spider
from scrapy.http import Response

from locations.categories import Categories, Extras, apply_category
from locations.items import Feature
from locations.linked_data_parser import LinkedDataParser


class NativeFoodsUSSpider(Spider):
    name = "native_foods_us"
    item_attributes = {"brand": "Native Foods", "brand_wikidata": "Q18636327"}
    start_urls = ["https://nativefoods.com/"]
    # Only Glendale is in the page's structured data. Palm Springs is stated in the footer, where
    # the owner typed both restaurants into the one address field; its own site is behind a challenge.
    ADDRESS = re.compile(
        r"^(?P<street>.+?),?\s+(?P<city>[A-Z][A-Za-z ]+),\s*(?P<state>[A-Za-z ]+?)\s+(?P<postcode>\d{5})"
    )

    def parse(self, response: Response, **kwargs: Any) -> Iterable[Feature]:
        glendale = LinkedDataParser.parse(response, "LocalBusiness")
        glendale.pop("name")
        glendale.pop("image")  # A stock photo the site builder supplied.
        glendale.pop("website")  # The brand's site, shared with Palm Springs, and stated without a scheme.
        glendale["ref"] = glendale["branch"] = glendale["city"]
        items = [glendale]

        phones = response.xpath('//p[@data-aid="FOOTER_PHONE_RENDERED"]//a/@href').getall()
        addresses = response.xpath('//p[@data-aid="FOOTER_ADDRESS_RENDERED"]/text()').get().split("/")
        # The footer states the two restaurants' addresses and numbers in the same order.
        for address, phone in zip(addresses, phones):
            location = self.ADDRESS.match(address.strip())
            if location["postcode"] == glendale["postcode"]:
                continue
            items.append(
                Feature(
                    ref=location["city"],
                    branch=location["city"],
                    street_address=location["street"],
                    city=location["city"],
                    state=location["state"],
                    postcode=location["postcode"],
                    phone=phone,
                )
            )

        for item in items:
            apply_category(Categories.RESTAURANT, item)
            # Everything both restaurants serve is vegan, which is "only" rather than apply_yes_no's "yes".
            item["extras"][Extras.VEGAN.value] = "only"
            yield item
