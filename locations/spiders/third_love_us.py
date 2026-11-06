import re
from typing import Any, Iterable

from scrapy.http import TextResponse

from locations.categories import Categories, Clothes, apply_category, apply_clothes
from locations.hours import DAYS, OpeningHours, day_range, sanitise_day
from locations.items import Feature
from locations.structured_data_spider import StructuredDataSpider

LOCATOR = "https://www.thirdlove.com/pages/stores"
DETAILS = "Store Details"
# "Mon - Sat: 10am - 8pm", "Mon - Wed: 11 am - 6 pm", "Mon - Sun: 10 am - 9 pm".
RULE = re.compile(
    r"^(?P<days>[A-Za-z]{3,9}(?:\s*[-–—&]\s*[A-Za-z]{3,9})?)\s*:\s*"
    r"(?P<opens>\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?)\s*[-–—]\s*(?P<closes>\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?)$",
    re.IGNORECASE,
)
SPLIT = re.compile(r"\s*[-–—&]\s*")
HEADING = "Hours"


class ThirdLoveUSSpider(StructuredDataSpider):
    name = "third_love_us"
    item_attributes = {"brand": "ThirdLove", "brand_wikidata": "Q54958385"}
    allowed_domains = ["www.thirdlove.com"]
    start_urls = [LOCATOR]
    wanted_types = ["ClothingStore"]
    # The image every store publishes is the same one, store-locator.png, which
    # is the chain's picture rather than the shop's.
    drop_attributes = {"image"}
    # The page states the chain's own accounts and addresses, not a shop's.
    search_for_email = False
    search_for_twitter = False
    search_for_facebook = False
    search_for_instagram = False

    def parse(self, response: TextResponse, **kwargs: Any) -> Iterable[Any]:
        """Follow the shops the locator gives a page of their own.

        The locator lists the four shops that are open and then eight more
        under "Coming Soon", named only by the shopping centre they are to
        stand in - no address, no page. Following the links is what divides
        them: only a shop that is open has one.

        The sitemap is no use here. It lists every page the shop's Shopify
        site has, and the four shops are among them under slugs with nothing
        in common - town-center, westfield-valley-fair,
        thirdlove-bay-area-california.
        """
        found = 0
        for href in response.xpath(f'//a[normalize-space()="{DETAILS}"]/@href').getall():
            found += 1
            yield response.follow(href, callback=self.parse_sd)
        if not found:
            self.logger.error(f'The locator links to no "{DETAILS}" pages, so it has changed')

    def post_process_item(
        self, item: Feature, response: TextResponse, ld_data: dict, **kwargs: Any
    ) -> Iterable[Feature]:
        item["ref"] = response.url.rstrip("/").rsplit("/", 1)[-1]
        # "ThirdLove Town Center", which is the brand and then the shop. None
        # of the four is named for the town it stands in, so all four keep it.
        item["branch"] = (item.pop("name", None) or "").removeprefix("ThirdLove").strip() or None

        # The hours are not in the structured data, which carries the address,
        # the position and the phone but no hours at all.
        item["opening_hours"] = self.hours(response)

        apply_category(Categories.SHOP_CLOTHES, item)
        apply_clothes([Clothes.UNDERWEAR], item)

        yield item

    def hours(self, response: TextResponse) -> OpeningHours:
        """Read the block the shop's page heads "Hours".

        Only that block: the page's footer states when the chain's customer
        service can be reached, "Monday - Sunday 8AM - 7PM PT", which is not
        when the shop is open.
        """
        oh = OpeningHours()
        for line in response.xpath('//div[contains(@class, "store-detail__hours")]//p'):
            stated = re.sub(r"\s+", " ", " ".join(line.xpath(".//text()").getall())).strip()
            if not stated or stated == HEADING:
                continue
            if not (rule := RULE.match(stated)):
                self.logger.warning(f"{response.url} states hours this cannot read: {stated!r}")
                continue
            named = [day for word in SPLIT.split(rule["days"]) if (day := sanitise_day(word))]
            if not named:
                self.logger.warning(f"{response.url} names days this cannot read: {rule['days']!r}")
                continue
            spans = len(named) > 1 and "&" not in rule["days"]
            for day in day_range(named[0], named[-1]) if spans else named:
                oh.add_range(day, self.time(rule["opens"]), self.time(rule["closes"]), "%I:%M %p")

        if not oh.as_opening_hours():
            self.logger.warning(f"{response.url} states no hours this could read")
        elif len(set(oh.day_hours) | oh.days_closed) < len(DAYS):
            self.logger.info(f"{response.url} states nothing for some days of the week")
        return oh

    @staticmethod
    def time(stated: str) -> str:
        """Return "10am", "11 am" or "10:30 pm" in the one shape strptime is given."""
        packed = re.sub(r"[\s.]", "", stated).upper()
        clock, meridiem = packed[:-2], packed[-2:]
        return f"{clock if ':' in clock else clock + ':00'} {meridiem}"
