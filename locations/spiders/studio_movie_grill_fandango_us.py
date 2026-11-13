from typing import Any, Iterable
from urllib.parse import urlsplit

from scrapy import Request
from scrapy.http import Response

from locations.categories import Categories, apply_category
from locations.items import Feature
from locations.structured_data_spider import StructuredDataSpider


class StudioMovieGrillFandangoUSSpider(StructuredDataSpider):
    name = "studio_movie_grill_fandango_us"
    item_attributes = {"brand": "Studio Movie Grill"}
    allowed_domains = ["www.fandango.com"]
    start_urls = ["https://www.fandango.com/movie-theaters/studio-movie-grill"]
    wanted_types = ["MovieTheater"]

    def parse(self, response: Response, **kwargs: Any) -> Iterable[Request]:
        links = set(response.css('a[href*="/studio-movie-grill-"][href$="/theater-page"]::attr(href)').getall())
        if not links:
            raise ValueError("No theater links found in the chain directory")
        yield from response.follow_all(sorted(links), callback=self.parse_sd)

    def post_process_item(self, item: Feature, response: Response, ld_data: dict, **kwargs: Any) -> Iterable[Feature]:
        item["ref"] = urlsplit(response.url).path.split("/")[1].rsplit("-", 1)[-1].lower()
        item["website"] = response.url
        apply_category(Categories.CINEMA, item)
        yield item
