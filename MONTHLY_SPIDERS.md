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
| `stefaninas_pizzeria_us` | 4 | 2026-11-10 |
| `the_simple_greek_us` | 6 | 2026-11-04 |
| `felipes_mexican_taqueria_us` | 6 | 2026-11-04 |
| `dukes_seafood_us` | 6 | 2026-11-04 |
| `cattle_baron_us` | 6 | 2026-11-04 |
| `natural_body_us` | 5 | 2026-11-04 |
| `mitchells_fish_market_us` | 5 | 2026-11-04 |
| `acme_oyster_house_us` | 5 | 2026-11-04 |
| `aquarium_restaurants_us` | 4 | 2026-11-09 |
| `arirang_hibachi_steakhouse_us` | 5 | 2026-11-04 |
| `bad_brads_bbq_us` | 5 | 2026-11-05 |
| `bulldog_ale_house_us` | 1 | 2026-11-09 |
| `burgers_and_beer_us` | 5 | 2026-11-05 |
| `cactus_restaurants_us` | 6 | 2026-11-10 |
| `cafe_hollander_us` | 5 | 2026-11-05 |
| `carmines` | 6 | never run whole; gated, see below |
| `copper_river_grill_us` | 5 | 2026-11-05 |
| `duckworths_grill_and_taphouse_us` | 5 | 2026-11-06 |
| `granville_us` | 5 | 2026-11-06 |
| `grotto_ristorante_us` | 4 | 2026-11-10 |
| `grove_wine_bar_and_kitchen_us` | 4 | 2026-11-10 |
| `heavenly_massage_us` | 5 | 2026-11-07 |
| `hoffbrau_steak_and_grill_house_us` | 4 | 2026-11-10 |
| `james_coney_island_us` | 5 | 2026-11-07 |
| `karinas_mexican_seafood_us` | 4 | 2026-11-06 |
| `kirbys_steakhouse_us` | 4 | 2026-11-10 |
| `new_orleans_hamburger_and_seafood_us` | 5 | 2026-11-09 |
| `on_the_border_us` | 4 | 2026-11-09 |
| `raffertys_pizza_us` | 4 | 2026-11-10 |
| `rams_head_group_us` | 6 | 2026-11-09 |
| `roka_akor_us` | 5 | 2026-11-06 |
| `strip_house_us` | 4 | 2026-11-10 |
| `the_post_sports_bar_and_grill_us` | 4 | 2026-11-10 |
| `third_love_us` | 4 | 2026-11-06 |
| `tom_and_chee_us` | 5 | 2026-11-06 |
| `tortas_manantial_us` | 4 | 2026-11-10 |
| `walnut_grill_us` | 3 | 2026-11-10 |
| `wildberry_cafe_us` | 5 | 2026-11-06 |
| `yafo_kitchen_us` | 4 | 2026-11-10 |
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

**`roka_akor_us` ignores the site's structured data, which is not to be
trusted.** Every page carries a Restaurant block listing all five restaurants
at once, and it is wrong in ways that would have been copied straight into the
output had the usual `LinkedDataParser` been pointed at it:

- every telephone number in it ends 123-4567 - 480-123-4567, 312-123-4567,
  415-123-4567 and so on - which is a placeholder, not a number;
- it puts the Chicago restaurant at 111 West Illinois Street where the page
  states 456 N Clark St, and numbers the Old Orchard one 4905 where the page
  states 4999;
- its hours are the chain's rather than each restaurant's, and only two of the
  five location nodes carry hours of their own at all;
- it quotes a review count of 75,018, images at /logo.png and /wagyu-steak.jpg,
  a Yelp address of yelp.com/biz/roka-akor, and a menu with prices and calorie
  counts.

The pages themselves are maintained and correct, so the spider reads those: the
block headed "Locations" for the address and phone, and the one headed "Hours".
Do not "simplify" this spider onto the ld+json.

The hours are written five ways between the five restaurants, and only the
dining room's are the restaurant's own. Four of them head each set with what it
is for - "Dining", "Dining Room", "Takeout", "Take Out & Delivery", "Happy
Hour" - and give the days and times beneath, over two lines or on one divided
by a bullet. The happy hour is stated **first** at Oak Brook, so the spider
follows the headings rather than stopping at the first set that is not the
dining room's. San Francisco heads nothing and instead names what each line is
for: "Monday - Thursday", "Lounge: 4:30pm - 9:30pm", "Dining Room: 5:00pm -
9:00pm". So every line is asked what it is for before what it says, and the
lounge, the takeaway and the happy hour are all left out. "Monday - Thursday &
Sunday" holds a span and a separate day at once, which is why the days are read
by splitting on the ampersand first.

Four of the five give a position, taken from the route the DIRECTIONS link ends
at. Scottsdale's link goes to google.com.ua and names no point, so that one has
no position and the spider warns; the map each page embeds is an address search,
which names none either. Only the Old Orchard restaurant carries a `branch`: the
other four are named for the town their address already states. The brand has no
Wikidata item, so there is no `brand_wikidata`.

`tom_and_chee_us` is the easy kind: the SOCi locator at
locations.tomandchee.com publishes a complete Restaurant block per restaurant -
address with country, real phone, real position, hours by the day - so the
spider is a `StructuredDataSpider` over the locator's own sitemap and little
else. Both robots.txt files, the site's and the locator's, allow everything.

Getting to the locator is the only awkward part. tomandchee.com publishes no
sitemap, its locator page holds no restaurants (SOCi draws them in afterwards),
and the three state links in its own menu - /ky, /oh, /ok - all answer 404. The
locator subdomain is named once in the page source, and its sitemap lists the
five restaurants among nine directory pages. A restaurant's page is one segment
ending in twelve hex characters, which is what the sitemap rule matches; the
captured slug is the ref, because the structured data's own @id is the whole
address. One slug carries an "e121" in front of its state, which is the
locator's doing and is left as published.

Three things on the page are the chain's rather than a restaurant's and are not
collected: contact@goldstarchili.com, which every one of the five states, and
the chain's own Facebook, Twitter and Instagram accounts. That address is a
reminder that Gold Star Chili owns the brand - and the Cincinnati restaurant on
Beechmont Avenue is named "Gold Star + Tom & Chee", trading alongside Gold Star
itself, which is kept as its `branch`. The other four are named for the town
they stand in, so three of those carry no branch; the Oklahoma City one is
named OKC, which is kept, being what the locator calls it.

The restaurant at 6300 Kings Island Drive states every day of the week closed
and publishes no hours at all in its structured data. It stands inside the Kings
Island amusement park, which is shut for the winter - its position falls nearest
Kings Mills - so it is collected as a restaurant that exists but with no hours
rather than seven closed days, which would read as permanent. The spider warns
when it does that. Expect hours to appear there in the spring.

`wildberry_cafe_us` reads the data the locator page was rendered from. The site
is built with Next.js, which sends that data down as a run of JSON string
literals pushed onto one array; the spider joins them back together and takes
the array the locator was handed, counting brackets to lift it whole out of a
much larger structure and stepping over strings so a bracket inside one cannot
close it early. What comes back is better than anything on the page: street,
town, state, postcode, position, phone, status and the hours day by day.

There is nothing else to read. The site publishes no sitemap and no structured
data at all, and its robots.txt answers **404** - a plain one from the site's own
application, not a challenge standing in its way, so by RFC 9309 nothing is asked
of a crawler. That is worth distinguishing from `claim_jumper_us`, where a
challenge sits where robots.txt should be and the policy cannot be read at all.

Two of the five are named "Chicago (Prudential Plaza)" and "Chicago (Water Tower
Place)", so the branch is taken from within the brackets where the part before
them is the town the address already states. The other three are named for their
town alone and carry no branch. The `website` is built from each slug rather than
published in the data; all five were checked and answer with the restaurant's own
page.

Each restaurant publishes a delivery link of its own and four of the five publish
somewhere to book, so those carry `delivery=yes` and `reservation=yes`. The
Prudential Plaza one simply offers no booking link, which is not the same as
stating it takes none, so nothing is recorded against it. The links to order
ahead are left alone, ordering online saying nothing certain about collecting in
person. Dated exceptions - Christmas Day and the like - are published separately
as special_hours and are left there: they name single days and would be wrong by
next year. All five state the same hours, 07:00 to 14:00 every day, which is what
each states for itself.

The brand is recorded as the site titles itself, "Wildberry Pancakes and Cafe",
rather than the shorter Wildberry Cafe of the merchant list; its own map embeds
search Google for "Wildberry Pancakes & Cafe". It has no Wikidata item, so there
is no `brand_wikidata`.

`third_love_us` is the first spider here with a `brand_wikidata`, `Q54958385`.
Every other merchant on this branch turned out to have no Wikidata item at all.
The QID was checked rather than assumed: its one search hit is "ThirdLove,
American lingerie company", and the Wikipedia article behind it gives the
official website as www.thirdlove.com. It is absent from `origin/master`, as are
the domain and the name.

It is also the only shop here rather than a restaurant, so it carries
`shop=clothes` with `clothes=underwear`, as upstream's `bravissimo` does.

The locator lists four shops that are open and then eight more under "Coming
Soon", named only by the shopping centre they are to stand in - Garden State
Plaza, Del Amo, Roosevelt Field and so on - with no address and no page.
Following the "Store Details" links is what divides them, since only an open
shop has one. The sitemap is no help: it lists every page of a Shopify site, and
the four shops sit among them under slugs with nothing in common - town-center,
westfield-valley-fair, thirdlove-bay-area-california. Expect the count to rise as
those eight open.

Each shop's page carries a complete ClothingStore block - address with country,
position, phone - so that is read rather than the locator's own text, which
writes the four addresses three different ways and gives Santa Clara's with no
comma between the town and the state. The structured data carries no hours,
though, so those come from the block the page heads "Hours". Only that block: the
footer states when the chain's customer service can be reached, "Monday - Sunday
8AM - 7PM PT", which is not when a shop is open.

The image every shop publishes is the same store-locator.png, the chain's
picture rather than the shop's, so it is dropped; the chain's own accounts and
contact address are not collected either. Everything that should differ between
the four does: town, postcode, street, branch, phone, hours and position are all
four of four distinct.

`heavenly_massage_us` reads the WP Store Locator the site runs. The locator
page holds no spas - the plugin asks for them afterwards - so the spider reads
the locator's own settings for the point it searches from, then asks the plugin
for the spas the way the page itself does. That endpoint is
/wp-admin/admin-ajax.php, which is the one path under /wp-admin/ that robots.txt
allows; everything else there is disallowed and is left alone. It runs at a ten
second delay, which robots.txt asks for, and three requests collect the lot.

**It cross-checks its own coverage, which is the point worth keeping.** The
plugin only answers a search within a radius, and refuses one wider than its own
menu offers - 500 miles. All five spas are in Illinois and well inside that, but
a spa opened further off would simply not come back, with nothing going wrong to
show it. So the spider first reads /wp-json/wp/v2/wpsl_stores, where the spas are
a post type of their own: that lists every one of them, though it carries none of
their details. If the radius search misses anything that list names, the spider
logs an error naming the spas it did not reach. Expect that to be how a sixth
somewhere distant announces itself.

