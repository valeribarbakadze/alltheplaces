import json

import pytest
from scrapy.http import HtmlResponse

from locations.items import Feature
from locations.spiders.bodybrite_ca_us import BodybriteCAUSSpider
from locations.spiders.el_gaucho_us import ElGauchoUSSpider
from locations.spiders.fresco_y_mas_snap_us import FrescoYMasSnapUSSpider
from locations.spiders.gofer_ice_cream_us import GoferIceCreamUSSpider
from locations.spiders.jalapeno_tree_us import JalapenoTreeUSSpider
from locations.storefinders.kahala import KahalaSpider
from locations.storefinders.toast import ToastSpider


def response(body, url="https://example.com/"):
    return HtmlResponse(url=url, body=body.encode(), encoding="utf-8")


def test_kahala_skips_future_branches_and_preserves_temporary_closure():
    location = dict(StoreId="1", Address="1 Main St", City="Town", State="TX", Zip="75001", Latitude=32, Longitude=-96)
    html = "".join(
        f"Locator.stores[{index}] = {json.dumps(dict(location, StoreId=str(index), StoreStatusId=status))};"
        for index, status in enumerate(["O", "TC", "CS"])
    )
    items = list(KahalaSpider(name="test").parse(response(html)))
    assert [item["ref"] for item in items] == ["0", "1"]
    assert "opening_hours" not in items[0]
    assert items[1]["opening_hours"].as_opening_hours() == "Mo-Su closed"


def test_toast_uses_location_coordinates_but_not_ordering_hours():
    state = {
        "RestaurantLocation:us": dict(
            id="us",
            name="Branch",
            country="US",
            shortUrl="branch",
            lat=32,
            long=-96,
            address1="1 Main St",
            schedule={"monday": "05:00-22:00"},
        ),
        "RestaurantLocation:ca": dict(id="ca", country="CA"),
        "Restaurant:group": dict(name="Not a branch"),
    }
    items = list(
        ToastSpider(name="test").parse(
            response("<script>window.__APOLLO_STATE__ = " + json.dumps(state) + ";</script>")
        )
    )
    assert len(items) == 1
    assert items[0]["lat"] == 32
    assert items[0]["website"] == "https://example.com/order/branch"
    assert "opening_hours" not in items[0]


@pytest.mark.parametrize("spider", [KahalaSpider, ToastSpider])
def test_missing_payload_is_an_error_instead_of_a_successful_empty_snapshot(spider):
    with pytest.raises(ValueError):
        list(spider(name="test").parse(response("<html>Security check</html>")))


def test_el_gaucho_uses_visible_postcode_and_one_address_copy():
    address = '<a href="https://maps.app.goo.gl/test" title="Boise ID 93702">610 W Idaho Street<br>Boise, ID 83702</a>'
    item = list(ElGauchoUSSpider().parse_location(response(address * 2, "https://elgaucho.com/boise/")))[0]
    assert item["street_address"] == "610 W Idaho Street"
    assert item["postcode"] == "83702"


def test_bodybrite_gets_a_fresh_nonce_from_the_public_page():
    config = {"ajax_url": "https://bodybriteusa.com/wp-admin/admin-ajax.php", "nonce": "fresh-for-this-page"}
    request = list(
        BodybriteCAUSSpider().parse(response("<script>var ASL_REMOTE = " + json.dumps(config) + ";</script>"))
    )[0]
    assert "nonce=fresh-for-this-page" in request.url
    assert "load_all=1" in request.url


def test_bodybrite_preserves_canadian_country_in_the_mixed_country_feed():
    location = dict(
        id="30",
        title="BodyBrite Mississauga",
        street="1900 Fowler Drive D102",
        city="Mississauga",
        state="Ontario",
        postal_code="L5K 1T7",
        country="Canada",
        lat="43.5271553",
        lng="-79.6502544",
    )
    item = list(BodybriteCAUSSpider().parse_locations(response(json.dumps([location]))))[0]
    assert item["country"] == "Canada"
    assert item["postcode"] == "L5K 1T7"


def test_snap_filters_other_brands_and_follows_transfer_limit():
    location = dict(
        Record_ID=1,
        Store_Name="Fresco Y Mas 101",
        Store_Street_Address="1 Main St",
        City="Miami",
        State="FL",
        Zip_Code="33101",
        Latitude=25,
        Longitude=-80,
    )
    data = {
        "features": [{"properties": location}, {"properties": dict(location, Store_Name="Other Fresco")}],
        "exceededTransferLimit": True,
    }
    spider = FrescoYMasSnapUSSpider()
    items = list(spider.parse(response(json.dumps(data), spider.start_urls[0])))
    assert len(items) == 2
    assert items[0]["ref"] == "1"
    assert "resultOffset=2" in items[1].url


def test_jalapeno_tree_falls_back_to_the_published_map_if_json_ld_has_no_geo():
    page = response(
        '<iframe src="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3372!2d-95.30888!3d32.30245"></iframe>',
        "https://jalapenotree.com/locations/tyler/",
    )
    item = list(JalapenoTreeUSSpider().post_process_item(Feature(), page, {}))[0]
    assert (item["lat"], item["lon"]) == (32.30245, -95.30888)


def test_gofer_does_not_export_reused_map_coordinates():
    page = response(
        "<h1>551 East Putnam Ave</h1><h2>Cos Cob, CT 06807</h2>"
        '<iframe src="https://www.google.com/maps/embed?pb=!1m14!1m8!1m3!1d6015!2d-73.471919!3d41.075345"></iframe>',
        "https://gofericecream.com/project/551-east-putnam/",
    )
    item = list(GoferIceCreamUSSpider().parse_location(page))[0]
    assert item["city"] == "Cos Cob"
    assert "lat" not in item and "lon" not in item
