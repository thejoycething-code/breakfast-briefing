---
name: breakfast-briefing
description: "Daily \"Breakfast Briefing\" news digest — RSS-based pipeline in ~/Downloads/breakfast-briefing, scheduled task, Drive folder ID, known limits"
metadata: 
  node_type: memory
  type: project
  originSessionId: 84d457ef-6b54-4c7b-8bd0-1fe284f8e407
  modified: 2026-08-16T12:34:31.759Z
---

Chris's daily curated news digest ("Breakfast Briefing"), a Google Doc in Drive folder
`1ff3EpR5ER6AxCopLDrVOlaQVlVhi2LzQ`. Automated 2026-08-12 by the scheduled task
`breakfast-briefing` (weekdays 06:30 local; prompt at `~/.claude/scheduled-tasks/breakfast-briefing/SKILL.md`).

**Pipeline lives in `~/Downloads/breakfast-briefing/`** — see its README.md. `fetch_feeds.py`
(pure stdlib, no pip deps) sweeps ~190 sources from `sources.opml` (Chris's Feedly export)
plus `extra_feeds.txt` overrides, filters by each item's own pubDate, dedupes against
`seen.json`, and prints ~615 candidates in ~50s. `shortlist.py` assigns them to **seven**
sections and prints them numbered; Claude picks numbers (no volume cap, ~120–200 items);
`compose.py` turns the picks into HTML copying every field verbatim from the JSON; Claude
creates the Doc via the Drive connector with `contentMimeType: text/html` and reads it back.

**Every candidate is READ and tier-ranked by subagents** (Chris asked 13.08.2026; "a layer of
context" means review the items, NOT add editorial lines to the doc — the document format is
unchanged). `slice_shortlist.py` cuts ~750 candidates into ~16 self-contained slices, each
carrying the review brief; one general-purpose subagent per slice returns
`index | tier 1-3 | six words why`. Merge tier 1 (all), tier 2 (until full), tier 3 (only for
thin sections). Costs ~50k subagent tokens per slice but almost nothing in the parent context,
since only the ranked lines come back. Validated on one slice: it surfaced the SCOTUS women's-spa
case, the SCOTUS trans-athlete ruling and a prisoner-transfer ruling, all of which the keyword
ranking had buried. Keyword score still decides the SECTION; judgement now decides inclusion.

**Commentary magazines must ALL be unfiltered.** Spectator Australia sat on `filter` while its
UK sibling was `pass`, so "It's a mad mad mad mad world" was dropped for matching no keyword
(Chris flagged it 13.08.2026). If a source is read for allusive commentary, it cannot be
keyword-gated. Same reasoning as spiked/Critic/UnHerd/Spectator.

**New Zealand and Utah were uncovered** (Chris, 13.08.2026): the FSU NZ / Bradbury blog-gagging
case ran in The Post and the ACLU-vs-LDS filing in the Salt Lake Tribune, neither of which was a
source. Added thepost.co.nz/rss, stuff.co.nz/rss, an @NZ Google edition, and sltrib via
gnews+bing (it serves HTML on every feed path).

**Daily Pioneer is blocked** — link integrity untrustworthy (its 13.08 URL was a resolver guess
that 404s). Blocked by domain and name in extra_feeds.txt.

**Repeats are allowed** (Chris, 13.08.2026): a story running in an earlier edition is no longer
suppressed. shortlist.py keeps it in its section marked `[ran DD]`. Multiple angles on a big
story are wanted — two or three.

**NINE sections, fixed order** (restructured 2026-08-15/16 at Chris's request; superseded the
earlier seven): Religious Freedom & Persecution; Free Speech & Civil Liberties; Marriage, Family
& Education; Gender, Identity & Sexuality; Life; Church & Religion (all religion grouped);
Immigration & Asylum; Politics, Government & Society (capped at 40); Other. `ORDER` in compose.py
must stay in step with `SECTION_NAMES` in shortlist.py — compose silently ignores picks under an
unknown section name, dropping items without warning. Free Speech is legitimately small on many
days; do NOT cap it to remove weak items, just remove them.

**"Other" is a positive category, not a landfill** (Chris, 2026-08-16): genuinely interesting
high-ranking news — new AI features, science, medicine, world events — NOT whatever failed to
match another section. `OTHER_INTEREST` enforces this (159 → 24 candidates).

**Region order** (`TIERS` in regions.py, settled 2026-08-15): UK → Ireland → Europe →
International → United States → Latin America → Canada → Australia → New Zealand → Africa →
Asia → Middle East → Unplaced. This supersedes the earlier UK→Europe→North America ordering.
US stories are capped at 25% of a section unless they rank very high (`cap_us_share`).

**Two classifier lessons, both learned the hard way:** keyword matching alone gave Free Speech
only 6 of 615 items, because FSU/spiked/Sex Matters headlines rarely say "free speech" — hence
`SOURCE_HINTS`, which routes single-issue outlets even when no keyword matches (→22 items). And
an ungated "Other" filled with 172 Spectator arts/history pieces, hence `CHAFF` plus the
`OTHER_ALLOW` public-affairs gate (→52). Audit with `shortlist.py <json> --show-chaff`.

**Chris does NOT want news.google.com links in the doc** (said so 2026-08-12). `resolve.py`
converts them: publisher domain comes from the feed's `<source url>` attribute, then match the
story on the publisher's front page or construct+verify a slug URL (this is how
adfinternational.org/news/nigerian-court-rules-… was recovered). ~40% hit rate, ~2 min, so it
runs at compose time on picked items only, cached in resolved.json. The bigger lever is
curation: prefer an unmarked item over a ↗ one covering the same story.