The hours are stored in two different fields. Four spas fill in the one meant for
them, "Mon-Fri 9:00am - 10:00pm"; Mount Prospect leaves it empty and puts its
hours in the description instead, spelt out in full and with its times divided by
"to" rather than a dash - "Monday - Friday 9:00am to10:00pm", with no space
before the closing time. So whichever field reads as hours is the one used.

Every spa gives the chain's home page as its own website, so no `website` is
recorded. Each has a phone number and an email address of its own, which are, and
the country is stated as "United States" and left for the country code pipeline
to resolve. The Chicago one is named "Chicago / Goldcoast", so its branch is
Goldcoast; the other four are named for their town and carry none. The brand has
no Wikidata item.

`james_coney_island_us` reads the one page that lists the restaurants, and the
reason it reads paragraphs rather than headings is worth knowing. The page nests
a paragraph inside a heading - `<h4><p>5730 Hollister St.<br>Houston, TX
77040</p></h4>` - which HTML does not allow, so the parser closes the heading
and lifts the paragraph out beside it. Select the headings and five empty
strings come back, for the addresses and the hours alike. The same will be true
of any Elementor page that writes its text this way.

The blocks are recognised by what they hold - one heading, one phone number and
one address - rather than by any class, since the markup names nothing. That
also keeps the corporate office out: the footer carries 1750 Stebbins Drive with
a Google map link of its own, which would otherwise read as a sixth restaurant.
It spells its state out in full, "Houston, Texas 77043", so the locality pattern
never matches it either.

**The branch names are left in the capitals the page uses**, which is a
deliberate departure from `duckworths_grill_and_taphouse_us`, where capitals
were put into ordinary case. Four of these five are places - Hollister,
Meyerland, Woodlands, Humble - but the fifth is NASA, for the space centre it
stands near, and ordinary case would spell that Nasa. Nothing on the site writes
the five any other way: the Google place names are proper case for only two of
them, one of which gives the town rather than the restaurant, and the ordering
links are lowercase slugs. Humble carries no branch at all, its heading being
the town the address already states.

All five state the same hours, 11:00 to 21:00 every day, because the page gives
that one range for Mon-Thur, for Fri-Sat and for Sunday alike. That may well
mean the weekend was never updated, but it is what each states for itself.
`delivery` and `takeaway` are recorded because the link to order by is labelled
"Delivery / Pickup" - both words the merchant's own, which is why these are
recorded where `duckworths_grill_and_taphouse_us` left a bare "Order Online"
alone. The NASA one lists Uber Eats and DoorDash besides.

It carries `brand_wikidata` `Q6131624`, which is the second on this branch after
`third_love_us`. Wikimedia rate-limited the item lookup repeatedly, so the QID
was established the other way round: the Wikipedia article at
en.wikipedia.org/wiki/James_Coney_Island states the company, its Houston
headquarters and jamesconeyisland.com as its site, and Wikipedia's own API gives
that article's `wikibase_item` as Q6131624. That is a firmer link than matching a
label, which is how `third_love_us` was checked. It is absent from
`origin/master`.

That article also records seventeen restaurants in February 2021, with closures
through 2021 and 2022, against the five its infobox lists now and the five this
spider collects. So this is a chain that has shrunk hard, and the count is worth
watching downwards rather than up.

`rams_head_group_us` is the first on this branch to cover a group rather than a
chain. Its six venues are separately branded, each runs its own site, and
between them those sites use three platforms: BentoBox for the Tavern,
Roadhouse, Dockside and Shore House, WordPress for Southernmost and Carbonhouse
for On Stage. So `operator` is Rams Head Group on all six and `brand` is the
venue's own name, and the page to read is named per venue rather than
discovered. None of the six has a Wikidata item - a search returns nothing for
the group or for any venue - so there is no `brand_wikidata`, and neither
ramsheadgroup.com nor the brand names appear in `origin/master`.

**Rams Head Presents is deliberately not collected.** It carries the group's
name and a site of its own, but it is the booking office: it buys talent for
halls other operators own - Maryland Hall, the Key West Theater, Point of the
Bluff Vineyards - and publishes an office address rather than a venue, under a
postcode its own footer contradicts. Collecting it would have put other
people's venues in the output.

**The spider reads the group's own sitemap page only to check its own
coverage.** That page lists every venue domain, so the spider compares those
against the six it reads and logs an error naming any it does not, with the
group's own site and Presents excluded by name. Expect that to be how a seventh
venue announces itself, the way the locator list does for
`heavenly_massage_us`.

**None of the structured data on these sites is usable.** Dockside's ld+json
still carries the CMS placeholder it was created with - the name reads
"ramsheaddockside placeholder locations created at 2025-06-02 16:22:55.915618" -
and states no hours at all; Shore House's ld+json block is an empty `{}`. The
page description meta is no better: Dockside's states hours that contradict its
own page, giving 11 AM to 11 PM Monday to Thursday where the page says Monday
and Tuesday closed. So all four BentoBox venues are read from what the page
displays, as `roka_akor_us` and `carmines` are.

**Southernmost states two different house numbers for itself**, 840 Whitehead
St in a block near the top of the page and 804 in the LOCATION block at the
foot. The spider reads the LOCATION block, because the address inside the
venue's own Google map embed is 804 as well, so two of its three statements
agree and the map is the one the merchant configured. It also keeps three
*stale* sets of hours in HTML comments - "9 AM to 11 PM Daily", "Food served
until 10 PM" and "Monday through Thursday 8:30AM to 11:00PM" - which no visitor
sees. Selecting the HOURS block keeps them out; sweeping the page text mixes
them into the live "Every Day 8:00AM to 11:00PM", and a naive tag strip leaks a
bare `-->` as well.

**"&" had to be added to the shared day delimiters, and it matters.**
`DELIMITERS_EN` does not hold it, and without it `add_ranges_from_string` reads
"Friday & Saturday 11 AM - 2 AM" as Saturday alone - Friday disappears with
nothing going wrong to show it. Dockside loses Monday and Wednesday the same
way. "Every Day" is likewise missing from `NAMED_DAY_RANGES_EN` and yields
nothing whatever, which is what Southernmost states. Both are passed to the
shared parser as arguments rather than written here as a weekday table of this
spider's own.

**On Stage is recorded with neither hours nor coordinates.** The only hours it
publishes are its box office's, which are not the hours the venue opens, and
its page carries no map. It shares 33 West Street and 410-268-4545 with the
Tavern because they are the same building, and both are kept - one a
restaurant, one a music venue - rather than one being treated as a duplicate.
Its coordinates are left unset rather than taken from the Tavern's, which would
be one venue's data standing in for another's.

**On Stage also needs the spider to name itself.** Its site sits behind Fastly,
and on a cache miss that returns an empty 406 to any request whose User-Agent
contains "Mozilla" - which the default one does, beginning "Mozilla/5.0 (X11;
Linux x86_64)" - while serving named crawlers normally. So the spider sets
`USER_AGENT` to the shared `BOT_USER_AGENT_SCRAPY`, which identifies All The
Places and carries no browser prefix; all seven hosts answer 200 to it. This is
the reverse of a bot block, and robots.txt on every one of these domains is
readable and permissive, so naming the crawler is the fix rather than a way
round anything. Worth knowing because the failure is quiet and misleading: the
venue simply drops out of a run, and a single retry can return 200 off the
cache and suggest a one-off.

Shore House's hours come out with adjacent and overlapping ranges - `Mo-Th
08:00-11:00,11:00-24:00` and `Su 00:00-02:00,08:00-12:00,08:00-24:00` - because
it states breakfast and lunch and dinner separately and `OpeningHours` does not
merge them. Both are the venue's own trading hours, unlike the coffee shop
beside the restaurant at St. Charles in
`new_orleans_hamburger_and_seafood_us`, so they are combined rather than one
being dropped. Friday keeps an 11:00 to 12:00 gap because the page gives
breakfast until 11 and lunch from 12.

Cuisine is recorded only for the Tavern and the Roadhouse, both `american`, from
the `servesCuisine` each states. Dockside calls itself a "Bar & Grill", Shore
House a "Chesapeake Restaurant" and Southernmost "modern island fare", none of
which names a cuisine, so none is recorded rather than guessed at. Every venue
gives marketing@ramsheadgroup.com as its email, which is the group's and not the
venue's, so no email is collected either. The Roadhouse's coordinates
reverse-geocode to Crownsville against the Annapolis it states: 1773 Generals
Highway is in Crownsville with an Annapolis postal address, so both are right.

`kirbys_steakhouse_us` was asked for as "Kirby's Prime Steakhouse" and is filed
under the name the merchant's own site uses, which is **"Kirby's Steakhouse"**.
"Prime Steakhouse" appears nowhere on kirbyssteakhouse.com - not in a title, not
in a heading, not in the `Organization` structured data, which names it "Kirby's
Steakhouse" - and the only "prime" on the site is its gift-card link to
`quickgifts.com/merchant/kirbys-prime-steakhouse/`. OpenTable lists the
restaurants as `kirbys-prime-steakhouse-southlake` and so on, so both names are
the merchant's; the own-site name won. **Search for either when checking this
brand against upstream.** Neither is there: nothing for `kirbyssteakhouse` or
`kirby` in `origin/master` beyond a Tendring address spider, and no Wikidata or
NSI entry by domain or label, so there is no `brand_wikidata`.

Four restaurants, found through the site's own Locations menu, whose remaining
entry is Mickey Mantle's OKC - a different brand of the same group, on its own
domain, and excluded by taking only same-host links. Dallas closed for good in
2015, so four is the whole chain rather than a shrunken one.

**The page carries a demo widget with a New York address and a New York phone
number, and both appear as visible text on all four pages.** The Elementor
template left `20 W 50th St, New York,` and `(212) 222-4444` in a reservation
block, and an OpenTable line adds a shared `(832) 527-6515`. So the first
phone-shaped line on the page is wrong three ways over. Everything is instead
read from the footer `Contact Info` block downwards, which holds each
restaurant's own number, its own mailbox and its own address; the placeholders
all sit above it. The fake address could not have been picked up anyway, having
no postcode for the address pattern to anchor on, but the phone would have been.

**Nothing on the page divides the street from the town.** The addresses read
`123 N. Loop 1604 E. San Antonio, TX 78232` - one comma, and it falls between
town and state. Town names here run to one word or two and the streets end in
`E.`, `Hwy.114`, `Pl` and `Drive`, so no rule about suffixes or capitals
separates them. What does is the page's own `<title>`: it names the place, and
where the address ends with that name the split is a verified match rather than
a guess. San Antonio, Southlake and The Woodlands all split that way. WinStar's
title names its casino instead, so its street and town are left unsplit, it
keeps `WinStar Casino` as its `branch`, and `addr_full` carries the published
line in full - which every one of the four gets, so nothing is lost either way.
States are written `TX`, `Texas`, `Texas` and `OK`, so a name longer than two
characters is title-cased for the state pipeline, as in `aquarium_restaurants_us`.

**The hours needed three separate corrections and the first is the one that
matters.** Every range is written with no meridiem on its opening time - "5 -
9pm" - and read as published that gives `05:00-21:00`, a steakhouse open at five
in the morning. So a bare opening time takes the closing one's am or pm, which
turns it into the `17:00-21:00` that is meant. The substitution only fires where
the opening time has no meridiem of its own, so `11am-3pm` and `3 pm - 10 pm`
pass through untouched. Second, `&` is rewritten as `and` before parsing,
because `DELIMITERS_EN` holds one and not the other and "Fri & Sat" otherwise
reads as Saturday alone - the fix taken from
`hoffbrau_steak_and_grill_house_us`. Third, WinStar states the Mickey Mantle
Lounge's hours beside the dining room's, and the Woodlands and Southlake state a
bar opening, a happy hour and a cigar lounge, so a rule counts only where its
days sit before the colon and only under a label naming the brand or under no
label at all. That keeps WinStar's `Kirby's Dining Room:` and drops its
`Mickey Mantle Lounge:`, which opens two hours earlier and closes later.

