#!/usr/bin/env python3
"""Turn picked item numbers into the briefing's HTML.

The curation step picks items by the numbers shortlist.py printed. This copies every
headline, URL, outlet and author straight out of the sweep JSON, so nothing is retyped
into the Drive call by hand — the 12.08.2026 edition shipped with a mistyped author
byline that way, and the connector cannot edit a doc once created.

Picks file is JSON: {"Section name": [12, 34, 56], ...}. Sections appear in the
briefing's fixed order regardless of the order they appear in the picks file.

Usage:
    python3 compose.py today.json picks.json > briefing.html
    python3 compose.py today.json picks.json --date 2026-08-13 --md briefing.md
"""

import argparse
import datetime as dt
import html
import json
import os
import re
import sys

HERE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE_DIR)
import fetch_feeds  # reuse url_key / load_seen / save_seen so dedup stays consistent
import regions      # shared UK-first ordering
import resolve      # Google News redirect -> publisher URL
import authors      # missing byline -> read it off the article page
import shortlist    # section classifier, used to validate the picks before rendering

ORDER = [
    "Religious Freedom & Persecution",
    "Free Speech & Civil Liberties",
    "Marriage, Family & Education",
    "Gender, Identity & Sexuality",
    "Life",
    "Church & Religion",
    # Split out of "Other" on 14.08.2026, when it held 514 of 1,567 candidates. Must stay
    # in step with SECTION_NAMES in shortlist.py: compose.py silently ignores picks under
    # a section name it does not know, so a mismatch drops items without warning.
    "Immigration & Asylum",
    "Politics, Government & Society",
    "Other",
]

# Sections that are deliberately a digest rather than a sweep.
# Church & Religion capped at 30 (Chris, 23.08.2026). It has the largest candidate pool of
# any section - 304 on 23.08.2026 against Politics' 284 - and a single papal trip clusters
# hard: Leo XIV's San Marino/Rimini weekend plus the Gallagher Moscow trip put 71 items in
# the section on a test run of the 24.08 edition, 31% of a 232-item briefing, which is a
# digest of the Vatican with a briefing attached rather than the reverse.
# NOTE this also tightens the US share in the section: us_allowance() returns share x cap
# when a cap exists, so Church & Religion now allows at most int(30 x 0.25) = 7 US items,
# where an uncapped section allowed a third of its non-US count.
SECTION_CAPS = {"Politics, Government & Society": 40, "Church & Religion": 30}

# Domains that republish other outlets' work. Their feeds credit the ORIGINAL publisher, so
# the item arrives as "The Telegraph" and sails past the outlet block in shortlist.py, but its
# URL points at the repost. The briefing would then print "- The Telegraph (£)" over a link to
# somebody else's site: a credit that does not match its own link. Found 17.08.2026, when three
# Telegraph and Times pieces reached the doc this way.
#
# These are dropped at compose time and PRINTED, never dropped quietly - the feed is still a
# useful way to SEE a paywalled piece exists, and if Chris wants one of them the answer is a
# real publisher URL, not a repost.
REPOST_DOMAINS = re.compile(r"anglicanmainstream\.org", re.I)

LINK_FIXES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "link_fixes.txt")


def load_link_fixes(path=LINK_FIXES):
    """'match | real URL' per line; match is a case-insensitive substring of headline or URL.

    Same shape as bylines.txt deliberately - it is the same kind of thing, a correction only a
    human can supply. Applied before the repost check so a rescued item keeps its ranking.
    """
    out = []
    if not os.path.exists(path):
        return out
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "|" not in line:
                continue
            match, _, url = line.partition("|")
            if match.strip() and url.strip().startswith("http"):
                out.append((match.strip().lower(), url.strip()))
    return out

