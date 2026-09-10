---
name: breakfast-briefing
description: Generate the daily Breakfast Briefing news digest as a Google Doc (weekdays 05:15, ready by 6am, 9 sections)
---

Generate today's "Breakfast Briefing" — a curated news digest Google Doc for Chris Joyce (CitizenGO).

Stories come from a local RSS sweep, NOT web searches. Do not use WebSearch or research
subagents: the sweep already gathers and date-filters everything, and search would be slower,
cost ~10x the tokens, and lose the exact time cutoff.

## Step 1: Idempotency check
Work out today's date. With the Google Drive connector, search files with an **exact title
match**:
  parentId = '1ff3EpR5ER6AxCopLDrVOlaQVlVhi2LzQ' and title = '<YYYYMMDD>: Breakfast Briefing'
If that returns a file, STOP — do nothing further.

A doc whose title begins `TEST ` is NEVER an edition, whatever date follows it. Note it in
your final message and carry on publishing the real one; do not treat it as the day already
being done. Test drafts are deliberately parked in this folder under that prefix (Chris,
23.08.2026), so the "same-day doc under another name" clause below does NOT apply to them.

Use `title =`, never `title contains '<YYYYMMDD>'`. The substring form failed in both
directions on 17.08.2026: it matched a leftover `TEST 20260817: Breakfast Briefing (v3)` from
calibration, which would abort a legitimate run, and it did **not** match that day's real
edition, which had been published under a different title — so a check meant to prevent a
duplicate would have permitted one. If the exact match finds nothing but you can see a
same-day doc under some other name, say so in your final message rather than publishing a
second copy.

## Step 2: Sweep, then shortlist
  cd ~/Downloads/breakfast-briefing && python3 fetch_feeds.py --json /tmp/today.json > /tmp/sweep.txt 2>&1; head -6 /tmp/sweep.txt
  cd ~/Downloads/breakfast-briefing && python3 shortlist.py /tmp/today.json > /tmp/short.txt 2>&1; cat /tmp/short.txt

The sweep fetches ~340 sources and keeps items published in the last 36 hours (84 on Mondays, to
cover the weekend). **It now takes ~15 minutes rather than ~5**: since 25.08.2026 it also asks
Google to decode every Google News redirect that index-scraping could not resolve, at roughly
1.2s each. That is the single highest-value step in the pipeline — it took the share of leads
the ranker can actually read from 26% to 72% in one change — so do not reach for `--no-decode`
to save time. The header reports the two routes separately:

  gnews: N matched to a direct link, M decoded via Google, K still redirects

K should be single digits. If it is in the hundreds the decoder has broken, which is a
RESOLVER DEGRADED-class problem: say so prominently, because every undecoded redirect is a
story the ranker will judge on its headline alone.

Stories a previous briefing already published are **kept and flagged**
`[ran MM-DD]`, not dropped — a running story can legitimately appear on consecutive days, so a
repeat is your choice to make (Chris, 13.08.2026).

**The test is the STORY, not the outlet or the headline** (Chris, 31.08.2026). Same actors,
same document, same event means the same story and it should be deduped, however different
the outlet and wording. Checked against the archive that day: all three stories he first
queried had genuinely run — Morning Star News on the Pakistani Christian girl was the same 11
lawmakers and the same 20 August letter Hindustan Times ran on 28.08; EWTN's DOJ/faith-leaders
piece was the same 27 August meeting PR Newswire ran on 28.08; Newsweek's Florida story was
the same dispute Ars Technica ran on 27.08. A specialist outlet being the better citation is
an argument for picking it FIRST TIME, not for running the story twice.

**Where the flag is genuinely wrong is the opposite direction — it clusters different stories
together.** It is computed on headline word overlap, so on 31.08.2026 it filed a Vietnamese
pastor's 7-year sentence as the same story as an Indonesian pastor's. That is the case to
override: check whether the actors and the event really match before dropping, and drop when
they do. A same-outlet, same-headline flag (City Journal's WPATH piece, Iona's Tánaiste piece,
both 31.08) needs no thought at all.

The sweep does NOT mark anything itself, and
neither does compose.py any more; marking happens in Step 7, after the doc verifies. Do not pass
--mark.

shortlist.py assigns every candidate to one of the nine briefing sections and prints them
numbered. The sections, in doc order, are: Religious Freedom & Persecution,
**Free Speech & Civil Liberties**, Marriage, Family & Education, Gender, Identity & Sexuality,
Life, **Church & Religion**, Immigration & Asylum, **Politics, Government & Society**, Other.
Immigration and Politics were split out of "Other" on 14.08.2026, when it held 514 of 1,567
candidates — a third of the day, with the Clacton by-election and asylum-hotel policy buried
inside it. The split only re-routes items that reached no other section, so nothing else lost
anything.

**Use these names exactly.** They are the keys you pass to compose.py, which exits with
"unknown section(s) in picks" on any mismatch — so a stale name costs you the whole run, not
one item. Three were renamed on 15–16.08.2026 (Free Speech, Church & Society, Politics &
Elections are all former names). If in doubt, copy the headings shortlist.py prints rather
than typing them from here — **the commas in "Marriage, Family & Education" and "Gender,
Identity & Sexuality" are part of the key.** Both were written here without them until
21.08.2026, which failed a compose run: the reclass check reports every pick in the section
as misfiled ("classifier says Marriage, Family & Education"), so 49 of the 55 lines looked
like transposed indexes when the only fault was one missing comma in the section name.

