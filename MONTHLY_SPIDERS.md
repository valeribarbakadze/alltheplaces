# Monthly merchant spiders

A private branch. **Not for submission upstream** — do not open a pull request from it.

## What it is

`upstream/master` plus the spiders that are ours alone. Two kinds live here:

1. Spiders upstream does not have — either not submitted yet, or not suitable for
   All the Places.
2. Spiders that read something other than a merchant's official store locator.
   Upstream only accepts official sources, so these can never go there.

Everything else comes from `upstream/master` and stays maintained by the project.

Spiders go on one at a time, each one run before it is committed.

## Before adding a spider, check upstream by brand

Whether upstream covers a merchant is **not** answered by whether
`locations/spiders/<our_name>.py` exists there. Upstream may file the same
merchant under a different name, or cover it inside a spider that handles a whole
group of brands. Five spiders have been caught by this check rather than by
their file names:

| looked new | upstream already covered it as |
| --- | --- |
| `hot_topic_us` | `hot_topic` |
| `shaws_us` | `albertsons`, which carries 17 brands including Shaw's |
| `foodmaxx_us` | `save_mart_us`, which crawls `foodmaxx.com` |
| `build_a_bear_us` | `build_a_bear_workshop_us` |
| `home_depot_us` | `home_depot`, which reads homedepot.com through a locator host |

So search for the merchant's Wikidata QID and its own domain, not its file name:

```sh
grep -rl "Q578387" locations/spiders/            # the brand's QID
grep -rl "foodmaxx.com" locations/spiders/       # the brand's own domain
```

A hit on either means upstream has the merchant and ours would be a duplicate.

## Adding one

```sh
git checkout monthly-merchant-spiders
git fetch upstream && git rebase upstream/master

# brand check first, per the section above, then:
uv run scrapy crawl <name> -O out.geojson        # prove it collects
echo "<name>" >> spiders.txt
git add locations/spiders/<name>.py spiders.txt
git commit -m "Add <name>"
git push fork monthly-merchant-spiders
```

Forgetting the `spiders.txt` line is the easy mistake: a spider file that is not
on the list is crawled by nothing, and nothing complains about it.

## Keeping it current

Rebase on upstream before each monthly run, so the 5,700-odd upstream spiders and the
shared library come along:

```sh
git fetch upstream
git rebase upstream/master
```

Rebase rather than merge: it keeps our own commits on top and makes it obvious which
files are ours. If a rebase conflicts on a spider we carry a fix for, upstream has
touched the same spider — read both versions before choosing, because upstream's may
already include the fix.

When a spider of ours is merged upstream, drop our copy on the next rebase: upstream's
is the maintained one from then on.

## Running it

One spider:

```sh
uv run scrapy crawl <spider_name> -O output.geojson
```

Every spider on the list, which is what a monthly run means:

```sh
mkdir -p out
grep -vE '^\s*(#|$)' spiders.txt \
  | while read -r s; do uv run scrapy crawl "$s" -O "out/$s.geojson"; done
```

## Testing after a push

This branch opens no pull request, and every upstream workflow is
`on: pull_request` — so nothing upstream runs here, ever. Two ways to check the
spiders instead:

**Locally**, which needs no push at all and is the quicker loop:

```sh
uv run scrapy crawl <spider_name> -O out.geojson
uv run pytest tests/test_item_attributes.py tests/test_spider_imports.py
```

**On a push**, via `.github/workflows/run-our-spiders.yml`, which runs every
spider on the list, keeps each one's geojson and log as a build artifact, prints
a table of counts, and fails if a spider finishes with nothing. That last part is
the signal worth having: a spider whose source has changed under it usually keeps
finishing and quietly stops collecting. It also takes a single spider name from
the "Run workflow" button, for checking one without crawling the lot.

That workflow is for testing. The monthly collection run belongs somewhere built
for it, with a proxy and a schedule — GitHub's hosted runners are meant for a
project's own software, not as a data pipeline.

## What is ours

`git diff --name-only upstream/master -- locations/spiders/` lists it at any time.