No coordinates: the only map link on any of the four pages is the same
`goo.gl/maps/bWWzyu7pj5pTvYKk9` on all of them, one pin for the brand rather
than four for the restaurants, and short links of that kind no longer redirect.
The Woodlands page alone adds a Street View link whose `@` holds a camera
position rather than the restaurant, which is not worth one position out of four.
Each restaurant's own mailbox is recorded, three of the four having one; WinStar
publishes none. All four state the same trading hours except WinStar, which runs
later and opens on Sundays and Mondays when the Texas three are closed.

`hoffbrau_steak_and_grill_house_us` is the first spider on this branch written
by hand rather than by the assistant, added in commit `300c9b600`, and it was
reviewed rather than rewritten. It is correct. The four restaurants it collects
are the four the merchant states it has - "Hoffbrau Steak & Grill House has four
Texas locations" is the locations page's own first line - and all four come back
with a distinct street, postcode, phone, website, branch and pin, each pin
reverse-geocoding to the town it states. Its robots.txt is readable and
permissive, `User-agent: *` with an empty `Disallow:`, and nothing named
`hoffbrau` appears anywhere in `origin/master`. Black, isort and flake8 pass it
unchanged and the four CI tests pass with it in place.

Its `brand_wikidata`, `Q136534380`, checks out: the item is labelled "Hoffbrau
Steak & Grill House" and described as a restaurant in Texas. Worth knowing for
later that the link rests on that label and description rather than on a
website: the item carries no `P856`, which is why searching
`nsi-wikidata.json` by domain - the way `on_the_border_us` found `Q7091305` -
turns up nothing for it, and the item is typed as a restaurant rather than a
chain.

**Two details in it are worth copying.** The first is the hours: it rewrites
" & " as " and " before parsing, which is the fix for a trap that cost real data
on `rams_head_group_us`. `DELIMITERS_EN` holds "and" but not "&", so
"Friday & Saturday: 11am to 10pm" read straight gives Saturday alone and drops
Friday silently. Rewriting the character into a delimiter the shared table
already knows is neater than extending the table, which is what
`rams_head_group_us` does. The second is that `extract_google_position` is
called on the restaurant's own paragraph rather than on the response, so it can
only find that restaurant's map link. Called page-wide it reads whatever map
link comes first, which is how `on_the_border_us` would have filed a South
Dakota restaurant in California.

It sets `country="US"` explicitly, which the country pipeline already does from
the spider's own `_us` suffix. It is harmless, and it is the one thing an
upstream reviewer would ask to be deleted.

What was missing was not the spider but its registration: the commit adds the
file alone, so `spiders.txt` did not list it and this file did not describe it,
and a monthly run would have skipped it without anything going wrong to show it.
Both are added here.

`walnut_grill_us` collects three restaurants around Pittsburgh. Nothing upstream
covers `eatwalnut.com`, and the only NSI entry matching "walnut" is a school
district in Los Angeles County, so there is no `brand_wikidata`.

**The chain is three websites rather than one.** `eatwalnut.com` is a landing
page; the restaurants live at `wexford.`, `robinson.` and
`washington.eatwalnut.com`, each a full site of its own. The spider starts at the
apex and follows the subdomain links it publishes, so a fourth restaurant
appearing in that list is picked up without editing anything. That also means
four robots.txt fetches per run, one per host - all four are permissive and
identical, `User-agent: *` with no `Disallow` and a sitemap line.

**The apex sitemap is worthless and the apex structured data is nearly so.**
`eatwalnut.com/sitemap.xml` holds three URLs - the home page, `/-party` and
`/accessibility-page-01` - and names no restaurant at all, so a `SitemapSpider`
there would have collected nothing; each subdomain keeps its own sitemap
instead. The apex's one `Restaurant` block describes a single restaurant and
gives it no street and no city, only `addressRegion: PA` and
`postalCode: 15090`. The subdomains carry no structured data whatsoever. So the
apex block was used only as a cross-check, and it passes: its
`openingHoursSpecification` matches what Wexford's own footer states, and its
`geo` is about 6 m from the pin on Wexford's map.

**A comma-separated day list is cut down to its last day by
`add_ranges_from_string`.** The footer states "Mon, Tue, Wed, Thur" against
"11:00 AM - 9:00 PM", and handing that to the parser returns `Th 11:00-21:00`:
Monday, Tuesday and Wednesday gone without a word, and Friday likewise out of
"Fri, Sat". `DELIMITERS_EN` holds no comma. The days are split and added one at
a time through `add_range`, which is what structured values should use anyway.
That is the third silent-loss shape recorded here, after the `&` that swallowed
Friday in `rams_head_group_us` and the "Noon" that removed Sundays in
`stefaninas_pizzeria_us`. All three look like a working spider until the output
is read against the page.

**`sanitise_day` strips `-.\t ` and not newlines**, which matters because this
markup puts each day list on its own line inside the div, so `sanitise_day(day)`
returns `None` and `add_range` raises. It is called as
`sanitise_day(day.strip())`. This was found by deleting the `.strip()` to test
whether it did anything - it did, and the crawl failed loudly rather than
quietly, which is the failure worth having.

The rest of the markup is a pleasure: `.address`, `.city-state` and `.zip` divs,
`.days` and `.from-to` divs in pairs, and the phone under the stable id
`contact_us_v3_section_phone_link`. The platform is SpotHopper, whose asset host
`static.spotapps.co` is also where `the_post_sports_bar_and_grill_us` sends its
online orders - the two brands share a vendor but not a locator, and nothing
about one spider transfers to the other.

`ref` is the `spot_id` each site declares in script - 115658, 169163, 169164 -
rather than the subdomain name. Wexford's sits in a different range from the
other two, which reads as its site having been built first. `email` is
per-restaurant and kept: `wexford@`, `robinson@` and `washington@eatwalnut.com`.
The hours are the same at all three, read from each footer separately rather
than assumed from one.

`reverse_geocoder` answers a neighbouring borough for every one of the three -
East Washington, Bradford Woods and Rennerdale - because Wexford and Robinson
Township are unincorporated and absent from its dataset. The pins are 14 to 32
miles apart and sit north, west and south of Pittsburgh, which is how the brand
describes itself. Three restaurants is below the ten upstream would ask for, and
that bar does not apply on this branch.

`cactus_restaurants_us` collects six restaurants - five around Seattle and one
in Tacoma - and at 25 lines is the second shortest here, because the site's
structured data is complete and correct.

**The brand check is the part worth keeping.** NSI holds two entries called
Cactus and neither is this one: Q466918 is a supermarket chain in Luxembourg
and Q5016149 is Cactus Club Cafe, the Canadian restaurant chain. Nothing
upstream covers `cactusrestaurants.com`. So there is no `brand_wikidata`, and
those two QIDs in particular must never be borrowed for it - the same trap as
Q20709024 in `grotto_ristorante_us`, where the one Wikidata item for the name
was a different chain.

**robots.txt is entirely comments.** All 1,248 bytes of it are Cloudflare's
content-signals preamble - the definitions of `search`, `ai-input` and
`ai-train`, and a notice reserving rights under Article 4 of the EU copyright
directive - with not one directive after it: no `Content-Signal:` line, no
`User-agent:`, no `Disallow:`, no `Sitemap:`. `protego` was asked directly and
reports nothing restricted for any agent, named or otherwise. By the preamble's
own wording, where the operator sets no signal for a use it "neither grants nor
restricts permission via content signal". That is a third shape to put beside
the two already recorded on this branch: not a 4xx, where the policy is
unavailable and crawling is permitted, and not a challenge served in place of
the file, where the policy is unreadable and the answer is to stop, but a
readable file that deliberately states no policy at all. Taken as permitted.

The sitemap had to be guessed, since robots.txt names none: `/sitemap.xml`
answers, while `/sitemap_index.xml` and `/locations/` are both 404.

**The structured data is good, and it was checked rather than trusted.** Every
location page carries a `Restaurant` in its `@graph` with a full address,
telephone, `geo` coordinates and a properly spelled `openingHoursSpecification`,
and the home page carries none, so nothing is collected twice. The visible hours
on each page match it exactly. That check mattered more than usual here, because
the same pages also publish a happy hour (every day, 2 to 6), a weekend brunch
(Saturday and Sunday, 10 to 2) and dated early closures for Christmas Eve, New
Year's Eve and Independence Day. Reading the visible text would have had to
filter three kinds of decoy; the structured data carries trading hours and
nothing else. After `strip_house_us` and `the_post_sports_bar_and_grill_us`,
where structured hours were stale boilerplate, this is the case where they were
right - which is the argument for checking rather than for distrusting them.

Bellevue Square keeps different hours from the other five - `Mo-Fr 11:00-22:00;
Sa-Su 10:00-22:00` against `Mo-Th 11:00-21:00` and later closings at weekends
elsewhere - which is the mall's hours, and the evidence that these values are
genuinely per-restaurant rather than one block copied six times.

`search_for_facebook` is off. The group's `sameAs` names one Facebook page and
`StructuredDataSpider` was filing it as the contact details of all six
restaurants, the same leak dropped in `strip_house_us`. `wanted_types` was set
to `Restaurant` at first and then removed: it is already in the default list and
none of the other types in the graph - `Organization`, `WebSite`, `WebPage`,
`BreadcrumbList` - are, so the default selects the same entry.

`ref` is the page slug, overriding an `@id` of the page URL with `#restaurant`
appended, as in `grotto_ristorante_us` and `tom_and_chee_us`. The slugs are
inconsistent and are left as the site writes them: five read
`locations-<place>` and the sixth is a plain `south-lake-union`.

`brand` is "Cactus Restaurants" - the name of the `Organization`, the `WebSite`
and the domain - although each restaurant is signed "Cactus <neighbourhood>",
which is what the structured data's `name` holds and what `branch` is taken
from once the prefix is removed. `cuisine` is `mexican` alone even though the
site states `["Southwestern", "Mexican"]`, because `southwestern` appears in no
upstream spider and taginfo could not be reached from here to check whether it
is established.

Three of the six reverse-geocode to a neighbouring municipality rather than the
city they state, and all three are right: Madison Park answers Medina, which is
across Lake Washington and genuinely closer than the centre of Seattle; Alki
Beach answers White Center; and Proctor answers Fircrest, a small city that
Tacoma surrounds. These pages publish no second coordinate - no map embed, no
directions link - so there was nothing to cross-check each pin against, and the
six were checked for mutual consistency instead: downtown, West Seattle, east
Seattle, Bellevue, Kirkland and Tacoma sit correctly relative to one another.