Four caps apply and are enforced by compose.py, so do not hand-trim to hit them:
**Politics, Government & Society is capped at 40** (Chris, 15.08.2026), **Church & Religion at
30** (Chris, 23.08.2026), **Immigration & Asylum at 30** (Chris, 27.08.2026, after an edition
ran 45 of them), and **US stories may not exceed 30% of any section** — the figure
here read 25% until 24.08.2026, which was wrong: US_SHARE has been 0.30 since 18.08.2026.
Exempt from the US share: an item whose importance clears US_EXEMPT_AT, and **anything you
tiered 1 or 2**. Only tier-3 filler competes for the US quota. Added 24.08.2026 after Chris
marked up the TEST 20260824 draft — a Life list of ten stories "should have been included even
if it meant breaching the cap", three of which had been picked and then silently cut by this
cap because the only exemption was a keyword score. Exempting tier 1 alone was measured and
was not enough: all three were tier 2, and Life still lost 22 of 28 US picks, because pro-life
news is overwhelmingly American and a 30% share cuts most of that section's real candidates
every day.

**So tier 3 now carries real weight: it is the only tier a cap will cut.** Tier 3 means
"filler I am happy to lose". Do not park a story there because you are unsure — that is what
tier 2 is for. Free Speech is legitimately
small on many days — do not pad it, and do not cap it to squeeze weak items out; remove them.

**"Other" is a positive category, not a landfill** (Chris, 16.08.2026): genuinely interesting
high-ranking news — new AI features, science, medicine, world events, and long-form ideas
essays from the Ideas: Essays sources — NOT whatever failed to match another section.

**Marriage, Family & Education stays one section** (Chris, 14.08.2026) — settled, do not
propose splitting it again. It does carry three beats, and on a results day education floods
it: A-levels took most of the section on 14.08.2026 and pushed marriage and family items down.
That is a ranking symptom, not a reason to split — if it bites, order within the section rather
than dividing it.

Each line is:

  N | headline | outlet | author | age    (£ = paywalled, ↗ = Google News redirect link,
                                           "new" = source publishes no dates)

**`[low-frequency source, NNNh window]` after the age is context, not a warning** (added
10.09.2026). A handful of sources declare their own longer window in `extra_feeds.txt` —
FoRB in Full, Charlotte Gill, ADF International, all `window=168h` — because they publish
two or three times a week and at the default 36h the sweep would miss them entirely. Their
items therefore arrive legitimately old: 63h to 157h on 10.09.2026. The age is normal and
the piece is not a leftover; **do not treat the flag as a reason to drop the story.** It
exists because the sheet printed a bare "63.2h" with nothing to say that was normal, and a
63.2h FoRB in Full piece was published that morning as though it were breaking news. The
genuine leak — an item older than its *own* source's window, which would mean a broken
cutoff or date parse — is a separate `WINDOW LEAK:` line on the sweep header, and was empty
on 10.09.2026.

N is the item's index — you will pass these numbers to compose.py, which copies the fields
verbatim. Never retype a headline, URL, outlet or author by hand.

From the sweep header: if more than 40 feeds failed, or fewer than 60 candidates came back, say
so explicitly in your final message. Celebrity/entertainment chaff is suppressed automatically;
`python3 shortlist.py /tmp/today.json --show-chaff` audits it if a section looks oddly thin.

**Source health — run this Mondays, or whenever a beat looks unusually quiet:**

  cd ~/Downloads/breakfast-briefing && python3 check_sources.py --quiet

It exits 1 and names any source that has produced nothing for three consecutive days,
separating sites that actively refuse automated access (retrying will not help — they need a
new route) from feeds that have simply gone empty. Put anything it reports in your final
message. This exists because Live Action News was unreachable for an unknown period and
nothing said so: Chris flagged one of its stories as missed, and it looked like a ranking
failure when the source had been dead all along. A silent source and a quiet news week are
indistinguishable in the output, so they have to be distinguished here.

Two files carry Chris's own judgements and are applied automatically — you do not need to
act on them, but know they exist before concluding something was wrongly dropped:
`exclusions.txt` (headlines he has ruled out, with his reasoning) and `bylines.txt` (authors
for articles whose page cannot be fetched).

Three things about the shortlist that exist because of specific failures:

- **The two SUPPRESSED blocks at the end are part of the read, not a footnote.** They are
  printed separately because they fail for opposite reasons and the combined list pointed
  every reader at the wrong one. `CHAFF` is celebrity/sport/schedule filler — genuinely
  small, 20 items on 14.08.2026 — and the rules there over-match, so on 13.08.2026 "slams"
  quietly deleted a Swedish abortion bill. **`NO SECTION MATCHED` is the dangerous one**:
  168 items, nothing to do with chaff, dropped only because no keyword reached a section.
  That is where the Farage by-election commentary, the A-level results and a Zelensky story
  went. Scan both; if something there is real news, take it and widen `OTHER_ALLOW`.
- **No outlet holds more than three slots at the top of a section** (`--per-outlet`, default
  3). Overflow moves to the lower-ranked tail, which always prints. Chris, 13.08.2026: a
  section must not be "just full on one source" — The Critic, UnHerd and spiked had been 17
  of 28 Free Speech candidates. Take from the tail freely; just don't rebuild the column.
- **Ranking is a reading order, not a verdict.** On 13.08.2026 four stories Chris wanted
  ranked 53rd, 65th, 80th and 88th of 134 in Life. The full read in Step 3 is what catches
  those, so the tiers you assign there outrank the shortlist's own order.

## Step 3: Read every candidate yourself, then curate

Every candidate is read and tier-ranked — not filtered by keyword score. Keyword scoring
picks the right section but is a bad judge of importance (it once ranked a papal letter
above a jailed Hong Kong publisher), so judgement happens here.

Read the whole day in ONE pass. Do not fan this out to subagents:

  cd ~/Downloads/breakfast-briefing && python3 shortlist.py /tmp/today.json --sheet --leads-json /tmp/leads.json > /tmp/sheet.txt 2>&1; cat /tmp/sheet.txt

**Always pass `--leads-json`.** It costs nothing and it is what Step 7 records the day's
judgement from. Without it the tier store gets no entry for the day, and every story you
read today looks unjudged to every later run — which is the loop this was built to break.