# Feed titles that read badly as a source credit.
OUTLET_FIXES = {
    # Chris's markup on the 19.08.2026 edition: four outlets printed as bare domains, which
    # reads as a scraping artefact rather than a masthead. "spiked" also lands in
    # PAYWALLED_OUTLETS once renamed, so the (£) he asked for follows from the rename.
    "morningstarnews.org": "Morning Star News",
    "ntnews.com.au": "NT News",
    "liveaction.org": "Live Action",
    "spiked-online.com": "spiked",
    # Shorter credit names, per Chris 16.08.2026.
    "Breitbart News": "Breitbart",
    # The OPML calls it "NSS", which reads as an unexplained acronym in the credit line.
    "NSS": "National Secular Society",
    # The feed titles itself in Arabic; the organisation's own English name is this.
    "المبادرة المصرية للحقوق الشخصية": "Egyptian Initiative for Personal Rights",
    "Спілка православних журналістів": "Union of Orthodox Journalists",
    "ABC News (Australia)": "ABC",
    "ABC News & Headlines – Australian Broadcasting Corporation": "ABC",
    "worldreligionnews.com": "World Religion News",
    "Daily Express": "Express",
    "Daily Express :": "Express",
    "CBN News": "CBN",
    "The Christian Post": "Christian Post",
    "Premier Christian News": "Premier",
    "Daily Mail": "Mail",
    "Mail Online UK": "Mail",
    "jurist.org": "Jurist",
    "The New York Times": "NY Times",
    "Stuff (New Zealand)": "Stuff",
    "The Post (New Zealand)": "The Post",
    "EWTN Great Britain": "EWTN",
    "The Daily Wire": "Daily Wire",
    "The Times of India (India)": "The Times of India",
    "ABC News & Headlines – Australian Broadcasti": "ABC",
    "Angelus News": "Angelus",
    "Christian Today | RSS": "Christian Today",
    "Anglican Ink © 2026": "Anglican Ink",
    "Iona Institute: News Roundup": "The Iona Institute",
    "LifeNews.com": "LifeNews",
    "Live Action News": "Live Action",
    "Statement - RSS": "Statement",
    "cbn.com": "CBN News",
    "www.christiandaily.com": "Christian Daily International",
    "standingforfreedom.com": "Standing for Freedom",
    "adfmedia.org": "Alliance Defending Freedom",
    "Alliance Defending Freedom International": "ADF International",
    "Free Speech Union — News & Publications": "Free Speech Union",
    "The Spectator Australi": "The Spectator Australia",
    # bare domains and non-Latin names that read badly as a credit line
    "rfi.fr": "RFI",
    "citynews.com.au": "Canberra CityNews",
    "post-gazette.com": "Pittsburgh Post-Gazette",
    "wng.org": "WORLD",
    "deseret.com": "Deseret News",
    "ewtnnews.com": "EWTN News",
    "upi.com": "UPI",
    "nwitimes.com": "The Times of Northwest Indiana",
    "조선일보": "Chosun Ilbo",
    "Christianity Daily News": "Christianity Daily",
    "THISDAYLIVE": "This Day",
    # === Chris's markup on the 20.08.2026 edition. Five mastheads printed wrong; two of
    # them ("ucanews.com", "telegraph.co.uk") are bare domains, which Google Docs auto-links
    # in the credit line - the same fault spiked-online.com had on 19.08.
    "EWTN UK": "EWTN",
    "EWTN News": "EWTN",              # ewtnnews.com already maps here, so the chain resolves
    "EWTN News Nightly": "EWTN",
    "ucanews.com": "UCA News",
    # PAYWALLED_OUTLETS already matches "the telegraph", so the (£) follows from the rename
    # rather than needing a second rule.
    "telegraph.co.uk": "The Telegraph",
    "BBC UK": "BBC",
    # The outlet field is truncated to 44 chars at fetch time, so the STORED name is the
    # cut-off form. Map both. Note this makes "ABC" mean the Australian ABC and US ABC News
    # alike - safe, because region is decided from the raw outlet and the URL (DOMAIN_HOME
    # keys on abc.net.au) before tidy_outlet ever runs at credit time.
    "ABC News - Breaking News, Latest News and Vi": "ABC",
    "ABC News - Breaking News, Latest News and Videos": "ABC",
    # The masthead styles itself "Notes from Poland"; the feed title capitalises the F.
    "Notes From Poland": "Notes from Poland",
}
# Author fields that are really feed plumbing, not a byline.
SKIP_AUTHORS = {
    "-", "rss", "press release", "commsmanager", "toi world desk", "adam",
    "staff writer", "thomas more legal society", "right to life uk", "admin",
    "editor", "news desk", "web desk", "staff", "guest writer", "cp video",
    "christian daily international-morning st", "gus ewtn", "pn freelance",
    "reduxx team",
}
GREY = "#666666"

# Paywalled by OUTLET NAME as well as domain, because these mostly reach us as Google News
# redirects where the URL host is news.google.com and the domain test cannot fire.
# Matched on the WHOLE tidied name: a prefix match put a (£) on "The Times of India" because
# it begins "The Times", which is the same trap that once caught it in PAYWALLED_DOMAINS.
PAYWALLED_OUTLETS = re.compile(
    r"^(the telegraph|telegraph|the times|the sunday times|ny times|new york times"
    r"|daily wire|the globe and mail|globe and mail|world|wng\.org|the spectator"
    r"|spectator|the critic|unherd|spiked|the catholic herald|catholic herald"
    r"|church times|the economist|new statesman|the australian|financial times"
    r"|the wall street journal|the washington post|the atlantic"
    r"|the scotsman|scotsman)$", re.I)   # Chris, 17.08.2026



# Type spec taken from Chris's own 20.04.2026 briefing, read off the Google Docs HTML export
# on 16.08.2026. Kept as constants so a future change is one edit, not a hunt through markup.
FONT = "Arial"
TITLE_STYLE = ("font-family:%s;font-size:36pt;color:#002060;font-weight:700" % FONT)
DATE_STYLE = ("font-family:%s;font-size:14pt;color:#00b0f0;font-weight:700" % FONT)
SECTION_STYLE = ("font-family:%s;font-size:16pt;color:#17365d;font-weight:700" % FONT)
HEADLINE_STYLE = ("font-family:%s;font-size:10pt;color:#3091f2;font-weight:700" % FONT)
CREDIT_STYLE = ("font-family:%s;font-size:10pt;color:#000000;font-weight:700" % FONT)
# Gap between stories, as real paragraph spacing rather than an empty paragraph.
#
# Verified against a Docs HTML export on 17.08.2026, which settled two things. First, Docs
# converts a <br/> inside a <p> into a FULL PARAGRAPH BREAK - so the headline and the credit
# have always been two paragraphs, not one paragraph with a line break; they merely looked
# like a shift+enter because every paragraph had zero space-after. Second, Docs preserves
# margin-bottom, rewriting it as padding-bottom on the resulting paragraph.
#
# That zero space-after is why Chris got a line break when he pressed Enter: he was getting a
# real new paragraph, but with no spacing it is indistinguishable from a line break. Putting
# the gap in the paragraph style fixes the typing behaviour AND removes the &nbsp; hack.
STORY_GAP = "12pt"