| spider | locations | last run |
| --- | --- | --- |
| `the_palm` | 17 | 2026-11-03 |
| `eatzis_us` | 6 | 2026-11-04 |
| `midwood_smokehouse_us` | 6 | 2026-11-04 |
| `seoul_taco_us` | 6 | 2026-11-04 |
| `the_simple_greek_us` | 6 | 2026-11-04 |
| `felipes_mexican_taqueria_us` | 6 | 2026-11-04 |
| `dukes_seafood_us` | 6 | 2026-11-04 |
| `cattle_baron_us` | 6 | 2026-11-04 |
| `natural_body_us` | 5 | 2026-11-04 |
| `mitchells_fish_market_us` | 5 | 2026-11-04 |
| `acme_oyster_house_us` | 5 | 2026-11-04 |
| `arirang_hibachi_steakhouse_us` | 5 | 2026-11-04 |
| `bad_brads_bbq_us` | 5 | 2026-11-05 |
| `burgers_and_beer_us` | 5 | 2026-11-05 |
| `cafe_hollander_us` | 5 | 2026-11-05 |
| `carmines` | 6 | 2026-11-05, 2 of 6 collected |
| `copper_river_grill_us` | 5 | 2026-11-05 |
| `tamollys_mexican_kitchen` | 6 | 2026-11-03 |
| `cyclone_anayas_us` | 5 | 2026-11-03 |

`the_palm` carries no country suffix because one of its 17 restaurants is in Mexico
City; the other 16 are in the US.

`carmines` carries no country suffix either: one of its six restaurants is at
Atlantis in the Bahamas and the other five are in the US. That one states its
country by name rather than by code, which the country code pipeline resolves.
The brand has no Wikidata item, so there is no `brand_wikidata`.

**Only two of its six restaurants have been collected.** Cloudflare began
answering this machine's address with a challenge partway through the work, and
held it over forty minutes of spaced retries, so Times Square and Atlantis were
read and Upper West Side, Atlantic City, Washington DC and Las Vegas were not.
Those two parse correctly end to end. The other four are written against the
same page template but have not been seen, so **check the first run**: it should
collect six, and the spider warns on close if the sitemap yields fewer, warns
per page if an address or a day cannot be read, and records no position rather
than a guessed one. A run from a home address rather than a datacenter one is
not challenged, so running it locally is what will confirm it. It is marked
`requires_proxy` for that reason, though with no `ZYTE_API_KEY` set that is only
a marker - robots.txt allows every crawler but three named SEO ones, so it is
the address's reputation being refused rather than the crawl.

It ignores the Restaurant block the pages publish in structured data, because
that block contradicts the page it sits on. For Times Square it states Monday
11:00 to 23:30 where the page's own table states 11:30 to 23:00, and its
position is 192 metres from the pin the address links to. The block has been
left behind - its map is a dead goo.gl short link and it names the restaurant's
Google+ page - and the Bahamas page carries no block at all. What each page
itself states is current, given per day, and there on all six, so the spider
reads the page: the contact block, the hours table, and the destination pin out
of the Google route its address links to. The Bahamas restaurant states one
range for the whole week in words instead of a table, which is read only where
the words name a range, since the same element elsewhere holds what a
restaurant is open for rather than when.

`cafe_hollander_us` runs at a ten second delay, which is the Crawl-delay both
cafehollander.com and the parent group's site ask for. One page holds all five
restaurants, so that costs nothing. It yields no coordinates: the addresses link
to a Google route stated as text and no map is embedded. All five keep the same
hours, which is what each states for itself.

`burgers_and_beer_us` reads one page of a site built with Wix, found by what it
holds rather than by its name, since the builder names and renames pages itself:
it is called contact-5 today. The page lists a corporate office alongside the
five restaurants, which the spider leaves out because it states a street with no
town, state or postcode - and which repeats one restaurant's position as its own.
The restaurants have no pages of their own, so the items carry no website.

`bad_brads_bbq_us` records what each restaurant's ribbon states it has - dine-in,
a bar, a patio, carryout - which differs between them: one of the five lists only
carryout and catering. A sixth restaurant, in Ferndale, is named in the menu as
opening in the summer of 2026 but has no page, so there is nothing to collect
yet; expect the count to reach six.

`arirang_hibachi_steakhouse_us` carries the brand as the site writes it,
"Arirang Hibachi Steakhouse", without the "& Sushi" the merchant list adds. It
yields no coordinates: the address links to a Google search for itself, naming no
point.