This is measured, not a preference. On the 13.08.2026 sweep the sheet was ~26k tokens for
the entire day; the 17-slice subagent fan-out it replaced cost roughly 250-300k, almost all
of it per-subagent scaffolding plus the same brief repeated seventeen times. Reading
headlines was never the expensive part.

**The sheet is now ~195k tokens on a heavy day** (246k on a Monday's 84-hour window), because
it carries article text rather than headlines (25.08.2026). Generating it takes ~10 minutes of
fetching on top of the sweep. It is still one pass and still cheaper than the fan-out, but it
is no longer a cheap read: budget for it, and do not re-generate the sheet casually once you
have it.

**Re-running a past day: use `--new-only`.** It prints only the leads `tiers.json` has no
verdict on, or whose article text has changed since it was judged:

  python3 shortlist.py /tmp/today.json --sheet --new-only --leads-json /tmp/leads.json

On the 24.08 re-run that turned a 163k-token re-read into 14k — 0 of 1,112 leads needed
judging again. Staleness is by text, not by date, so a story judged on a bare headline comes
back the moment its text arrives (a redirect decoded, a preview added); one that had no text
before and none now correctly stays decided. **Do not use `--new-only` for the morning
edition** — the day's stories are new by definition, and a full pass is the point.

The sheet is also *better*, for a reason worth understanding: slicing by section made
cross-cluster judgement impossible. A reviewer holding only Life cannot know whether a
Nigerian court ruling matters more than the fifth Trump piece — and ranking across the
issue cluster is the whole job. One pass sees everything at once.

**★ marks a primary/watched source, and those lines are the ones you miss.** The sheet is
ordered by corroboration, which is right for judging how big a story is and wrong for finding
the reporting Chris asks for: an advocacy body's own release is x1 by definition, so SPUC, ADF,
ChinaAid, Live Action, Desiring God and WORLD sink to the bottom of a 2,400-line sheet however
important they are. On 24.08.2026 he listed 33 stories that should have run; 17 were in that
day's sweep, unpicked, most of them exactly that shape. Read every ★ line before you tier.
compose.py then runs a **COVERAGE check** and warns when a watched source filed that day and
nothing of theirs was picked — treat that warning as a question you must answer, either by
picking one or by saying in the final message why not. It is the only thing in the pipeline
that catches a source that filed and was read past; check_sources.py only catches one that
stopped filing.

**The `> is:` line is the article's own opening, read back as flags** (built 24.08.2026,
options 1/3/5): `report` or `comment`, `doc` when the piece names a document it rests on,
`update` when it is a follow-up rather than a first report, and the jurisdiction the text
itself names. It exists because the sheet's other text lines tell you what a story SAYS and
not what KIND of thing it is — and on 18.08.2026 keyword scoring over body text was rejected
for rewarding commentary, so the distinction is now shown rather than scored.

Treat a missing `> is:` line as unknown, never as "fine". The coverage gap that used to make
this acute was closed on 25.08.2026 — signals reached ~41% of leads before, and reach ~89%
now — but `TEXT_SIGNAL_WEIGHT` stays 0, because the residue is still not random: what remains
unreadable is disproportionately paywalled commentary, so a comment penalty would still fall
hardest on the outlets that charge. Measured effect of turning it on is in rank_eval_log.txt.

Three things the sheet gives you that the section lists do not:

- **`xN` is the corroboration count** — how many outlets filed on that story, computed
  across all sections. It is the only free measure of how big a story actually is, and the
  sheet is ordered by it. On 13.08.2026 the Medicaid gender-care ruling came in at x18 and
  led the day correctly, where keyword scoring had it mid-pack.
- **One line per story, not per item.** Same-story duplicates are collapsed into their
  best-outlet lead, so `x5` is one line to judge, not five to compare.
- **Article text, under nearly every line** (added 18.08.2026 — Chris: assess on the text,
  not just the headline; widened 25.08.2026 — rank on the article, not the headline). Four
  kinds of line, and the difference between them matters:

    - `> text:` — the article's own opening, up to 900 chars, scrubbed of nav and script
      furniture. **This is the one to rank on.**
    - `> preview (£, publisher's own summary):` — a PAYWALLED story's public preview, capped
      at 600 chars. Short *by design*, not because the story is thin: judge it against other
      previews, never against a full `> text:` line. The cap is a boundary, not a setting —
      several metered paywalls ship the whole article in the HTML and taking it would be
      circumventing the paywall.
    - `> via <outlet> on the same story:` — a DIFFERENT outlet's account, read because the
      lead itself refuses machine access. It tells you what the story is. It is not the
      lead's words, and the briefing still links the lead.
    - `> feed:` — the outlet's own RSS summary, used when the page could not be fetched.

  No text line at all means nothing was readable anywhere — judge on the headline, and
  **don't mistake silence for insignificance.** On 25.08.2026 that was 104 of 930 leads,
  and 97% of them were x1, so there was no sibling to read either.

  **The Telegraph and The Times get the benefit of the doubt on the core issues** (Chris,
  25.08.2026). They are the worst-affected outlets — 8 of the Telegraph's 12 leads and both
  of The Times' were unreadable on 25.08 — and the block is inconsistent rather than
  absolute, so one of their stories arriving as a bare headline says nothing about whether
  it matters. So:

    - In **Life**, **Marriage, Family & Education**, **Gender, Identity & Sexuality**,
      **Free Speech & Civil Liberties** and **Religious Freedom & Persecution** — the life,
      family and freedom beats — treat an unreadable lead from either as an **include**.
      Tier it on the headline as if the text supported it, not below the stories you could
      read.
    - In **Politics, Government & Society**, **Church & Religion**, **Immigration & Asylum**
      and **Other**, it earns its place like anything else. No bias, and no tier-3 parking
      to be safe.

  *(Immigration & Asylum is in the second group because Chris named the core as life, family
  and freedom. It is a live CitizenGO beat and he may want it moved — worth one question if
  a strong unreadable Telegraph immigration story turns up.)*

  This does NOT apply to the readable paywalled outlets — Spectator, Critic, UnHerd,
  Statement, Catholic Herald and the rest all produce a `> preview:` line now, so judge
  those on what it says. **The Church Times is no longer in this group**: its own RSS was
  added on 25.08.2026 and carries real standfirsts, so it should arrive with `> feed:` text.
  If Church Times leads start showing `> NO TEXT` again, that feed has broken.

  **Read the text before tiering**: it is what separates an interview with new content from
  a rehash, and a report from commentary wearing a news headline. The sheet runs ~195k
  tokens on a heavy day — up from ~100k before the text was widened, and still one pass,
  still far below the fan-out it replaced. Keyword scoring deliberately ignores this text
  (measured 18.08.2026: body text rewards commentary that narrates outcomes), so the text
  lines exist for YOUR judgement only.

