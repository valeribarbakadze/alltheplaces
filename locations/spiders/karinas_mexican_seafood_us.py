import re
from typing import Any, Iterable

from scrapy import Spider
from scrapy.http import Response

from locations.categories import Categories, Extras, apply_category, apply_yes_no
from locations.hours import DAYS, OpeningHours, day_range, sanitise_day
from locations.items import Feature

LOCATOR = "https://www.karinasseafood.com/"
# The menu heads the restaurants with this, and lists them in the panel below.
CHOOSE = "CHOOSE A LOCATION"
# "Chula Vista, CA 91910", written on its own line below the street.
LOCALITY = re.compile(r"^(?P<city>[A-Za-z .'-]+),\s*(?P<state>[A-Z]{2})\s+(?P<postcode>\d{5})$")
# "Sunday - Thursday 11am to 10pm", "Friday-Sunday 12pm-2am", "Daily 11am to
# 9pm". The days are spanned with a dash and paired with an ampersand, and the
# times are divided either way.
RULE = re.compile(
    r"^(?P<days>daily|[A-Za-z]{3,9}(?:\s*(?:[-–]|&|and)\s*[A-Za-z]{3,9})?)\s+"
    r"(?P<opens>\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?)\s*(?:[-–]|to)\s*"
    r"(?P<closes>\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?)$",
    re.IGNORECASE,
)
PAIR = re.compile(r"&|\band\b", re.IGNORECASE)
EVERY_DAY = re.compile(r"^daily$", re.IGNORECASE)
# The happy hour is stated last and runs over as many as three paragraphs, only
# the first of which names it: "Happy Hour All Day", "Monday and 3pm-6pm",
# "Tuesday-Sunday". So the reading stops here rather than skipping a line.
PROMOTION = re.compile(r"happy hour", re.IGNORECASE)
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
# What the ribbon beneath the description states each restaurant has. Events are
# listed too, which is a service rather than something the place holds.
RIBBON = {
    "DINE IN": Extras.INDOOR_SEATING,
    "BAR": Extras.BAR,
    "TO GO": Extras.TAKEAWAY,
    "PATIO": Extras.OUTDOOR_SEATING,
}
# The four restaurants trade under three names, which each page states in its
# own description and nowhere a machine can read: "Karina's Mexican Seafood in
# Bonita", "the vibrant and lively atmosphere of Karina's Cantina", "Karina's
# Ceviches & More offers casual al fresco or to go dining". The group calls
# itself Karina's Seafood, which is the name in the page titles and the notice
# of copyright, and is not what any one of them trades as.
BRANDS = {
    "bonita": {"brand": "Karina's Mexican Seafood", "cuisine": "mexican;seafood"},
    "otay-ranch": {"brand": "Karina's Mexican Seafood", "cuisine": "mexican;seafood"},
    "gaslamp-quarter": {"brand": "Karina's Cantina", "cuisine": "mexican"},
    "mission-hills": {"brand": "Karina's Ceviches & More", "cuisine": "mexican;seafood"},
}
GROUP = "Karina's Seafood"


