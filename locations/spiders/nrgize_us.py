from locations.categories import Categories
from locations.storefinders.kahala import KahalaSpider


class NrgizeUSSpider(KahalaSpider):
    name = "nrgize_us"
    item_attributes = {"brand": "NrGize Lifestyle Cafe"}
    allowed_domains = ["www.nrgizejuice.com"]
    start_urls = ["https://www.nrgizejuice.com/locator/"]
    category = Categories.CAFE
