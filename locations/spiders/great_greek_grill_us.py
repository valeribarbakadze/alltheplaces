from locations.storefinders.toast import ToastSpider


class GreatGreekGrillUSSpider(ToastSpider):
    name = "great_greek_grill_us"
    item_attributes = {"brand": "The Great Greek Mediterranean Grill"}
    allowed_domains = ["orders.thegreatgreekgrill.com"]
    start_urls = ["https://orders.thegreatgreekgrill.com/"]
    cuisine = "greek"