class KarinasMexicanSeafoodUSSpider(Spider):
    name = "karinas_mexican_seafood_us"
    allowed_domains = ["www.karinasseafood.com", "karinasseafood.com"]
    start_urls = [LOCATOR]
    # robots.txt asks for twenty seconds between requests, which is all it asks
    # for. Five requests collect the lot, so the crawl costs under two minutes.
    custom_settings = {"DOWNLOAD_DELAY": 20}

    def parse(self, response: Response, **kwargs: Any) -> Iterable[Any]:
        """Follow the restaurants the menu lists under "Choose a location".

        The sitemap lists sixteen pages and marks none of them as a
        restaurant's, so the menu is what names them. Following it also keeps
        the crawl to five requests, which matters at twenty seconds apiece.
        """
        found = 0
        for url in response.xpath(f'//a[normalize-space()="{CHOOSE}"]/following-sibling::ul[1]//a/@href').getall():
            found += 1
            yield response.follow(url, callback=self.parse_location)
        if not found:
            self.logger.error(f'The menu holds no "{CHOOSE}" panel, so the site has changed')

    def parse_location(self, response: Response, **kwargs: Any) -> Iterable[Feature]:
        """Read the restaurant the page states.

        Nothing is published in structured data at all, so the page's own
        widgets are what state the restaurant: a heading, a paragraph holding
        the address over two lines, a box holding the phone number, and the
        paragraphs beneath "Opening Hours".
        """
        lines = next(
            (
                found
                for paragraph in response.xpath('//div[contains(@class, "elementor-widget-text-editor")]//p')
                if len(found := [text for raw in paragraph.xpath("./text()").getall() if (text := self.clean(raw))]) > 1
                and LOCALITY.match(found[-1])
            ),
            None,
        )
        if not lines:
            self.logger.warning(f"{response.url} states no address this could read")
            return
        stated = LOCALITY.match(lines[-1])

        item = Feature()
        item["ref"] = response.url.rstrip("/").rsplit("/", 1)[-1]
        item["website"] = response.url
        item["street_address"] = " ".join(lines[:-1])
        item["city"] = stated["city"]
        item["state"] = stated["state"]
        item["postcode"] = stated["postcode"]
        item["country"] = "US"
        # The page is headed with the restaurant's own name, which is the
        # neighbourhood or the centre it stands in rather than the town: two of
        # the four stand in Chula Vista and two in San Diego.
        item["branch"] = self.clean("".join(response.xpath("(//h1)[1]//text()").getall())) or None

        if known := BRANDS.get(item["ref"]):
            item["brand"] = known["brand"]
            item["extras"]["cuisine"] = known["cuisine"]
        else:
            # A restaurant the site has added since. The group's name is the
            # most that can be said of it without reading the page's prose.
            item["brand"] = GROUP
            self.logger.warning(f"{item['ref']} is not a restaurant this knows the trading name of")

        # The number beside the telephone icon. No restaurant links it.
        contact = response.xpath(
            '//div[contains(@class, "elementor-widget-icon-box")][.//i[contains(@class, "fa-phone")]]'
            '//*[contains(@class, "elementor-icon-box-title")]'
        )
        item["phone"] = self.clean("".join(contact.xpath(".//text()").getall())) or None
        if not item["phone"]:
            self.logger.warning(f"{response.url} states no phone number this could read")

        # One of the four gives an address of its own, in the same block.
        listed = self.clean(
            " ".join(response.xpath('//div[contains(@class, "elementor-widget-icon-list")]//text()').getall())
        )
        if found := EMAIL.search(listed):
            item["email"] = found.group(0)

        # No position: the only map is an embed that searches Google for the
        # restaurant by name, which names no point.
        item["opening_hours"] = self.hours(response)

        # Only what the ribbon states is recorded, and it differs between them:
        # one of the four lists neither a bar nor private events.
        offered = {
            self.clean("".join(h.xpath(".//text()").getall())) for h in response.xpath("//h2|//h3|//h4|//h5|//h6")
        }
        for stated_feature, tag in RIBBON.items():
            if stated_feature in offered:
                apply_yes_no(tag, item, True)

        apply_category(Categories.RESTAURANT, item)

        yield item

    @staticmethod
    def clean(value: str) -> str:
        return re.sub(r"[\s ​]+", " ", value).strip()

    def hours(self, response: Response) -> OpeningHours:
        """Read the paragraphs beneath "Opening Hours".

        Two kinds of line stand among the rules. Notes on when the kitchen
        shuts - "*Kitchen closes 10:45pm", "(Food served until 10:30pm)" - sit
        between the rules at one restaurant, so those are passed over. The
        happy hour comes last and runs over up to three paragraphs, of which
        only the first names it, so the reading stops at that one instead.
        """
        oh = OpeningHours()
        panel = response.xpath(
            '//h1[normalize-space()="Opening Hours"]/ancestor::div[contains(@class, "elementor-element")][1]'
            '/following::div[contains(@class, "elementor-widget-text-editor")][1]'
        )
        for paragraph in panel.xpath(".//p"):
            line = self.clean("".join(paragraph.xpath(".//text()").getall()))
            if PROMOTION.search(line):
                break
            if not (rule := RULE.match(line)):
                continue
            if EVERY_DAY.match(rule["days"]):
                days = list(DAYS)
            else:
                named = [day for word in re.split(r"[-–&]|\band\b", rule["days"]) if (day := sanitise_day(word))]
                if not named:
                    continue
                spans = len(named) > 1 and not PAIR.search(rule["days"])
                days = day_range(named[0], named[-1]) if spans else named
            for day in days:
                oh.add_range(day, self.time(rule["opens"]), self.time(rule["closes"]), "%I:%M %p")

        if not oh.as_opening_hours():
            self.logger.warning(f"{response.url} states no hours this could read")
        elif len(set(oh.day_hours) | oh.days_closed) < len(DAYS):
            self.logger.info(f"{response.url} states nothing for some days of the week")
        return oh

    @staticmethod
    def time(stated: str) -> str:
        """Return "11am" or "11:30pm" in the one shape strptime is given."""
        packed = re.sub(r"[\s.]", "", stated).upper()
        clock, meridiem = packed[:-2], packed[-2:]
        return f"{clock if ':' in clock else clock + ':00'} {meridiem}"