**`discover_feeds.py` closes the Google-link gap at source** (Chris asked 2026-08-12 to subscribe
directly to every outlet that arrived via Google News, keeping the Google feeds as backup). It
reads `<link rel=alternate>` off each publisher's front page, falls back to common feed paths, and
verifies the feed parses. First run: 163 unsubscribed publishers → 79 feeds added, sources 191→268,
sweep 50s→62s, and redirect-only candidates fell 239→200 while resolved links doubled to 116 —
because the same story now arrives directly and wins the dedup. Re-run it whenever redirects creep
up. Unescape HTML entities in discovered URLs (a `&amp;` in one broke it).

**Be precise about WHICH edition a story ran in.** On 2026-08-12 I told Chris nine flagged
articles had "run in yesterday's edition" — wrong. They ran in the 20260812 doc I generated at
01:07 *that same morning*, not in the human-made 20260811 briefing. Chris rightly pushed back.
Two same-day docs existed (01:07 old-format + 06:03 new-format preview) and the first had consumed
the second's best stories. Resolved by treating the 01:07 doc as superseded and releasing its 77
URLs from seen.json. Lesson: never say "yesterday" — name the document (20260811 vs 20260812), and
never publish two editions for the same date.

**Suppressed items are visible, not hidden:** fetch_feeds tags them `seen_on` and shortlist prints
an "Already sent in an earlier edition" list with dates, so a still-running story can be
deliberately repeated and "already sent" is distinguishable from "missed". Check it before
diagnosing a coverage gap.

**Dedup precedence: keep the higher-tier outlet, always.** I made this mistake TWICE on
2026-08-12 — dropped the Catholic Herald Massachusetts piece for OSV, then dropped the
Telegraph's "Labour allows Left-wing councils to defy trans guidance" (idx 444) because a
GB News version was already picked. Keeping the secondary outlet over the paper of record is
backwards. When two items cover one story, include the tier outlet, or include both.
Now BUILT: `cluster_duplicates()` in shortlist.py groups same-story items by significant-word
overlap and marks one `<<< TAKE THIS ONE`, the rest `(same story as N - prefer that)`, ranked by
rank_score so outlet tier decides. Verified on the Telegraph/GB News councils pair: Telegraph
leads. ~120 near-duplicates flagged per sweep.

**Two curation lessons from Chris's 2026-08-12 feedback on missing articles:** (1) do NOT drop a
core outlet's version as a "duplicate" — he wanted the Catholic Herald Massachusetts piece even
though OSV/LifeSiteNews covered the story; the two-angles rule is about wire copy, not about
outlets he reads. (2) When he says an article is missing, check seen.json first — two of the five
he flagged had already run in the 12.08 edition, so dedup was working correctly. India coverage
was a genuine gap: ToI top-stories misses city/state reporting and All India Radio was absent;
both now added.

**Regional Google News editions (added 2026-08-12):** a GB/US edition barely indexes non-Western
reporting, which is why two Indian abortion stories were missed. `gnews_url()` now accepts an
`@CC` suffix for the edition and a `kw:` prefix for keyword (rather than site:) searches — e.g.
`kw:abortion OR surrogacy@IN`. India, Nigeria, Kenya, Pakistan, Philippines, Ireland, Australia
and Canada editions added. Never use a pipe inside those queries: `|` is the extra_feeds.txt
field separator. Sources 270 -> 280, candidates ~600 -> ~920.