Then tier every line yourself: **1** must run, **2** if there is room, **3** filler for a
thin section. Compare across sections, not within one. Rank order in the sheet is a reading
order, not a verdict — on 13.08.2026 four stories Chris wanted ranked 53rd to 88th of 134
inside Life, which is exactly what a single pass over everything prevents.

`slice_shortlist.py` still exists for the rare case where a section needs a deep second
read, but it is no longer the default path.

There is no overall volume cap. A typical edition runs 120-200 items. Do not trim to a
number. The only caps are per-section: Politics, Government & Society at 40, Church &
Religion at 30, Immigration & Asylum at 30, and the 30% US share — all applied by compose.py,
so leave them to it. These four are the whole of SECTION_CAPS plus US_SHARE; if compose.py
reports a cap this list does not name, the list has drifted and is what needs fixing.

**Provenance: cite the body that published the document, not whoever reported it.** When a
court, a UN body, a government department or an advocacy organisation issues something, the
release itself is the story — link ADF International, SPUC, ICC, Sex Matters, Right To Life,
ChinaAid, the ACLU on a suit they filed, over a newsroom's write-up of the same document.
Choosing between two versions of one story is a provenance question, never a news-value one.

shortlist.py now enforces this inside a cluster (`cluster_rank` ranks primary source → cited
outlet → not already published → outlet preference → link quality), but clustering only finds
pairs whose headlines overlap enough, so watch for the ones it misses. The rule exists because
on 14.08.2026 the briefing credited EWTN for a UN letter that ADF International had obtained
and published: both scored identically, and the tiebreak was a regex rewarding the active verb
"warns" over the noun "Warning". Advocacy bodies title releases in nouns and newsrooms use
active verbs, so that bias ran one way every time.

Your remaining job is to assign each index to its section (the sheet names the section it
came from) and to keep the geographic order, which compose.py enforces anyway.

**Some routing cannot be read off a headline, and that part is yours.** Chris moved TVP
World's "Swedish police probe online networks after teenage girl killed in school sword
attack" out of Marriage, Family & Education and into Immigration & Asylum on 24.08.2026,
because the attacker was an immigrant — a fact nowhere in the headline. testcases.txt records
that case as explicitly NOT encodable: a rule reading "school attack -> Immigration" would
misfile every school attack that is not. Where the section turns on who did it or what the
story is really arguing, place it yourself; the classifier will not, and compose.py's reclass
check will ask you to confirm with --allow-reclass.

**A `(same story as N - prefer that)` flag is a starting point, not a verdict.** It is
produced by word-overlap clustering, not judgement. Before accepting one, check whether the
item being dropped is the *primary source* — see the provenance rule below. This paragraph
used to read "trust their output — do not re-litigate their picks", written when Step 3 was
a subagent fan-out. After that fan-out was replaced it silently came to mean "never question
shortlist.py", and on 14.08.2026 it did exactly that: ADF International's own release of a UN
letter on Nigeria was dropped for EWTN's write-up of it, and the flag went unchallenged
because this brief said not to challenge it.

## Step 4: Compose the HTML
Write your picks to /tmp/picks.json **carrying the tiers you assigned in Step 3**:

  {"Section name": {"1": [numbers], "2": [numbers], "3": [numbers]}, ...}

using the exact section names above. Tier 1 = must run, 2 = if room, 3 = filler — the same
judgement you already made reading the sheet, which until 18.08.2026 was thrown away at this
boundary and survived only as list order. It matters now because the caps cut from the bottom
and section-cap losers retire permanently: compose.py spends tier-3 picks first, then tier-2,
and touches tier-1 only if tier-1 alone overfills a cap, which it reports as a loud WARNING —
treat that as a rebalancing error of yours, not something to pass through silently. Order
within a tier still breaks ties, so keep each tier roughly best-first. A section can omit
tiers it doesn't use. (The old flat-list format still works and is treated as all tier-2;
don't use it deliberately.) Then:

  cd ~/Downloads/breakfast-briefing && mkdir -p out && python3 compose.py /tmp/today.json /tmp/picks.json --no-mark --md out/<YYYYMMDD>-breakfast-briefing.md > /tmp/briefing.html && wc -c /tmp/briefing.html && head -4 /tmp/briefing.html

compose.py emits the exact format and saves a markdown backup. The typography matches Chris's
own hand-made 20.04.2026 briefing and he asked for it explicitly on 15.08.2026 — do not
"tidy" it. Title 36pt #002060 bold and the date 14pt #00b0f0 bold, both as styled `<p>` (as
`<h1>` Google Docs normalises them); section headings `<h1>` 16pt #17365d bold, which is what
gives the outline sidebar; headline links 10pt #3091f2 bold; credit 10pt black bold.

