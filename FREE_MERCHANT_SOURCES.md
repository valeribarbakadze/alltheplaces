# Free merchant sources

Live runs on November 13, 2026 collected **338 source-listed locations for 16 of
the 41 supplied merchants**. Of those records, 301 have coordinates and 37 are
address-only. These are review snapshots, not independently confirmed operating
store counts. No paid service or proxy was used.

## Run again each month

From the repository root, with the project dependencies installed:

```sh
uv run python contrib/run_free_merchant_spiders.py --output out/free-merchants-2026-12
```

Use a new directory for each run. The runner refuses to overwrite a previous
snapshot. It saves one GeoJSON per spider, `run.json` with counts and crawl
statistics, and `crawl.log`. It exits with a failure if any source is empty or
has detected crawl errors. Inspect all source results before accepting a run.
It does not automatically replace a last-good dataset.

To run one source:

```sh
uv run python contrib/run_free_merchant_spiders.py --output out/fresco-check --spiders fresco_y_mas_snap_us
```

Compare accepted snapshots by `@spider` and `ref`. Every spider re-enumerates its
source rather than revisiting a fixed list of known branches. A new reference is
**newly observed**, not a confirmed opening date. A missing reference, especially
from an ordering, SNAP or ticketing feed, does not establish permanent closure.
Investigate a sharp count drop before replacing accepted data.

The registry `contrib/free_merchant_sources.json` connects each spider to the
original merchant ID and states its coverage limits. All 16 also appear in the
branch's main `spiders.txt`. No schedule has been created.

## Passing live collectors

| Merchant | Spider | Records | With coordinates | Source and limits |
| --- | --- | ---: | ---: | --- |
| BodyBrite | `bodybrite_ca_us` | 17 | 17 | [Merchant map](https://bodybriteusa.com/locations/); 15 US and 2 Canadian branches; reads a fresh public nonce each run. |
| Cool Hand Luke's | `cool_hand_lukes_us` | 6 | 0 | [Merchant directory](https://coolhandlukes.com/locations/); address and phone. |
| El Gaucho | `el_gaucho_us` | 6 | 0 | [Merchant navigation](https://elgaucho.com/); El Gaucho-branded restaurants, excluding sister concepts. |
| Fresco y Más | `fresco_y_mas_snap_us` | 25 | 25 | [USDA SNAP layer](https://services1.arcgis.com/RLQu0rK7h4kbsBq5/arcgis/rest/services/snap_retailer_location_data/FeatureServer/0); SNAP-authorized Florida stores only. May lag openings. |
| The Friendly Toast | `friendly_toast_us` | 14 | 14 | [Merchant directory](https://thefriendlytoast.com/locations); embedded Toast location records. |
| Frullati | `frullati_us` | 8 | 8 | [Merchant-hosted locator](https://www.frullati.com/locator/index.php?brand=5&mode=map). |
| Gofer Ice Cream | `gofer_ice_cream_us` | 7 | 0 | [Merchant directory](https://gofericecream.com/locations/); addresses retained, unreliable map coordinates omitted. |
| The Great Greek Grill | `great_greek_grill_us` | 95 | 95 | [Ordering network](https://orders.thegreatgreekgrill.com/); US participants, completeness unverified. |
| Great Steak | `great_steak_us` | 21 | 21 | [Merchant-hosted locator](https://www.thegreatsteak.com/locator/index.php?brand=8&mode=map); includes two temporary closures. |
| Hash House a Go Go | `hash_house_a_go_go_us` | 8 | 0 | [Merchant directory](https://www.hashhouseagogo.com/locations/); addresses and phone. |
| Jalapeno Tree | `jalapeno_tree_us` | 15 | 15 | [Merchant directory](https://jalapenotree.com/restaurants-locations/); restaurant JSON-LD and map fallback. |
| NrGize Lifestyle Cafe | `nrgize_us` | 54 | 54 | [Merchant locator](https://www.nrgizejuice.com/locator/); includes one temporary closure. |
| Pizza Shoppe | `pizza_shoppe_us` | 14 | 14 | [Merchant map](https://pizzashoppe.com/locations/); read-only WordPress feed. |
| Studio Movie Grill | `studio_movie_grill_fandango_us` | 18 | 18 | [Fandango directory](https://www.fandango.com/movie-theaters/studio-movie-grill); ticketing partner coverage, completeness unverified. |
| T.O. Haas Tire & Auto | `to_haas_tire_and_auto_us` | 20 | 20 | [Merchant directory](https://www.tohaastire.com/locations); follows current branch pages. |
| Willie Jewell's | `willie_jewells_us` | 10 | 0 | [Merchant page](https://williejewells.com/locations/); deduplicated by phone; Peachtree City needs review. |

## Specific data issues

- Great Steak refs `7634` and `7145`, and NrGize ref `2682`, are marked temporarily
  closed by the source. Their `opening_hours` is `Mo-Su closed`; do not interpret
  these as permanent closures.
- Willie Jewell's Peachtree City ref `7707311926` appears only in a secondary
  location section. It is included for review and must not be assumed active.
- Gofer's Cos Cob and Darien pages reuse the same numeric map coordinates.
  Gofer emits addresses only until the map data can be trusted. Seasonal listings
  also do not confirm current trading status.
- Jalapeno Tree Tyler has no geometry in its Restaurant JSON-LD. Its published
  Google map embed supplies the coordinates. El Gaucho Boise's visible postcode
  is used because its link's title contains a conflicting postcode.
- Toast ordering schedules are omitted: ordering windows can differ from dining
  hours. Unavailable coordinates are left absent, not fabricated or geocoded.

## Other 25 merchants

No unvalidated collector is included in the monthly batch:

- **Blocked in the live Scrapy run (8):** Carolina Ale House, Tarka Indian
  Kitchen, Rock & Brews, Snooze Eatery, Pizza Factory, Golden Krust, El Tiempo
  Cantina and the candidate Guapo's Cocina & Bar. Requests returned HTTP 403,
  although some earlier research clients received usable pages. Guapo's also
  needs identity confirmation because the supplied `guapos.com` is unrelated.
- **Source restricts automated scraping (3):** Simon directory alternatives for
  Journeys, Belk and Seasons 52 were not bulk-collected.
- **Discovery incomplete (2):** Sleep Inn has city-search URLs rather than a
  complete working hotel-record route. The Children's Place has usable individual
  store details but its all-store discovery query is blocked.
- **Free merchant feed still unresolved (12):** Omaha Steaks, P.C. Richard & Son,
  CB2, 110 Grill, Tire Warehouse, 4 Wheel Parts, Peachwave Yogurt, Jaggers,
  Moretti's, Village Tavern, Lucy's Pizzeria and Pep Boys. Open-data alternatives
  remain untested for these brands; no coverage is claimed.

The review workbook includes all 41 merchants with these statuses. Blank counts
mean no accepted dataset, not zero locations in the real world. Public access
alone does not establish permission to redistribute a third-party dataset; reuse
terms were not validated in these crawl tests. These collectors belong on the
private merchant branch, not in an upstream pull request.

## Verification

The collectors were run through the project's normal pipelines with robots
handling enabled and no response cache. The final review data has 338 unique
spider/reference pairs and no missing street addresses. Parser and repository
import/attribute tests passed (14 tests). Formatting checks passed for the new
files. All 16 new names pass the naming rule; the repository-wide naming hook
still fails on the pre-existing `IIIForksUSSpider` class, which is outside this
change.
