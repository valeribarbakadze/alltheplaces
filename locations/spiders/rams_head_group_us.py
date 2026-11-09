import re
from typing import AsyncIterator, Iterable
from urllib.parse import urlparse

from scrapy import Request, Selector, Spider
from scrapy.http import Response

from locations.categories import Categories, apply_category
from locations.google_url import extract_google_position
from locations.hours import DAYS, DELIMITERS_EN, NAMED_DAY_RANGES_EN, OpeningHours
from locations.items import Feature
from locations.user_agents import BOT_USER_AGENT_SCRAPY


def host_of(url: str) -> str:
    return (urlparse(url).hostname or "").removeprefix("www.")


class RamsHeadGroupUSSpider(Spider):
    name = "rams_head_group_us"
    item_attributes = {"operator": "Rams Head Group"}
    # On Stage sits behind a cache rule that answers 406 to any User-Agent
    # holding "Mozilla" and serves named crawlers, so the spider gives its own
    # name rather than the default's browser prefix.
    custom_settings = {"USER_AGENT": BOT_USER_AGENT_SCRAPY}

    # The venues are separately branded and each runs its own site on one of
    # three platforms, so the page to read is named per venue. The group's own
    # sitemap is read only to notice a venue this spider does not cover.
    GROUP = "https://www.ramsheadgroup.com/sitemap"
    BENTOBOX = {
        "https://www.ramsheadtavern.com/location/ramsheadtavern/": ("Rams Head Tavern", "american"),
        "https://www.ramsheadroadhouse.com/location/ramsheadroadhouse/": ("Rams Head Roadhouse", "american"),
        "https://www.ramsheaddockside.com/location/rams-head-dockside/": ("Rams Head Dockside", None),
        "https://www.ramsheadshorehouse.com/location/rams-head-shore-house/": ("Rams Head Shore House", None),
    }
    SOUTHERNMOST = "https://ramsheadsouthernmost.com/location/"
    ON_STAGE = "https://www.ramsheadonstage.com/about/contact"
    # Rams Head Presents buys talent for halls other operators own and states
    # only an office address, so it is not a venue of the group's own.
    NOT_VENUES = {"ramsheadgroup.com", "ramsheadpresents.com"}

    LOCALITY = r"(?P<city>[^,]+),\s*(?P<state>[A-Z]{2})\s+(?P<postcode>\d{5})"
    ADDRESS = re.compile(rf"^(?P<street>.+?\w)\W*,\s*{LOCALITY}$")
    LOCALITY_ONLY = re.compile(rf"^{LOCALITY}$")
    PHONE = re.compile(r"^(?:Phone:\s*)?(?P<phone>[\d(][\d\s().+-]{8,})$")
    # "&" joins two days on these sites, which the shared delimiters omit.
    DELIMITERS = DELIMITERS_EN + ["&", "and"]
    NAMED_DAYS = NAMED_DAY_RANGES_EN | {"Every Day": DAYS}

    async def start(self) -> AsyncIterator[Request]:
        yield Request(self.GROUP, callback=self.parse_group)
        for url in self.BENTOBOX:
            yield Request(url, callback=self.parse_bentobox)
        yield Request(self.SOUTHERNMOST, callback=self.parse_southernmost)
        yield Request(self.ON_STAGE, callback=self.parse_on_stage)

    def parse_group(self, response: Response) -> None:
        listed = {host for url in response.xpath("//a/@href").getall() if "ramshead" in (host := host_of(url))}
        covered = {host_of(url) for url in [*self.BENTOBOX, self.SOUTHERNMOST, self.ON_STAGE]}
        if missed := listed - covered - self.NOT_VENUES:
            self.logger.error(f"The group lists venues this spider does not read, so add them: {sorted(missed)}")

    def parse_bentobox(self, response: Response) -> Iterable[Feature]:
        brand, cuisine = self.BENTOBOX[response.url]
        item = Feature(ref=host_of(response.url), brand=brand, website=response.url)
        location = response.xpath("//div[@data-gmaps-lat]")
        self.set_address(item, location.attrib["data-gmaps-address"])
        item["lat"], item["lon"] = location.attrib["data-gmaps-lat"], location.attrib["data-gmaps-lng"]
        item["phone"] = response.xpath('//a[starts-with(@href, "tel:")]/@href').get()
        # Read the hours the page shows: both the structured data and the
        # description meta are stale here.
        item["opening_hours"] = self.read_hours(
            response.xpath('//section[contains(@class, "c-intro")]//p[strong]//text()').getall()
        )
        apply_category(Categories.RESTAURANT, item)
        if cuisine:
            item["extras"]["cuisine"] = cuisine
        yield item

    def parse_southernmost(self, response: Response) -> Iterable[Feature]:
        item = Feature(ref=host_of(response.url), brand="Rams Head Southernmost", website=response.url)
        # This block states the address the venue's own map pin also gives; a
        # second copy higher up the page states a different house number.
        lines = self.lines(response.xpath('//*[normalize-space(text()) = "LOCATION"]/..'))
        self.set_address(item, self.address_from(lines))
        item["phone"] = self.phone(lines)
        extract_google_position(item, response)
        item["opening_hours"] = self.read_hours(self.lines(response.xpath('//*[normalize-space(text()) = "HOURS"]/..')))
        apply_category(Categories.RESTAURANT, item)
        yield item

    def parse_on_stage(self, response: Response) -> Iterable[Feature]:
        item = Feature(ref=host_of(response.url), brand="Rams Head On Stage", website=response.url)
        # The block is recognised by holding an address, which keeps the box
        # office hours beneath it and the footer's spelt-out state out.
        for paragraph in response.xpath("//p"):
            lines = self.lines(paragraph)
            if address := self.address_from(lines):
                self.set_address(item, address)
                item["phone"] = self.phone(lines)
                break
        # The only hours this venue states are its box office's, which are not
        # the hours it opens.
        apply_category(Categories.MUSIC_VENUE, item)
        yield item

    @staticmethod
    def lines(selector: Selector) -> list[str]:
        return [text.strip() for text in selector.xpath(".//text()").getall() if text.strip()]

    def address_from(self, lines: list[str]) -> str | None:
        at = next((i for i, text in enumerate(lines) if i and self.LOCALITY_ONLY.match(text)), None)
        return f"{lines[at - 1]}, {lines[at]}" if at is not None else None

    def phone(self, lines: list[str]) -> str | None:
        return next((match["phone"] for line in lines if (match := self.PHONE.match(line))), None)

    def set_address(self, item: Feature, address: str | None) -> None:
        if address and (match := self.ADDRESS.match(address.strip())):
            item["street_address"], item["city"] = match["street"], match["city"]
            item["state"], item["postcode"] = match["state"], match["postcode"]
        else:
            self.logger.error(f"{item['brand']} states an address this spider cannot read: {address!r}")

    def read_hours(self, texts: list[str]) -> OpeningHours:
        hours = OpeningHours()
        hours.add_ranges_from_string(
            re.sub(r"\s+", " ", " ".join(texts)).strip(),
            named_day_ranges=self.NAMED_DAYS,
            delimiters=self.DELIMITERS,
        )
        return hours