`acme_oyster_house_us` is marked `requires_proxy` for the same reason as
`dukes_seafood_us`, on what looks like the same hosting: an intermittent
SiteGround captcha for datacenter addresses over a permissive robots.txt. It
follows the menu rather than the sitemap, which lists every restaurant twice -
once plainly and once under a slug suffixed with its state - with both copies
carrying the same address and each declaring itself canonical. Crawling the
sitemap would report ten restaurants where there are five.

`mitchells_fish_market_us` carries two brands. Four restaurants are Mitchell's
Fish Market and the fifth trades as Columbus Fish Market, which only the slug of
its page and its own text state - the page title calls every location Mitchell's.
It yields no coordinates: the address links to a Google place by CID, which
carries none.

`natural_body_us` collects five of the seven spas its locator lists. The other
two are not trading - one marked a former location, one shut for a rebuilding
that reopens under another brand - and both state 00:00 to 00:00 for every day,
which is how the spider tells. Expect the count to change as that rebranding
proceeds.

`cattle_baron_us` yields no coordinates: the only map on each page is an embed
that searches Google for the restaurant by name rather than naming a point. It
also publishes 88240 for both Hobbs and Las Cruces, which belongs to one of them
at most, and the spider warns about that when it closes. It runs at a three second
delay, which is what the site's robots.txt asks for.

`dukes_seafood_us` is marked `requires_proxy`. Its host sometimes answers a
datacenter address with a SiteGround captcha instead of the page, naming the
address's reputation as the reason; it refused a run of attempts and then served
twelve requests in a row. It works without a proxy, but some monthly runs will
collect nothing until a Zyte key is configured, and the workflow's empty-run check
is what will say so.

`felipes_mexican_taqueria_us` publishes one position for two different
restaurants, Uptown and Old Metairie, whose addresses are some four kilometres
apart. Both are recorded as published and the spider warns, because the locator
gives nothing to say which of the two the position belongs to.

`copper_river_grill_us` reads the one page that lists the restaurants. The site
answers every path with its home page - /locations and /sitemap_index.xml come
back byte for byte identical to / - so a path returning 200 says nothing, and
the sitemap is what names locations.php. That page lists the five twice: once in
blocks and again in the footer. The spider reads the blocks, because the footer
is wrong about the phones - it states a South Carolina area code for the
Kentucky restaurant in its text, and in its links it repeats two numbers and
puts a third under the wrong area code again.

Its coordinates come from the map each restaurant embeds, which the merchant
publishes through Google My Maps and which the page states nowhere else. Each
map holds a single pin and is named for the restaurant it belongs to, so the
spider checks that name against the block the map sits in and records no
position rather than a guessed one if a map ever holds anything else. All five
pins came back distinct and in the right state. The restaurants have no pages
of their own, so each `website` is the anchor on locations.php that the site's
own menu links them by.

All five state the same hours and all five state Wi-Fi, which is what each
states for itself rather than anything brand-wide. Each block ends with the
name of its operating partner, which the spider leaves alone: it names a person
rather than the place. The brand has no Wikidata item, so there is no
`brand_wikidata`.

`eatzis_us` yields no coordinates. The markets' addresses link to Google places by
CID, which carries no position, and nothing else on the page publishes one, so the
six items are address-only. Worth knowing if a monthly run is matched on position
rather than on address.

Candidates held on per-merchant branches, each checked against upstream by brand
and genuinely absent: `cool_hand_lukes_us` (6). Also clean on that check and ready when wanted:
`abelardos_mexican_food`, `hh_bagels`, `one_stop_nutrition`, `the_great_frame_up`,
`uno_pizzeria_and_grill`.

Brand-checked on 2026-11-06 and genuinely absent upstream: `claim_jumper_us` and
`pc_richard_and_son_us`. Neither domain appears anywhere in `origin/master`, neither
brand appears there by name, and upstream's `landrys_seafood_us` carries only
Landry's Seafood, so it does not cover Claim Jumper the way `albertsons` covers
Shaw's. `home_depot_us` failed the same check and is in the table above.

`claim_jumper_us` is clean on brand and still not for collecting: the site serves a
challenge in place of its robots.txt, so its crawling policy cannot be read at all.
That is not the same as `dukes_seafood_us` or `carmines`, where a permissive
robots.txt reads fine and only a datacenter address is refused. An unreadable policy
is a reason to stop; a refused address is a reason to run from somewhere else.

Needing a Zyte key before they run at all: `pep_boys`, `belk`,
`pc_richard_and_son_us`. Needing Camoufox: `morettis_us`.
