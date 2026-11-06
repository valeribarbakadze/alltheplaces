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
| `carmines` | 6 | never run whole; gated, see below |
| `copper_river_grill_us` | 5 | 2026-11-05 |
| `duckworths_grill_and_taphouse_us` | 5 | 2026-11-06 |
| `granville_us` | 5 | 2026-11-06 |
| `karinas_mexican_seafood_us` | 4 | 2026-11-06 |
| `tamollys_mexican_kitchen` | 6 | 2026-11-03 |
| `cyclone_anayas_us` | 5 | 2026-11-03 |

`the_palm` carries no country suffix because one of its 17 restaurants is in Mexico
City; the other 16 are in the US.

`carmines` carries no country suffix either: one of its six restaurants is at
Atlantis in the Bahamas and the other five are in the US. That one states its
country by name rather than by code, which the country code pipeline resolves.
The brand has no Wikidata item, so there is no `brand_wikidata`.

**As it stands this spider collects nothing, and two of its six restaurants are
all that has ever been read.** Cloudflare served the pages to a plain client at
first - Times Square and Atlantis were fetched and parse correctly end to end -
and then began challenging, and has not stopped. The first diagnosis here was
that a datacenter address was being refused and that a run from a home network
would collect normally. That was wrong, and testing on 2026-11-06 from two
different networks disproved it: a plain request gets 403 from both. The
challenge is Cloudflare's managed kind, which answers any client that does not
run JavaScript, so `scrapy crawl carmines` returns nothing wherever it runs.

The parser is sound on what it has seen and the remaining four pages are written
against the same template, but they have never been fetched. To collect this at
all the pages have to come through something that runs JavaScript: a
`ZYTE_API_KEY`, which is what the `requires_proxy` marker already asks for, or
Camoufox, which upstream uses for 27 spiders. Nothing about the site's stated
policy is the obstacle - robots.txt allows every crawler but three named SEO
ones. The obstacle is the gate in front of it.

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

`duckworths_grill_and_taphouse_us` follows the locator rather than the
sitemap, which lists a beer list for each restaurant but none of the restaurants
themselves. Their pages sit under /location/ where the locator sits under
/locations/. Nothing is published in structured data: the one ld+json block on
every page is an empty object.

Its coordinates come from the street level view each page embeds, so they give the
point the photograph was taken from - out on the road - rather than the building.
That is the only position published: the address links to a Google place by CID,
which carries none. ATP's own `extract_google_position` reads these, and all five
came back distinct and in the right part of North Carolina.

Four of the five are headed in capitals, which is styling rather than spelling, so
a heading in capitals is recorded in the ordinary case; SouthPark is not in capitals
and keeps its own. Huntersville and Mooresville are headed with the town they stand
in, which the address already states, so those two carry no `branch`. Each
restaurant keeps its own Facebook page, which is recorded; the Instagram account in
the same block is the chain's and is not. All five state the same hours, which is
what each states for itself. Each also states that reservations are accepted Monday
to Thursday, which is not recorded - the tag cannot say "on four days", and a plain
yes would claim three days the restaurant does not. The brand has no Wikidata item,
so there is no `brand_wikidata`.

Third-party directories list a sixth restaurant at Ballantyne that the locator does
not. Rea Farms stands in that part of Charlotte, so it may be the same place under
an older name; the spider collects what the locator publishes, which is five.

`granville_us` reads the home page, which is also where the menu's "Contact &
Locations" points - the sitemap lists eight pages and no locator among them. The
page is built with Wix, which writes each restaurant as two blocks in a row: one
holding nothing but a heading, the next holding the hours, address, phone and
email. The spider pairs them by that order and takes a pair only where the
second block states an address, so a heading that is not a restaurant's is
passed over.

Wix also breaks a line across spans wherever its styling changes, so the text
of a block has to be joined with nothing between its parts rather than with
spaces. Joined with spaces, three of the five addresses come out misspelt -
"11136 Magnolia Blv d", "2 70 South Lake Ave" - and so do the hours, as
"10p m". That is why the spider has its own text helper instead of the usual
one.

**It records no coordinates, deliberately.** Every one of the five blocks links
its first line to the same Google place, the Burbank restaurant's, so the link
inside a block says nothing about the restaurant the block is for: a spider that
read it would put all five at one point. Three blocks carry a second link of
their own, but those name a map centred at zoom 15 rather than a pin, and the
other two carry none. A page whose links have been pasted about like that is not
one to take a position from, so the five items are address-only. Do not "fix"
this by picking up the link in the block.