# Chris, 15.08.2026: "If a comment include author, if just a news article do not."
# A byline is part of a commentary piece's identity - you read Brendan O'Neill or Katy Faust
# by name - but on a wire report it is noise. Detected from the outlet and the URL shape,
# since neither the feed nor the headline reliably says which it is.
COMMENTARY_OUTLETS = re.compile(
    r"spiked|the critic|unherd|spectator|first things|public discourse|national review"
    r"|the federalist|daily wire|daily signal|washington stand|quillette|conservative woman"
    r"|catholic herald|catholic world report|national catholic|christian concern"
    r"|lifesitenews|reduxx|the tablet|church times|new statesman|the atlantic"
    r"|guido fawkes|order-order|the article|compact|american conservative"
    # Chris, 19.08.2026, twice in one edition: "Statement articles usually have a listed
    # author which should be included." Statement was missing from this list, so its bylines
    # were discarded at the credit line even when authors.py had recovered them - a manual
    # bylines.txt entry would not have printed either. Verified before and after.
    r"|\bstatement\b", re.I)
COMMENTARY_URL = re.compile(
    r"/(opinion|comment|commentisfree|columnists?|blogs?|analysis|editorial|essays?"
    r"|perspectives?|viewpoint|leader)s?/", re.I)


def is_commentary(item):
    if COMMENTARY_URL.search(item.get("url") or ""):
        return True
    return bool(COMMENTARY_OUTLETS.search(item.get("outlet") or ""))


def tidy_outlet(name):
    """Resolve the alias map to a fixed point, not just one hop.

    The map grew in layers: "cbn.com" -> "CBN News" was added months before Chris asked for
    "CBN News" -> "CBN" on 16.08.2026. A single lookup stopped at the intermediate name, so
    the edition still read "CBN News" and "Daily Mail" after the rename. Follow the chain.
    """
    seen = set()
    while name in OUTLET_FIXES and name not in seen:
        seen.add(name)
        name = OUTLET_FIXES[name]
    name = re.sub(r"\s*[|:-]\s*(RSS|News Feed|Feed)\s*$", "", name).strip()
    # A few feeds leave a dangling separator in the masthead itself, which rendered as
    # "- The MoCo Show -" in the credit line (19.08.2026: The MoCo Show, WOUB Public Media).
    return re.sub(r"\s*[|\-–—:]\s*$", "", name).strip()


def credit(item):
    """'- Outlet (£) · Author' — the grey line beneath a headline. The leading dash
    matches the hand-made briefings; Chris asked for it on 12.08.2026."""
    name = tidy_outlet(item["outlet"] or "")
    out = "- " + name
    if item.get("paywalled") or PAYWALLED_OUTLETS.match(name.strip()):
        out += " (£)"
    author = (item.get("author") or "").strip()
    if "@" in author or author.startswith("http"):
        author = ""          # some feeds put a contact address in the byline field
    # Some feeds glue the byline onto the outlet ("Christian Today | Martin Saunders");
    # split it back out so the credit line reads properly.
    if not author and "|" in out:
        head, _, tail = out.rpartition("|")
        if tail.strip() and len(tail.strip().split()) <= 4 and tail.strip()[0].isupper():
            out, author = head.strip().rstrip("-").strip(), tail.strip()
    # The duplicate guard compares against the OUTLET NAME, not the assembled line. It used to
    # test `out`, which by this point is "- Christian Concern" and sometimes "- Outlet (£)", so
    # an author identical to the outlet never matched it and the credit printed "Christian
    # Concern | Christian Concern" (Chris, 25.08.2026: "Unless there is a named author just say
    # Christian Concern as the source"). Feeds set author=outlet routinely on advocacy pages
    # that have no writer.
    if (author and (is_commentary(item) or item.get("byline_forced"))
            and author.lower() not in SKIP_AUTHORS
            and author.lower() != name.lower()
            and author.lower() != out.lower()):
        out += " | " + author
    return out


def spread_outlets(nums, items):
    """Stop one masthead running consecutively, without breaking the region order.

    The regional sort is the outer key and stays exactly as it is - UK first, then Europe,
    and so on. Inside each region block this deals the items round-robin by outlet, so a
    day when The Spectator files six pieces reads as a spread rather than a column of one
    name (Chris, 13.08.2026: "the other section is just full on one source").
    """
    blocks, order = {}, []
    for n in nums:
        tier = regions.region(items[n]["headline"], items[n]["outlet"], "",
                              shortlist.region_text(items[n]))
        if tier not in blocks:
            blocks[tier] = []
            order.append(tier)
        blocks[tier].append(n)
    out = []
    for tier in order:
        buckets, seq = {}, []
        for n in blocks[tier]:
            key = tidy_outlet(items[n]["outlet"] or "").lower()
            if key not in buckets:
                buckets[key] = []
                seq.append(key)
            buckets[key].append(n)
        while any(buckets[k] for k in seq):
            for k in seq:
                if buckets[k]:
                    out.append(buckets[k].pop(0))
    return out