Each story is: headline link, `<br/>`, then `- Outlet (£) | Author`, and the gap below it
comes from `margin-bottom` on the paragraph — NOT from an empty spacer paragraph any more
(changed 17.08.2026). Two things were established from a Docs HTML export that day: Docs
converts a `<br/>` inside a `<p>` into a full paragraph break, so headline and credit have
always been separate paragraphs rather than one paragraph with a line break; and Docs
preserves `margin-bottom`, rewriting it as `padding-bottom`. The old empty-paragraph spacers
left every paragraph with zero space-after, which is why pressing Enter in the document
produced something that looked like a line break. Do not reintroduce them.

**Authors appear on commentary only**, never on straight news reports (Chris, 15.08.2026).
compose.py now runs authors.py over the picked items, which reads the article page to recover
a byline the feed omitted. This matters most for the Spectator: it has no RSS anywhere, so it
is index-scraped and *every* Spectator item arrives with no author. An item that exists only
as a Google News redirect has no page to read — for those, add a line to bylines.txt.

**compose.py now REFUSES to build if a pick is filed under a section the classifier
disagrees with.** It prints the item number, the section you filed it under and the section
the classifier expects. Nine times out of ten that means a transposed number — the ranking
sheet's line number copied instead of the item index, which happened three times on
17.08.2026 and put a Nigerian election piece in Life. Check the number against the sheet
first. Only if the placement is genuinely deliberate, re-run with `--allow-reclass` and say
so in your final message. Do not reach for that flag to make an error go away.