`yafo_kitchen_us` collects four restaurants in Charlotte, all of them from the
"Where is YAFO?" cards on the home page. Nothing upstream covers it and it is
absent from NSI - the only matches for "yafo" across the data files are inside
"Matsuya Foods" - and Wikidata and Wikipedia are both still rate-limiting this
address, so there is no `brand_wikidata`. The footer names the operator as FS
Food Group, worth knowing if a sibling brand is asked for later.

**The site has a `location` post type, it has its own sitemap, and the four
pages in it are empty.** `/blog/location/yafo-dilworth/` and its three siblings
carry a heading and the site navigation and nothing else: no address, no phone,
no hours, no map. A `SitemapSpider` over `location-sitemap.xml` is the obvious
way into this site and would have produced four records holding nothing but a
name. The stubs are also why no `website` is set.

**Every page on the site carries all four restaurants in its structured data**,
including each stub, so `StructuredDataSpider` would have emitted the whole
chain once per page crawled. That data is good as far as it goes - clean
`streetAddress`, `addressLocality`, `postalCode`, `telephone` and
`servesCuisine` for each - but it has no coordinates, no hours, and a `url` of
the site root on all four, so it cannot say where any single restaurant lives.
It was used as a second opinion rather than a source: every address and phone
number the cards give matches it exactly.

**The hours are a time of day with no days attached.** All four cards read
"11 am - 9 pm", and nothing anywhere on the site says what that covers - not the
four per-restaurant menu pages, not the contact page, not the structured data.
It almost certainly means daily, but "almost certainly" is a guess about when
four restaurants are open, so `opening_hours` is left unset. Set it to
`Mo-Su 11:00-21:00` across the four if the likely answer is worth more here than
no answer.

The map links are `/maps/place/` links and the camera is displaced again, as in
`grove_wine_bar_and_kitchen_us`, though by far less. Three of the four are keyed
to the street address, and on those the `@latitude,longitude` sits about 200 m
west of the `!3d`/`!4d` pair in the same link; the Ballantyne link is keyed to
the business name and the two agree exactly. The displacement is longitude-only
and the same size every time, which is Google shifting the map centre to clear
its info panel rather than anything about the restaurants.
`extract_google_position` returns the camera, because the `@...z` branch is
tested before everything else, so the `!3d`/`!4d` place is read instead. Second
merchant running where that helper had to be set aside; the pattern to watch for
is any Google link carrying `@` coordinates and a `data=` block, where the two
are different things.

`branch` is the card heading with the brand prefix removed, giving Southpark,
Plaza Midwood, Dilworth and Ballantyne, and `ref` repeats it because the site
publishes no id for a restaurant anywhere. The structured data's `@id` fragments
- `#southpark`, `#plazamidwood`, `#dilworth`, `#ballantyne` - are the nearest
thing to one, but nothing ties a fragment to a card except matching on text, so
they are not used. Note that the structured data spells the first "SouthPark",
which is how Charlotte writes the neighbourhood, where the card heading spells
it "Southpark"; the heading won because the rest of the record comes from the
card.

Ballantyne reverse-geocodes to Pineville rather than Charlotte, which is
correct: it is the adjacent town and genuinely the nearer of the two. The other
three answer Charlotte.

`tortas_manantial_us` is **21 lines, the shortest spider on this branch** by
half, and the first here to subclass one of upstream's store finders. The site
runs Agile Store Locator, `locations/storefinders/agile_store_locator.py`
already speaks to it, and `DictParser` fills in everything but the branch name,
so the spider sets a brand, a domain, a category and a cuisine and gets out of
the way. Four shops in the Phoenix West Valley. Nothing upstream covers it, it
is absent from NSI, and Wikidata and Wikipedia are both still rate-limiting this
address, so there is no `brand_wikidata`.

**Nothing here could be fetched with curl.** Every request to the host - apex
and `www`, HTTP/2 and HTTP/1.1 - answered `PROTOCOL_ERROR` or "Empty reply from
server", while a control site answered 200 on the same egress and the proxy
reported healthy; `urllib` failed the same way. Scrapy's own stack fetches the
site without complaint, and so does the web fetch tool. So it is a client
fingerprint the host dislikes rather than a block on the address, it is not
something `requires_proxy` would help with, and the spider runs normally. It
does mean the usual hand exploration does not work: every page here was read
through `scrapy fetch`, which is worth remembering the next time a site looks
dead from the shell but fine in a browser. This is the same symptom as the
`jolly_pumpkin` investigation and, again, not a bot wall.

robots.txt carries two `User-agent: *` groups - WooCommerce and `wp-admin`
disallows in the first, Yoast's empty `Disallow:` in the second - and `protego`,
the parser Scrapy uses, was asked directly rather than read by eye. Everything
needed is allowed, no agent is named or refused, and although `/wp-admin/` is
disallowed the `Allow: /wp-admin/admin-ajax.php` line permits the locator
endpoint, so `ROBOTSTXT_OBEY` stays on here. `modern_market_us` upstream turns
it off for the same platform, which is not necessary on this site.

**The locator's `slug` field is the plugin's demo data and must not be used for
anything.** The Phoenix shop's slug is `port-alfred-restaurant-port-alfred` and
the Indian School Rd shop's is `grahamstown-restaurant-grahamstown` - Port
Alfred and Grahamstown are towns in South Africa, shipped as Agile Store
Locator's sample stores and never cleared - while the Buckeye Rd shop's slug
reads `tortas-manantial-laveen-laveen-village`, which belongs to a different
shop. `modern_market_us` upstream builds its `website` from `feature["slug"]`;
copying that pattern here would have published four wrong URLs, two of them in
another country. `website` comes from the locator's own `website` field and
`ref` from its `id`.

**The page URLs are named after cross streets rather than the labels the rest of
the site uses**, and all four resolve to the right shop, which was checked
rather than assumed: `/tortas-manantial-phoenix/` is 59th Ave,
`/tortas-manantial-avondale-blvd/` is Buckeye Rd, `/tortas-manantial-107th-ave/`
is Indian School Rd, and `/tortas-manantial-laveen/` is Laveen. Each page's
title names its own intersection and agrees.

**The header navigation is a name behind the rest of the site.** It offers
"Avondale 107th Ave" where the footer, the restaurant selector and the locator
all say "Avondale Indian School Rd", for the same shop at 10665 W Indian School
Rd. `branch` is taken from the locator's `title`, which is the surface the
business maintains, giving 59th Ave, Avondale Buckeye Rd, Avondale Indian School
Rd and Laveen.

The hours really are per-shop, which is worth saying after several merchants
here where they were not: the original 59th Ave shop opens 07:00 to 23:00 every
day and the other three run 08:00 to 22:00. `email` is one company address on
all four and is dropped. `state` arrives spelled "Arizona" and the state code
pipeline resolves it to AZ, which works only because the spelling is exactly
title case - the trap that silently emptied Houston's state in
`aquarium_restaurants_us`.

The pins were checked against the Phoenix numbered-avenue grid, which runs eight
avenues to the mile, because `reverse_geocoder` answers Tolleson for two of the
four - a nearest-known-place artifact, since Maryvale and north Avondale are not
in its dataset. The locator's own descriptions place the shops at 59th, 107th
and 51st Avenues; measured from the 59th Ave pin, Indian School Rd sits 5.7
miles west where 107th Ave predicts 6.0, and Laveen sits 1.03 miles east where
51st Ave predicts 1.00. Avondale's grid is offset slightly from Phoenix's, which
covers the difference.

`the_post_sports_bar_and_grill_us` collects four restaurants around St. Louis
from one page. Nothing upstream covers it, it is absent from NSI, and Wikidata
and Wikipedia are both still rate-limiting this address, so there is no
`brand_wikidata`.

**The sitemap offers a list of five locations and the fifth is a staff
archive.** `managerlocation-sitemap.xml` names `/location/maplewood/`,
`/location/fenton/`, `/location/creve-coeur/`, `/location/lake-saint-louis/`
and `/location/plt/`, which reads as the location list and is not one: it is a
taxonomy of managers by location, and `/location/plt/` is titled "PLT Archives"
with four people's names as its headings. Driving the spider from that sitemap
would have published a restaurant made out of a staff page. The four are
confirmed by the menu, beer and spirits sub-pages, which exist for those and
not for `plt`, and by the picker on `/locations/`. None of the five is a
restaurant page in any case - `/location/maplewood/` is the manager archive for
Maplewood, not the restaurant - so there are no per-restaurant pages to follow
and no `website` on these records.

**The page's own structured data describes two of the four restaurants.**
Maplewood and Creve Coeur appear as `Restaurant` entries in a hand-written
"Multisite Schema from Chris Gans" block; Fenton and Lake Saint Louis are
absent from it. It also nests `telephone` inside `address` and spells its hours
key `OpeningHoursSpecification`, which no parser reads. So
`StructuredDataSpider` here would have collected half the chain with no hours,
and reported nothing wrong.

**Where the two surfaces overlap they disagree, and the structured data is the
stale one.** Its Friday and Saturday close at 01:00 where the picker closes at
midnight; Monday to Thursday and Sunday agree exactly, which is the
corroboration for the two restaurants it covers. The picker won because it is
what the site shows a visitor and what drives the live open/closed indicator,
while the schema block is demonstrably unmaintained - two restaurants missing,
under a key nothing reads, so no one would see it drift. The same shape as
`strip_house_us`, where the structured hours were brand-wide boilerplate, and
the reverse of `grotto_ristorante_us`, where the prose was stale and the
structured list was kept.

Everything comes off `/locations/`, where each restaurant is a
`tracking-location-item` carrying `data-location`, `data-address` with the
street and locality separated by a literal `<br>`, `data-phone`, `data-lat` and
`data-lng`, and `data-hours` as a day-keyed JSON object. Structured values, so
the hours go through `add_range` rather than `add_ranges_from_string`.
`11am - 12am` is a midnight close and `time_format="%I%p"` renders it
`11:00-24:00`; read as `00:00` it would have said the opposite of what it means.

**"Closed" beside each restaurant is the live status, not a closure.** The
picker prints `data-status` next to "Today's Hours", so reading the visible text
would have recorded four closed restaurants - these pages were fetched about
twenty minutes before the 11:00 opening, Central time.
`data-today-open` and `data-today-close` are one day's times and are ignored for
the same reason.

`data-facebook` is per-restaurant and is kept. `data-twitter` and
`data-instagram` are per-restaurant for Creve Coeur and Fenton
(`TheposttweetsC`, `thepostup_fenton`) and the brand's own accounts for
Maplewood and Lake Saint Louis, so both fields are dropped rather than filing
the brand's handle as two restaurants' own - the partial version of what was
dropped wholesale in `strip_house_us`.

**Maplewood's postal city is St. Louis.** The address reads "St. Louis, MO
63143" and the structured data agrees, while the pin reverse-geocodes to
Maplewood, which is its own municipality in St. Louis County. `city` holds the
postal one and `branch` the municipality, both correct. Worth knowing if a
monthly run is matched on city rather than postcode. The other three pins
reverse-geocode to exactly the city they stated.

