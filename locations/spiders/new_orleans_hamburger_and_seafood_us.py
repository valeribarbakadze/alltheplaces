import re
from typing import Any

from scrapy import Selector, Spider
from scrapy.http import Response

from locations.categories import Categories, apply_category
from locations.hours import OpeningHours, sanitise_day
from locations.items import Feature


class NewOrleansHamburgerAndSeafoodUSSpider(Spider):
    name = "new_orleans_hamburger_and_seafood_us"
    item_attributes = {"brand": "New Orleans Hamburger & Seafood Co."}
    start_urls = ["https://nohsc.com/locations/"]

    BR = re.compile(r"<br\s*/?>", re.IGNORECASE)
    BRANCH = re.compile(r"^(?P<branch>.+?)\s*[–-]\s*\(MENU\)$")
    # Street and locality share one line, divided only by a run of spaces.
    ADDRESS = re.compile(
        r"^(?P<street>\S.*?\w)\W*\s{2,}(?P<city>[A-Za-z][\w .'-]*?)\s+(?P<state>[A-Z]{2})\s+(?P<postcode>\d{5})$"
    )
    PHONE = re.compile(r"^Phone:\s*(?P<phone>.+)$", re.IGNORECASE)
    # St Charles lists its coffee shop's longer hours beside the restaurant's.
    SECTION = re.compile(r"^(?P<label>[A-Za-z][A-Za-z ]*?)\s+[–—]\s+(?=\S)")

    def parse(self, response: Response, **kwargs: Any) -> Any:
        stores = []
        for paragraph in response.xpath('//div[@class="postcontent"]/p'):
            text = Selector(text=self.BR.sub("\n", paragraph.get())).xpath("string()").get()
            for line in text.split("\n"):
                line = line.replace(" ", " ").strip()
                if match := self.BRANCH.match(line):
                    stores.append([match["branch"], []])
                elif line and stores:
                    stores[-1][1].append(line)

        for branch, lines in stores:
            item = Feature(ref=branch, branch=branch)
            hours = OpeningHours()
            wanted = True
            for line in lines:
                if match := self.ADDRESS.match(line):
                    item["street_address"], item["city"] = match["street"], match["city"]
                    item["state"], item["postcode"] = match["state"], match["postcode"]
                elif match := self.PHONE.match(line):
                    item["phone"] = match["phone"]
                else:
                    line = re.sub(r"^Hours:\s*", "", line, flags=re.IGNORECASE)
                    if (match := self.SECTION.match(line)) and not sanitise_day(match["label"]):
                        wanted = match["label"].casefold() == "restaurant"
                        line = line[match.end() :]
                    if wanted and line:
                        hours.add_ranges_from_string(line)
            if not item.get("street_address"):
                self.logger.error(f"{branch} publishes no address this spider can read, so check the page layout")
            item["opening_hours"] = hours
            apply_category(Categories.FAST_FOOD, item)
            item["extras"]["cuisine"] = "seafood;burger"
            yield item
