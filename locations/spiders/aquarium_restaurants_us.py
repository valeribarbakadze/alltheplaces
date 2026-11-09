import re
from typing import Any, AsyncIterator
from urllib.parse import urlparse

from scrapy import Request, Spider
from scrapy.http import Response

from locations.categories import Categories, apply_category
from locations.hours import OpeningHours
from locations.items import Feature


class AquariumRestaurantsUSSpider(Spider):
    name = "aquarium_restaurants_us"
    item_attributes = {"brand": "Aquarium Restaurant"}

    # Each restaurant sits inside a Landry's aquarium that runs its own site.
    # Three share one template; Denver's is an older one, and the only one to
    # state the restaurant's hours rather than leave them to Yext.
    PORTAL = "https://www.aquariumrestaurants.com/"
    VISITOR_INFO = {
        "https://www.downtownaquariumhouston.com/visitor-info": "houston",
        "https://www.aquariumkemah.com/visitor-info": "kemah",
        "https://www.aquariumnashville.com/visitor-info": "nashville",
    }
    DENVER = "https://www.aquariumrestaurants.com/downtownaquariumdenver/visitorInfo.asp"
    COVERED = {"aquariumrestaurants.com", "downtownaquariumhouston.com", "aquariumkemah.com", "aquariumnashville.com"}

    LOCALITY = re.compile(r"^(?P<city>[^,]+),\s*(?P<state>[A-Za-z][A-Za-z .]*?)\s+(?P<postcode>\d{5})$")
    MICRODATA = {
        "streetAddress": "street_address",
        "addressLocality": "city",
        "addressRegion": "state",
        "postalCode": "postcode",
    }

    async def start(self) -> AsyncIterator[Request]:
        yield Request(self.PORTAL, callback=self.parse_portal)
        for url in self.VISITOR_INFO:
            yield Request(url, callback=self.parse_visitor_info)
        yield Request(self.DENVER, callback=self.parse_denver)

    def parse_portal(self, response: Response) -> None:
        linked = {
            host
            for url in response.xpath("//a/@href").getall()
            if "aquarium" in (host := (urlparse(url).hostname or "").removeprefix("www."))
        }
        if missed := linked - self.COVERED:
            self.logger.error(f"The portal links aquariums this spider does not read, so add them: {sorted(missed)}")

    def parse_visitor_info(self, response: Response) -> Any:
        item = Feature(ref=self.VISITOR_INFO[response.url], website=response.url)
        for paragraph in response.xpath("//p"):
            if locality := self.LOCALITY.match(self.text(paragraph)):
                item["city"], item["postcode"] = self.cased(locality["city"]), locality["postcode"]
                # The state pipeline matches a code as given and a name in
                # title case, and these pages write both in capitals.
                item["state"] = locality["state"] if len(locality["state"]) == 2 else locality["state"].title()
                item["street_address"] = self.cased(self.text(paragraph.xpath("preceding-sibling::p[1]")))
                break
        else:
            self.logger.error(f"{response.url} states no address this spider can read, so check the page layout")
        item["phone"] = response.xpath('//a[starts-with(@href, "tel:")]/@href').get()
        # No hours: this page leaves them to empty divs that Yext fills in from
        # the browser, and the dining page beside it states the lounge's.
        apply_category(Categories.RESTAURANT, item)
        yield item

    def parse_denver(self, response: Response) -> Any:
        item = Feature(ref="denver", website=response.url)
        for field, key in self.MICRODATA.items():
            item[key] = response.xpath(f'//*[@itemprop="{field}"]/text()').get()
        item["phone"] = self.text(response.xpath('//*[@itemprop="telephone"]'))
        # This page states the exhibit's, the gift shop's and the lounge's
        # hours beside the restaurant's.
        item["opening_hours"] = OpeningHours()
        item["opening_hours"].add_ranges_from_string(
            self.text(response.xpath('//h2[normalize-space(text()) = "Restaurant Hours"]/following-sibling::p[1]'))
        )
        apply_category(Categories.RESTAURANT, item)
        yield item

    @staticmethod
    def text(selector: Any) -> str:
        return re.sub(r"[\s ]+", " ", " ".join(selector.xpath(".//text()").getall())).strip()

    @staticmethod
    def cased(value: str) -> str:
        return value.title() if value.isupper() else value