`DOWNLOAD_DELAY` is raised to 10 for this one spider. robots.txt opens with
" Crawl-delay: 10" as its first line, above any `User-agent:`, where it belongs
to no group - `protego`, the parser Scrapy itself uses, reports `crawl_delay` as
None for every agent asked, and `Disallow:` is empty so nothing is restricted.
The directive is void as written, but the intention is not in doubt and four
restaurants come off a single page, so honouring it costs seconds. Drop the
`custom_settings` line if this branch would rather never vary throttling.

One thing to be wary of: **Maplewood's `data-map` holds injected link spam** - a
paragraph fixed off-screen at `opacity:0` with `pointer-events:none`, carrying a
link to an AI-research site, sitting inside the Google Maps iframe markup. The
other three `data-map` values are the iframe alone. Nothing here reads
`data-map`, since the coordinates come from `data-lat` and `data-lng`, but it
means something has written into that field, and anything taken from it later
should be treated as untrusted. The stale `/locations-old/` tree is still in the
sitemap as well, with its own Creve Coeur, Fenton, Lake Saint Louis and two
Maplewood pages.

`grove_wine_bar_and_kitchen_us` collects four restaurants around Austin. The
brand check found nothing upstream and nothing in NSI, and Wikidata and
Wikipedia are both still rate-limiting this address, so there is no
`brand_wikidata`. It was asked for as "The Grove Wine Bar and Kitchen" and is
filed under the name the site gives itself, which is **Grove Wine Bar &
Kitchen** with no "The" in all five page titles. Google holds it both ways -
"The Grove Wine Bar & Kitchen - Westlake" against "Grove Wine Bar & Kitchen -
Northwest Hills" - so the site's own consistent spelling wins, as it did for
`kirbys_steakhouse_us`.

**The hours are stated times first and days second** - "11am - 10pm Mon-Fri" -
and `add_ranges_from_string` returns nothing at all for that order. Not a wrong
day or a wrong time: nothing, on all four restaurants, which would have shipped
four records with no hours and no error. The spider reverses each line into
"Mon-Fri 11am - 10pm" before parsing. That is the same class of failure as the
"Noon" that silently removed Sundays in `stefaninas_pizzeria_us`, and the same
lesson: a rule the parser cannot read is dropped in full rather than flagged, so
the parse has to be checked against the page every time.

One regex does the filtering as well as the reordering. Requiring a line to
begin with a time and end with day names keeps the two real rules and drops the
rest, because every other line leads with its own label: "CURRENT HOURS",
"Brunch 10:30am - 3pm Sat & Sun", "Happy Hour 2pm - 6pm M-F & 3pm - 6pm
Sat-Sun", "MOTHER'S DAY OPENS AT 10:00am" and "Closed Jan. 1, Thanksgiving,
Dec. 24-25". Brunch matters most of those: it is a real service with real
times, and letting it through would have closed three restaurants at 3 PM at
weekends instead of 10 PM.

**That filter only works on whole paragraphs, and the reason is worth keeping.**
The labels are marked up as `<strong>Brunch</strong>10:30am - 3pm Sat-Sun`, so
reading the block text node by text node splits the label away from its times
and leaves a bare "10:30am - 3pm Sat-Sun" that passes a leading-digit test
perfectly. Taking `string()` of each `<p>` instead keeps the label attached and
the line is rejected. Anywhere a label and its value are separate elements, a
per-text-node filter sees the value alone.

**Westlake's hours are in plain `<p>` tags while every other paragraph on the
page carries `style="text-align: center;"`,** and they close with stray
unmatched `</strong>` tags, which is WordPress editor damage rather than a
template. Selecting the block by that inline style - the obvious thing to do,
since it holds on the other three - returns only Westlake's brunch line, and
Westlake would have been published as open 10:30 AM to 3 PM at weekends and shut
the rest of the week. The block is found from the `Hours` heading instead, the
same heading-anchored approach as `aquarium_restaurants_us` and
`raffertys_pizza_us`. Inline style is not structure.

All four publish the same two rules, and unlike `strip_house_us` that is
honest: each page states them itself and they were read separately from each
page, Westlake included.

**The coordinates needed `extract_google_position` to be set aside.** Every
"Get directions" link has the shape
`/maps/dir/''/<address>/@30.2964274,-97.9027222,12z/data=...!1d-97.832682!2d30.296446`,
and the helper checks for `@latitude,longitude,<zoom>` before anything else, so
it returns the camera - which at zoom 12 is **6.4 km** from the Westlake
restaurant and 6.5 km from Lakeway. The `!1d`/`!2d` pair at the end of the same
link is the destination Google resolved for that place, and for Northwest Hills
a second field in the same payload, `!3d`/`!4d`, repeats it. Those are what the
spider reads. Each restaurant page also carries a map embed whose `!2d`/`!3d`
is a third value, a map camera from 2018 to 2024; it agrees with the pin to
between 210 m and 283 m on all four, which is what the pins were checked
against. Three Google numbers per restaurant, and only one of them is the
restaurant.

**The pins come from the home page rather than the restaurant pages**, because
Northwest Hills' own page offers only a `maps.app.goo.gl` short link, which no
longer redirects and which this branch does not follow in any case. The home
page's locations row carries a card per restaurant holding the full directions
link, so the pin is read from each card and handed to the page callback. The
card is also the scope: read page-wide, the first directions link found would
have been filed against whichever restaurant was parsed, which is the mistake
caught in `on_the_border_us`.

The sitemap cannot drive this one. It lists twelve pages, of which the four
restaurants are single-segment paths - `/westlake/`, `/lakeway/`,
`/cedar-park/`, `/northwest-hills/` - indistinguishable by pattern from
`/about/`, `/careers/` and `/gift-cards/`, and each has a
`/<slug>/<slug>-qrmenupage/` child a looser rule would pick up as well. The
home page's cards name the four exactly, and the navigation menu agrees.

`branch` is the URL slug title-cased, which gives Westlake, Lakeway, Cedar Park
and Northwest Hills. Neither of the two labels the site writes is usable as it
stands: the page titles read "Westlake Grove", "Lakeway Grove", "Cedar Park
Grove" and "Northwest Hills", which puts a brand word in three of four branches,
and the home page cards read "Westlake", "Lakeway", "Cedar Park" and "NW Hills",
which abbreviates the fourth. The slugs match the names Google lists the four
under.

Addresses come from the restaurant pages rather than the cards, the two being
worded differently and neither consistently better: the Cedar Park page has
"1310 E. Whitestone Blvd., #500" where its card drops the "Blvd.", while the
Lakeway card spells out "3001 Ranch Road 620 South" where its page abbreviates
to "3001 RR 620 South". The page was taken as each restaurant's own authority,
so Lakeway carries the abbreviation. Worth knowing if a monthly run is matched
on street text.

Two signs the site is not closely maintained, neither of which affects what is
collected: "MOTHER'S DAY OPENS AT 10:00am" still sits in the hours block in
November, and the Westlake page announces "FULL BAR NOW OPEN!!!" twice.

`strip_house_us` is the third Landry's brand on this branch, after
`aquarium_restaurants_us` and `grotto_ristorante_us`, and the brand check came
back the same way: `striphouse` appears in no upstream spider, and upstream's
seven Landry's brands - Morton's, Landry's Seafood, Chart House, Bubba Gump,
McCormick & Schmick's, Rainforest Cafe and Saltgrass - each cover only their own
domain. There is no `brand_wikidata`: Strip House is absent from NSI, and
Wikidata's and Wikipedia's APIs have both been rate-limiting this address all
week, so nothing could be verified and nothing is claimed.

**The structured data's opening hours are wrong on every venue, and wrong in a
way that looks right.** The group's `/locations/` page and each restaurant page
publish the same seven-line `openingHours` block - `Mo 16:00-21:00`, `Tu-Sa
16:00-22:00`, `Su 16:00-21:00` - on Downtown, Speakeasy and Midtown alike, and
it matches none of them. Downtown's own page states Friday and Saturday to
11 PM, not 10. Midtown opens at 11:30 AM from Monday to Friday, not 4 PM. Las
Vegas carries no `openingHours` at all, which is what gave it away: a field that
was genuinely per-restaurant would not be identical on three and missing from
the fourth. So `StructuredDataSpider` reads the addresses, phones and labels,
and the hours are taken from the page instead.

The hours block needs no content filter, because the markup ends it. The weekly
rules sit in one `<p>`, which the site follows with an `<h4>Holiday Hours` and a
block of dated exceptions running to "Fri, Jan 1, 2027" - and a heading closes
an open paragraph, so the parser leaves those lines outside the `<p>` the spider
reads. `grotto_ristorante_us` had to recognise its holiday lines by shape, and
`mortons_the_steakhouse_us` upstream drops them by excluding any line holding a
four-digit year; here the structure does the work, and the `Pick Up` and
`Delivery` headings that follow fall outside it the same way.

`SUN - MON` and `SUN - THU` are wrap-around ranges, and `add_ranges_from_string`
reads them as Sunday with Monday, and Sunday through Thursday, rather than as
the whole week. Worth testing before trusting rather than after.

**The site's list of venues is in the locator's structured data, not its
sitemap** - the same lesson as `grotto_ristorante_us`, with one venue at stake
rather than two. The sitemap names `/downtown/`, `/midtown/` and `/las-vegas/`
and omits the Speakeasy entirely; `/speakeasy/` answers 404. The `/locations/`
page states all four as `subOrganization` entries, and the visible list and the
reservation form's dropdown agree on four, so the count is confirmed three ways.
Unlike Grotto, no surface here claims a larger number than it publishes.

The Speakeasy is counted as a restaurant of its own, and that is a judgement
worth recording rather than burying. It has a separate street address - 11 E
12th St against Downtown's 13 - its own phone, its own page, its own Google
place id and its own pin a few metres off; it is bookable separately in the
reservation form; and it serves the Strip House menu rather than drinks alone.
Its own description explains the arrangement: 11 East 12th Street was a
Prohibition speakeasy whose hidden connection to 13 East above it meant officers
arriving with a warrant for "13 East" could not lawfully enter "11". It shares
Downtown's trading hours, which is the one place two venues here hold the same
value honestly.

Two fields are dropped and one kept, on the same test. `search_for_facebook` and
`search_for_twitter` are off because the only accounts on these pages are the
brand's own, linked from the footer of all four, so `StructuredDataSpider` would
have filed one Facebook page and one Twitter handle as four restaurants' contact
details. The images are the opposite case and stay: each venue's `og:image` is
its own page picture, distinct across the four.

The pin is the `data-gmaps-lat` and `data-gmaps-lng` pair on the page's map
element, the same source as `grotto_ristorante_us`, and it is a marker rather
than a viewport - the static map URL beside it centres on the coordinates it
marks. All four reverse-geocode to where they claim to be, with two differences
that are right rather than wrong: Midtown resolves to Manhattan rather than New
York, and Las Vegas to Paradise, NV, the unincorporated town the Strip actually
lies in. The page agrees with the second, placing that restaurant on the
mezzanine of the Planet Hollywood casino.

One thing not to carry over from the other Landry's spiders: upstream's seven
all read a BentoBox `storeLocatorConfig(...)` object from `/store-locator/`, and
Strip House publishes no such object. `/store-locator/` redirects to
`/locations/`, and the page it lands on carries the `subOrganization` list
instead.

