import re
from typing import Any, Iterable

from scrapy.http import Response
from scrapy.spiders import SitemapSpider

from locations.categories import Categories, apply_category
from locations.hours import NAMED_TIMES_EN, OpeningHours
from locations.items import Feature


class MannysChophouseUSSpider(SitemapSpider):
    name = "mannys_chophouse_us"
    item_attributes = {"brand": "Manny's Original Chophouse"}
    sitemap_urls = ["https://www.mannyschophouse.com/sitemap.xml"]
    sitemap_rules = [("", "parse_location")]
    LOCALITY = re.compile(r"^(?P<city>.+),\s*(?P<state>[A-Z]{2})\s+(?P<postcode>\d{5})$")
    # Winter Haven opens at "12 Noon" on Sundays, which the parser holds no spelling for.
    NAMED_TIMES = NAMED_TIMES_EN | {"12 Noon": NAMED_TIMES_EN["Midday"]}

    def parse_location(self, response: Response, **kwargs: Any) -> Iterable[Feature]:
        tout = response.xpath('//section[contains(@class, "c-tout-overlay")]')
        lines = [text for raw in tout.xpath(".//p//text()").getall() if (text := raw.strip())]
        # Every page carries this section; only the two restaurants state an address in it.
        stated = [index for index, line in enumerate(lines) if self.LOCALITY.match(line)]
        if not stated:
            return

        locality = self.LOCALITY.match(lines[stated[0]])
        item = Feature(
            ref=response.url,
            branch=tout.xpath("normalize-space(.//h2)").get(),
            website=response.url,
            street_address=lines[stated[0] - 1],
            city=locality["city"],
            state=locality["state"],
            postcode=locality["postcode"],
            phone=tout.xpath('.//a[starts-with(@href, "tel:")]/@href').get(),
            opening_hours=OpeningHours(),
        )
        # The neighbouring paragraph holds holiday closures, which are not a weekly schedule.
        for rule in tout.xpath('.//p[contains(., "Hours of Operation")]//text()').getall():
            if not rule.strip().startswith("Hours of Operation"):
                item["opening_hours"].add_ranges_from_string(rule, named_times=self.NAMED_TIMES)

        apply_category(Categories.RESTAURANT, item)
        item["extras"]["cuisine"] = "steak_house"
        yield item
