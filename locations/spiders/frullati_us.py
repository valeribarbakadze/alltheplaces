from locations.categories import Categories
from locations.storefinders.kahala import KahalaSpider


class FrullatiUSSpider(KahalaSpider):
    name = "frullati_us"
    item_attributes = {"brand": "Frullati Cafe & Bakery"}
    allowed_domains = ["www.frullati.com"]
    start_urls = ["https://www.frullati.com/locator/index.php?brand=5&mode=map"]
    category = Categories.CAFE