`ref` arrived as the structured data's `@id`, which is the page URL with
`#foodestablishment` appended, and is overridden with the page slug as in
`grotto_ristorante_us` and `tom_and_chee_us`. `wanted_types` was set to
`FoodEstablishment` at first and then removed: it is already in
`StructuredDataSpider`'s default list, and the output was byte-identical without
it.

`grotto_ristorante_us` is the second Landry's brand on this branch after
`aquarium_restaurants_us`, and the brand check went the same way: `grotto`
appears in no upstream spider, and upstream's five other Landry's brands each
cover only themselves. **The one Wikidata item for the name is a different
chain** - Q20709024 is Grotto Pizza, the Delaware pizza chain - so there is no
`brand_wikidata` here, and that QID in particular must not be borrowed.

This one is short because the structured data is good. Every restaurant page
publishes a `FoodEstablishment` with its address, phone and `servesCuisine`, so
`StructuredDataSpider` reads all of that, `name_is_branch` moves the label into
`branch`, and only three things are added by hand: the pin, the hours and the
cuisine in lower case.

**The site's own list of restaurants is in the locator's structured data, not
its sitemap.** The `/locations/` page states each restaurant as a
`subOrganization` of the group with its URL, and that is what the spider
follows. Its sitemap names only two of the four - Galveston and Lake Charles -
so a `SitemapSpider` would have missed both Houston restaurants, whose pages
exist at `grotto-westheimer-tx` and `grotto-downtown-houston-tx` and are linked
from nowhere a crawler would reach them except that list. Guessing those slugs
failed: `grotto-houston-tx`, `grotto-westheimer` and `grotto-downtown-houston`
all answer 404.

**The description claims seven restaurants and the spider collects four.** The
group's own `description` reads "one of our seven locations in Lake Charles, LA,
Las Vegas, NV, Atlantic City, NJ, Galveston, TX, Westheimer, TX, The Woodlands,
TX, and Downtown Houston, TX" - three more than it publishes anywhere else. Las
Vegas, Atlantic City and The Woodlands appear in no `subOrganization`, in no
sitemap, and `/location/grotto-las-vegas/`, `/location/grotto-atlantic-city/`
and `/location/grotto-the-woodlands/` all answer 404. The FAQ page answers
"Where are the Grotto Ristorante locations?" by pointing at the locator rather
than naming seven. So the prose is the stale surface and the structured list is
the kept one, exactly the reverse of `bulldog_ale_house_us`, where the menu was
current and the sitemap was not. Worth watching if the count ever reads seven.

The hours need filtering and the filter is upstream's. These pages state the
trading hours, then a promotion - "Happy Hour MON - FRI: 2:00 PM - 7:00 PM |
Brunch SAT - SUN: 11:00 AM - 3:00 PM" - and then a "Holiday Hours" block of
dated exceptions running to "Fri, Jan 1, 2027". `mortons_the_steakhouse_us`
upstream, another Landry's brand on the same BentoBox platform, drops those by
excluding any line holding "hour" and any line holding a four-digit year. Here
the same job is done by requiring the shape of a rule instead: a day or day
range, a colon, then something with a digit or the word closed in it. The
promotions lead with their own name and the holiday lines lead with a weekday
and a comma, so neither matches, and feeding the rest of the section's text to
the parser is harmless - the addresses, phone numbers and the long prose
paragraphs carry nothing it reads as a time.

Two shapes caught here were already familiar. The `p[skip="true"]` that holds
Galveston's hours holds nothing on the other three, so the hours are found by
what the lines say rather than by that attribute, as in `bulldog_ale_house_us`.
And `ref` arrived as the structured data's `@id`, which is the page URL with
`#foodestablishment` on the end, so it is overridden with the page's slug the
way `tom_and_chee_us` does.

Galveston omits Tuesday from its hours rather than marking it closed, which in
`opening_hours` means the same thing, so nothing is added for it. Lake Charles
states "SUN - THU: Closed" and keeps only Friday and Saturday, which reads
oddly for a casino restaurant but is what it publishes. The branch labels have
their state stripped, which is why one reads "Houston (Galleria)" rather than
"Houston, TX (Galleria)" - the state sits mid-string there, not at the end, so
anchoring the pattern at the end left it in place on the first run. `brand` is
"Grotto Ristorante", the name the FAQ uses, rather than the "Grotto" of the
group's own `Organization` name. Each image is the restaurant's own page
picture, distinct across the four, so none is dropped; two of them are of food
rather than the room.

`aquarium_restaurants_us` is the second group spider on this branch after
`rams_head_group_us`, and the one where the brand check mattered most. Aquarium
is a Landry's brand, and upstream already carries five of its siblings -
`landrys_seafood_us`, `bubba_gump_shrimp_us`, `rainforest_cafe_us`,
`chart_house_us` and `mortons_the_steakhouse_us` - so this needed checking
against the family rather than the name. It is clean: `landrys_seafood_us` is
scoped to `landrysseafoodhouse.com` and carries only that brand, no upstream
spider mentions an aquarium, and the brand has no Wikidata item and no NSI
entry, so there is no `brand_wikidata`.

**robots.txt on the portal is a soft 404 and the distinction matters.**
aquariumrestaurants.com/robots.txt answers `200` with the site's own branded
"Error 404 (Not Found)" page, which holds no `User-agent`, `Disallow` or
`Allow` line anywhere. Parsed as robots.txt it yields no rule at all, so
nothing is restricted either way. This is not `claim_jumper_us`, where a
challenge stands in place of robots.txt and the policy cannot be read: here the
response reads perfectly and simply expresses no policy. The three venue
domains do have real robots.txt, all `User-agent: *` with no `Disallow`, and
each carries `Content-Signal: search=yes, ai-input=yes, ai-train=yes` - the
opposite of the `ai-train=no` on Dos Caminos.

Four restaurants, each inside a Landry's aquarium with a site of its own:
Houston and Kemah and Nashville on one modern template, Denver on an older one
reached as a path of the portal rather than a domain. The portal's home page is
read only to notice an aquarium domain the spider does not cover.

**Only Denver states the restaurant's hours.** The other three leave them to
empty divs that Yext fills in from the browser -
`<div data-yext-field="hours-monday" data-yext-id="AQNV">` - so the day names
are in the page and the times never are. Those three are recorded without
hours rather than with a JavaScript runtime or a call to Yext's own API. Denver,
on the old template, states them as text and labels them `Restaurant Hours`,
which is the label the spider keys on, because that page states the exhibit's,
the gift shop's and the Dive Lounge's hours beside them.

**Houston's dining page looked like the missing hours and is not.** It states
"Sunday - Thursday: 11:00am - 8:30pm" in plain text, which parses cleanly and
would have been the obvious fix for the Yext gap - but the heading above it is
"tHE dive lounge" and the sentence beside it places it on the second floor. They
are the bar's. That is the `roka_akor_us` problem again, and the reason the
spider reads only the page that names the restaurant.

**The addresses are published in capitals, and that cannot simply be passed
through.** Houston writes its state as "TEXAS", and `StateCodeCleanUpPipeline`
matches a code exactly as given and a state name only in title case, so "TEXAS"
matches neither branch, falls through to reverse geocoding, finds no
coordinates to geocode from, and the state comes out empty. So a value longer
than two characters is title-cased and a two-letter code is left alone, which
turns "TEXAS" into "Texas" for the pipeline to resolve to TX while "TX" and
"TN" pass untouched. Street and city are title-cased on the same reading, which
is what turns "410 BAGBY STREET" into "410 Bagby Street"; Denver needs none of
it, publishing schema.org microdata in ordinary case.

Denver is the easiest of the four to read despite being the oldest: its address
and phone are `itemprop` microdata, so they are selected by name rather than by
position. The three modern pages put the restaurant's name, street and locality
in three consecutive paragraphs, which Houston and Nashville wrap in a maps link
and Kemah does not, so the block is found by which paragraph holds the locality
and the street taken from the one before it.

No position for any of the four. The modern pages link
`maps.app.goo.gl` short links, which no longer redirect and are not ours to
follow for coordinates in any case, and Denver's page carries no map at all. No
cuisine either: the dining page describes "seafood specialties, steaks,
chicken, salads, pasta dishes", which names a variety rather than a cuisine, so
nothing is recorded instead of `seafood` being inferred - the same reading as
Dockside's "Bar & Grill" in `rams_head_group_us`. `brand` is "Aquarium
Restaurant", which is what the restaurant is called on all four sites, rather
than the "Downtown Aquarium" that Houston and Denver call the complex around
it. No `operator` is recorded, though the footers all read "© Landry's, Inc.".

`bulldog_ale_house_us` collects **one** restaurant, and the one is the point.
The site publishes `-location/` pages for four - Bolingbrook, Carol Stream,
Lansing and New Lenox - all four reachable, all four carrying a street address,
a phone number, a full week of hours and a Yelp waitlist widget. Three of them
are closed.

New Lenox, at the 2387 Joliet Highway the page still gives, closed "effective
immediately" in December 2023, and a different restaurant was slated for the
unit. Carol Stream, at the 1021 Fountain View Dr. the page still gives, is
marked closed by Yelp as of October 2026 and by Foursquare and MapQuest as well.
Bolingbrook, at 157 S. Weber Road, is marked closed by Foursquare. North Aurora
was open alongside them in December 2023 and its page has since been deleted
outright, so pages do get removed here - just not reliably, and not these three.

**So the sitemap is the wrong source for this merchant and the navigation is the
right one.** The site's own Locations menu offers exactly one restaurant,
Lansing IL, and that is what the spider reads: the menu's `-location/` links
from the home page. Every other menu on the site - Menu, Order Online,
Fundraisers, Contact, Employment - likewise offers Lansing alone, and no
`-location/` link for any other restaurant appears anywhere on the home page.
The menu is the surface the merchant keeps current; the sitemap is the one it has
let rot. A `SitemapSpider` over `-location/` was written first and collected all
four, which is how the three stale pages came to light: the count looked
plausible and the addresses were all distinct, and only checking the chain
against the outside world showed three of them were for restaurants that no
longer exist.

Nothing excludes the three by name. The spider cannot tell a closed restaurant
from an open one by reading its page - they are indistinguishable, which is the
whole difficulty - so it does not try, and it does not record them with an
`end_date` either, because the merchant publishes no closure date and taking one
from a news story is not collecting. If Bolingbrook reopens and returns to the
menu, the spider picks it up with no change. If the menu is ever restructured so
that it names no restaurant, the spider logs an error rather than quietly
yielding nothing.

The hours are read by recognising a line that opens with a day name rather than
by where the line sits, because the pages disagree about that: on three of them
"Hours:" is an `<h5>` beside the address block, and on Lansing's - which doubles
as the site's home page and is laid out differently - it is a paragraph inside
it, with the "Address:" label inside the block too. Keying on `sanitise_day`
reads both. All four pages state the same hours, 11:00 to 22:00 on Monday, to
23:00 Tuesday to Thursday, to midnight Friday and Saturday and to 22:00 on
Sunday.