**Source credit line carries a leading dash** (`- The Telegraph (£) · Author`), matching the
hand-made briefings. Chris asked for this on 2026-08-12.

**Geographic ordering (Chris chose this 2026-08-12, "Option B", explicitly no sub-headings):**
every section runs UK → Europe → North America → Australia/NZ → Asia → Africa → Latin America →
global → Unplaced, owned by `regions.py` and applied by both shortlist.py and compose.py.
Region comes from headline place names first, outlet home country second; outlet-only placements
rank *below* headline placements in the same tier so PinkNews-on-the-NBA doesn't lead the UK
block. ~90% accurate; unrecognised → "Unplaced", sorted last, never guessed into a lead tier.
Beware substring traps when editing: `tories` matched inside "s-tories" (put Massachusetts in the
UK block), and england/wales need guards for "New England"/"New South Wales". Earlier the task
prompt said UK→US→Europe, which contradicted Chris's preference — fixed.

**Typography matches Chris's own hand-made 20.04.2026 briefing** (he asked 2026-08-15 for the
same sizes and colours). Constants at the top of compose.py: Title 36pt #002060 bold; date 14pt
#00b0f0 bold; section 16pt #17365d bold; headline 10pt #3091f2 bold; credit 10pt #000000 bold.
Title and date must be styled `<p>`, not `<h1>`, or Docs normalises them; sections stay `<h1>`
so the outline sidebar works. Per story: headline link, `<br/>` (= shift+enter), then
`- Outlet (£) | Author`, then a **blank spacer paragraph** (Chris asked 2026-08-16). Docs DROPS a
truly empty `<p>`, so `SPACER` carries `&nbsp;` at 10pt. Authors appear on commentary only.

**Drive connector can create and read but NOT update** — a published briefing cannot be edited
programmatically, so the task reads the doc back and reports discrepancies instead. It also
returns a spurious "Resource has been exhausted" quota error sometimes; a second attempt works,
but check the folder first so you don't create a duplicate. First real edition
(20260812, 77 items, all direct links) shipped with one mistyped author byline because the HTML
was hand-typed into the tool call — build the HTML with a script and copy fields verbatim.

**Why RSS, not web search:** the first version used four WebSearch subagents — ~400k tokens per
run and unreliable dates. RSS gives an exact cutoff and ~35k tokens. Do not reintroduce
search-based gathering.

**Only PUBLISHED stories are marked in seen.json, and `compose.py` marks them — not the sweep.**
Marking everything swept burns unchosen candidates: it consumed 538 unused stories on the first
run (2026-08-12), which is why marking moved to compose. `fetch_feeds.py --mark` still exists but
is almost never wanted.

**Window is 36h (84h Mondays), deliberately overlapping the previous run** so nothing near a
cutoff is missed; `seen.json` makes the overlap free by dropping repeats (verified: two
back-to-back runs returned 741 then 25 items). Chris asked for this explicitly on 2026-08-12.

**Paywalled outlets are wanted, not avoided** (Chris asked for Spectator/Telegraph/Times
on 2026-08-12). Feeds still yield headline+link+date behind a paywall. `PAYWALLED_DOMAINS` in
fetch_feeds.py drives the `£` flag in the sweep output → "(£)" in the doc; match on domain, not
outlet name, or "The Times of India" and "Bloomberg School of Public Health" get flagged.
Telegraph's own RSS is abandoned (stale since June 2026) so it comes via Bing + Google News;
the Spectator has no RSS anywhere and is index-scraped from **spectator.com** (it left
spectator.co.uk). Bing News site: search is the trick for direct publisher links — its
apiclick wrapper carries the real URL in the `url=` param, unlike Google's opaque redirects.

**Commentary magazines (Spectator, The Critic, UnHerd, spiked) are deliberately UNFILTERED**
(Chris asked for all four on 2026-08-12). Keyword-filtering them lost the pieces they're read
for — spiked's "Jason Arday's enablers are insufferable pseuds" is the free-speech story of the
day and matches no keyword. Accept off-topic noise (arts, history) and let curation drop it.
Two gotchas fixed while wiring these up, both generic: **The Critic dates pieces to a future
magazine issue** (weeks ahead), so future dates are clamped to now rather than rejected; and
**UnHerd's feed has an invalid UTF-8 byte mid-CDATA**, so `sanitise_xml()` retries a failed
parse after repairing bad bytes and bare ampersands. thecritic.co.uk returns 403 to scrapers.

Doc is titled `YYYYMMDD: Breakfast Briefing`.

