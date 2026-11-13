from locations.storefinders.toast import ToastSpider


class FriendlyToastUSSpider(ToastSpider):
    name = "friendly_toast_us"
    item_attributes = {"brand": "The Friendly Toast"}
    allowed_domains = ["thefriendlytoast.com"]
    start_urls = ["https://thefriendlytoast.com/locations"]
