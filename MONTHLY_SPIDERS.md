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
group of brands. Four spiders were dropped from an earlier attempt at this branch
for exactly that reason:

| looked new | upstream already covered it as |
| --- | --- |
| `hot_topic_us` | `hot_topic` |
| `shaws_us` | `albertsons`, which carries 17 brands including Shaw's |
| `foodmaxx_us` | `save_mart_us`, which crawls `foodmaxx.com` |
| `build_a_bear_us` | `build_a_bear_workshop_us` |

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
| `tamollys_mexican_kitchen` | 6 | 2026-11-03 |
| `cyclone_anayas_us` | 5 | 2026-11-03 |

`the_palm` carries no country suffix because one of its 17 restaurants is in Mexico
City; the other 16 are in the US.

`eatzis_us` yields no coordinates. The markets' addresses link to Google places by
CID, which carries no position, and nothing else on the page publishes one, so the
six items are address-only. Worth knowing if a monthly run is matched on position
rather than on address.

Candidates held on per-merchant branches, each checked against upstream by brand
and genuinely absent: `cool_hand_lukes_us` (6). Also clean on that check and ready when wanted:
`abelardos_mexican_food`, `hh_bagels`, `one_stop_nutrition`, `the_great_frame_up`,
`uno_pizzeria_and_grill`.

Not yet brand-checked, and to be checked before adding: `claim_jumper_us`,
`home_depot_us`, `pc_richard_and_son_us`. Needing a Zyte key before they run at all:
`pep_boys`, `belk`, and those three. Needing Camoufox: `morettis_us`.
