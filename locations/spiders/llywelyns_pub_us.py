import re
from typing import Any, Iterable

from scrapy import Spider
from scrapy.http import Request, Response

from locations.categories import Categories, apply_category
from locations.google_url import extract_google_position
from locations.hours import OpeningHours
from locations.items import Feature
from locations.pipelines.address_clean_up import merge_address_lines


class LlywelynsPubUSSpider(Spider):
    name = "llywelyns_pub_us"
    item_attributes = {"brand": "Llywelyn's Pub"}
    start_urls = ["https://www.llywelynspub.com/"]
    LOCALITY = re.compile(r"^(?P<city>.+),\s*(?P<state>[A-Z]{2})\s+(?P<postcode>\d{5})$")
    TAIL = re.compile(r"^(?P<state>[A-Z]{2})\s+(?P<postcode>\d{5})$")

    def parse(self, response: Response, **kwargs: Any) -> Iterable[Request | Feature]:
        for column in response.xpath('//div[contains(@class, "ly-col")][.//iframe[contains(@src, "maps/embed")]]'):
            lines = [text for raw in column.xpath(".//text()").getall() if (text := raw.strip())]
            stated = [index for index, line in enumerate(lines) if self.LOCALITY.match(line)][0]
            locality = self.LOCALITY.match(lines[stated])
            branch = column.xpath("normalize-space(.//h4)").get()
            item = Feature(
                ref=branch,
                branch=branch,
                street_address=lines[stated - 1],
                city=locality["city"],
                state=locality["state"],
                postcode=locality["postcode"],
                phone=column.xpath('.//a[starts-with(@href, "tel:")]/@href').get(),
            )
            # Both pubs state the same info@ address, and neither states its hours.
            extract_google_position(item, column)
            apply_category(Categories.PUB, item)
            yield item

        # The Kansas City pub keeps a site of its own, linked from here.
        yield response.follow(response.xpath('//a[contains(., "KC location")]/@href').get(), self.parse_kansas_city)

    def parse_kansas_city(self, response: Response, **kwargs: Any) -> Iterable[Feature]:
        stated, label = {}, None
        for raw in response.xpath('//div[contains(@class, "ly-col")][.//text()[contains(., "Address:")]]//text()'):
            if not (line := raw.get().strip()):
                continue
            if line.endswith(":"):
                label = line
                stated[label] = []
            elif label:
                stated[label].append(line)

        tail = self.TAIL.match(stated["Address:"][-1])
        item = Feature(
            ref=response.url,
            # Street and city run together with nothing between them, so the address is left whole.
            addr_full=merge_address_lines(stated["Address:"]),
            state=tail["state"],
            postcode=tail["postcode"],
            phone=stated["Phone:"][0],
            email=stated["Email:"][0],
            opening_hours=OpeningHours(),
        )
        for rule in stated["Open Hours:"]:
            item["opening_hours"].add_ranges_from_string(rule)
        apply_category(Categories.PUB, item)
        yield item