def normalize_picks(picks):
    """Accept both pick formats and return (flat, tier_of).

    Flat:    {"Section": [n, ...]}                          every pick treated as tier 2
    Tiered:  {"Section": {"1": [n, ...], "2": [...], "3": [...]}}

    Tiers are the curator's own ranking from the reading pass - 1 must run, 2 if room,
    3 filler - and until 18.08.2026 they were thrown away at this boundary, surviving only
    as list order. That was tolerable when order was cosmetic; it stopped being tolerable
    when the caps started cutting from the tail and section-cap losers began retiring
    permanently: a flat array of integers was deciding what got binned forever.

    The returned lists are ordered tier 1 first, then 2, then 3, preserving order within a
    tier. That single property is what makes the caps tier-aware without either cap knowing
    tiers exist: the section cap truncates the tail, and the US share cap walks best-first,
    so both spend tier-3 picks before tier-2 and touch tier-1 last.
    """
    flat, tier_of = {}, {}
    for sec, val in picks.items():
        if isinstance(val, dict):
            try:
                order = sorted(val, key=int)
            except ValueError:
                sys.exit("picks for %r use non-numeric tier keys %s - expected \"1\"/\"2\"/\"3\""
                         % (sec, sorted(val)))
            rows, tiers = [], {}
            for t in order:
                for n in val[t]:
                    if n not in tiers:          # first (best) tier wins on duplicates
                        rows.append(n)
                        tiers[n] = int(t)
            flat[sec], tier_of[sec] = rows, tiers
        else:
            flat[sec] = list(val)
            tier_of[sec] = {n: 2 for n in val}
    return flat, tier_of


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json_path")
    ap.add_argument("picks_path")
    ap.add_argument("--date", help="ISO date for the heading (default: today)")
    ap.add_argument("--md", metavar="PATH", help="also write a markdown copy")
    ap.add_argument("--no-mark", action="store_true",
                    help="do not record these stories as published (dry run)")
    ap.add_argument("--no-check-links", action="store_true",
                    help="skip verifying that every emitted URL is live. Do not use: the "
                         "check is what stops a dead or invented link reaching the doc")
    ap.add_argument("--allow-reclass", action="store_true",
                    help="permit picks filed under a section the classifier disagrees with. "
                         "Use only for a deliberate override, and say so in the run notes")
    ap.add_argument("--no-resolve", action="store_true",
                    help="skip trying to turn Google News redirects into publisher "
                         "URLs (the attempt takes a couple of minutes)")
    ap.add_argument("--no-authors", action="store_true",
                    help="skip fetching article pages to recover missing bylines")
    ap.add_argument("--no-region-sort", action="store_true",
                    help="keep the picked order exactly as given, instead of enforcing "
                         "UK -> Europe -> rest within each section")
    args = ap.parse_args()

    data = json.load(open(args.json_path))
    # importance() scales its age thresholds by the sweep window (84h Mondays, 36h else);
    # without this every weekend story would take the stale malus on a Monday compose.
    shortlist.SWEEP_WINDOW_H = data.get("window_hours") or shortlist.SWEEP_WINDOW_H
    items = data["items"]
    picks, pick_tiers = normalize_picks(json.load(open(args.picks_path)))
    link_fixes = load_link_fixes()

    # Classify the WHOLE sweep once, then stamp corroboration, before anything reads
    # importance(). Two consumers depend on this: the reclass guard just below, and the US
    # share cap further down.
    #
    # It has to be the whole sweep, not the picks. Corroboration counts how many outlets filed
    # on a story, and curation deliberately drops the near-duplicates that constitute the
    # count - so measured over picks alone an x18 story reads as x1, which inverts the signal.
    # Skipping this is what left the US cap's exemption inert on 18.08.2026: _corr defaulted
    # to 1, reach scored 0 for every story, and a Supreme Court ruling could be dropped for
    # being American, the one outcome cap_us_share exists to prevent.
    #
    # ~0.9s on a 1,360-item sweep, against minutes already spent resolving links.
    for it in items:
        section_of, score = shortlist.classify(it["headline"], it.get("outlet") or "",
                                               it.get("categories"),
                                               shortlist.region_text(it))
        it["_section"] = section_of
        it["_score"] = score
    # Placed and not chaff - the same basis shortlist.py corroborates over, so importance()
    # means the same thing in both programs and US_EXEMPT_AT keeps its calibration.
    # Blocked outlets are excluded as well as chaff (Chris, 24.08.2026: "don't include or count
    # anything on their site"). shortlist.py drops them before classifying, so its corroboration
    # never saw them; this basis filtered only on chaff, so a blocked repost could still inflate
    # a story's _corr here - and _corr is what US_EXEMPT_AT reads. Editorial weight from a source
    # ruled out entirely.
    shortlist.stamp_corroboration(
        [it for it in items if it.get("_section")
         and not shortlist.is_blocked_outlet(it.get("outlet") or "")
         and not shortlist.is_chaff(it["headline"], it.get("outlet") or "",
                                    it.get("categories"))])

    # A blocked outlet must never reach the document, whoever picked it and however good the
    # story looks. On 20.08.2026 three Christianity Daily items published against a standing
    # BLOCKED rule from 19.08: shortlist.py suppressed them, but suppression only removes an
    # item from the SHORTLIST - nothing downstream re-checked, so picking the index by hand
    # walked straight past the ban. There is deliberately no --allow flag here. These are
    # standing decisions, not judgement calls, and the predicate is imported from shortlist
    # so the two layers cannot drift apart.
    banned = []
    for section, idxs in picks.items():
        for n in idxs:
            if not (isinstance(n, int) and 0 <= n < len(items)):
                continue
            it = items[n]
            if shortlist.is_blocked_outlet(it.get("outlet") or ""):
                banned.append((n, it.get("outlet") or "", html.unescape(it["headline"])[:58]))
    if banned:
        sys.stderr.write(
            "\n%d pick(s) are from an outlet that has been ruled out as a source.\n"
            "These are listed under SUPPRESSED, BLOCKED SOURCES in the shortlist, which is\n"
            "not a review bucket - remove them from picks.json rather than overriding.\n\n"
            % len(banned))
        for n, outlet, head in banned:
            sys.stderr.write("  %-5d %-28s | %s\n" % (n, outlet[:28], head))
        sys.exit("refusing to compose with blocked sources in picks")

    # Every pick is checked against the classifier before anything is rendered.
    #
    # On 17.08.2026 three picks were filed under the wrong section because the ranking sheet's
    # LINE NUMBER was copied instead of the item index: a 5Pillars election piece landed in
    # Life, an Idaho abortion story in Church & Religion, a Bangladeshi athletics story in
    # Politics. Two were spotted by eye; the third only turned up when this comparison was run
    # by hand. Nothing in the pipeline was wrong - the curation step was - which is exactly the
    # kind of error that needs a gate rather than good intentions.
    mismatched = []
    for section, idxs in picks.items():
        for n in idxs:
            if not (isinstance(n, int) and 0 <= n < len(items)):
                continue
            it = items[n]
            got = it.get("_section")
            if got and got != section:
                mismatched.append((n, section, got, html.unescape(it["headline"])[:58]))
    if mismatched:
        sys.stderr.write(
            "\n%d pick(s) are filed under a section the classifier disagrees with.\n"
            "This is usually a transposed index - check the number against the sheet.\n"
            "If the placement is deliberate, re-run with --allow-reclass.\n\n" % len(mismatched))
        for n, want, got, head in mismatched:
            sys.stderr.write("  %-5d filed under %-32s classifier says %-32s | %s\n"
                             % (n, want[:32], got[:32], head))
        if not args.allow_reclass:
            sys.exit("refusing to compose with mismatched picks")
        sys.stderr.write("\n--allow-reclass given: continuing.\n")

    day = (dt.date.fromisoformat(args.date) if args.date else dt.date.today())
    heading = day.strftime("%A %-d %B %Y") if sys.platform != "win32" \
        else day.strftime("%A %d %B %Y")

    unknown = [s for s in picks if s not in ORDER]
    if unknown:
        sys.exit("unknown section(s) in picks: %s\nvalid: %s"
                 % (", ".join(unknown), ", ".join(ORDER)))

    # Chris wants publisher links, never Google redirects, wherever one can be found.
    picked = [items[n] for ns in picks.values() for n in ns if 0 <= n < len(items)]
    if not args.no_resolve:
        got, missed = resolve.resolve_items(picked)
        sys.stderr.write("resolved %d Google News links to publisher URLs; "
                         "%d could not be resolved\n" % (got, len(missed)))
        # Tripwire. decode_gnews() asks Google for the real URL and answers for essentially
        # everything (114/114 on 18.08.2026), but it leans on undocumented details - the
        # data-n-a-sg/ts/id attributes, the batchexecute path, the Fbv4je RPC id, the
        # garturlres envelope. When Google changes any of them the decode just returns None,
        # the slug-guessing fallback quietly takes over, and the run still exits 0 with a
        # doc full of ↗ links. That is a silent regression to the old behaviour, so say so
        # loudly instead: a healthy day is 0 unresolved, and anything past a fifth of the
        # batch means the route needs re-testing, not that the news changed shape.
        attempted = got + len(missed)
        if attempted and len(missed) > max(3, attempted // 5):
            sys.stderr.write(
                "\n*** RESOLVER DEGRADED: only %d of %d Google News links decoded (%.0f%%).\n"
                "*** decode_gnews() is probably broken - Google moves these details without\n"
                "*** notice. Re-test it before trusting the ↗ count, and say so in the\n"
                "*** run's final message. The briefing is still valid: unresolved links keep\n"
                "*** their redirect, which is ugly but never wrong.\n\n"
                % (got, attempted, 100.0 * got / attempted))
        if resolve.BLOCKED:
            # Separating these matters: a blocked host will never resolve however good the
            # resolver gets, while a genuine miss is a resolver bug worth chasing.
            sys.stderr.write("  %d host(s) refused the verification fetch (403/405/429), so "
                             "their links keep the redirect by design: %s\n"
                             % (len(resolve.BLOCKED), ", ".join(sorted(resolve.BLOCKED))))
        for it in missed:
            sys.stderr.write("  unresolved: %s — %s\n"
                             % (it.get("publisher") or "?", it["headline"][:70]))

    # Bylines. Runs AFTER resolve on purpose: resolve turns some Google redirects into real
    # publisher URLs, and each one it converts is a page the byline reader can then open.
    if not args.no_authors:
        filled, overridden, unreachable = authors.enrich(
            picked, is_commentary=is_commentary)
        sys.stderr.write("bylines: %d read from the article page, %d from bylines.txt, "
                         "%d unreachable (Google redirect, no page to read)\n"
                         % (filled, overridden, unreachable))

    # Title and date are styled paragraphs, not headings - that is how they appear in
    # Chris's own editions, and it stops Google Docs normalising them to its default
    # Heading 1 and overriding the 36pt/14pt sizes. Only the section names are real H1,
    # which keeps the document outline useful.
    out = ['<p style="%s">Breakfast Briefing</p>' % TITLE_STYLE,
           '<p style="%s">%s</p>' % (DATE_STYLE, day.strftime("%d.%m.%Y"))]
    md = ["# Breakfast Briefing", "", "*%s*" % heading]
    seen, total = set(), 0
    # What actually reached the doc, and what a cap threw out. mark_published.py reads
    # this so the marking can never disagree with the cap: before it existed, marking ran
    # off picks.json and recorded 357 stories for a 333-item doc (18.08.2026), stamping 24
    # cap-dropped items as published.
    composed_out, cut_by_cap = {}, {}

    for section in ORDER:
        chosen = [i for i in picks.get(section, []) if not (i in seen or seen.add(i))]
        if not chosen:
            continue
        # Chris, 14.08.2026: Politics & Government runs to 40 items maximum - originally 30,
        # lifted when he chose to keep Immigration & Asylum as its own section rather than
        # fold it in here. With the
        # widened prefilter there are 150-250 political candidates a day competing for those
        # slots, so this is the one section where ranking is genuinely load-bearing.
        #
        # Capped BEFORE the region sort, never after: sorting first and truncating second
        # chops whole regions off the end, which is how Africa and Latin America vanished
        # from an earlier edition. The shortlist still prints every political candidate, so
        # this caps what is PUBLISHED, not what is visible - nothing is hidden from review.
        kept = []
        for n in chosen:
            it = items[n] if 0 <= n < len(items) else None
            # A supplied publisher URL rescues the item: the credit and the link agree again,
            # so the repost check below no longer fires and the story keeps its place.
            if it:
                hay = ((it.get("headline") or "") + " " + (it.get("url") or "")).lower()
                for match, real in link_fixes:
                    if match in hay:
                        if it.get("url") != real:
                            sys.stderr.write("link fixed: %s -> %s\n"
                                             % (html.unescape(it["headline"])[:52], real[:64]))
                        it["url"] = real
                        break
            if it and REPOST_DOMAINS.search(it.get("url") or ""):
                sys.stderr.write(
                    "DROPPED (repost link, credit would not match): %d | %s | credited to %s "
                    "| %s\n" % (n, html.unescape(it["headline"])[:66],
                                it.get("outlet") or "?", (it.get("url") or "")[:60]))
                continue
            kept.append(n)
        chosen = kept
        cap = SECTION_CAPS.get(section)

        # US share cap, BEFORE the section cap. Chris, 16.08.2026, wired in on 18.08.2026 at
        # 30%: American coverage is prolific and files in English, so left alone it crowds out
        # the UK, Europe and the persecution reporting from Africa and Asia this briefing
        # exists to surface. It ran at 38% the day the cap was wired in.
        #
        # Order matters. Capping US share first and truncating second keeps Politics at its
        # full 40 with a balanced mix; doing it the other way round would publish 34 items and
        # could still leave the surviving 40 US-heavy, since truncation is blind to region.
        us_rows = [items[n] for n in chosen]
        n_non_us = sum(1 for it in us_rows
                       if regions.region(it["headline"], it.get("outlet") or "", "",
                                         shortlist.region_text(it))
                       != "United States")
        # Tiers 1 AND 2 are exempt (Chris, 24.08.2026). See cap_us_share: importance() was the
        # only exemption, so a must-run American story could be cut by a score that disagreed
        # with the judgement already made. Tier 1 alone was not enough - the three Life stories
        # Chris named on the TEST 20260824 draft were all tiered 2, and Life was still losing
        # 22 of 28 US picks after exempting tier 1, because pro-life news is overwhelmingly
        # American and a 30% share cuts most of the section's real candidates every day. So
        # only TIER 3 filler now competes for the US quota. Exempt rows still consume quota,
        # so they displace tier-3 American items before any non-US item is touched.
        tier1_ids = frozenset(id(items[n]) for n in chosen
                              if pick_tiers.get(section, {}).get(n) in (1, 2))
        keep_rows, drop_rows = shortlist.cap_us_share(
            us_rows, limit=shortlist.us_allowance(n_non_us, section_cap=cap),
            exempt_ids=tier1_ids)
        if drop_rows:
            dropped_ids = {id(it) for it in drop_rows}
            dropped_ns = [n for n in chosen if id(items[n]) in dropped_ids]
            chosen = [n for n in chosen if id(items[n]) not in dropped_ids]
            sys.stderr.write("%s: US share cap dropped %d of %d US item(s)\n"
                             % (section, len(drop_rows), len(us_rows) - n_non_us))
            # Tiers 1-2 are exempt above, so this can no longer fire. Kept as an assertion:
            # if it ever does, the exemption has broken, not the picks.
            t1_lost = [n for n in dropped_ns
                       if pick_tiers.get(section, {}).get(n) in (1, 2)]
            if t1_lost:
                sys.stderr.write("%s: WARNING - the US share cap cut %d TIER-1 pick(s) "
                                 "despite the exemption; this is a BUG, not a rebalancing "
                                 "problem: %s\n"
                                 % (section, len(t1_lost),
                                    ", ".join(str(n) for n in t1_lost)))
            # NOT retired to cut.json. A section-cap loss means "40 better things ran today",
            # which is a quality verdict and retires the story (Chris, 18.08.2026). A US-share
            # loss means "wrong passport today" - the story may be the best thing available
            # tomorrow, when the section's mix differs. Retiring these would systematically
            # bin good American reporting, since the surplus recurs daily.

        if cap and len(chosen) > cap:
            sys.stderr.write("%s: capped %d picks to %d\n" % (section, len(chosen), cap))
            # chosen is tier-ordered (normalize_picks), so truncating the tail cuts tier 3
            # first, then tier 2, and reaches tier 1 only if tier 1 alone overfills the cap.
            # A tier-1 cut retires a "must run" story PERMANENTLY (cut.json), so it is the
            # one case that must be shouted about rather than logged.
            t1_cut = [n for n in chosen[cap:]
                      if pick_tiers.get(section, {}).get(n) == 1]
            if t1_cut:
                sys.stderr.write("%s: WARNING - the section cap is retiring %d TIER-1 "
                                 "pick(s) permanently; tier-1 alone exceeds the cap of %d. "
                                 "Rebalance the picks: %s\n"
                                 % (section, len(t1_cut), cap,
                                    ", ".join(str(n) for n in t1_cut)))
            cut_by_cap[section] = chosen[cap:]
            chosen = chosen[:cap]
        if not args.no_region_sort:
            # Stable, so any deliberate ordering inside a region survives.
            chosen = regions.sort_by_region(
                chosen, key=lambda n: (items[n]["headline"], items[n]["outlet"],
                                       items[n].get("url") or ""))
            chosen = spread_outlets(chosen, items)
        composed_out[section] = list(chosen)
        out.append('<h1 style="%s">%s</h1>' % (SECTION_STYLE, html.escape(section)))
        md += ["", "## %s" % section, ""]
        for n in chosen:
            if not 0 <= n < len(items):
                sys.exit("pick %d is out of range (0-%d)" % (n, len(items) - 1))
            it = items[n]
            total += 1
            # unescape first: sweeps taken before the fetch_feeds fix may hold
            # literal entities, and escaping those again shows "&#8217;" in the doc
            headline = html.unescape(it["headline"])
            cred = html.unescape(credit(it))
            out.append('<p style="margin-bottom:%s"><a href="%s"><span style="%s">%s</span></a>'
                       '<br/><span style="%s">%s</span></p>'
                       % (STORY_GAP, html.escape(it["url"], quote=True), HEADLINE_STYLE,
                          html.escape(headline), CREDIT_STYLE, html.escape(cred)))
            md.append("- [%s](%s) — *%s*" % (headline, it["url"], cred))

    # Verify every link before it can reach the document. On 12.08.2026 seven invented
    # URLs were typed into the Drive call in place of unresolved Google redirects; this
    # gate makes that impossible to repeat.
    if not args.no_check_links:
        # Match the paragraph regardless of its attributes. The literal '<p><a href="' broke
        # on 17.08.2026 when the item paragraph gained style="margin-bottom:12pt" (the
        # spacer-paragraph change), and the failure was silent in the worst way: the regex
        # found 0 URLs, so the dead-link probe checked nothing, "none missing" was vacuously
        # true, and expected_urls.txt was written empty - disarming the one check that
        # distinguishes an invented URL from a corrupted one, on the very day the markup
        # changed. Anchor on the tag, never on the exact attribute list.
        urls = re.findall(r'<p[^>]*>\s*<a href="([^"]+)"', "\n".join(out))
        dead = []

        # A gate that verifies nothing must fail, not pass. If the document has items but
        # no URL was extracted, the pattern above has drifted from the markup again.
        if not urls and any('<a href="' in chunk for chunk in out):
            sys.stderr.write(
                "compose.py: link check extracted 0 URLs from a document that contains "
                "links - the item-paragraph pattern no longer matches the markup. Refusing "
                "to write an unverified briefing.\n")
            sys.exit(1)

        # A 403 proves nothing: news.com.au returns 403 for a URL that was invented and
        # Daily Signal returns 403 for URLs straight out of its own feed. So only treat
        # "not found" as fatal, and report blocked ones as unverifiable.
        def probe(u):
            import urllib.error
            try:
                fetch_feeds.fetch(u, retry_uas=2)
                return u, "live"
            except RuntimeError as exc:
                msg = str(exc)
                if "404" in msg or "410" in msg:
                    return u, "missing"
                return u, "blocked"
            except Exception:  # noqa: BLE001
                return u, "blocked"

        import concurrent.futures as _f
        blocked = []
        with _f.ThreadPoolExecutor(max_workers=10) as pool:
            for u, verdict in pool.map(probe, urls):
                if verdict == "missing":
                    dead.append(u)
                elif verdict == "blocked":
                    blocked.append(u)
        # Provenance is the real guarantee: every URL here came out of the sweep JSON,
        # so writing this list lets a published doc be checked against it afterwards.
        with open(os.path.join(HERE_DIR, "expected_urls.txt"), "w") as fh:
            fh.write("\n".join(urls) + "\n")
        # Indices, not URLs: the resolver rewrites item["url"] in place, so a URL cannot
        # be traced back to the pick it came from, but an index always can.
        with open(os.path.join(HERE_DIR, "composed.json"), "w") as fh:
            json.dump({"composed": composed_out, "cut_by_cap": cut_by_cap}, fh, indent=1)
        if cut_by_cap:
            sys.stderr.write("cut by cap: %d item(s) recorded in composed.json - "
                             "mark_published.py will retire them\n"
                             % sum(len(v) for v in cut_by_cap.values()))
        if blocked:
            sys.stderr.write("%d links could not be verified (403/timeout - the outlet "
                             "blocks automated requests). They came from the feed data, "
                             "so use them as-is.\n" % len(blocked))
        if dead:
            sys.stderr.write("\nDEAD LINKS (%d) - not writing the briefing:\n" % len(dead))
            for u in dead:
                sys.stderr.write("  %s\n" % u)
            sys.exit(1)
        redirects = [u for u in urls if "news.google.com" in u]
        sys.stderr.write("\nPASTE VERBATIM - %d links, none missing. Full list written to "
                         "expected_urls.txt; anything not in that file is fabricated.\n"
                         % len(urls))
        if redirects:
            sys.stderr.write("%d are Google News redirects the resolver could not convert. "
                             "KEEP THEM AS-IS:\n" % len(redirects))
            for u in redirects:
                sys.stderr.write("  KEEP AS-IS  %s\n" % u[:110])

    sys.stdout.write("\n".join(out) + "\n")
    if args.md:
        with open(args.md, "w") as fh:
            fh.write("\n".join(md) + "\n")

    # Record only what is actually going into the doc, so unchosen candidates stay
    # available for tomorrow.
    marked = 0
    if not args.no_mark:
        db = fetch_feeds.load_seen()
        stamp = dt.datetime.now(dt.timezone.utc).isoformat()
        for n in seen:
            db[fetch_feeds.url_key(items[n]["url"])] = stamp
            marked += 1
        fetch_feeds.save_seen(db)

    # Coverage check. Chris, 24.08.2026, having listed 33 stories that should have run: 17 of
    # them were in that day's sweep and simply were not picked, most from sources whose own
    # releases are x1 and sink in a corroboration-ordered sheet. Nothing in the pipeline
    # noticed. check_sources.py catches a source that stopped FILING; nothing caught a source
    # that filed and was then read past. This is that check, and it runs at compose time - the
    # last point before publishing, where it can still be acted on.
    picked_outlets, cand = set(), {}
    for sec in ORDER:
        for n in composed_out.get(sec, []):
            picked_outlets.add((items[n].get("outlet") or "").lower())
    for it in items:
        outlet = (it.get("outlet") or "")
        if not it.get("_section") or shortlist.is_blocked_outlet(outlet.lower()):
            continue
        if any(t in outlet.lower() for t in shortlist.COVERAGE_WATCH):
            cand.setdefault(outlet, []).append(it["headline"][:58])
    missed = {o: hs for o, hs in cand.items() if o.lower() not in picked_outlets}
    if missed:
        sys.stderr.write(
            "\nCOVERAGE - %d watched source(s) filed today and NOTHING of theirs was picked.\n"
            "These are the ones that sink in a corroboration-ordered sheet. Check each before\n"
            "publishing; if a miss is deliberate, say so in the final message.\n" % len(missed))
        for o, hs in sorted(missed.items(), key=lambda kv: -len(kv[1])):
            sys.stderr.write("  %-30s %d unpicked | %s\n" % (o, len(hs), hs[0]))
        sys.stderr.write("\n")

    sys.stderr.write("composed %d items across %d sections%s\n"
                     % (total, sum(1 for s in ORDER if picks.get(s)),
                        "; %d recorded as published" % marked if marked else ""))


if __name__ == "__main__":
    main()
