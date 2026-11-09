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
| `heavenly_massage_us` | 5 | 2026-11-07 |
| `james_coney_island_us` | 5 | 2026-11-07 |
| `karinas_mexican_seafood_us` | 4 | 2026-11-06 |
| `new_orleans_hamburger_and_seafood_us` | 5 | 2026-11-09 |
| `roka_akor_us` | 5 | 2026-11-06 |
| `third_love_us` | 4 | 2026-11-06 |
| `tom_and_chee_us` | 5 | 2026-11-06 |
| `wildberry_cafe_us` | 5 | 2026-11-06 |
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
both turned away from any network, home ones included. Each was tested from two
networks on 2026-11-06.

| merchant | state |
| --- | --- |
| Carmine's, `carminesnyc.com` | spider written and committed; two of six restaurants ever collected, before the challenge armed. Permissive robots.txt reads fine. |
| Fadó Irish Pub, `fadoirishpub.com` | not written. Six pubs named by the sitemap: atlanta, atlanta-midtown, chicago, columbus, johns-creek, philadelphia. |
| Strong's Brick Oven Pizza, `strongsbrickovenpizza.com` | not written. Five restaurants named by the sitemap: lawrenceburg, newport, reading, union, westside. |
| Texadelphia, `texadelphia.com` | not written. Five restaurants named by the sitemap: eastland, memorial, okc, sunset-valley, west-love. |
| Tommy John, `tommyjohn.com` | not written, and nothing is readable but robots.txt - the sitemap is gated too. Brand is `Q30598534`, absent upstream. Stores do exist: King of Prussia, Charlotte SouthPark, Southlake TX, Scottsdale, Birmingham and more by the trade press. |

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