No position is recorded: the Elementor map widget embeds
`maps.google.com/maps?q=<the address as text>`, which carries no coordinates,
and geocoding it is not ours to do. No branch either - the one restaurant's name
is its town, which `city` already states. The brand has no Wikidata item and no
NSI entry, so there is no `brand_wikidata`, and `bulldogalehouse.com` appears
nowhere in `origin/master`. The category is `restaurant` rather than `pub` or
`bar`, following upstream's `millers_ale_house` and `sedona_taphouse_us`, which
are the closest things to this and both sit at `restaurant`; no cuisine is
recorded, the site describing itself only as "Food & Brews".

`stefaninas_pizzeria_us` reads four pizzerias around St. Charles County,
Missouri, from the `-location/` pages its sitemap names, and the two things
worth keeping about it are a scare that turned out to be nothing and an hours
bug that was something.

**The scare: a fifth location that does not exist.** The sitemap carries nine
pages beginning `veterans-memorial-` - a lunch menu, a dinner menu, pizza,
pasta, desserts and so on - with no `-location/` page among them, and
`/veterans-memorial-location/` answers 301. That looks exactly like
`bulldog_ale_house_us`, where pages outlived a closed restaurant. It is not:
**Veterans Memorial is a street.** The O'Fallon restaurant stands at 8645
Veterans Memorial Pkwy, and those are its menus under an older naming scheme,
which the 301 confirms by redirecting to one of them. Four is the number, and
the home page's own Locations menu lists the same four.

**The bug: "Noon" is not a time the hours parser reads, and a rule naming it is
dropped whole.** Lake St. Louis and Jungermann both state "Sunday: Noon-9pm",
and read as published both came back with no Sunday at all - not a wrong
Sunday, an absent one, which is the kind of loss that leaves nothing behind to
notice. Rewriting "Noon" as "12pm" gives the `Su 12:00-21:00` meant. "Closed"
needs no such help: `CLOSED_EN` holds it, so Zumbehl's "Sunday: Closed" reads
as `Su closed` on its own, and the first draft of the filter here wrongly
excluded that line for having no am or pm in it. Feed the parser every line of
the block and it handles the closed day itself.

A leading "Open " is stripped from the first rule of each block, that being how
each is written: "Open Mon-Thurs 11am-9pm".

**Every page's footer lists all four restaurants** with their addresses and
phone numbers, in white text, so reading the page at large would give each
record four addresses to choose between. Both blocks are instead taken from the
Avada heading standing above them - `Address` and `Order by Phone` - which is
the same heading-anchored approach `aquarium_restaurants_us` uses on Denver and
`raffertys_pizza_us` on its Webflow pages, and it is what the generated
`fusion-text-1` class names would not survive. The phone comes from the page's
one `tel:` link rather than from the footer's four.

Coordinates come from each page's Google Maps embed, which carries them as
`!2d` for longitude and `!3d` for latitude, and all four land in the town the
page states - St. Charles, St. Peters, Lake Saint Louis and O'Fallon all
matching exactly on a reverse-geocode, which is a cleaner result than most on
this branch. Branch names are kept only where they are not the town, so
Jungermann and Zumbehl carry one, both being named for their street while
trading in St. Peters and St. Charles, and O'Fallon and Lake St. Louis carry
none.

One thing to know if this is matched on strings: **O'Fallon's `city` holds a
curly apostrophe**, `O’Fallon`, because that is how the site writes it and no
pipeline normalises quotes. The brand is written with a straight one, as
upstream's brand strings are.

The site's own title is "Stefanina's Pizzeria O'Fallon Missouri", which is the
WordPress title with a town bolted on for search and wrong for three of the
four, so `brand` is "Stefanina's Pizzeria". The brand has no Wikidata item and
no NSI entry, and nothing for `stefaninas` or `stefanina` appears in
`origin/master`. Incidentally the site still carries the Avada theme's demo
portfolio - four plumbing jobs, including a wet-room construction and a
commercial maintenance contract - in its own sitemap. The `-location/` rule
does not reach them.

`raffertys_pizza_us` is the shortest spider on this branch at 46 lines, and it is
short because the site is well built rather than because anything was skipped.
Rafferty's runs four pizza restaurants around the Brainerd lakes in Minnesota on
Webflow, and Webflow renders the whole page on the server: the sitemap named in
robots.txt lists the four `/location/` pages and nothing else that looks like
one, each page carries its own address, phone and hours in the markup, and a
plain `SitemapSpider` reaches all of it in one pass. No JavaScript, no locator
API, no challenge, no stale second copy of the data to choose between. **The
count is the merchant's own**: every page's description reads "one of the four
Rafferty's locations".

Its robots.txt is 67 bytes and holds a `Sitemap:` line and nothing else - no
`User-agent`, no `Disallow` - so nothing is restricted, which is the same
practical outcome as `User-agent: *` with no rules but reached a different way.

The two blocks worth reading are labelled `Hours` and `Info`, and the spider
finds them by those headings rather than by class, because Webflow generates
the class names - `rich-text-block-2`, `rich-text-block-5` - and they would move
with any edit to the page. Under `Info` the street and the locality are two text
nodes divided by a `<br>`, which is the shape `rams_head_group_us` and
`bulldog_ale_house_us` read, and the locality carries a two-letter state, so
none of the splitting trouble of `kirbys_steakhouse_us` or
`new_orleans_hamburger_and_seafood_us` arises. The hours parse with no
preparation at all: "Sun-Thu: 11:00am to 9:00pm" uses `to`, which is already one
of the shared delimiters, and states am and pm on both ends, so neither the `&`
rewrite nor the bare-opening-time fix those two spiders needed is wanted here.

Crosslake closes an hour earlier than the other three every day. Branch names
are kept only where they are not the town, so only Baxter carries one: its
heading reads "Baxter Mall and Delivery" while its address states Brainerd,
which is the neighbouring city, so that one is a genuine branch rather than a
repetition of `city`. The other three are named for their towns and carry none.
Worth knowing if this is matched against merchant data that files that
restaurant under Baxter rather than Brainerd - the site states Brainerd and
56401, and that is what is recorded.

No coordinates: none of the four pages carries a map, an embed or a link with a
position in it. The brand has no Wikidata item and no NSI entry, so there is no
`brand_wikidata`, and nothing for `raffertyspizza` or `rafferty` appears in
`origin/master`. Note when checking that name in future that **Rafferty's
Restaurant & Bar is a different chain** - a Kentucky one - and not this
merchant.

`on_the_border_us` is the first on this branch for a chain that used to be
large. On The Border ran around a hundred restaurants, filed Chapter 11 in March
2025, closed every company-operated one during 2026 and now survives as
franchises only. Its locator lists four, and the four are what the spider
collects, so **this count is worth watching downwards rather than up** - the
same caution as `james_coney_island_us`, only further along.

**The locator is one restaurant short of what the trade press counted.** Yahoo
Finance and the Las Vegas Weekly both put five left in June 2026, across
California, Florida, Nevada and South Dakota; ontheborder.com lists Las Vegas
NV, San Diego CA, Orlando FL and Rapid City SD, which is one per state. The
missing one is Escondido CA, which Patch names as still open under the same
franchisee as Mira Mesa, Brett Almquest. The site does not publish it: there is
no row for it in the locator, it is absent from the sitemap, and
/locations/escondido/ answers 302. Nothing is hardcoded to make up the
difference - the merchant's own locator is the source and inventing a fifth row
from a news story is not collecting - but if the count ever reads five, that is
why.

The data comes from the locator's MapSVG database, which the page carries whole
in a `mapsvg_options` object, so one request gets everything: address, pin,
phone, hours, services and a `restaurant_number` that serves as `ref` (2034,
2009, 2093, 2053). No per-restaurant request is needed, and the four location
pages are used only as each `website`, taken from the post's `url` rather than
its `guid`, which for Las Vegas still reads `/locations/ann-road/` from an
address it has since left.

**Two fields in that database are wrong and are deliberately not used.** The
plugin stores its own geocoding of each address beside the typed one, and at the
airport the two disagree: the restaurant states 9000 Airport Blvd and the
geocoder resolved 9333. The typed address is collected, being the restaurant's
own statement of where it is. Worse, each record carries a `google_maps_url`,
and Rapid City's centres on `@33.9769421,-117.5524625` - Riverside County,
California, some fifteen hundred miles from South Dakota. So coordinates come
from the record's own stored pin and `extract_google_position` is not called
here: it reads exactly that link and would file the South Dakota restaurant in
California. All four pins reverse-geocode to their stated place, Mira Mesa
answering Poway and the airport answering Taft, both neighbours of the stated
city rather than errors.

`cuisine` is `tex-mex` and `name` and `official_name` are filled in, none of
which this spider sets: the NSI pipeline supplies all three off
`brand_wikidata`, and the run reports `atp/nsi/match_perfect` for all four. The
QID, `Q7091305`, was read out of `locations/data/nsi-wikidata.json` in the
checkout rather than from Wikidata's API, which has rate-limited this egress all
week; that file ties the QID to ontheborder.com directly, so it is a firmer
check than matching a label. NSI spells the brand "On The Border" with a capital
T, against the "On the Border" of the Wikidata label, and NSI's spelling is what
`tests/test_item_attributes.py` compares against.

Branch names are kept only where they are not the town: Mira Mesa and Orlando
Airport carry one, Las Vegas and Rapid City name their own cities and carry
none. Services are recorded from the `available_services` each restaurant
lists, so Mira Mesa gets `delivery` and `takeaway` but no `indoor_seating`,
which the site does not claim for it, and the airport gets no `delivery`. The
`owner` field holds franchise codes rather than names - `franchiseSYNPAC`,
`franchiseDosGringos`, `franchiseHMSHost`, `franchiseFronteraChicos` - so no
`operator` is recorded; un-camel-casing an internal code into a company name
would be invention. Each record also carries a `restaurant_status`, false on all
four, with nothing on the pages to say what true would mean, so it is left
unread rather than guessed at as a closure flag.

`new_orleans_hamburger_and_seafood_us` reads the one page that lists the five
restaurants. They have no pages of their own: the site's page-sitemap names nine
pages and not one of them is a restaurant, so the locations page is the whole
source. Its /coming-soon/ page says only "Coming Soon!" and names nothing.

**The address shape is the thing to know.** Street and locality share one line
with no comma anywhere in it - "1005 S. Clearview Parkway  New Orleans LA 70121"
- and the only thing dividing them is a run of two or more spaces. So the spider
must not collapse whitespace before matching: it resolves non-breaking spaces and
trims the ends, and leaves the runs inside alone. Should the site ever write that
divide as a single space, the split cannot be guessed back - "New Orleans" is two
words and "Metairie" is one, so counting words back from the state tells them
apart for neither - and the spider logs an error naming the restaurant rather
than inventing a boundary. Expect that to be how a re-typed page announces
itself.

Veterans @ Martin Behrman writes its street as "817 Veterans Memorial Blvd,.",
and the street capture ends at its last word character, which drops the stray
punctuation. Left to the address pipeline it would have come back as "817
Veterans Memorial Blvd, ." instead, that pipeline splitting on commas and keeping
the period as a line of its own.

