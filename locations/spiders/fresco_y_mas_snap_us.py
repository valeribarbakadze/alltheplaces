from typing import Iterable
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from scrapy import Request, Spider
from scrapy.http import Response

from locations.categories import Categories, apply_category
from locations.items import Feature


class FrescoYMasSnapUSSpider(Spider):
    name = "fresco_y_mas_snap_us"
    item_attributes = {"brand": "Fresco y M\u00e1s"}
    allowed_domains = ["services1.arcgis.com"]
    start_urls = [
        "https://services1.arcgis.com/RLQu0rK7h4kbsBq5/arcgis/rest/services/"
        "snap_retailer_location_data/FeatureServer/0/query?"
        + urlencode(
            {
                "where": "UPPER(Store_Name) LIKE 'FRESCO Y MAS%'",
                "outFields": "Record_ID,Store_Name,Store_Street_Address,City,State,Zip_Code,Latitude,Longitude",
                "outSR": 4326,
                "f": "geojson",
                "orderByFields": "Record_ID",
                "resultRecordCount": 1000,
                "resultOffset": 0,
            }
        )
    ]

    def parse(self, response: Response) -> Iterable[Feature | Request]:
        data = response.json()
        if "error" in data or "features" not in data:
            raise ValueError("The SNAP service did not return a feature collection")
        features = data["features"]
        if not features:
            raise ValueError("The SNAP service returned an empty page")
        for feature in features:
            location = feature["properties"]
            if not location["Store_Name"].upper().startswith("FRESCO Y MAS") or location["State"] != "FL":
                continue
            item = Feature(
                ref=str(location["Record_ID"]),
                name=location["Store_Name"],
                street_address=location["Store_Street_Address"],
                city=location["City"],
                state=location["State"],
                postcode=location["Zip_Code"],
                country="US",
                lat=location["Latitude"],
                lon=location["Longitude"],
                website="https://www.frescoymas.com/",
            )
            apply_category(Categories.SHOP_SUPERMARKET, item)
            yield item
        if data.get("exceededTransferLimit"):
            parts = urlsplit(response.url)
            params = parse_qs(parts.query)
            params["resultOffset"] = [str(int(params["resultOffset"][0]) + len(features))]
            yield Request(urlunsplit(parts._replace(query=urlencode(params, doseq=True))))
