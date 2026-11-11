from typing import Any, Iterable

from scrapy import Request
from scrapy.http import Response
from scrapy.spiders import Spider

from locations.categories import Categories, apply_category
from locations.items import Feature


class CinemaCafeUSSpider(Spider):
    name = "cinema_cafe_us"
    item_attributes = {"brand": "Cinema Cafe"}
    start_urls = ["https://www.cinemacafe.com/page-data/locations/page-data.json"]

    def parse(self, response: Response, **kwargs: Any) -> Iterable[Request]:
        # Webedia's Gatsby build keeps the theatre list in a static query named for a build hash,
        # which this stable page-data.json lists. Same platform as bb_theatres_us.
        for query in response.json()["staticQueryHashes"]:
            yield response.follow(f"/page-data/sq/d/{query}.json", self.parse_theaters)

    def parse_theaters(self, response: Response, **kwargs: Any) -> Iterable[Feature]:
        theaters = response.json().get("data", {}).get("allTheater", {}).get("nodes")
        if not theaters:
            return  # This static query is about something else.

        for theater in theaters:
            # A second query lists the same ids and nothing else on them.
            if "practicalInfo" not in theater or theater["practicalInfo"]["closed"]:
                continue

            info = theater["practicalInfo"]
            location = info["location"]
            item = Feature(
                ref=theater["id"],
                # The name repeats the city after a comma, which addr:city already states.
                branch=theater["name"].split(",")[0],
                website=response.urljoin(theater["path"]),
                street_address=location["address"],
                city=location["city"],
                state=location["state"],
                postcode=location["zip"],
                phone=info["phone"],
                lat=info["coordinates"]["latitude"],
                lon=info["coordinates"]["longitude"],
            )
            # info["links"] holds one Facebook, Instagram, Twitter and YouTube account for the brand.
            if images := info["images"]:
                item["image"] = images[0]["url"]
            item["extras"]["screen"] = str(len(theater["screens"]))
            apply_category(Categories.CINEMA, item)
            yield item