**Known limits:** ~190 candidates/run carry `news.google.com` redirect links (Catholic Herald
dropped RSS on its Webflow move; Times/WORLD/CBN/Premier/Baptist Press block or omit feeds).
Google no longer allows server-side resolution of those links; the script scrapes publisher
index pages and swaps in direct URLs where headlines match (~30/run). Telegraph and Times are
underrepresented vs a hand-made briefing. Coverage overlap with the human-curated 11.08.2026
edition measured ~two thirds.

Feedly Pro was considered and rejected: no Claude connector exists, its API needs a paid plan,
and `extra_feeds.txt` gives the same source control for free. Scheduled tasks only run while
the Claude Code app is open. Revisited 2026-08-15: Feedly's API and search are now Enterprise-only,
so the decision stands.

**Test editions run with `--no-mark`** so they don't consume candidates from the scheduled 06:30
run, and are uploaded with a "TEST" title prefix. `trash_file` sometimes returns "The caller does
not have permission" even when the trash succeeds — verify by listing the parent folder rather
than trusting the error.

**`scrape_index()` takes the card's HEADING, not all the anchor text, and reads the card's
printed date.** Modern sites wrap the whole card — kicker, date, headline, excerpt, "Read
More" — in one `<a>`, so the old all-text extraction produced headlines like "Press Release
July 9, 2026 European Parliament strongly condemns… Read More", and because scrapesrc was
treated as dateless the site's entire archive entered as new. Both fixed 17.08.2026 after
Chris pointed at adfinternational.org/newsroom/. Dates need `parse_card_date()` ("August 13,
2026"), which `parse_date()` cannot handle — it only does RFC-2822 and ISO. A scraped card
WITH a date now obeys the window; only genuinely undated cards fall back to the seen-cache
diff, which is still how The Spectator works (41 clean, dateless cards — verified unbroken).

**ADF International's only working route is scraping /newsroom/** — `adf.uk/feed/` and
`adfinternational.org/feed/` both parse but serve zero items, `/newsroom/feed/` is WordPress's
*comments* feed and permanently empty, and Google indexes nothing for the domain. Do not
re-probe those. A `kw:"ADF International" OR "Alliance Defending Freedom"` gnews feed runs
alongside it to catch ADF's cases as reported by other outlets, which is often the better item.

**`check_sources.py` exists because a dead source and a quiet news week look identical.**
Live Action News had been unreachable for an unknown period; Chris flagged one of its stories
as missed and it looked like a ranking failure. It reports sources failing 3+ CONSECUTIVE days
(one bad day is noise), keeps history in source_health.json, exits 1 if anything is broken, and
separates bot-walls from empty feeds. Scrape-mode sources must be counted by links, not
`<item>`, or every one reports as dead — the first run called The Spectator broken on a day it
supplied eight stories.

**liveaction.org and cmf.org.uk are deliberate bot walls** (Vercel `x-vercel-mitigated:
challenge` / Cloudflare Turnstile), not rate limits. Not to be worked around. Their Google News
index is stale since April 2026 and Bing has nothing, so there is no legitimate route. The
daily pro-life beat survives it — LifeSiteNews gave 21 candidates and LifeNews 6 in one sweep.

**Summary-based keyword matching was tested and REJECTED (17.08.2026) — do not retry it.**
The prefilter reads the headline only (fetch_feeds.py line ~694) though `summary` is captured,
and matching both doubles what survives (110 → 221 across five feeds). Almost all of it is
noise, and not from a regex bug: "the fascinating lives of flies" matched *bird* migration,
an embroidery history matched "the church", a farm-emissions piece matched "unborn calf".
A passing mention in a long summary is not aboutness. Requiring 2+ distinct hits still admitted
a TV drama review. The working lever is the Spectator Australia one: move sources read for
judgement from `filter` to `pass`. Ten commentary/think-tank feeds were switched on 17.08.2026
(+18 real items); PinkNews was deliberately left filtered because its only gain was chaff.

**`disable | fragment` used to silently no-op on gnews/bing feeds** — the check sat inside a
`if not mode.startswith(("gnews","bing"))` branch, so the line looked applied and was not.
Fixed 17.08.2026; verified exactly one feed was affected. Also: `extra_feeds.txt` is
first-wins, so re-declaring a URL later in the file does nothing — edit the original line.

**The schedule is WEEKDAYS ONLY.** A gap in the folder over a Saturday/Sunday is correct, not a
failed run — check the calendar before reporting a missing edition (I got this wrong 2026-08-16).
