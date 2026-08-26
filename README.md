# Breakfast Briefing — daily news digest

Generates the daily "Breakfast Briefing" Google Doc in
[this Drive folder](https://drive.google.com/drive/folders/1ff3EpR5ER6AxCopLDrVOlaQVlVhi2LzQ),
matching the format of the existing briefings.

## How it works

A scheduled task (`breakfast-briefing`, weekdays 06:30) runs this chain:

1. **`fetch_feeds.py`** fetches ~190 sources and writes ~615 candidates to JSON.
2. **`shortlist.py`** assigns each candidate to one of the seven briefing sections and
   prints them numbered, suppressing celebrity/entertainment chaff.
3. **Claude** picks item numbers per section — no volume cap, typically 120–200 items.
4. **`compose.py`** turns those numbers into the final HTML, copying every headline,
   URL, outlet and author verbatim from the JSON, and saves a markdown backup.
5. **Claude** creates the Google Doc from that HTML, then reads it back to verify.

Stories come from RSS, not web search. Every item carries its own publish timestamp, so
the cutoff is exact rather than guessed, and the sweep plus curation costs roughly 60–80k
tokens instead of the ~400k the original search-based version used.

Seven, in this fixed order: **Religious Freedom & Persecution**, **Free Speech**,
**Marriage, Family & Education**, **Gender, Identity & Sexuality**, **Life**,
**Church & Society** (church and public life, CofE, Vatican, faith stories not covered
above), **Other** (interesting leftovers — politics, law, migration, culture war, tech).

Section sizes vary a lot day to day. Free Speech is often small — some days the Free
Speech Union publishes nothing at all — and a short section is the right answer.

### How items are assigned

`shortlist.py` scores each headline against weighted keyword sets. Three details matter:

- **Priority, not first match.** The five specific sections win first; Church & Society
  is the residual faith bucket; Other is the residual interest bucket.
- **Source hints.** Single-issue outlets route their own items: anything from the Free
  Speech Union, spiked, FIRE or Reclaim The Net leans Free Speech even when the headline
  never says "free speech" (Sex Matters' "BBC Northern Ireland's coverage of the
  cancellation of WRN NI's panel" matches no keyword at all). Without this, Free Speech
  collected 6 items instead of 22.
- **Chaff suppression.** ~110 items a day are dropped as celebrity, entertainment, sport,
  broadcast listings or lifestyle filler, and unmatched items must still read as public
  affairs to reach Other. Without it Other was 172 items of Spectator arts and history
  pieces. Audit with `python3 shortlist.py today.json --show-chaff`.


### Freshness window and deduplication

The window is **36 hours** (84 on Mondays, to reach back to Friday morning). That
deliberately overlaps the previous run by 12 hours so nothing published near a cutoff
is missed. The overlap is free: `seen.json` records every story used in an earlier
edition and silently drops repeats. Verified — running the sweep twice in a row
returns ~775 items the first time and ~25 the second.

So the two settings work together: a generous window catches everything, and the
dedup cache guarantees no story reaches the doc twice.

Suppressed stories are **listed, not hidden**: the shortlist ends with "Already sent in
an earlier edition", each with its send date, so "already sent" can be told apart from
"missed" — and a still-running story can be deliberately repeated. This exists because
five of the nine articles Chris reported missing on 12.08.2026 had in fact run the day
before.

**Only published stories are marked seen**, and `compose.py` does the marking — not the
sweep. This matters: the sweep returns ~600 candidates and an edition uses a couple of
hundred, so marking everything swept silently burns the rest. It did exactly that on the
first run, consuming 538 unused stories, which is why marking moved to compose.

## Ordering within a section

Every section runs **UK first, then Europe, North America, Australia/NZ, Asia, Africa,
Latin America, global bodies**, and finally anything unplaced — the pattern the
hand-made briefings follow. `regions.py` owns this, and both `shortlist.py` (which
presents candidates in that order) and `compose.py` (which re-applies it as a backstop)
import from it, so the two cannot drift apart.

A story's region comes from place names in its headline, falling back to where the outlet
is based. Two details earn their keep:

- **Headline beats outlet.** "Australia adds sexuality and gender identity to census" is
  an Australian story even when an Iowa paper files it.
- **Outlet-only placements rank below headline placements inside the same tier**, so a
  British outlet writing about American sport (PinkNews on the NBA) doesn't lead the UK
  block ahead of stories actually about Britain.

Accuracy is roughly 90%. Unrecognised items become `Unplaced` and sort last rather than
being guessed into a leading tier. Watch for substring traps when editing the patterns —
`tories` matched inside "s-tories" and put Massachusetts stories in the UK block until
word boundaries were added, and `england`/`wales` need guards against "New England" and
"New South Wales".

No sub-headings: items are simply listed in region order.

## Sections

## Running it by hand

```bash
cd ~/Downloads/breakfast-briefing && python3 fetch_feeds.py --json /tmp/today.json > /tmp/sweep.txt && python3 shortlist.py /tmp/today.json
```

Then write picks as `{"Section name": [12, 34], ...}` and compose:

```bash
cd ~/Downloads/breakfast-briefing && python3 compose.py /tmp/today.json /tmp/picks.json --md out/copy.md > /tmp/briefing.html
```

Useful flags:

| Flag | Effect |
| --- | --- |
| `--hours N` | Override the freshness window (default 36, or 84 on Mondays) |
| `--mark` | Record every swept item as seen. Rarely wanted — see below |
| `--include-seen` | Ignore the dedup cache (shows stories used in past briefings) |
| `--json PATH` | Also dump structured results |
| `--no-resolve` | Skip scraping index pages for direct links (faster) |

Needs only Python 3 — no pip installs, so nothing to break in an unattended run.

## Files

- `sources.opml` — the Feedly export. Replace it with a fresh export whenever you
  reorganise Feedly; the script re-reads it every run.
- `extra_feeds.txt` — hand-maintained overrides, and the file to edit to change
  coverage. Corrected URLs for feeds that moved, ~40 outlets missing from Feedly,
  Google News fallbacks, and lists of dead feeds and blocked aggregators.
- `seen.json` — URLs already **published**, so a story never appears twice. Pruned
  after 21 days.
- `fetch_feeds.py` — the fetcher.
- `shortlist.py` — assigns candidates to the seven sections. `SECTIONS`, `SOURCE_HINTS`,
  `CHAFF` and `OTHER_ALLOW` are all at the top; edit them if stories keep landing in the
  wrong place. Items are flagged `£` (paywalled) and `↗` (Google News redirect link).
- `compose.py` — picked numbers → the briefing HTML. Exists so no field is ever retyped
  by hand into the Drive call. Also records the published stories in `seen.json`.
- `regions.py` — the UK-first ordering, shared by shortlist and compose.
- `resolve.py` — converts Google News redirects to publisher URLs at compose time.
- `discover_feeds.py` — finds real feeds for outlets that only arrived via Google
  News. Run `python3 discover_feeds.py <sweep.json>` to see what's missing, add
  `--write` to append them. Google News entries are kept as the safety net.
- `out/` — markdown copies, written only when the Drive upload fails.

### Adding or removing a source

Edit `extra_feeds.txt`. One source per line, `mode | category | name | url`:

- `pass` — issue-specific feed, keep every item
- `filter` — general news feed, keep only items matching the topical keywords
- `gnews` / `gnewsf` — outlet publishes no usable feed; search Google News for
  `site:<domain>`. Links are Google redirects (see limits below)
- `bing` / `bingf` — same idea via Bing News, which unlike Google exposes the real
  publisher URL. Coverage is thinner (~14 items) but the links are direct
- `scrapesrc` / `scrapesrcf` — outlet has no feed anywhere: read its index page as a
  source. No dates, so a link absent from `seen.json` counts as new
- `scrape` — an index page read *only* to turn Google News redirects into direct links
- `disable | <url fragment>` — never fetch this (dead, stale or hijacked feed)
- `block | <outlet or domain>` — never include items from this source (aggregators)

The `f` suffix on any mode means "apply the topical keyword filter". Use it for broad
general outlets and omit it for single-issue sources.

The keyword list lives at the top of `fetch_feeds.py` (`KEYWORDS`). Add a term there
if on-topic stories from general outlets are being missed.

### Paywalled outlets

Paywalled sources are included deliberately — Telegraph, Times, Spectator (UK and
Australia), The Critic, UnHerd, spiked, Church Times, Catholic Herald, WSJ, NYT,
Washington Post, Bloomberg, The Australian, SMH, Herald Scotland, Economist. A feed still gives the headline, link and
date even when the article needs a subscription, which is all the briefing needs.

`PAYWALLED_DOMAINS` in `fetch_feeds.py` lists them, matched on the article's own domain
so lookalikes ("The Times of India", "Bloomberg School of Public Health") are not
caught. Matching items are flagged `£` in the sweep output and the digest appends
"(£)" after the outlet name. Add a domain to that set to mark a new one.

Several need special handling, all already configured:

- **The Telegraph's own RSS feeds are abandoned** — `telegraph.co.uk/news/rss.xml` was
  last updated in June 2026. It comes in via Bing (fresh, direct links) plus Google
  News for breadth.
- **The Spectator publishes no RSS at all**, and Google and Bing barely index it, so its
  index pages are scraped directly. Note the UK edition now serves articles from
  `spectator.com`, not `spectator.co.uk` — its own homepage links there.
- **The Critic dates pieces to a future magazine issue** (weeks ahead). The sweep treats
  any future date as "just published" rather than discarding the item, since a feed only
  lists what already exists. Dates more than 120 days ahead are still rejected as junk.
- **UnHerd's feed contains an invalid UTF-8 byte** mid-CDATA that kills a strict XML
  parser. `sanitise_xml()` repairs invalid bytes and bare ampersands and retries, which
  fixed UnHerd and several other feeds that previously failed to parse.

### Commentary magazines are unfiltered

The Spectator, The Critic, UnHerd and spiked are read **without** the keyword filter, on
purpose. Their headlines routinely carry no matching keyword even when the piece is
central to the briefing — spiked's "Jason Arday's enablers are insufferable pseuds, too"
is the free-speech story of the day and matches nothing in `KEYWORDS`. Filtering them
lost exactly the commentary they're read for.

The cost is some genuinely off-topic material in the candidate list (Henry VIII, Ricky
Gervais, Immanuel Kant). That is intended: volume is capped per source and the digest
step is told to drop what doesn't fit.

## Document format

`compose.py` emits real document structure rather than the old wall of bold text:

```html
<h1>Breakfast Briefing</h1>
<p><i>Thursday 13 August 2026</i></p>
<h2>Religious Freedom &amp; Persecution</h2>
<p><a href="URL">Headline as a plain link</a><br/>
<span style="color:#666666"><i>Outlet (£) · Author</i></span></p>
```

Google Docs converts `<h1>`/`<h2>` to genuine Heading styles, which bring their own
spacing *and* populate the outline sidebar — so the section list doubles as navigation.
A `<br/>` inside a `<p>` becomes a second paragraph, giving the headline-then-source
layout with breathing room between items.

## Known limits

- **Google News redirect links.** `resolve.py` converts these to publisher URLs for the
  items actually picked, by taking the publisher domain from the feed's `<source url>`
  and either matching the story on the publisher's front page or constructing and
  verifying a slug URL. It succeeds about 40% of the time and takes ~2 minutes, so it
  runs at compose time on the picked items only, and caches results in `resolved.json`.
  The stronger lever is curation: prefer an unmarked (direct) item over a ↗ one covering
  the same story. Detail on why resolution is hard: roughly 260 of ~615 candidates link to
  `news.google.com/rss/articles/...` rather than the publisher. These come from
  outlets with no usable feed (Catholic Herald moved to Webflow and dropped RSS;
  The Times, WORLD, CBN, Premier and Baptist Press block or omit feeds) and from
  the Google News keyword alerts in the Feedly export, which are the main source of
  long-tail regional coverage. Google no longer permits server-side resolution of
  these links — the old base64 and batchexecute tricks are both dead. Two fallbacks
  recover about 70 per run: scraping publisher index pages, and matching against every
  direct link already in the sweep. The rest still work when clicked, and the task is
  told to prefer a direct-link version when one exists.
- **The Times.** Has no RSS anywhere, so it arrives only through Google News with
  redirect links, and is thinner than in a hand-made briefing.
- **Coverage overlap.** On a like-for-like test against the human-curated 11.08.2026
  briefing, the sweep contained roughly two thirds of the stories that were chosen.
  Selection will never match a human's exactly — the sweep supplies the raw material.
- **Section balance is uneven by nature.** From one day's data: Persecution ~37 candidates,
  Free Speech ~22, Family ~32, Gender ~112, Life ~111, Church ~140, Other ~52. Gender,
  Life and Church always have more to choose from than the other four.
- **App must be open.** Scheduled tasks only run while the Claude Code app is
  running; if it's closed at 06:30 the briefing generates at next launch.
- **Docs cannot be edited after creation.** The Drive connector can create and read but
  not update, so the briefing is verified by reading it back and reporting any problem —
  a mistake has to be fixed by hand in the Doc. Drive also occasionally returns a quota
  error on create; a second attempt a moment later normally works.