**St. Charles publishes two sets of hours and only one of them is the
restaurant's.** It labels them "Restaurant" and "Coffee Shop", and the coffee
shop opens at 07:00 where the restaurant opens at 11:00, so collecting the wrong
one would have the restaurant open four hours early every day. An unlabelled set
is the restaurant's, which is how the other four read. A label counts as a
section only when it is not a day name, so a restaurant writing "Monday -
Thursday" with spaces around the dash cannot have its hours silently dropped as
somebody else's section. This is the same problem as `roka_akor_us`, where dining
room and lounge each state hours, and `karinas_mexican_seafood_us`, where happy
hour sits among the trading hours.

St. Charles also runs across two paragraphs, the first ending at the bare word
"Hours:" and the second carrying both sets, so restaurants are grouped by where
their headings fall rather than one to a paragraph. The headings are not written
consistently either: Clearview wraps its name and its menu link in one
`<strong><em>`, the other four use two, which is why the lines are cut at `<br>`
rather than selected by element.

**It yields no coordinates**, because the page publishes none - no map embeds, no
Google links, nothing with a position in it - so the five are address-only, as
`eatzis_us` is. Worth knowing if a monthly run is matched on position rather than
on address. No `website` is recorded either: with all five on the one page the
only URL available is the same for each, and `@source_uri` already records where
the data came from.

All five state the same hours, 11:00 to 21:00 Sunday to Thursday and 11:00 to
22:00 Friday and Saturday, which each states for itself rather than anything
brand-wide. The category is `fast_food` on the merchant's own account of itself:
the about page calls the food "always served fresh, fast and counter-casual",
which is ordering at a counter whatever the dining rooms look like. Upstream puts
sit-down seafood chains such as `landrys_seafood_us` and `joes_crab_shack_us` at
`restaurant` and the counter-service `skrimp_shack_us` at `fast_food`, which is
the line this follows. Cuisine is `seafood;burger`, for a menu built on both.

The brand has no Wikidata item - a search returns nothing at all - so there is no
`brand_wikidata`, and neither nohsc.com nor the brand's name appears anywhere in
`origin/master`. Aggregators still list restaurants in Houma and Mandeville that
the brand's own site no longer does, and neither name appears on its pages; the
five the merchant publishes are the five collected.

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
read, and from `dukes_seafood_us`, where it reads permissive and only a datacenter
address is refused. Here the policy reads clearly and names us.

## Merchants behind a challenge that needs a browser

A third kind, and the most common one. These sites publish a robots.txt that
invites crawling and then put Cloudflare's **managed** challenge in front of every
page. That challenge answers any client which does not run JavaScript, so it is not
a datacenter address being refused: a plain `curl` and a plain Scrapy request are
both turned away from any network, home ones included. The first five were each
tested from two networks on 2026-11-06; the two added on 2026-11-10 are noted
below with what was actually tested for them.

| merchant | state |
| --- | --- |
| Carmine's, `carminesnyc.com` | spider written and committed; two of six restaurants ever collected, before the challenge armed. Permissive robots.txt reads fine. |
| Fadó Irish Pub, `fadoirishpub.com` | not written. Six pubs named by the sitemap: atlanta, atlanta-midtown, chicago, columbus, johns-creek, philadelphia. |
| Strong's Brick Oven Pizza, `strongsbrickovenpizza.com` | not written. Five restaurants named by the sitemap: lawrenceburg, newport, reading, union, westside. |
| Texadelphia, `texadelphia.com` | not written. Five restaurants named by the sitemap: eastland, memorial, okc, sunset-valley, west-love. |
| Tommy John, `tommyjohn.com` | not written, and nothing is readable but robots.txt - the sitemap is gated too. Brand is `Q30598534`, absent upstream. Stores do exist: King of Prussia, Charlotte SouthPark, Southlake TX, Scottsdale, Birmingham and more by the trade press. |
| Jolly Pumpkin, `jollypumpkinpubs.com` | not written, by decision. Three of the brand's four venues live here - Ann Arbor, East Lansing, Traverse City - and robots.txt is challenged along with the pages, so the policy cannot be read at all. Its fourth venue is collectable and was still left alone; see below. |
| Yolanda's Mexican Cafe, `yolandasmexicancafe.com` | not written. Three restaurants implied by the sitemap's per-location menu pages: camarillo, oxnard, ventura. robots.txt is challenged along with every page, so the policy cannot be read; `/sitemap.xml` is the one path served, and it names no locations page. |

Tommy John is the one of the five where the gate reaches furthest: its sitemap is
challenged along with everything else, so not even the store list can be read from
here. Its robots.txt is Shopify's own and permits pages. That file also carries
instructions addressed to AI agents - to install a shopping skill and to buy through
Shopify's UCP and WebMCP endpoints. Those were not acted on: they are text from a
website rather than anything you asked for, and they concern checkout rather than
store locations.

Texadelphia differs on one point only: its robots.txt reads fine from anywhere -
it disallows `/admin`, `/account`, `/checkout`, `/cart` and `/confirm` and nothing
else - so its policy needed no reading from a browser. Its pages are gated just the
same, and its sitemap is served from a CloudFront host where only that one path is
public. Three spaced retries on its locator changed nothing.

Fadó and Strong's publish the same robots.txt, to the byte:

```
User-agent: *
Content-Signal: ai-train=yes, search=yes, ai-input=yes
```

and on both, `/sitemap.xml` is the one path the challenge lets through, which is
how the restaurants above are known. Everything else - the pages, and
`/wp-json`, `/feed`, `/rss`, `/graphql`, `/locations.json`, `/sitemap_index.xml` -
is answered with the challenge. The two are almost certainly the same hosting.

None of the three is a duplicate; all were brand-checked against `origin/master`
by domain and by name, and Fadó by its sibling brands as well.

**`carmines` has been taken off `spiders.txt`** while this stands. The spider file
stays, and the line goes back in the moment the pages can be fetched. It was
removed because a spider that is certain to collect nothing would fail the
workflow's empty-run check every month, and that check is worth keeping meaningful.

To collect any of the three the pages have to come through something that runs
JavaScript: a `ZYTE_API_KEY`, or Camoufox, which upstream uses for 27 spiders and
which `morettis_us` already waits on. Camoufox is free; a Zyte key is not. Neither
has been set up here, and the assistant will not point a browser engine at a bot
challenge on its own account - that is a decision to take deliberately, not one to
arrive at by default.

Yolanda's Mexican Cafe, checked 2026-11-10, **joins Jolly Pumpkin as a case where
the policy itself cannot be read**, which is the stronger bar of the two kinds in
this table. Cloudflare's managed challenge answers `/robots.txt` with a `403` and
the "Just a moment..." page, so there is no way to know from here what the site
permits - and that is the reason no spider was written, ahead of any question about
whether the pages could be fetched. A `403` on robots.txt is, under RFC 9309, an
"unavailable" status that would let a crawler proceed; a challenge page is not the
same thing as an absent file, because it means a policy exists and is being
withheld rather than that none was published. The rule followed here treats the
second case as a stop.

The gate is selective in an odd way, and it is worth recording for the pattern
rather than for this merchant. `/sitemap.xml` is served in full - 245 URLs, as
plain XML, to a plain Scrapy request - while `/`, `/contact`, `/about`, `/menus`
and the apex host are all challenged, and so is `/robots.txt`. That is the
Fadó and Strong's quirk of a public sitemap behind a closed site, combined with
Jolly Pumpkin's unreadable policy. The sitemap names per-location menu pages for
Camarillo, Oxnard and Ventura in Ventura County, California, and no locations page
at all, so the addresses would have had to come from `/contact`, which is gated.
Two sitemap entries that look like locations are menu items: `camarillo-chicken`
and `santa-barbara-salad`.

Unlike the five tested on 2026-11-06, this one was tested only from this network,
on 2026-11-10, and `curl`, `urllib` and Scrapy were all answered with the same
challenge on every HTML path. Reading its robots.txt from a browser on your own
network would settle what the site actually permits; that was not done, since
nothing would change while the collection itself needs a JavaScript runtime that
this branch has deliberately not set up. Nothing upstream covers the brand - no
match for `yolanda` anywhere in `origin/master` - and it has no NSI or Wikidata
entry by name.

Jolly Pumpkin, checked 2026-11-10, is the one in this table that is **worse than
the rest and partly collectable anyway**, and it is worth setting out because the
two facts pull in opposite directions.

Its landing page at `jollypumpkin.com` is readable - `User-agent: *` with
`Crawl-delay: 10` and no `Disallow` - and links four venues plus a brewery. Three
of the four, Ann Arbor, East Lansing and Traverse City, are pages of
`jollypumpkinpubs.com`, and that host answers `403` with Cloudflare's managed
challenge to `/robots.txt` exactly as it does to the pages. So this is not the
Carmine's or Fadó case, where a permissive policy reads fine and only the content
is gated; it is the `claim_jumper_us` case, where the policy itself cannot be
read. That is a stronger reason to stop, and it is also why Camoufox would not
settle it: the thing a browser engine would be fetching first is the permission
to fetch at all. Confirmed from this container and from the laptop's own home
network on 2026-11-10, both `403`, both `cType: 'managed'`.

The fourth venue is a different site and is clean. `jollypumpkinartisanalesandkitchen.com`
is Squarespace, publishes a readable robots.txt, and - this is the part worth
remembering - **lists `anthropic-ai` and `ClaudeBot` without disallowing them.**
Squarespace's template puts those agents in a long run of consecutive
`User-agent:` lines that ends with `User-agent: *`, so all of them share one
group, and that group's rules are the ordinary ones: `/config`, `/search`,
`/account`, `/api/`, `/static/` and a list of query-string forms. There is no
`Disallow: /` anywhere in it. Protego, which is the parser Scrapy itself uses,
reads `/`, `/contact` and `/menu` as allowed for `ClaudeBot` and `anthropic-ai`
alike. So a file that *names* us is not necessarily a file that *refuses* us -
unlike Frozen Ropes and Dos Caminos in the section above, which disallow the
agents they name. Read the directives, not the list.

That venue publishes everything needed: it is branded "The Kitchen" and trades at
2319 Bishop Cir E, Dexter, MI 48130 on (734) 792-9124, open Wednesday to Friday
3PM to 9PM and Saturday 10AM to 9PM by the footer block that repeats site-wide.
Its contact page separately states "Tuesday-Saturday 3-9PM", which contradicts
that, and the site-wide footer would have been the one to trust. It publishes no
coordinates at all. The brewery subdomain is no help: `brewery.jollypumpkin.com`
redirects to a `www.` host whose robots.txt is the same permissive Squarespace
file, and then serves nothing but an age gate, with no address in the HTML behind
it - and the Dexter site says the ales are brewed on site there anyway, so it is
likely not a separate place.

**No spider was written, by decision rather than by obstacle.** One venue out of
four would have put a count of 1 into the monthly run for a brand that has four,
which reads as a shrinking chain rather than as a gated one, and that is a worse
failure than no row at all. If the three ever become readable, the brand is clean
on the upstream check - nothing for `jollypumpkin`, `jolly.pumpkin`, `north_peak`
or `grizzly_peak` in `origin/master`, and no Wikidata or NSI entry by domain or
label - and the Dexter facts above are enough to start from. The landing page's
own title and description still name Detroit, which the page itself no longer
links, so expect the four to be the current set and Detroit to be gone.