**That refusal applies to calling compose.py by hand. finish_edition.sh passes
`--allow-reclass` unconditionally** (Chris, 26.08.2026: "make it unconditional, I always
check the numbers anyway"), so the mismatch list is a REPORT there, not a gate. It still
prints — compose writes it to stderr and the script does not redirect stderr, so it appears
just above `composed N items`. **Read it before accepting the edition**, because a transposed
index will now publish rather than stop the run, and say in your final message that any
reclassed picks were deliberate. Rescues from the two SUPPRESSED blocks always show up here:
those items reached no section at all, so every one of them is a "mismatch" by construction —
27 of the 31 on 26.08.2026 were exactly that.

**Before touching any pattern in shortlist.py or regions.py, run the fixture:**

  cd ~/Downloads/breakfast-briefing && python3 run_tests.py

`testcases.txt` holds Chris's own corrections as executable assertions — which section a story
belongs in, which country an outlet is, what must be suppressed, how an outlet is named. It
exits non-zero on any failure. When Chris marks up a briefing, his correction goes into that
file as a FAILING case *before* the rule is edited; that ordering is the point, because it
stops a correction being satisfied by special-casing one headline, and stops it regressing
later. `link_fixes.txt` is the sibling file for a publisher URL only a human can supply.

**Always pass --no-mark.** Nothing is recorded as published until Step 7, after the doc exists
and its links verify. compose.py used to mark at compose time; on 14.08.2026 that marked 249
stories and the upload then produced a doc with two dead links. Had the publish failed outright,
those 249 stories would have been burned — never offered again — for a doc that did not exist.
Marking is the last step of a successful publish, not a side effect of rendering HTML.

**Links are never authored, only copied — and that includes the Step 10 Slack post.**
Nothing downstream checks the Slack message: compose.py resolves and title-verifies, and
publish.sh --verify diffs the Doc byte-exact, but the five links in Slack are composed by
hand afterwards and `URLs N/N verified` says nothing about them. On 31.08.2026 four of five
were typed from memory and were fabricated — an invented BBC article ID, an invented domain
for Decision Magazine, and two wrong path segments — and a correction had to be posted to
the channel. **Since 10.09.2026 you do not build that list by hand at all — `slack_five.py`
does, and Step 10 says how.** Never reconstruct a URL from an outlet and a headline slug,
however obvious the pattern looks.

compose.py resolves what it can and prints
`KEEP AS-IS` beside every Google News redirect it could not convert. Keep those redirects.
An ugly `↗` link is always better than a wrong one, and `expected_urls.txt` is the record:
anything in the published doc that is not in that file was invented.

The resolver now title-verifies — it fetches a candidate URL and requires the page's own
`<title>`/`og:title` to match the headline before accepting it. That check exists because
liveness proved nothing: on 12.08.2026 seven publisher URLs were typed in by hand and all
were dead, and twice a *guessed* URL was accepted because the outlet answered 403 or served
a soft-404. Chris supplied the real WORLD link on 13.08.2026 — `wng.org/sift/…-1786558522`,
where the resolver had guessed `wng.org/article/…`. No slug pattern would ever produce it,
which is the point: if the page cannot identify itself, the redirect stays.

## Steps 5-9 in one command — and preferably in a fresh session

Once /tmp/picks.json is written, everything that follows is mechanical and needs none of the
sheet. Run:

  cd ~/Downloads/breakfast-briefing && ./finish_edition.sh

It does compose → publish → verify → mark → record tiers → archive → back up, in that order,
and stops at the first failure so nothing downstream runs against an unverified doc. The
individual steps are still documented below — read them to understand what it is doing and
to recover when it stops partway.

**Use it. Do not hand-run steps 5-9 unless it actually fails.** On 26.08.2026 it was skipped
because its compose call lacked `--allow-reclass` and `set -e` turned the refusal into a stop
with 31 deliberate off-classifier picks; the tail was then run by hand. Both causes are fixed
— the flag is unconditional now, and the same session found a second latent abort: `set -u`
plus this Mac's bash 3.2 made the empty `REASONS` array an unbound-variable error on the
record-tiers line, which fires on any run without /tmp/reasons.json (almost every run) and
would have died AFTER marking but BEFORE archive and the push. `python3 run_tests.py` now
covers both, so if the script aborts, that is news worth reporting rather than routing around.

**Start a fresh session for it if you can.** The ranking sheet is 165-250k tokens and has to
be held to curate; afterwards it is dead weight that gets re-read on every remaining step.
Measured on 25.08.2026: ~259k tokens of context per step through the tail against ~128k
during curation, about 15% of the edition's whole cost spent carrying a corpus nothing was
reading. finish_edition.sh needs only /tmp/today.json, /tmp/picks.json, /tmp/leads.json and
the files on disk.

`--dry-run` composes and stops before publishing, changing no state.

## Step 5: Publish the Google Doc

**Preferred — upload the file, do not retype it:**

  cd ~/Downloads/breakfast-briefing && ./publish.sh --verify

This uploads /tmp/briefing.html to Drive as a multipart POST, so the published doc contains
the exact bytes compose.py produced. Link corruption becomes impossible rather than merely
detectable, and it finishes in about a second. `--verify` then exports the doc back and diffs
every URL, which is Step 6 done for free; it exits non-zero if anything mismatches. It also
refuses to publish if a doc of that title already exists, unless you pass `--force`.

If it exits saying no credential is configured, run `./publish.sh --check` — it prints exactly
what is missing and how to fix it — then say so in your final message and fall back below.
Do not try to create, mint or refresh credentials yourself; that is Chris's to do.

**Fallback — the model-transcribed path.** Only when publish.sh reports no credential. Read
/tmp/briefing.html and pass its contents as textContent to create_file:
- title: "<YYYYMMDD>: Breakfast Briefing"    e.g. "20260813: Breakfast Briefing"
- parentId: 1ff3EpR5ER6AxCopLDrVOlaQVlVhi2LzQ
- contentMimeType: text/html
- textContent: the file's contents, copied exactly — do not reformat, re-order or "tidy" it

Know what this costs before choosing it: the payload passes through the model token by token,
so ~250 links are retyped by hand on every run. On 17.08.2026 that was ~33k output tokens and
13 minutes for one call, and on 14.08.2026 it silently corrupted two Google News redirects.
When you use this path, Step 6's link diff is mandatory, not optional.

If create_file returns a quota or rate-limit error, it usually succeeds on a second attempt a
moment later. Before retrying, search the folder to confirm the doc was not in fact created — if
it exists, do not create a second one.

## Step 6: Verify what you published

**If you published with `./publish.sh --verify`, the link diff has already run** — it reported
`URLs N/N verified` and exited non-zero on any mismatch. Skip to the structural checks at the
end of this step. Everything between here and there applies to the fallback path only.

**On the fallback path, diff the links first. This is the check that matters.** Retyping all
~250 links by hand makes corrupted URLs the likeliest defect and the only one that has actually
shipped: on 14.08.2026 two Google News redirects came out wrong. Heading, count and layout
checks all passed on that broken doc — they cannot catch it.

**Do not rely on `expected_urls.txt` alone.** It is meant to be the record of legitimate links,
and the distinction matters — diffing against /tmp/briefing.html catches a *corrupted* URL, but
only expected_urls.txt catches an *invented* one that compose.py never emitted. On 17.08.2026 it
was written 1 byte long, i.e. empty, so that check was silently unavailable. Check its size
before trusting it, and report it if it is empty.

Read the new doc back with read_file_content (its markdown contains every URL as a real
`[title](url)` link, so the regex below finds all of them), then:

  python3 - <<'EOF'
  import json,re,html,sys
  doc=json.load(open(sys.argv[1]))["fileContent"]          # the saved read_file_content result
  local=open('/tmp/briefing.html').read()
  want=[html.unescape(u) for u in re.findall(r'href="([^"]*)"',local)]
  got=set(re.findall(r'https?://[^\s\)\]>"]+',doc))
  bad=[u for u in want if u not in got]
  print("URLs %d/%d ok, %d corrupted" % (len(want)-len(bad),len(want),len(bad)))
  for u in bad: print("  MISSING:",u[:110])
  EOF

If a large result is written to a file instead of returned, run the diff against that file rather
than pasting it back into context. Also confirm every headline and source string appears
(`Word\&Way` mismatches are a false positive — the export escapes `&`).

**Use read_file_content, not a plain-text export, and do not "improve" this recipe into one.**
A `text/plain` export of a Google Doc keeps the visible link text and discards every href, so
the diff finds zero URLs in the doc and reports every link corrupted on a doc that is
byte-perfect. publish.sh hit this on 17.08.2026 (0 of 246) and exports `text/html` for exactly
this reason; on 10.09.2026 the same trap was walked into again from the other direction — a
hand-rolled `export?mimeType=text/plain` diff was run *instead of* this recipe, reported
`0/304 ok, 304 corrupted`, and that was briefly written up as a flaw in Step 6 rather than in
the substitute. The recipe as printed above is correct and returned 304/304 on that same doc.
If you do diff outside the connector, use `mimeType=text/html` and unwrap Docs' redirector
(`https://www.google.com/url?q=…`) the way publish.sh does — but note that an authenticated
export is not available on this path anyway, because the fallback only runs when publish.sh
reported no credential. So: run the recipe as written.

Then the structural checks: a heading for every section you picked for, item count per section
matches your picks,
layout is headline-then-source rather than one run of bold text.

**If any link is corrupted, do not mark and do not accept the doc.** The connector cannot edit a
doc's body (update_file changes title/parent only). Republish with create_file and verify again —
a clean re-transcription is achievable, the second attempt on 14.08.2026 verified 249/249 exact.
Then trash the bad doc with trash_file so the folder is not left holding two same-titled
documents, and only then proceed to Step 7.

## Step 7: Record what was published
Only after the doc exists and its links verify:

  cd ~/Downloads/breakfast-briefing && python3 mark_published.py /tmp/today.json /tmp/picks.json

This marks both the raw feed URL and the doc's final resolved URL for each story. Both are needed:
compose.py's resolver rewrites item["url"] in place, so the two forms differ for some stories (25
of 249 on 14.08.2026), and marking only one lets a story reappear tomorrow depending on whether
that day's sweep happened to resolve it. Use --dry-run to see the count without writing.