The addresses themselves are written two ways: four put the street and the town
on one line with no comma between them, and North Hollywood gives the street a
line of its own. The town is found by matching the heading against the end of
the line, so the street is whatever stands before it. Four restaurants link
their phone number and North Hollywood writes it as plain text, which is read
from the line it heads "Tel:". Pasadena states "No Reservations. First-Come,
First-Served" where the other four state "Walk-In or Reservations", so that one
carries `reservation=no` and the rest `yes` - stated outright on both sides
rather than merely left unsaid. The page's happy hour and weekend brunch are
left out of the hours. No cuisine is recorded: the site calls the food
"globally-inspired" and names no kitchen. The brand has no Wikidata item, so
there is no `brand_wikidata`, and GRANVILLE is in capitals because that is how
the brand writes itself, in its own structured data and its logo alike.

`karinas_mexican_seafood_us` carries three brands across four restaurants.
Bonita and Otay Ranch trade as Karina's Mexican Seafood, the Gaslamp Quarter one
as Karina's Cantina, and the Mission Hills one as Karina's Ceviches & More. Each
page says so only in its own prose - "Karina's Mexican Seafood in Bonita", "the
vibrant and lively atmosphere of Karina's Cantina", "Karina's Ceviches & More
offers casual al fresco or to go dining" - and nowhere a machine can read it, so
the spider holds the three names against the four page slugs and warns if the
site ever adds a fifth it does not know the name of. The group calls itself
Karina's Seafood, in its page titles and its notice of copyright, which is not
what any one of the four trades as. Each map embed searches Google for a
different one of the three names, which is the other sign of the split.

It runs at a twenty second delay, which is what robots.txt asks for and all it
asks for. Following the menu rather than the sitemap keeps the crawl to five
requests, so it finishes in a little over two minutes; reading the sixteen pages
the sitemap lists to find the four would take five.

It yields no coordinates: the only map on a page is an embed that searches Google
for the restaurant by name, which names no point.

The hours need care on both counts the page gets wrong. Notes on when the
kitchen shuts sit between the rules at the Gaslamp one - "Monday - Thursday
12pm-11:30pm", "*Kitchen closes 10:45pm", "Friday-Sunday 12pm-2am" - so those
lines are passed over rather than stopping the reading. The happy hour comes
last and runs over as many as three paragraphs of which only the first names it:
"Happy Hour All Day", "Monday and 3pm-6pm", "Tuesday-Sunday". Reading stops at
the paragraph that names it, because skipping only that one would let "Monday
and 3pm-6pm" through as a rule. Two of the four shut after midnight, which ATP
splits across the days by itself - Otay Ranch comes out as
`Fr 11:00-24:00; Sa 00:00-01:00,11:00-24:00`.

What each ribbon states is recorded and it differs between them: the Mission
Hills one lists neither a bar nor private events where the other three list
both. Private events are not recorded, being a service rather than something the
place holds. Only the Gaslamp one gives an address of its own. None of the four
links its phone number, so it is read from beside the telephone icon. No brand
here has a Wikidata item, so none carries `brand_wikidata`.

Worth watching: the local press has the group opening a seventh restaurant, and
this site's menu lists four. Either the others trade under names that are not
Karina's or they are listed somewhere this spider does not read, so do not take
four as the whole of the group.

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

## Merchants whose robots.txt refuses this assistant

Some sites name Anthropic's crawlers - `ClaudeBot`, `anthropic-ai`, `Claude-Web` -
and disallow them, while allowing everything else under `User-agent: *`. On those,
the spider can be written and run from here but the pages cannot be collected from
here, so the content has to come from a crawl you run yourself.

| merchant | robots.txt |
| --- | --- |
| Frozen Ropes, `frozenropes.com` | disallows the three named Anthropic agents |
| Dos Caminos, `doscaminos.com` | same, plus a Cloudflare-managed block on 30-odd other AI crawlers; `User-agent: *` is `Allow: /` with `Content-Signal: search=yes,ai-train=no,use=reference` |

Neither is a duplicate: checked 2026-11-06 against `origin/master` by domain and by
name, and for Dos Caminos by its parent group BR Guest Hospitality and its sibling
brands as well. Both are absent.

This is a different thing again from `claim_jumper_us`, where the policy cannot be
read, and from `dukes_seafood_us` and `carmines`, where it reads permissive and only
a datacenter address is refused. Here the policy reads clearly and names us.
