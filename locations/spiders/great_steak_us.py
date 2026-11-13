from locations.categories import Categories
from locations.storefinders.kahala import KahalaSpider


class GreatSteakUSSpider(KahalaSpider):
    name = "great_steak_us"
    item_attributes = {"brand": "Great Steak"}
    allowed_domains = ["www.thegreatsteak.com"]
    start_urls = ["https://www.thegreatsteak.com/locator/index.php?brand=8&mode=map"]
    category = Categories.FAST_FOOD
    cuisine = "sandwich"