If you never reached a verified doc, do NOT run this — the stories stay available for tomorrow,
which is the whole point of deferring it.

**Then record the judgement**, under exactly the same condition:

  cd ~/Downloads/breakfast-briefing && python3 record_tiers.py /tmp/leads.json /tmp/picks.json --date <YYYYMMDD>

This writes every lead into `tiers.json` — tier 1/2/3 for the picks, **tier 0 for the ones you
read and passed over**. Tier 0 is the whole point: without it a later run cannot tell a story
you rejected from one you never saw, so it re-reads the day from scratch. Optionally pass
`--reasons /tmp/reasons.json`, a `{"<index>": "one line"}` sidecar; compose.py never reads it,
so notes cannot break a build. Most stories will never have one.

Same rule as marking: only for an edition that published. Recording tiers for a draft nobody
shipped would suppress those stories from tomorrow's `--new-only` sheet on a judgement no one
acted on.

## Step 8: Archive the edition (the ranking evaluation corpus)
Immediately after Step 7, in the same conditions — only for an edition that published:

  cd ~/Downloads/breakfast-briefing && python3 archive_day.py /tmp/today.json /tmp/picks.json

This is the only place the day's judgement is preserved. Today's tiering of ~1,000 stories is a
labelled dataset — /tmp/today.json and /tmp/picks.json are gone by tomorrow and composed.json is
overwritten, so an edition that is not archived is a day of labels lost for good. ~320KB.

It exists because every scoring change here used to be argued from one remembered example.
`python3 rank_eval.py` replays the current scorer against every archived edition and reports how
often it agrees with the tiers; a proposed change is run before and after. **Read rank_eval.py's
header before trusting a number from it** — concordance measures agreement with your picks, not
correctness, and a bug that correlates with a favoured beat can score well (proved on
18.08.2026). testcases.txt keeps veto power. Do not run rank_eval as part of the morning
briefing; it is for sessions that change scoring.

**Nor do you need to: `eval_week.sh` runs both scorers every Saturday 08:00** (the
`briefing-eval-week` scheduled task, added 10.09.2026). Barring them from the morning path
was right and also meant nothing ever ran them — `rank_eval_log.txt` had not been written
since 31.08 and `repeat_eval_log.txt` since 28.08, while the corpus grew from 4 archived
editions to 18. Saturday because the briefing is weekdays only, so the archive is complete
through Friday and nothing contends. It exits non-zero only on a real crash; `repeat_eval.py`
exiting 1 on a failing GOLD case is the standing state, because testcases.txt is written
red-first — see `known_red.txt` for which failures are deliberate.

If archiving fails, the edition is still fine — say so in the final message and move on.

## Step 9: Back up state, judgements and the archive to Drive
Last, and only if Step 7 actually marked against a verified doc:

  cd ~/Downloads/breakfast-briefing && ./state_sync.sh push
  cd ~/Downloads/breakfast-briefing && ./upload-archive-to-drive.sh

Forty-two files in the first: the eight state files (seen, cut, source_health, resolved,
authors, ledes, and — added 25.08.2026 — openings and previews, the two article-text caches,
each worth about ten minutes of refetching), the seven that are judgements (testcases.txt,
exclusions.txt, bylines.txt, link_fixes.txt, extra_feeds.txt, sources.opml and — added
25.08.2026 — **tiers.json**, the accumulated record of what was decided about every story
read, which cannot be rebuilt from anything and whose loss would silently make every story
look unjudged again) and **every .py and .sh in the directory** — 27 of them as of 28.08.2026,
not the ten this line used to name. The list was completed to "everything" on 20.08.2026 for a
reason state_sync.sh's own header gives: enumerating the rest ends the drift, because a script
added later is then the exception that stands out rather than one more quiet gap. Count the
`pushed` lines against 42 if you want to check it ran whole — and expect that number to keep
creeping as scripts are added, so a count one or two ABOVE it is the list working, not a fault;
only a count below it is worth stopping for. The judgement files are the only irreplaceable things here —
weeks of accumulated corrections — and before 19.08.2026 they existed nowhere but ~/Downloads.
That the scripts are in there is not decoration: on 20.08.2026 a `cp` that followed a symlink
overwrote five of them with an older copy, and this push was the only thing that got them back.

The second command backs up `archive/` — the ranking corpus Step 8 just wrote — as one tarball
per edition. It is separate from `state_sync.sh` because the two have different shapes:
state_sync overwrites a fixed list of files every day, while an archived edition is written once
and never touched again, so the archive upload is incremental and skips days already in Drive.
Added 20.08.2026, when Step 9 pushed state faithfully every morning and left the labels — the
only record of how ~1,600 candidates were tiered — on one Mac's disk. rank_eval.py has nothing
to score against if that disk goes.

Both are insurance and neither is load-bearing. If the archive upload fails the edition is
still fine and so is the local archive; say so and move on.

**Steps 5 → 6 → 7 → 9 are an order, not a suggestion.** Pushing an unmarked `seen.json`
throws the day away, because tomorrow's sweep pulls a state that never recorded today's
edition. Pushing a *marked* one for a doc that failed to publish burns those stories — never
offered again. So: no verified doc → no marking → no push.

On this Mac the run does not `pull` at the start (state lives on disk and is authoritative),
which makes the push pure insurance rather than load-bearing. If it fails, the edition is
still completely fine: say so in the final message, note that state is un-backed-up until the
next successful push, and move on. Never re-run it to "fix" a failed publish.

## Step 10: Announce the edition in Slack
Only for an edition that reached Step 7 — a verified doc that was marked. No verified doc means
no Slack post, for the same reason it means no marking: an announcement pointing at a briefing
that does not exist is worse than silence.

**Do not compose the message by hand. `slack_five.py` builds it** (10.09.2026). Write your
choices to a spec — a list of slots, each a lead index plus optional nested indexes, with
`note` for your own prose — then:

  cd ~/Downloads/breakfast-briefing && python3 slack_five.py --history          # what the last fives ran
  cd ~/Downloads/breakfast-briefing && python3 slack_five.py --spec /tmp/five.json \
      --doc-url "<the published Doc URL>"

It refuses a pick that did not actually publish (a cap loser included — on 10.09.2026 it
caught index 921, which was in the picks and then retired by the Church cap, so the link
would have pointed at a story absent from the Doc), refuses a URL that is not in
`expected_urls.txt`, refuses a URL smuggled into a note, warns on anything over 36h, and
refuses a story that already ran in one of the last 10 fives unless you pass
`--allow-repeat`. It writes `five/<date>.json`, which is the only record of this list that
has ever existed — the Doc gets tiers.json, archive/ and rank_eval; the five got nothing, so
Chris replacing three of five on 25.08 and cutting a repeat on 31.08 taught the pipeline
nothing. **Post the emitted text VERBATIM.** Retyping any part of it restores the exact
hand-copying that fabricated four links on 31.08.2026.

Post to **#campaigns-en-gb** (`C9RH217PZ`) with `slack_send_message`. The message is short and
has a fixed shape, which is the shape the script emits:

- one line saying the briefing is out, that it is automated, and linking the Doc
- **the top five stories**, each as a headline link with the outlet after it
- where several of the day's stories belong to **one running fight**, give that slot a lead
  link and nest the others under it as indented sub-items (Chris, 31.08.2026). The assisted
  suicide Bill is the standing example: the national-press lead on top, then the primary
  document, the advocacy bodies' releases and any related story beneath it. This is the one
  place the Doc's provenance rule and this list's national-press-first rule stop competing —
  the newsroom piece leads, and the primary source still gets linked.
- one closing line inviting people to open the Doc for the rest

Pick the five for a **GB campaigns audience**, not by the sheet's global ranking. The Doc is
ordered UK-first within each section but ranks nothing across sections; the five here are a
separate editorial judgement and should lead on what a UK campaigner would act on — a live
bill, a consultation with a deadline, a UK court or regulator decision — over whatever had the
highest corroboration count that day. A US story earns a slot only when it is genuinely the
day's biggest news.

**Chris replaced three of five on 25.08.2026, the first run of this step.** What he kept, cut
and added is the shape to copy:

- **UK only.** He cut France enacting its assisted dying law — a significant story, in the Doc,
  and not for this list. Non-UK goes in the Doc, not the five.
- **National-press reporting beats an advocacy body's campaign update.** The assisted-dying
  slot went to Politico Europe's piece on where the bill's Labour champion is taking it, not
  Right To Life UK's "just over 2 weeks left". **The Doc's provenance rule does not govern this
  list** — there, an advocacy body's own release beats a newsroom write-up of it, because the
  question is who published the document. Here the question is what a campaigner wants to read,
  and a ★ primary source has no automatic claim on a slot.
- **Immigration and Islam in Britain carry real weight for this audience.** He added two: the
  Telegraph on Muslim gangs forcing white prisoners to convert, and GB News on a Sudanese
  migrant who cannot be deported because she married her cousin. Neither was in the first draft
  and both are exactly the beat this channel works on.
- He kept the two that were a UK institution acting on Christians directly — the EHRC schools
  guidance consultation, and Päivi Räsänen's visa arriving too late for the Belfast conference.

Keep his ordering sense too: the list is not ranked by scale, it opens on the live legislative
fight and closes on the sharpest single story.

**Do not re-run a story Chris has already had in this list.** The Slack five is a much
narrower window than the Doc, so a repeat is far more visible: on 31.08.2026 Päivi Räsänen's
visa/travel-ban story was put up again after running several times, and Chris cut it. The
Doc's rule that a running story may legitimately run again does NOT carry over here — check
the last several editions' five before picking, and prefer a genuinely new development over
the next instalment of one the channel has already seen.

Say "automated" plainly in the first line. It sets the right expectation about what the list is
and is not: nobody sub-edited it, and the ranking is a machine's reading order plus one pass of
judgement.

Do NOT post to `#campaigns-en_gb-alerts` (`C8RC23N56`) — that channel is for campaign alerts,
not a daily digest.

If the Slack post fails, the edition is still completely fine: it is published, verified, marked
and backed up. Say so in the final message and move on. Never re-run any earlier step to "fix"
a failed Slack post.

## Fallback
compose.py has already written the markdown copy to
~/Downloads/breakfast-briefing/out/<YYYYMMDD>-breakfast-briefing.md. If Drive keeps failing, say
clearly in your final message that the upload failed and point to that file.

## Final message
Report: feeds ok/failed, candidates returned, how many carried a `[ran]` flag, how many were
dropped as cut by an earlier cap, items per section, **the link-diff result from Step 6
(N/N verified)**, the resolver line (`resolved N; M could not be resolved` — a healthy day is
M=0, and a `RESOLVER DEGRADED` warning means say so prominently), **the sweep's decode line and
how many leads the ranker could actually read** (the `text: N lede(s), M paywalled preview(s),
K read via another outlet` line from Step 3 — a healthy day reads ~89% of leads, and a sharp
drop there means the day was ranked on headlines whatever else went right), whether Step 7
marking, Step 8
archiving, both halves of Step 9 (state push, archive upload) and the Step 10 Slack post each
ran, the Doc link, and anything that looked wrong.

Steps 8, 9 and 10 are the ones whose failure is survivable, so state their outcome explicitly
rather than by omission: an unarchived edition is a day of ranking labels lost for good, a
failed state push leaves the pipeline un-backed-up until the next one, a failed archive
upload leaves the labels on this Mac alone, and a failed Slack post leaves a published briefing
nobody has been told about. Each is worth a line even when it worked. Name the five stories you
put in the Slack post — that selection is a judgement nothing else in the run records.