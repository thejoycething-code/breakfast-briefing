#!/usr/bin/env python3
"""Run the regression fixture in testcases.txt against the live classifier and region map.

Written 17.08.2026. Everything in this pipeline was verified ad hoc until now: I checked a
change by hand, the check scrolled away, and the next change had no memory of it. Two bugs
that day came straight from that. Wiring is_school_routine in activated a latent "assembly"
rule that suppressed the West Bengal and NI Assemblies, and it was caught only because I
happened to read the suppression list; and seven substring collisions of the same shape
(oman/Woman, WHO/who, telegraph/telegraphindia, herald/Deccan, express/Indian Express,
the federal/The Federalist, assembly/NI Assembly) had all shipped unnoticed.

Every case here is a claim someone made about what this briefing is for - mostly Chris's, in
his own words, dated. Run it before and after any change to the patterns:

    python3 run_tests.py            # all cases
    python3 run_tests.py -v         # print passes too

Exit status is 1 if anything fails, so it can gate a commit or a scheduled run.
"""

import datetime as dt
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# Drop any cached bytecode for this directory BEFORE importing anything from it.
#
# This is not housekeeping, it is a correctness guard on the fixture itself. CPython
# invalidates a .pyc on (mtime, size), and this Mac's python sets sys.pycache_prefix to
# ~/Library/Caches/com.apple.python - so the cache lives OUTSIDE the project and a
# `find . -name __pycache__` finds nothing to suggest it exists.
#
# On 01.09.2026 an edit and a test run landed in the same second. shortlist.py and its .pyc
# then carried identical mtimes, python reused the stale bytecode, and run_tests measured a
# version of the code that was no longer on disk. It was caught only because a new assertion
# happened to compare two functions whose call order had been swapped: the source said one
# thing and dis() said the other. Everything mutation-tested in that session had to be
# re-run. A test suite that can silently grade the wrong build is worse than no test suite,
# so the cache goes before the imports.
sys.dont_write_bytecode = True
_cache_root = sys.pycache_prefix
if _cache_root:
    import shutil
    shutil.rmtree(os.path.join(_cache_root, HERE.lstrip(os.sep)), ignore_errors=True)
shutil = None  # noqa: F811  - not needed again; keep the namespace tidy

import shortlist   # noqa: E402
import regions     # noqa: E402
import compose     # noqa: E402
import fetch_feeds # noqa: E402
import resolve     # noqa: E402

CASES = os.path.join(HERE, "testcases.txt")


def parse(path=CASES):
    """Yield (lineno, kind, expected, fields). Tolerates | inside headlines.

    The Washington Post files headlines like "Opinion | Virginia is putting...", so the
    headline is whatever remains after the fixed leading fields - never split it blindly.
    """
    with open(path) as fh:
        for n, line in enumerate(fh, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            head, _, rest = line.partition("|")
            head = head.strip()
            kind, _, expected = head.partition(" ")
            kind, expected = kind.strip().upper(), expected.strip()
            parts = [p.strip() for p in rest.split("|")]
            yield n, kind, expected, parts, rest.strip()


def run(verbose=False, known_red=None):
    passed, failed = 0, []
    for n, kind, expected, parts, rest in parse():
        try:
            if kind == "SECTION":
                outlet, headline = parts[0], "|".join(parts[1:]).strip()
                # Optional article opening after "::text::", same convention as REGION. The
                # lead-text tiebreak (25.08.2026) can only be tested with a body attached.
                body = ""
                if "::text::" in headline:
                    headline, _, body = headline.partition("::text::")
                    headline, body = headline.strip(), body.strip()
                got = shortlist.classify(headline, outlet, None, body)[0]
                # "SECTION None" asserts the item must reach NO section at all - the guard
                # on widening the Other gates. Added 19.08.2026: without it the landfill
                # rule ("Other is a positive category") was unexpressible, so a widening
                # that swept in Spectator lifestyle columns would pass the fixture.
                want = None if expected in ("None", "-") else expected
                ok = (got == want)
                detail = "%s -> %s" % (headline[:54], got)
            elif kind == "REGION":
                outlet, url = parts[0], ("" if parts[1] == "-" else parts[1])
                headline = "|".join(parts[2:]).strip()
                # Optional article text, after a "::text::" marker. Not a new pipe-separated
                # field: everything after the url is joined back into the headline precisely
                # because headlines contain "|", so another field could never be parsed. Added
                # 25.08.2026 with region_detail's `text` argument - a correction that turns on
                # the body needs a fixture that can carry the body.
                body = ""
                if "::text::" in headline:
                    headline, _, body = headline.partition("::text::")
                    headline, body = headline.strip(), body.strip()
                got = regions.region_detail(headline, outlet, url, body)[0]
                ok = (got == expected)
                detail = "%s / %s -> %s" % (outlet[:18], headline[:38], got)
            # Added 19.08.2026 with Chris's markup on that edition. Two kinds of correction
            # he makes regularly had no executable form: "mark this outlet (£)" and "remove
            # this source". Both were previously a hand edit to a regex with nothing holding
            # them, which is the failure testcases.txt exists to prevent.
            elif kind == "PAYWALLED":
                raw = parts[0]
                line_out = compose.credit({"outlet": raw, "author": "", "url": ""})
                ok = ("(£)" in line_out) and (expected in line_out)
                got, detail = line_out, "%s -> %s" % (raw[:28], line_out)
            elif kind == "HEADLINE":
                # HEADLINE <expected suffix, or "-" for none> | <raw title>
                # The expected value is the SUFFIX, not the cleaned headline: a headline may
                # contain "|" (the Washington Post's "Opinion | ...") and that is this file's
                # field separator, so it can only ever appear on the right-hand side.
                raw = rest
                head, suffix = fetch_feeds.strip_outlet_suffix(raw)
                got = suffix or "-"
                # The reconstruction check can no longer be "raw minus the suffix": suffixes
                # stack, so the head may have had a second one removed as well. What must
                # still hold is that the head is a genuine PREFIX of the raw title - nothing
                # invented, nothing reordered - and that the suffix really was at the end.
                ok = (got == expected) and (suffix == "" or
                                            (raw.startswith(head) and raw.endswith(suffix)))
                detail = "%r -> head=%r suffix=%r" % (raw[:44], head[:40], suffix)
            elif kind == "HEADCLEAN":
                # HEADCLEAN <expected cleaned headline> | <raw title>
                # Written when Google News stacks its own suffix on top of the publisher's:
                # only the head shows whether BOTH came off, and the suffix cannot say so.
                got = fetch_feeds.strip_outlet_suffix(rest)[0]
                ok = (got == expected)
                detail = "%r -> %r" % (rest[:40], got[:52])
            elif kind == "BYLINE":
                # BYLINE shown|hidden | <outlet> | <author> [| <url>]
                # Not a full-credit comparison: the credit line itself contains "|", which is
                # this file's field separator, so an expected line could never be written.
                # A 4th field is the article's own opening. Added 28.08.2026 with the text
                # signal: whether a byline shows can now turn on the body, so a case about
                # that has to be able to carry one.
                outlet, author = parts[0], (parts[1] if len(parts) > 1 else "")
                url = parts[2] if len(parts) > 2 else ""
                opening = "|".join(parts[3:]).strip() if len(parts) > 3 else ""
                # "::section:: opinion" sets the PAGE's own section marker instead, which is
                # what authors.py now reads off the article while it is there for the byline.
                section = ""
                if opening.startswith("::section::"):
                    section = opening[len("::section::"):].strip()
                    opening = ""
                line_out = compose.credit({"outlet": outlet, "author": author, "url": url,
                                           "_opening": opening, "_page_section": section})
                shown = ("| " + author) in line_out
                got = "shown" if shown else "hidden"
                ok = (got == expected.lower())
                detail = "%s -> %s" % (outlet[:24], line_out)
            elif kind == "KEYWORD":
                # KEYWORD <keep|drop> | <headline>
                # The FETCH-TIME gate, which no other assertion reaches: SECTION and SUPPRESS
                # both run on items that already got past it. A headline the filter rejects
                # never enters the sweep at all, so its absence cannot be diagnosed later -
                # which is how the Stars and Stripes lawsuit went missing with nothing to show
                # for it (28.08.2026). Applies to filter/gnewsf/bingf/scrapesrcf sources.
                raw = "|".join(parts).strip()
                got = "keep" if fetch_feeds.KEYWORD_RE.search(raw) else "drop"
                ok = (got == expected.lower())
                detail = "%s -> %s" % (raw[:54], got)
            elif kind == "BLOCKED":
                raw = parts[0]
                # A neutral headline, so only the outlet can be doing the blocking.
                got = shortlist.is_chaff("Council approves new bus timetable", raw, None)
                ok = bool(got)
                detail = "%s -> %s" % (raw[:34], "blocked" if got else "NOT blocked")
            elif kind in ("SUPPRESS", "KEEP"):
                outlet, headline = parts[0], "|".join(parts[1:]).strip()
                sec, sc = shortlist.classify(headline, outlet, None)
                sup = (shortlist.is_chaff(headline, outlet, None)
                       or (bool(sec) and (shortlist.is_school_routine(headline, sc)
                                          or shortlist.is_school_crime(headline, sc)
                                          or shortlist.is_local_incident(headline, sc, sec))))
                got = "SUPPRESS" if sup else "KEEP"
                ok = (got == kind)
                detail = "%s -> %s" % (headline[:54], got)
            elif kind == "ABOVE":
                # RANK ordering: the first headline must outrank the second. Encodes the
                # outcome-over-process axis, which no other assertion type can express.
                ha, hb = parts[0], "|".join(parts[1:]).strip()
                ia = shortlist.importance({"headline": ha, "outlet": "x", "_corr_tier": 0})
                ib = shortlist.importance({"headline": hb, "outlet": "x", "_corr_tier": 0})
                ok = ia > ib
                detail = "%d vs %d | %s" % (ia, ib, ha[:40])
            elif kind in ("SAMESTORY", "NOCLUSTER"):
                # Clustering ground truth: must these two headlines merge, or stay apart?
                # Added 19.08.2026 with the entity co-occurrence floor. Both headlines are
                # built as a two-item corpus so the shared entity clears ENTITY_MIN_DF=2,
                # which is what makes a two-line fixture case meaningful at all.
                ha, hb = parts[0], "|".join(parts[1:]).strip()
                a = {"headline": ha, "outlet": "x", "_section": "Life", "_score": 5}
                b = {"headline": hb, "outlet": "y", "_section": "Life", "_score": 5}
                wa, wb = shortlist.sig_words(ha), shortlist.sig_words(hb)
                ents = shortlist.entity_index([a, b])
                shared = {e for e in (shortlist.ent_tokens(ha) & shortlist.ent_tokens(hb))
                          if e in ents}
                merged = shortlist.same_story(a, b, wa, wb, shared)
                got = "SAMESTORY" if merged else "NOCLUSTER"
                ok = (got == kind)
                detail = "%d shared words, entity=%s -> %s" % (
                    len(wa & wb), sorted(shared)[:1] or "-", got)
            elif kind == "COUNTRY":
                # COUNTRY <country> | <outlet> | <headline>
                # Region alone cannot express "group the two Cameroon stories together":
                # Africa is one tier holding many countries. This asserts the finer detector;
                # the grouping itself is a property of a list, so it is a smoke test below.
                outlet, headline = parts[0], "|".join(parts[1:]).strip()
                got = regions.country_of(headline, outlet, "")
                ok = (got == expected)
                detail = "%s -> %s" % (headline[:48], got)
            elif kind == "SECTIONCAT":
                # SECTIONCAT <section> | <outlet> | <cat,cat,...> | <headline>
                # Same as SECTION but carries the publisher's own tags, which classify()
                # weighs against the headline. Added 20.08.2026: the plain SECTION form
                # passes categories=None, so it could not express the case Chris actually
                # marked up - The Federalist's UK speech-ban story routes to Free Speech on
                # its headline alone, and only the "Religious Freedom" TAG pulled it back.
                outlet = parts[0]
                cats = [c.strip() for c in parts[1].split(",") if c.strip()]
                headline = "|".join(parts[2:]).strip()
                got = shortlist.classify(headline, outlet, cats)[0]
                want = None if expected in ("None", "-") else expected
                ok = (got == want)
                detail = "%s +%d tag(s) -> %s" % (headline[:40], len(cats), got)
            elif kind == "DEVELOPMENT":
                # DEVELOPMENT <yes|no> | <headline A> ::vs:: <headline B>
                # Tests is_development_of directly. Added 27.08.2026 with the noun/verb fix:
                # the collision was found THROUGH ran_before, but it belongs to this function,
                # and a case written at the ran_before level would still pass if the bug moved.
                joined = "|".join(parts)
                ha, _, hb = joined.partition("::vs::")
                got = "yes" if shortlist.is_development_of(
                    {"headline": ha.strip()}, {"headline": hb.strip()}) else "no"
                ok = (got == expected)
                detail = "%s -> %s" % (ha.strip()[:46], got)
            elif kind in ("RANBEFORE", "NOTRANBEFORE"):
                # RANBEFORE | <headline today> ::was:: <headline in a recent edition>
                #            [::sections:: <today section> >> <past section>]
                # Both sides default to one section. That default used to be justified here
                # as "asserting the cross-section rejection would only be re-testing
                # same_story's guard" - which assumed the guard was right. On 08.09.2026 it
                # cost a real repeat, so the sections are now settable and the guard is
                # asserted rather than assumed. See the 08.09.2026 block in testcases.txt.
                joined = "|".join(parts)
                today_h, _, past_h = joined.partition("::was::")
                flags = {}
                if "::entity::" in past_h:
                    past_h = past_h.replace("::entity::", "")
                    flags["ENTITY"] = True
                sec_today = sec_past = "Life"
                if "::sections::" in past_h:
                    past_h, _, secspec = past_h.partition("::sections::")
                    a, _, b = secspec.partition(">>")
                    sec_today, sec_past = a.strip(), b.strip()
                today_h, past_h = today_h.strip(), past_h.strip()
                # ENTITY on the kind line turns the entity arm on for that case, by
                # building an index over the pair. Two documents is a degenerate corpus, so
                # this asserts the ARM fires, not that a real DF gate would keep the token -
                # repeat_eval.py is what measures the gate over a real corpus.
                hist = [{"date": "20260825", "section": sec_past,
                         "headline": past_h, "outlet": "x", "key": ""}]
                ents = (shortlist.entity_index(
                            [{"headline": today_h}, {"headline": past_h}])
                        if flags.get("ENTITY") else None)
                hit = shortlist.ran_before(
                    {"headline": today_h, "_section": sec_today}, hist, ents=ents)
                got = "RANBEFORE" if hit else "NOTRANBEFORE"
                ok = (got == kind)
                detail = "%s -> %s" % (today_h[:46], got)
            elif kind == "OUTLET":
                # Join, do not take parts[0]. A masthead can contain a pipe of its own -
                # FIRE reaches us as "FIRE | Foundation for Individual Rights and " - and
                # splitting on it tested the string "FIRE", which tidy_outlet returns
                # unchanged. The case passed while the bug it was written for was live
                # (Chris, 27.08.2026: "This source should just be FIRE").
                raw = "|".join(parts)
                got = compose.tidy_outlet(raw)
                ok = (got == expected)
                detail = "%s -> %s" % (raw[:34], got)
            elif kind == "CREDIT":
                # CREDIT <shown outlet> | <raw outlet> | <url> [| paywalled]
                # Who the credit line NAMES, and whether it earns its (£), given the feed's
                # outlet field and the link TOGETHER. OUTLET cannot express this: tidy_outlet
                # is handed the name alone and never sees the URL, so it cannot tell a
                # masthead from a site reposting it. credit() receives the whole item.
                # The two are asserted as one string because they are one fault: a repost
                # inherits both the wrong name and the quoted paper's paywall flag, and a fix
                # that corrected only the name would print "The Daily Sceptic (£)".
                # The optional trailing "paywalled" sets that inherited flag.
                outlet = parts[0]
                url = parts[1] if len(parts) > 1 else ""
                flag = len(parts) > 2 and parts[2].strip().lower() == "paywalled"
                line_out = compose.credit(
                    {"outlet": outlet, "author": "", "url": url, "paywalled": flag})
                got = line_out[2:].split(" | ")[0].strip()
                ok = (got == expected)
                detail = "%s + %s -> %s" % (outlet[:16], url[:34], got)
            elif kind == "SPREAD":
                # SPREAD <same|apart> | <outlet> ::at:: <url> | <outlet> ::at:: <url>
                # Do these two land in the SAME per-outlet bucket in spread_outlets?
                # Asserted through spread_outlets itself, not through the key function it
                # happens to call: the 28.08.2026 fault was precisely that credit() and
                # spread_outlets resolved the masthead by two different routes, so a case
                # pinned to the shared helper would pass again the moment one of them
                # stopped using it. A third, unrelated outlet is added because with only
                # two items the round-robin cannot distinguish one bucket from two -
                # grouped deals 0,2,1 and separate deals 0,1,2.
                def _mk(field):
                    o, _, u = field.partition("::at::")
                    return {"headline": "UK council approves new policy",
                            "outlet": o.strip(), "url": u.strip(),
                            "summary": "", "categories": []}
                probe = [_mk(parts[0]), _mk(parts[1]),
                         {"headline": "UK council approves new policy",
                          "outlet": "Filler Gazette", "url": "",
                          "summary": "", "categories": []}]
                order = compose.spread_outlets([0, 1, 2], probe)
                got = "same" if order == [0, 2, 1] else (
                    "apart" if order == [0, 1, 2] else "order=%s" % order)
                ok = (got == expected.lower())
                detail = "%s + %s -> %s" % (probe[0]["outlet"][:14],
                                            probe[1]["outlet"][:14], got)
            elif kind == "PAYWALL":
                # PAYWALL <yes|no> | <outlet>
                # Whether the credit line earns its "(£)". Naming and paywall status are set
                # by two different tables, and on 27.08.2026 Chris corrected both on the same
                # outlet in one note - so the fixture has to be able to state them separately.
                raw = "|".join(parts).strip()
                name = compose.tidy_outlet(raw)
                got = "yes" if compose.PAYWALLED_OUTLETS.match(name) else "no"
                ok = (got == expected)
                detail = "%s -> %s" % (name[:34], got)
            else:
                failed.append((n, "unknown assertion %r" % kind))
                continue
        except Exception as exc:  # noqa: BLE001
            failed.append((n, "%s raised %s: %s" % (kind, type(exc).__name__, exc)))
            continue
        if ok:
            passed += 1
            if verbose:
                print("  pass  %-8s %s" % (kind, detail))
        else:
            failed.append((n, "%-8s expected %-32s got: %s" % (kind, expected, detail)))

    # Smoke test: the ranking sheet must actually generate. The assertions above test pure
    # functions, so on 18.08.2026 a refactor left main()'s sheet block reading a deleted
    # variable and the fixture stayed green while --sheet died with a NameError - the crash
    # would have surfaced at 6am the next morning. One subprocess run on a 3-item sweep
    # catches that whole class. --no-ledes so the test never touches the network.
    import json
    import subprocess
    import tempfile
    mini = {"sources": 1, "items": [
        {"headline": "Nigerian court frees Christian woman arrested for conversion",
         "outlet": "ADF International", "url": "https://example.org/a", "author": "",
         "paywalled": False, "gnews": False, "publisher": "", "feed": "t",
         "category": "t", "categories": [], "published": "", "age_h": 2, "summary":
         "The regional court in Kano ruled the arrest unlawful and ordered her release."},
        {"headline": "Court frees Christian convert in Nigeria", "outlet": "CP",
         "url": "https://example.org/b", "author": "", "paywalled": False,
         "gnews": False, "publisher": "", "feed": "t", "category": "t",
         "categories": [], "published": "", "age_h": 3, "summary": ""},
        {"headline": "Holyrood passes assisted dying safeguards", "outlet": "The Herald",
         "url": "https://example.org/c", "author": "", "paywalled": False,
         "gnews": False, "publisher": "", "feed": "t", "category": "t",
         "categories": [], "published": "", "age_h": 4, "summary": ""},
    ]}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump(mini, fh)
        mini_path = fh.name
    try:
        proc = subprocess.run(
            [sys.executable, os.path.join(HERE, "shortlist.py"), mini_path,
             "--sheet", "--no-ledes"],
            capture_output=True, text=True, timeout=120)
        if proc.returncode == 0 and "RANKING SHEET" in proc.stdout:
            passed += 1
        else:
            failed.append(("smoke", "--sheet exited %d: %s"
                           % (proc.returncode, (proc.stderr or proc.stdout)[-200:])))
    except Exception as exc:  # noqa: BLE001
        failed.append(("smoke", "--sheet smoke test raised %s: %s"
                       % (type(exc).__name__, exc)))
    finally:
        os.unlink(mini_path)

    # Smoke test: archive_day.py -> rank_eval.py. archive_day runs in the 6am path, and a
    # break there loses that edition's labels silently - the edition still publishes, so
    # nothing else would complain. Uses a temp archive dir so the real corpus is untouched.
    with tempfile.TemporaryDirectory() as tmpdir:
        sweep = os.path.join(tmpdir, "sweep.json")
        picks = os.path.join(tmpdir, "picks.json")
        arch = os.path.join(tmpdir, "archive")
        mini2 = dict(mini, generated="2026-01-02T06:00:00+00:00", window_hours=36)
        with open(sweep, "w") as fh:
            json.dump(mini2, fh)
        with open(picks, "w") as fh:                       # tiered format
            json.dump({"Religious Freedom & Persecution": {"1": [0], "3": [2]}}, fh)
        try:
            a = subprocess.run([sys.executable, os.path.join(HERE, "archive_day.py"),
                                sweep, picks, "--archive-dir", arch,
                                "--composed", os.path.join(tmpdir, "nope.json")],
                               capture_output=True, text=True, timeout=120)
            e = subprocess.run([sys.executable, os.path.join(HERE, "rank_eval.py"),
                                "--archive-dir", arch],
                               capture_output=True, text=True, timeout=180)
            if (a.returncode == 0 and os.path.isdir(os.path.join(arch, "20260102"))
                    and e.returncode == 0 and "concordance" in e.stdout):
                passed += 1
            else:
                failed.append(("smoke", "archive/eval round-trip failed: archive rc=%d %s | "
                               "eval rc=%d %s" % (a.returncode, a.stderr[-120:],
                                                  e.returncode, (e.stderr or e.stdout)[-120:])))
        except Exception as exc:  # noqa: BLE001
            failed.append(("smoke", "archive/eval smoke raised %s: %s"
                           % (type(exc).__name__, exc)))

    # Grouping is a property of a LIST, so no per-item assertion can express it. Chris asked
    # for the two Cameroon stories to sit together (20.08.2026); they were separated by a
    # Nigeria story. Also asserts the half that is easy to lose: the group's position follows
    # its FIRST member, so the highest-ranked country still leads the region.
    grouping = [
        {"headline": "Two Christians kidnapped in Cameroon", "outlet": "Open Doors"},
        {"headline": "The world finally noticed Nigeria's persecuted Christians",
         "outlet": "Christian Post"},
        {"headline": "Cameroon Announces the Closure of 1,400 Revivalist Churches",
         "outlet": "Bitter Winter"},
    ]
    got = [it["headline"][:9] for it in regions.sort_by_region(
        grouping, lambda it: (it["headline"], it["outlet"]))]
    if got == ["Two Chris", "Cameroon ", "The world"]:
        passed += 1
    else:
        failed.append(("smoke", "country grouping: expected the two Cameroon items adjacent "
                                "and leading, got %r" % (got,)))

    # A per-feed window longer than seen.json's retention would re-offer stories that have
    # already been published - the sweep would find them again and nothing would remember.
    # Cheap to assert, invisible if it ever breaks.
    fetch_feeds.load_extra()
    longest = max(list(fetch_feeds.FEED_WINDOWS.values()) or [0])
    if fetch_feeds.SEEN_RETENTION_DAYS * 24 > longest:
        passed += 1
    else:
        failed.append(("smoke", "SEEN_RETENTION_DAYS (%dd) must exceed the longest per-feed "
                                "window (%dh)" % (fetch_feeds.SEEN_RETENTION_DAYS, longest)))

    # A genuinely undated item must age out on the date we FIRST SAW it, not on the run time.
    # Chris, 08.09.2026: "Why do you keep including this every single day? What in the
    # deduplication process has broken?" - the Spectator's surrogacy piece had been in every
    # sweep from 18.08 to 08.09. Nothing in dedup was broken. Dateless scrapesrc items were
    # stamped published=now, so they never left the window, and the only thing holding them
    # back was seen.json - which records PUBLISHED items only, so anything offered and passed
    # over stayed "new" for ever. 41 items carried age_h=None in the 08.09 sweep alone.
    try:
        cutoff = dt.datetime(2026, 9, 7, tzinfo=dt.timezone.utc)
        old = {fetch_feeds.url_key("https://spectator.com/article/x"):
               dt.datetime(2026, 8, 18, tzinfo=dt.timezone.utc).isoformat()}
        stale = fetch_feeds.dateless_is_new("https://spectator.com/article/x", old, cutoff)
        fresh = fetch_feeds.dateless_is_new("https://spectator.com/article/y", old, cutoff)
        if (not stale) and fresh:
            passed += 1
        else:
            failed.append(("smoke", "dateless freshness: first seen 18.08 against a 07.09 "
                                    "cutoff must NOT be new (got new=%s), and an unseen link "
                                    "must be new (got new=%s)" % (stale, fresh)))
    except Exception as exc:  # noqa: BLE001
        failed.append(("smoke", "dateless freshness: %s: %s" % (type(exc).__name__, exc)))

    # The shell tail must survive `set -u` on this Mac's bash. See the two functions below.
    bad_syntax = test_shell_syntax()
    if not bad_syntax:
        passed += 1
    else:
        failed.append(("smoke", "shell script(s) do not parse: %s"
                       % "; ".join("%s: %s" % (s, m) for s, m in bad_syntax)))

    bare = test_shell_empty_array_guards()
    if not bare:
        passed += 1
    else:
        failed.append(("smoke", "%d unguarded empty-array expansion(s) under `set -u` - use "
                                "${a[@]+\"${a[@]}\"}, not \"${a[@]}\": %s"
                       % (len(bare), "; ".join("%s:%d %s" % b for b in bare))))

    # Every script must be in state_sync.sh's backup list. See test_all_scripts_backed_up.
    unbacked, dupes = test_all_scripts_backed_up()
    if not unbacked and not dupes:
        passed += 1
    else:
        msg = []
        if unbacked:
            msg.append("%d script(s) missing from state_sync.sh CODE_FILES, so they are "
                       "backed up NOWHERE: %s" % (len(unbacked), ", ".join(unbacked)))
        if dupes:
            msg.append("%d duplicate entr(y/ies) in CODE_FILES, uploaded twice every push: %s"
                       % (len(dupes), ", ".join(dupes)))
        failed.append(("smoke", " | ".join(msg)))

    # No configured feed may match the sweep-time block list. See test_no_self_blocked_feed.
    self_blocked = test_no_self_blocked_feed()
    if not self_blocked:
        passed += 1
    else:
        failed.append(("smoke", "%d configured feed(s) are blocked by their own block list, "
                                "so every item they cost a request to fetch is discarded: %s"
                       % (len(self_blocked),
                          ", ".join(sorted({b for b, _ in self_blocked})))))

    # No health record may outlive its feed. See test_no_orphaned_health_records.
    orphans = test_no_orphaned_health_records()
    if not orphans:
        passed += 1
    else:
        failed.append(("smoke", "%d orphaned record(s) in source_health.json for feeds "
                                "check_sources.py no longer probes, so their state is frozen "
                                "and the file misreports them: %s"
                       % (len(orphans),
                          "; ".join("%s (%dd)" % (n, f) for n, _u, f in orphans[:6]))))

    # repeat_eval's GOLD veto must not read a harness marker as a word. See the function below.
    gm = test_gold_pairs_strip_markers()
    if not gm:
        passed += 1
    else:
        failed.append(("smoke", "%d gold pair(s) still carry a harness marker: %s"
                       % (len(gm), "; ".join(gm))))

    # Every corpus DIRECTORY must be carried by an uploader. See the function below.
    corp = test_corpus_dirs_backed_up()
    if not corp:
        passed += 1
    else:
        failed.append(("smoke", "%d corpus director(y/ies) backed up NOWHERE: %s"
                       % (len(corp), "; ".join(corp))))

    # The age gloss must fire only where the printed age actually misleads, and the window
    # leak guard must stay quiet on a legitimate long window. See the function below.
    agef = test_age_flag_and_window_leak()
    if not agef:
        passed += 1
    else:
        failed.append(("smoke", "%d age-flag/window-leak problem(s): %s"
                       % (len(agef), "; ".join(agef))))

    # The gnews decoder must not truncate a URL at its query value. See the function below.
    trunc = test_gnews_decode_unescape()
    if not trunc:
        passed += 1
    else:
        failed.append(("smoke", "%d gnews payload(s) decoded to a truncated URL: %s"
                       % (len(trunc), "; ".join("got %s, want %s" % (g, w)
                                                for g, w in trunc))))

    # publish.sh --verify must see URLs containing ")" and still catch real losses.
    pv = test_publish_verify_parens()
    if not pv:
        passed += 1
    else:
        failed.append(("smoke", "%d publish --verify misjudgement(s): %s"
                       % (len(pv), "; ".join(pv))))

    # 27.09.2026 additions: the resume path's verifier, the text scrubber, the paywall
    # re-check after decoding, and the Bing topic routes. See each function below.
    for fn, what in ((test_verify_links, "verify_links (--from) misjudgement"),
                     (test_boilerplate_scrub, "boilerplate scrub problem"),
                     (test_paywall_rechecked_after_decode, "paywall re-check problem"),
                     (test_bing_topic_routes, "Bing topic-route problem"),
                     (test_finish_edition_from_guards, "finish_edition --from guard problem"),
                     (test_event_sizes, "event-size problem"),
                     (test_feedly_parse, "Feedly-route problem"),
                     (test_batched_decode_mapping, "batched-decode problem"),
                     (test_syndicated_credit, "syndicated-copy problem"),
                     (test_decoded_link_tidy, "decoded-link tidy problem"),
                     (test_action_desk, "Action Desk problem"),
                     (test_five_uses_published_url, "Slack-five URL problem"),
                     (test_sheet_fold, "sheet-fold problem"),
                     (test_refresh_petitions, "petition-refresh problem")):
        got = fn()
        if not got:
            passed += 1
        else:
            failed.append(("smoke", "%d %s(s): %s" % (len(got), what, "; ".join(got))))

    # A decode that is really a paginated index must not be trusted. See the function below.
    idx = test_gnews_index_decode_flagged()
    if not idx:
        passed += 1
    else:
        failed.append(("smoke", "%d decoded URL(s) misjudged as article/index: %s"
                       % (len(idx), "; ".join(idx))))

    # A relaying primary source must not lead a cluster. See the function below.
    relay = test_cluster_relay_not_primary()
    if not relay:
        passed += 1
    else:
        failed.append(("smoke", "%d cluster-provenance failure(s): %s"
                       % (len(relay), "; ".join(relay))))

    # An issuing primary source must LEAD a cluster on the sheet. See the function below.
    issuing = test_cluster_lead_prefers_an_issuing_primary()
    if not issuing:
        passed += 1
    else:
        failed.append(("smoke", "%d cluster-provenance failure(s), issuing: %s"
                       % (len(issuing), "; ".join(issuing))))

    # A stock topic phrase must not glue a day's stories together. See the function below.
    phrase = test_common_words_do_not_cluster()
    if not phrase:
        passed += 1
    else:
        failed.append(("smoke", "%d topic-phrase merge(s): %s" % (len(phrase), "; ".join(phrase))))

    # SOURCE_TIER must not substring-match a different masthead. See the function below.
    tiermatch = test_source_tier_not_substring()
    if not tiermatch:
        passed += 1
    else:
        failed.append(("smoke", "%d SOURCE_TIER mis-match(es): %s"
                       % (len(tiermatch), "; ".join(tiermatch))))

    # A dead redirect must not lead a cluster over a clean sibling. See the function below.
    clead = test_cluster_lead_prefers_a_readable_link()
    if not clead:
        passed += 1
    else:
        failed.append(("smoke", "cluster lead link quality: %s" % "; ".join(clead)))

    # A site that identifies articles by query string must not retire wholesale. See below.
    ukey = test_url_key_keeps_article_ids()
    if not ukey:
        passed += 1
    else:
        failed.append(("smoke", "url_key: %s" % "; ".join(ukey)))

    # A WordPress REST collection must parse as a feed. See the function below.
    wpj = test_wpjson_parses_as_a_feed()
    if not wpj:
        passed += 1
    else:
        failed.append(("smoke", "wpjson feed mode: %s" % "; ".join(wpj)))

    # A Google News sitemap must parse as a feed. See the function below.
    nsm = test_news_sitemap_parses_as_a_feed()
    if not nsm:
        passed += 1
    else:
        failed.append(("smoke", "news sitemap: %s" % "; ".join(nsm)))

    # The sheet's coverage line must measure readability, not fetch work. See below.
    cov = test_text_coverage_line_counts_openings()
    if not cov:
        passed += 1
    else:
        failed.append(("smoke", "text coverage line: %s" % "; ".join(cov)))

    # Judgement/measurement files, not just scripts. See test_all_data_files_backed_up.
    unbacked, orphans = test_all_data_files_backed_up()
    if not unbacked:
        passed += 1
    else:
        # Three failure classes share this list and the message must fit all of them: a plain
        # filename means "backed up nowhere"; the other two arrive as whole sentences. The
        # first version hard-coded the first class into the prefix and then printed
        # "not declared derived: X is declared derived by compose.py", which reads as a
        # contradiction to whoever hits it at 6am.
        failed.append(("smoke", "%d data-file backup problem(s) - a bare filename is in no "
                                "backup list and declared derived by nothing: %s"
                       % (len(unbacked), "; ".join(unbacked))))
    if orphans:
        print("  note: %d orphan data file(s) on disk, in no backup list and read by no "
              "code: %s" % (len(orphans), ", ".join(orphans)))

    print("\n%d passed, %d failed, %d total" % (passed, len(failed), passed + len(failed)))
    for n, msg in failed:
        # n is a line number for a testcases.txt case and a label ("smoke") for the built-in
        # assertions. This printed with %d until 24.08.2026, so ANY smoke failure crashed the
        # reporter with a TypeError instead of reporting the failure - the one moment the
        # harness exists for. Found by deliberately breaking the new self-block assertion.
        print("  FAIL  %-9s %s" % ("line %d" % n if isinstance(n, int) else n, msg))

    if known_red is not None:
        return _known_red_verdict(failed, known_red)
    return 1 if failed else 0


def _known_red_verdict(failed, path):
    """Exit 0 if every failure is a WAIVED one, 1 otherwise. Opt-in, via --known-red.

    Chris, 10.09.2026. Why this exists. testcases.txt works failing-first: a correction is
    written as a red case BEFORE the rule is edited, which is what stops the fix being a
    special case for one headline. The cost is that the fixture is legitimately red for as
    long as the fix takes - the cross-section RANBEFORE case sat red from 08.09 to 10.09 -
    and hooks/pre-commit gates on the fixture. So for those two days EVERY commit needed
    --no-verify, which also skipped the step BEFORE the fixture: the drift check on
    SKILL.md and memory/, the two least replaceable files in the setup. A deliberate red
    case was silently disarming an unrelated backup guarantee. Splitting the two gates is
    not enough on its own, because the thing you actually want is for a NEW red to keep
    blocking while a KNOWN one does not.

    Two properties make the waiver safe to have at all:

      - it is matched on the failure MESSAGE, not the line number, because a line number
        moves the moment anyone edits testcases.txt above it and a waiver that drifts onto
        a different case is worse than no waiver;
      - a waiver that matches nothing is itself a failure. Otherwise the fix lands, nobody
        removes the entry, and the allowlist quietly grows into permission for that whole
        class of failure to come back unnoticed.
    """
    patterns = []
    try:
        for raw in open(path, encoding="utf-8"):
            line = raw.split("#", 1)[0].strip()
            if line:
                patterns.append(line)
    except IOError as exc:
        print("\n  known-red list %s could not be read: %s" % (path, exc))
        return 1
    if not patterns:
        return 1 if failed else 0

    waived, unexpected, used = [], [], set()
    for n, msg in failed:
        hit = next((p for p in patterns if p in msg), None)
        if hit:
            waived.append((n, msg))
            used.add(hit)
        else:
            unexpected.append((n, msg))

    if waived:
        print("\n  %d WAIVED failure(s) - known red, see %s:" % (len(waived), path))
        for n, msg in waived:
            print("    %-9s %s" % ("line %d" % n if isinstance(n, int) else n, msg[:96]))
        print("  These are red on purpose. They do not block, and they are the reason the")
        print("  fixture must not be the only thing standing between you and a commit.")

    stale = [p for p in patterns if p not in used]
    if stale:
        print("\n  %d STALE waiver(s) in %s - they match no current failure, so the case they"
              % (len(stale), path))
        print("  covered is fixed. Delete them; a waiver nobody removed is permission for")
        print("  that failure to come back unnoticed:")
        for p in stale:
            print("    %s" % p[:96])

    if unexpected:
        print("\n  %d UNEXPECTED failure(s) - these block:" % len(unexpected))
        for n, msg in unexpected:
            print("    %-9s %s" % ("line %d" % n if isinstance(n, int) else n, msg[:96]))

    return 1 if (unexpected or stale) else 0



def _shell_scripts():
    """The repo's shell scripts, in a stable order.

    hooks/* is included even though git hooks carry no .sh suffix: hooks/pre-commit is a
    `set -u` bash script like any other, and it runs on every commit, so a syntax error or an
    unguarded empty array there breaks the thing that is supposed to be catching breakage.
    """
    import glob
    return sorted(glob.glob(os.path.join(HERE, "*.sh"))
                  + [p for p in glob.glob(os.path.join(HERE, "hooks", "*"))
                     if os.path.isfile(p) and not p.endswith(".sample")])


def test_shell_syntax():
    """Every shell script must parse. `bash -n` only, so nothing is executed.

    The scripts in here are the load-bearing tail - publish, mark, archive, push - and none
    of them is exercised by the assertions above, which all test pure Python functions. A
    syntax error would surface at 6am.
    """
    import subprocess
    bad = []
    for path in _shell_scripts():
        proc = subprocess.run(["bash", "-n", path], capture_output=True, text=True)
        if proc.returncode != 0:
            bad.append((os.path.basename(path), proc.stderr.strip().splitlines()[-1][:90]))
    return bad


def test_shell_empty_array_guards():
    """No `set -u` script may expand a possibly-empty array as "${arr[@]}".

    Added 26.08.2026. This Mac runs bash 3.2, where expanding an EMPTY array under `set -u`
    is an unbound-variable error, not the empty list you expect. finish_edition.sh had
    `"${REASONS[@]}"` on the record-tiers line, and REASONS is empty whenever there is no
    /tmp/reasons.json - which is almost every run, because most stories never get a note. So
    the tail died with

        finish_edition.sh: line NN: REASONS[@]: unbound variable

    AFTER mark_published.py and BEFORE archive and the state push: stories burned as
    published, that day's labels lost, state un-backed-up. Precisely the split the step order
    in SKILL.md exists to prevent, and invisible until the day it fires, because the happy
    path (reasons.json present) works fine.

    The safe form is ${arr[@]+"${arr[@]}"}: expands to nothing when unset, to the quoted
    elements otherwise, on every bash.

    A dynamic "does the bare form fail?" check would be wrong here - it passes on bash >=4.4
    and would go quietly green if this Mac were ever upgraded, taking the guard's reason with
    it. So the assertion is static: find the arrays that are declared empty, and require every
    expansion of them to be guarded.
    """
    import re
    bad = []
    for path in _shell_scripts():
        with open(path) as fh:
            src = fh.read()
        if not re.search(r"set -[a-z]*u", src):
            continue
        # Arrays that can be empty are the ones declared as `NAME=()`.
        empties = set(re.findall(r"^\s*([A-Za-z_][A-Za-z0-9_]*)=\(\s*\)\s*$", src, re.M))
        for name in sorted(empties):
            guarded = "${%s[@]+\"${%s[@]}\"}" % (name, name)
            for n, line in enumerate(src.splitlines(), 1):
                if line.lstrip().startswith("#"):
                    continue
                # Remove the guarded form first - it legitimately contains the bare form.
                stripped = line.replace(guarded, "")
                if ("${%s[@]}" % name) in stripped:
                    bad.append((os.path.basename(path), n, name))
    return bad


def test_all_scripts_backed_up():
    """Every .py and .sh here must appear exactly once in state_sync.sh's CODE_FILES.

    Added 26.08.2026. state_sync.sh's own header states the invariant - "every .py and .sh in
    the directory is now here... a script added later is now the exception that stands out,
    rather than one more quiet gap nobody notices until the disk goes" - but nothing enforced
    it, so it was upheld by memory alone and had already slipped twice. textsignals.py and
    tier_model.py were written straight into ~/Downloads on 24.08.2026 and were backed up
    nowhere; sync_docs.sh went the same way on 26.08.2026. Both were caught by chance.

    Also asserts no entry appears twice: archive_day.py was listed twice until 26.08.2026, so
    every morning's push uploaded it a second time. Harmless, but it is the same drift in the
    other direction, and cheap to hold.

    Returns (missing_from_list, duplicated_in_list).
    """
    import glob
    import re
    path = os.path.join(HERE, "state_sync.sh")
    if not os.path.isfile(path):
        return (["state_sync.sh itself is missing"], [])
    with open(path) as fh:
        src = fh.read()
    m = re.search(r'CODE_FILES="((?:[^"\\]|\\.)*)"', src, re.S)
    if not m:
        return (["could not parse CODE_FILES out of state_sync.sh"], [])
    # Shell line continuations: a backslash-newline is whitespace, not part of a filename.
    listed = m.group(1).replace("\\\n", " ").split()
    on_disk = {os.path.basename(p) for p in
               glob.glob(os.path.join(HERE, "*.py")) + glob.glob(os.path.join(HERE, "*.sh"))}
    missing = sorted(on_disk - set(listed))
    dupes = sorted({f for f in listed if listed.count(f) > 1})
    return (missing, dupes)


def test_no_self_blocked_feed():
    """No configured feed may match the sweep-time block list.

    Added 24.08.2026 after the block list was extended to every BLOCKED_OUTLETS source. Two
    feeds were left enabled while every item they produced was discarded - a wasted request
    per run, and check_sources.py counting them as healthy contributors. It also caught a
    typo in the same change: the Anglican Mainstream block was written .net when the feed is
    .org, which the display-name block masked completely.
    """
    import json as _json
    import fetch_feeds as _ff
    feeds, _scrapes, blocked = _ff.load_feeds()
    bad = []
    for f in feeds:
        blob = _json.dumps(f).lower()
        for b in blocked:
            if b and b in blob:
                bad.append((b, blob[:90]))
    return bad

def test_no_orphaned_health_records():
    """Every record in source_health.json must be a feed check_sources.py still probes.

    Added 06.09.2026. check_sources.py probes only the URLs currently in load_feeds()[0], and
    it never removes a record for a URL that has since left that list. So a retired feed's
    last state is frozen in the file forever. Sixteen such records had accumulated, three of
    them stuck at fails=3 - including Live Action News on its old liveaction.org/news/feed
    route, which is the exact source whose silent death this whole tool was built to catch.

    They are inert: never re-probed, never reported, never in the exit code. The damage is to
    the reader. Reading the file by hand shows three sources apparently three days dead when
    all three are fine on a different route - so the one file you would open to answer "has a
    source gone quiet?" is the file that misleads you about it. That misreading happened on
    06.09.2026 and took four commands to unpick.

    Pruning discards a retired feed's history. That is the right trade: a record nothing
    probes is not history, and if the URL ever returns to the list it rebuilds from fails=0
    on the next check.

    Static assertion, no network. Returns a list of problems; empty means pass.
    """
    import json as _json
    import fetch_feeds as _ff
    health = os.path.join(HERE, "source_health.json")
    if not os.path.exists(health):
        return []
    try:
        with open(health) as fh:
            hist = _json.load(fh)
    except Exception as exc:  # noqa: BLE001
        return [("source_health.json", "could not be read: %s" % exc, 0)]
    live = {f[2] for f in _ff.load_feeds()[0]}
    return [(rec.get("name") or "?", url, rec.get("fails", 0))
            for url, rec in sorted(hist.items()) if url not in live]

def test_cluster_lead_prefers_a_readable_link():
    """The one line the sheet prints must not be the cluster member with a dead link.

    corroborate() sorts on rank_score, which is _score + TIER_BUMP + ACTION_BUMP and knows
    nothing about the URL. So an item whose link is an undecodable Google News redirect
    sorted level with a sibling carrying a clean publisher URL for the identical story.
    On 01.09.2026 that put Japan Today's redirect - which resolve() returns None for - at
    the head of a cluster whose other member, The Japan Times, had
    japantimes.co.jp/news/2026/08/31/japan/marriage-wish-survey and was supplying the text
    the sheet printed. Chris asked why the story linked where it did.

    This is the same shape as the relay bug fixed the day before: cluster_rank DOES weigh
    link quality, and cluster_rank is not what chooses this line.

    Relay status still dominates - a primary source with an ugly link keeps the lead over a
    newsroom relaying it, because that is a provenance question and this is only a
    readability one.
    """
    import shortlist
    bad = []
    GN = ("https://news.google.com/rss/articles/CBMirAFBVV95cUxQZGNNQ1pQLW1mU3dndF9i"
          "NjlRa2tFNWIwa3pwSGE1UDJMSGZ4Q0Jndj")
    def it(outlet, url, headline):
        return {"outlet": outlet, "url": url, "headline": headline, "_score": 5,
                "summary": "", "categories": []}
    a = it("Japan Today", GN,
           "35% of unmarried young people in Japan say they do not plan to marry: survey")
    b = it("The Japan Times",
           "https://www.japantimes.co.jp/news/2026/08/31/japan/marriage-wish-survey",
           "35% of young unmarried people in Japan have no wish to get wed")
    for pair in ([a, b], [b, a]):          # order in must not decide order out
        ranked = sorted(pair, key=shortlist.cluster_lead_key)
        if "news.google.com" in (ranked[0].get("url") or ""):
            bad.append("a cluster led by an undecodable redirect while a sibling had a "
                       "direct publisher URL (input order %s)"
                       % ("redirect first" if pair[0] is a else "direct first"))
    # ORDERING: provenance must outrank readability. Without this the two terms can be
    # swapped and every test still passes - which was true when this test was first written,
    # so the docstring's claim that relay dominates was unenforced.
    # relays_another_outlet() is True only for a PRIMARY_SOURCE item - a newsroom holds no
    # provenance bump and so cannot lose it. Both fixtures therefore have to be primary
    # sources; only their summaries and links differ.
    relay_clean = it("SPUC", "https://spuc.org.uk/burnham-abstains",
                     "Andy Burnham will NOT vote on assisted suicide")
    relay_clean["summary"] = ("According to The Telegraph, the Prime Minister will abstain "
                              "at second reading.")
    primary_ugly = it("ADF International", GN,
                      "ADF files brief in Supreme Court prayer case")
    primary_ugly["summary"] = "ADF International filed its opening merits brief on Monday."
    if not shortlist.relays_another_outlet(relay_clean):
        bad.append("fixture problem: the relay item is not being detected as a relay, so "
                   "the ordering assertion below proves nothing")
    else:
        ranked = sorted([relay_clean, primary_ugly], key=shortlist.cluster_lead_key)
        if ranked[0] is relay_clean:
            bad.append("a relaying newsroom with a clean link beat a primary source with a "
                       "redirect - readability is outranking provenance")
    return bad


def test_url_key_keeps_article_ids():
    """seen.json keys must distinguish articles a site identifies by query string.

    url_key dropped the whole query, which is right for tracking junk and for display
    variants (edition=us-edition is most of the query-carrying URLs in any sweep and must
    still collapse), and catastrophic for a site whose article id IS the query. Forum 18
    serves every article from /archive.php?article_id=N, so all of them keyed to
    "forum18.org/archive.php": one piece ran on 19.08.2026 and every later Forum 18 article
    arrived flagged "[ran 08-19]" and was skipped as a repeat. Found 01.09.2026 when Chris
    asked why a Forum 18 report on Russia ordering Bibles destroyed was not picked.
    """
    import fetch_feeds
    bad = []
    k = fetch_feeds.url_key
    if k("https://www.forum18.org/archive.php?article_id=3067") == \
       k("https://www.forum18.org/archive.php?article_id=3041"):
        bad.append("two different Forum 18 articles share one seen-key - the whole source "
                   "retires the first time any one of its articles runs")
    if "article_id=3067" not in k("https://www.forum18.org/archive.php?article_id=3067"):
        bad.append("article_id is not retained in the key")
    # Display variants and tracking must STILL collapse, or one article keys twice and
    # every repeat check silently stops working for it.
    if k("https://spectator.com/a/?edition=us-edition") != \
       k("https://spectator.com/a/?edition=uk-edition"):
        bad.append("edition= is being kept; one Spectator article now has two keys")
    if k("https://e.com/s?utm_source=x&utm_medium=y") != k("https://e.com/s"):
        bad.append("utm_* tracking parameters are being kept")
    if k("https://e.com/s/") != k("https://e.com/s"):
        bad.append("trailing-slash normalisation regressed")
    return bad


def test_news_sitemap_parses_as_a_feed():
    """News-sitemap parsing (24.09.2026). Returns a list of problems; empty means pass.

    A Google News sitemap lists every article of the last 48 hours, where a Google News
    search stops at 100 results. The fixture is modelled on the Times' - which was measured
    and then NOT added, because its robots.txt disallows us (see extra_feeds.txt). The
    parser is kept for publishers that do permit it. Entries must come out shaped exactly
    like parse_feed's RSS entries, or the sweep would drop them silently.
    """
    import fetch_feeds
    raw = (b'<?xml version="1.0" encoding="UTF-8"?><urlset '
           b'xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
           b'xmlns:news="http://www.google.com/schemas/sitemap-news/0.9"><url>'
           b'<loc>https://www.thetimes.com/uk/article/trump-media-ban-judge-abc123</loc>'
           b'<lastmod>2026-09-24T08:02:47.000Z</lastmod><news:news><news:publication>'
           b'<news:name>The Times</news:name><news:language>en</news:language>'
           b'</news:publication><news:publication_date>2026-09-24T06:10:00.000Z'
           b'</news:publication_date><news:title><![CDATA[Trump ordered to lift White '
           b'House media ban by judge &amp; told why]]></news:title>'
           b'<news:keywords>media, courts</news:keywords></news:news></url></urlset>')
    try:
        rows = fetch_feeds.parse_feed(raw)
    except Exception as exc:  # noqa: BLE001
        return ["parse_feed raised %s on a news sitemap" % type(exc).__name__]
    if len(rows) != 1:
        return ["parsed %d rows, expected 1" % len(rows)]
    r = rows[0]
    bad = []
    for k in ("title", "link", "date", "author", "source", "feed_title", "summary",
              "categories"):
        if k not in r:
            bad.append("missing the %r key parse_feed emits" % k)
    if not (r.get("title") or "").startswith("Trump ordered to lift"):
        bad.append("title not read from news:title, got %r" % r.get("title"))
    if "&amp;" in (r.get("title") or ""):
        bad.append("entities not unescaped - the doc quotes headlines verbatim")
    if r.get("link") != "https://www.thetimes.com/uk/article/trump-media-ban-judge-abc123":
        bad.append("link not read from loc")
    d = r.get("date")
    if d is None or d.tzinfo is None:
        bad.append("date must be tz-aware or the window filter compares naive to aware")
    elif d.hour != 6:
        bad.append("publication_date must win over lastmod, got hour=%d" % d.hour)
    return bad


def test_wpjson_parses_as_a_feed():
    """The ADF route. Returns a list of problems; empty means pass.

    A WordPress REST collection must come out shaped exactly like parse_feed's entries -
    same keys, tz-aware date from date_gmt, entities unescaped - or the sweep drops it
    silently. Exists because ADF is the body the provenance rule names first and it had gone
    eight editions contributing one item: adfmedia.org was never a configured source, and
    every conventional route into it is dead (its feeds serve zero, /press-releases 404s,
    gnews indexes nothing but "Book an Interview"). wp-json was the way in.
    """
    import fetch_feeds
    import json as _json
    bad = []
    raw = _json.dumps([
        {"date": "2026-08-31T15:56:50",
         "date_gmt": "2026-08-31T19:56:50",
         "link": "https://adfmedia.org/press-release/orthodox-jew-asks-us-supreme-court/",
         "title": {"rendered": "Orthodox Jew asks for freedom to pray with friends&#8217; "
                               "without a permit"},
         "excerpt": {"rendered": "<p>ADF attorneys filed a petition.</p>"}},
    ]).encode()
    try:
        rows = fetch_feeds.parse_wpjson(raw, "ADF")
    except Exception as exc:  # noqa: BLE001
        return ["parse_wpjson raised %s" % type(exc).__name__]
    if len(rows) != 1:
        return ["parsed %d rows, expected 1" % len(rows)]
    r = rows[0]
    for k in ("title", "link", "date", "author", "source", "feed_title", "summary",
              "categories"):
        if k not in r:
            bad.append("missing the %r key parse_feed emits" % k)
    if r.get("date") is None or r["date"].tzinfo is None:
        bad.append("date must be tz-aware or the window filter compares naive to aware")
    elif r["date"].hour != 19:
        bad.append("date_gmt must win over site-local date, got hour=%d" % r["date"].hour)
    if "&#8217;" in r.get("title", ""):
        bad.append("WordPress entities not unescaped - the doc quotes headlines verbatim")
    if "<p>" in r.get("summary", ""):
        bad.append("excerpt HTML not stripped")
    try:
        fetch_feeds.parse_wpjson(b'{"code":"rest_no_route"}', "ADF")
        bad.append("an error body parsed as an empty feed instead of raising")
    except ValueError:
        pass
    except Exception as exc:  # noqa: BLE001
        bad.append("an error body raised %s, expected ValueError" % type(exc).__name__)
    return bad


def test_text_coverage_line_counts_openings():
    """The sheet's coverage line must count `opened`. Returns problems; empty means pass.

    Until 01.09.2026 it reported only what the run had to FETCH and omitted openings - the
    main text route - entirely. On a warm cache that read 19% while true coverage was 89%,
    and in the other direction a total failure of attach_openings would have left the line
    looking unchanged. The brief tells the morning run to report this number and treat a
    drop as "the day was ranked on headlines", so it has to mean readability.
    """
    bad = []
    src = open(os.path.join(HERE, "shortlist.py")).read()
    i = src.find("text coverage:")
    if i < 0:
        return ["the sheet no longer prints a 'text coverage:' line"]
    block = src[max(0, i - 2500):i + 1500]
    if "opened" not in block:
        bad.append("the coverage line does not mention `opened`; the main text route is "
                   "being dropped from the number again")
    if "_text_route" not in block:
        bad.append("coverage is not computed per-lead, so it cannot report readability")
    # Must mirror the sheet's own branch order or the number describes something the sheet
    # does not print.
    for route in ("_opening", "_preview", "real_summary", "_lede", "_sibtext"):
        if route not in block:
            bad.append("coverage route %s missing from _text_route" % route)
    return bad


def test_gold_pairs_strip_markers():
    """repeat_eval's GOLD veto must strip every ::marker:: before comparing.

    Chris, 10.09.2026. This is the SECOND time the same bug has been found. repeat_eval's own
    comment records the first: leaving ::entity:: in the string "made it a word in the
    comparison, which is how it first showed up as a phantom GOLD failure". On 08.09.2026 the
    RANBEFORE cases gained a ::sections:: marker for run_tests, repeat_eval was not taught
    about it, and the result was two GOLD failures that were not real - reported as a VETO,
    which is the strongest signal the scorer has, every time the job ran.

    So this asserts the general property rather than the specific marker: no gold pair may
    contain "::" by the time it reaches the comparison. Any marker added to testcases.txt in
    future fails here on the day it is added, rather than quietly becoming a word.
    """
    try:
        import repeat_eval
    except ImportError as exc:
        return ["could not import repeat_eval: %s" % exc]
    bad = []
    for today, past, _want in repeat_eval.gold_pairs():
        for side, text in (("today", today), ("past", past)):
            if "::" in text:
                bad.append("%s side still has a marker: %r" % (side, text[:70]))
    return bad


def test_corpus_dirs_backed_up():
    """A directory of write-once day records must be carried by an uploader.

    Chris, 10.09.2026. CODE_FILES has caught the same mistake three times - a new script
    written straight into ~/Downloads and backed up nowhere (textsignals/tier_model 24.08,
    sync_docs 26.08, slack_five 10.09). The same afternoon it missed that mistake in a
    different shape: five/ and markup/ were created and neither was in any backup list,
    because state_sync.sh takes a flat FILE list and cannot express a directory at all. So
    the guard that existed for scripts had no counterpart for corpora, and five/ - the only
    record of the Slack five that has ever existed - was one rm from gone.

    It PARSES the uploader's own corpus list rather than grepping for the name. The first
    version of this test grepped, and its own mutation test caught it out: removing five/
    from the uploader left the test GREEN, because the substring "five" also occurs in
    slack_five.py and in the prose of both scripts. A guard that cannot fail is worse than
    none, because it reports a guarantee it is not providing.
    """
    import re
    here = os.path.dirname(os.path.abspath(__file__))
    # Directories the pipeline WRITES and would want back. Not a glob of everything on disk:
    # __pycache__ and out/ are derived and deliberately not backed up.
    corpora = ["archive", "five", "markup"]

    uploader = os.path.join(here, "upload-archive-to-drive.sh")
    if not os.path.exists(uploader):
        return ["upload-archive-to-drive.sh is missing, so no corpus is backed up at all"]
    text = open(uploader, encoding="utf-8").read()

    covered = set()
    # archive/ is this script's whole reason for existing; it tars archive/<day>/ directly.
    if re.search(r"archive/\*/|\$HERE/archive", text):
        covered.add("archive")
    # the rest come from the explicit list it loops over
    m = re.search(r"for\s+corpus\s+in\s+([^;\n]+?)\s*;\s*do", text)
    if m:
        covered.update(t for t in m.group(1).split() if t)

    bad = []
    for d in corpora:
        if not os.path.isdir(os.path.join(here, d)):
            continue          # not created yet; nothing to lose, and markup/ is written lazily
        if d not in covered:
            bad.append("%s/ is written by the pipeline and no uploader carries it" % d)
    return bad


def test_age_flag_and_window_leak():
    """The age gloss is context, not an alarm, and the leak guard is not the same thing.

    Chris, 10.09.2026. Four items in that day's sweep were older than the 36h window - 63h to
    157h - and the obvious reading was a leak. It was not: FoRB in Full and Charlotte Gill both
    declare window=168h in extra_feeds.txt because they publish two or three times a week, so
    at 36h the sweep would miss them entirely. The mistake was the other way round - the sheet
    printed a bare "63.2h" with nothing to say that was normal for that source, and the piece
    got published as that morning's news.

    So two separate things, and this asserts they stay separate:

      - age_flag() glosses an age that has run past the sweep window for a source allowed a
        longer one. It must NOT fire on a young item from the same source, because there is
        nothing misleading about "4h", and it must not fire on an ordinary source at all. A
        flag on every long-window line every day would be noise on exactly the ★ primary and
        low-frequency sources the brief says get read past.
      - outside_own_window() is the actual leak guard: older than the item's OWN allowance,
        which means a cutoff or a date parse is wrong. It was empty on 10.09.2026 and should
        stay empty.
    """
    bad = []
    try:
        import shortlist
        import fetch_feeds
    except ImportError as exc:
        return ["could not import: %s" % exc]

    fetch_feeds.load_extra()
    long_src = next((k for k, v in fetch_feeds.FEED_WINDOWS.items() if v > shortlist.SWEEP_WINDOW_H),
                    None)
    if not long_src:
        return ["no source in extra_feeds.txt declares a window longer than the sweep's, so "
                "the age gloss has nothing to explain - did a window= line get dropped?"]
    win = fetch_feeds.FEED_WINDOWS[long_src]

    old_item = {"feed": long_src, "age_h": shortlist.SWEEP_WINDOW_H + 20.0}
    if "low-frequency source" not in shortlist.age_flag(old_item):
        bad.append("a %.0fh item from %r (window %dh) got no age gloss" %
                   (old_item["age_h"], long_src, win))

    young = {"feed": long_src, "age_h": 4.0}
    if shortlist.age_flag(young):
        bad.append("a 4h item from %r was glossed; nothing about '4h' misleads" % long_src)

    plain = {"feed": "no such feed declares a window", "age_h": shortlist.SWEEP_WINDOW_H + 20.0}
    if shortlist.age_flag(plain):
        bad.append("an ordinary source was glossed as low-frequency")

    # The leak guard: inside its own window is fine, past it is not.
    inside = {"_i": 1, "feed": long_src, "age_h": win - 1.0}
    if shortlist.outside_own_window([inside]):
        bad.append("a %.0fh item inside its own %dh window was called a leak" %
                   (inside["age_h"], win))
    beyond = {"_i": 2, "feed": long_src, "age_h": win + 50.0}
    if not shortlist.outside_own_window([beyond]):
        bad.append("a %.0fh item past its own %dh window was NOT reported as a leak" %
                   (beyond["age_h"], win))
    return bad


def test_gnews_decode_unescape():
    """decode_gnews must return the WHOLE publisher URL, query value included.

    Chris, 31.08.2026. Google escapes characters inside the batchexecute payload as \\uXXXX,
    and "=" is the one that matters because every query value starts with one. _GARTURL_RE
    captured [^\\"]+, which stops dead at the backslash, so every decoded URL was cut at its
    first parameter: "...obituary?id" for "...obituary?id=62306633".

    It never published a wrong link - _looks_truncated plus the title check caught these and
    fell back to keeping the redirect - so the symptom was silent: redirects reported as
    "could not be resolved" that Google had in fact resolved correctly. Two of today's were
    porn spam injected into a compromised Smithsonian host, which is how it was noticed at
    all. Fixtures are real payloads captured off the wire, so this runs offline.
    """
    cases = [
        # legacy.com - the query value IS the article id. Captured off the wire 31.08.2026;
        # the payload nests one JSON string in another, so \" is one backslash and the
        # \uXXXX escape arrives with two.
        (r'[\"garturlres\",\"https://www.legacy.com/us/obituaries/name/'
         r'james-rushton-obituary?id\\u003d62306633\",1]',
         "https://www.legacy.com/us/obituaries/name/james-rushton-obituary?id=62306633"),
        # the ABC News shape named in _looks_truncated (20.08.2026)
        (r'[\"garturlres\",\"https://abcnews.go.com/Politics/story?id\\u003d12345\",1]',
         "https://abcnews.go.com/Politics/story?id=12345"),
        # two parameters, plus an escaped forward slash in the path
        (r'[\"garturlres\",\"https://example.com/a\\/b?x\\u003d1&y\\u003d2\",1]',
         "https://example.com/a/b?x=1&y=2"),
        # no query at all - must come back byte-identical
        (r'[\"garturlres\",\"https://example.com/plain-story\",1]',
         "https://example.com/plain-story"),
    ]
    bad = []
    for raw, want in cases:
        m = resolve._GARTURL_RE.search(raw)
        got = resolve._unescape_garturl(m.group(1)).rstrip("/") if m else None
        if got != want:
            bad.append((got, want))
    return bad


def test_gnews_index_decode_flagged():
    r"""A decode that is really a paginated index must be made to prove itself.

    Chris, 31.08.2026, found while fixing the \uXXXX truncation above - and the reason that
    fix could not ship on its own. resolve_one() treats a well-formed decode as authoritative
    and returns it WITHOUT a title check, on the reasoning in decode_gnews: Google's answer
    beats a constructed URL, and title-verifying it would throw away correct decodes whenever
    the publisher blocks the fetch (the Telegraph and Times do).

    That reasoning holds for article URLs. It does not hold for what Google actually returns
    for some feeds: a paginated category index. Nine Premier Christian News items and two
    Desiring God items decoded to "/category/uk-news?page=475" and "/articles/all?page=271"
    on 31.08.2026 - one listing page standing in for nine different stories.

    Before the truncation fix these arrived as "...?form" and "...?page", which _looks_truncated
    caught, so the title check ran, the index page failed it and the redirect was kept. Safe,
    but only by accident: repairing the truncation made them structurally clean and would have
    published all nine as article links. So index-shaped decodes now take the same route
    truncated ones do - confirm or be dropped. Syntactic, no network, so a correct article
    decode from a blocking publisher is never discarded.
    """
    bad = []
    index_shaped = [
        "https://premierchristian.news/en/category/uk-news?form=pcn-main&page=475",
        "https://premierchristian.news/us/category/uk-news?page=791&form=newsnewsletter",
        "https://www.desiringgod.org/articles/all?page=271&sort=864",
        "https://www.desiringgod.org/scripture/1-corinthians.html?page=10&sort=oldest",
        "https://example.com/tag/abortion",
        "https://example.com/author/jane-smith?page=2",
        "https://example.com/",
    ]
    article_shaped = [
        "https://www.legacy.com/us/obituaries/name/james-rushton-obituary?id=62306633",
        "https://www.telegraph.co.uk/us/news/2026/08/30/maduro-flashes-peace-sign-prison-picture",
        "https://youtu.be/OICjuY3PZHE?si=oMhJ3skAgdCyDJkB",
        "https://www.brusselstimes.com/belgium/2294776/flemish-students-return-to-school",
        "https://www.milb.com/asheville/video/christian-rodriguez-in-play?t=t573-default-vtp",
        # WORLD's real URL shape - the standing proof that slugs are not guessable. Must
        # never be mistaken for an index just because the tail is numeric.
        "https://wng.org/sift/some-headline-here-1786558522",
    ]
    for u in index_shaped:
        if not resolve._looks_like_index(u):
            bad.append("index not flagged: %s" % u)
    for u in article_shaped:
        if resolve._looks_like_index(u):
            bad.append("article wrongly flagged: %s" % u)
    return bad


def test_cluster_relay_not_primary():
    r"""A primary source RELAYING another outlet must not lead a cluster over that outlet.

    Chris, 31.08.2026, from his markup of the 31.08 edition. Six national newsrooms filed
    original reporting that Burnham would abstain on the assisted dying Bill - Telegraph,
    Times, Independent x2, Manchester Evening News, LBC - and cluster_rank collapsed every
    one of them under SPUC's item, whose own summary opens "According to Politics UK, Andy
    Burnham has told Labour MPs...". The sheet prints one line per story, so the only line
    the curator ever saw was SPUC's, and the edition ran an opinion column in place of the
    news report. Same mechanism put Advocate.com over the Washington Post on the trans
    military filing.

    PRIMARY_SOURCE exists for the opposite case and must keep working: when ADF International
    obtains and publishes a UN letter, that release IS the document and beats a newsroom's
    write-up of it (14.08.2026). The distinction is issuing versus relaying, so the test is
    attribution in the item's OWN feed summary - available at cluster time, unlike article
    text, which is fetched only after leads are chosen.

    The institution guard is the load-bearing half: "according to a new Government
    assessment" is Right To Life reading a document, not relaying a newsroom, and that item
    was tier 1 in the same edition.
    """
    prim = "SPUC"
    cases = [
        # (outlet, summary, expect_relay)
        (prim, "Image Source: (L) UK Parliament According to Politics UK, Andy Burnham has "
               "told Labour MPs that he will not be voting on the Bill.", True),
        (prim, "Total decriminalisation would strip away existing legal time limits, opening "
               "the door to abortion on demand up to the moment of birth.", False),
        ("Right To Life UK",
               "29 August 2026 - A new Government assessment of the revived assisted suicide "
               "Bill has warned that poverty and poor care could lead to more deaths.", False),
        ("Right To Life UK",
               "A leaked copy of the Scottish National Party's conference draft agenda has "
               "revealed that it includes a motion calling for a change in the law.", False),
        # ADF publishing a document it obtained - must stay primary
        ("ADF International",
               "UN experts have released a letter warning Nigeria over blasphemy laws, "
               "according to the United Nations special rapporteurs.", False),
        # explicit newsroom relay forms
        (prim, "The Telegraph reports that the Bill will return to the Commons in September.", True),
        (prim, "As reported by Politico, the vote has been delayed.", True),
        # a newsroom is never penalised - the bump is not theirs to lose
        ("The Telegraph", "According to Politics UK, Burnham will abstain.", False),
    ]
    bad = []
    for outlet, summary, want in cases:
        got = shortlist.relays_another_outlet({"outlet": outlet, "summary": summary})
        if bool(got) != want:
            bad.append("%s: relay=%s want=%s | %s" % (outlet, bool(got), want, summary[:52]))

    # THE SHEET's collapse, which is what a curator actually sees. corroborate() picks the
    # one line printed per story and sorts by rank_score - which has no PRIMARY_SOURCE term
    # at all - so this is a DIFFERENT selection from cluster_rank below. Getting this wrong
    # once (31.08.2026) meant a fix that passed its own test changed nothing in the sheet.
    spuc_row = {"headline": "Andy Burnham will NOT vote on assisted suicide", "outlet": "SPUC",
                "summary": "According to Politics UK, Andy Burnham has told Labour MPs that "
                           "he will not be voting on the Bill.",
                "_score": 40, "_section": "Life"}
    tel_row = {"headline": "Burnham to abstain from assisted dying vote",
               "outlet": "The Telegraph", "summary": "Burnham to abstain from assisted dying "
                                                     "vote The Telegraph",
               "_score": 10, "_section": "Life"}
    rows = [spuc_row, tel_row]
    corr = shortlist.corroborate(rows)
    lead = corr[id(spuc_row)][1]
    if lead is not tel_row:
        bad.append("sheet lead is %s, want The Telegraph (corroborate/rank_score path)"
                   % lead.get("outlet"))

    # and the ordering the whole thing exists for
    tel = {"outlet": "The Telegraph", "summary": "Burnham to abstain from assisted dying vote",
           "headline": "Burnham to abstain from assisted dying vote", "_score": 5}
    spuc = {"outlet": "SPUC", "headline": "Andy Burnham will NOT vote on assisted suicide",
            "summary": "According to Politics UK, Andy Burnham has told Labour MPs that he "
                       "will not be voting on the Bill.", "_score": 5}
    if shortlist.cluster_rank(spuc) > shortlist.cluster_rank(tel):
        bad.append("relaying SPUC still outranks the Telegraph's own report")
    # ...without breaking the ADF case it was built for
    adf = {"outlet": "ADF International", "headline": "UN Experts Release Letter Warning of",
           "summary": "ADF International has obtained and published the letter.", "_score": 5}
    ewtn = {"outlet": "EWTN", "headline": "UN letter warns Nigeria", "summary": "", "_score": 9}
    if shortlist.cluster_rank(adf) < shortlist.cluster_rank(ewtn):
        bad.append("ADF's own release no longer beats EWTN's write-up")
    return bad


def test_cluster_lead_prefers_an_issuing_primary():
    r"""A primary source ISSUING its own analysis must lead the sheet over a write-up of it.

    Chris, 15.09.2026, from his markup of the 15.09 edition. Sex Matters published "NSPCC's
    changing-room guidance fails girls" - their own analysis of the charity's new schools
    guidance. The Telegraph filed its own story on the same guidance. corroborate() collapsed
    the two and printed the Telegraph's line, so the only version on the sheet was a
    paywalled headline with no readable text, it read as a story that had already run the day
    before, and the whole cluster was dropped. The compose-time COVERAGE check caught it -
    "Sex Matters 1 unpicked" - and the piece had to be added to the Doc after publication.

    This is the MIRROR of the 31.08.2026 relay case above, and the half that case did not
    cover. Both selections were wired then, but only in one direction:

      cluster_rank      has a PRIMARY_SOURCE term, so it promotes an issuing primary. The
                        section shortlist got this right and even printed
                        "<<< TAKE THIS ONE of 2 on this story" against the Sex Matters line.
      cluster_lead_key  has no PRIMARY_SOURCE term at all. Its first term only DEMOTES a
                        relaying primary; nothing promotes an issuing one, so the tie falls
                        through to rank_score - 11 for the Telegraph against 7 for Sex
                        Matters, on keyword vocabulary alone - and the newsroom wins.

    So the two paths disagree on the same cluster, and the sheet is the one the curator
    reads. Fixing cluster_rank in August did not touch this, exactly as the comment in
    corroborate() warns.

    The relay guard must keep working while this is fixed: an issuing primary leads, a
    relaying one still sorts last. Those are the two halves of the same provenance rule, and
    a change that satisfies one by dropping the other is not a fix.
    """
    bad = []
    # The real pair, with the scores classify() actually gave them on 15.09.2026 and the
    # times the 15.09 sweep recorded (archive/20260915/sweep.json.gz): Sex Matters 08:09,
    # the Telegraph 09:37, both on 14.09.
    sm = {"outlet": "Sex Matters",
          "headline": "NSPCC’s changing-room guidance fails girls",
          "summary": "The National Society for the Prevention of Cruelty to Children (NSPCC) "
                     "is the country's best-known child-protection charity, and the only one "
                     "with statutory powers.",
          "url": "https://sex-matters.org/posts/updates/nspccs-changing-room-guidance-fails-girls",
          "published": "2026-09-14T08:09:12+00:00", "age_h": 20.1,
          "_score": 1, "_section": "Gender, Identity & Sexuality"}
    tel = {"outlet": "The Telegraph",
           "headline": "Male teachers can supervise girls in changing rooms under NSPCC guidance",
           "summary": "",
           "url": "https://www.telegraph.co.uk/news/2026/09/14/nspcc-changing-rooms-guidance/",
           "published": "2026-09-14T09:37:00+00:00", "age_h": 18.7,
           "_score": 5, "_section": "Gender, Identity & Sexuality"}

    # Neither is relaying: Sex Matters is reading the guidance, not a newsroom. If this
    # trips, the failure below is about the relay guard and not about issuing.
    if shortlist.relays_another_outlet(sm):
        bad.append("Sex Matters' own analysis is being read as a relay")

    # THE SHEET's collapse, which is what a curator actually sees.
    for order, label in (([sm, tel], "issuing first"), ([tel, sm], "write-up first")):
        lead = shortlist.corroborate(order)[id(order[0])][1]
        if lead is not sm:
            bad.append("sheet lead is %s, want Sex Matters (%s, corroborate path)"
                       % (lead.get("outlet"), label))

    # ...and the selection stated directly, so a fix cannot pass by input-order luck.
    # Chris, 27.09.2026: the rule is "favour the earliest publisher" - so the same pair
    # with the times swapped must go to the Telegraph, and an undated release, which cannot
    # show it came first, must fall back to the old key (the Telegraph, on score).
    if shortlist.choose_cluster_lead([tel, sm])[0] is not sm:
        bad.append("choose_cluster_lead still puts the Telegraph's later write-up first")
    sm_late = dict(sm, published="2026-09-14T10:15:00+00:00")
    if shortlist.choose_cluster_lead([sm_late, tel])[0] is not tel:
        bad.append("a release published AFTER the Telegraph still leads it")
    sm_undated = dict(sm, age_h=None)
    if shortlist.choose_cluster_lead([sm_undated, tel])[0] is not tel:
        bad.append("an undated release is treated as first")

    # The August relay case must survive the fix: a RELAYING primary still sorts last.
    spuc = {"outlet": "SPUC", "headline": "Andy Burnham will NOT vote on assisted suicide",
            "summary": "According to Politics UK, Andy Burnham has told Labour MPs that he "
                       "will not be voting on the Bill.",
            "_score": 40, "_section": "Life"}
    tel2 = {"outlet": "The Telegraph",
            "headline": "Burnham to abstain from assisted dying vote",
            "summary": "Burnham to abstain from assisted dying vote The Telegraph",
            "_score": 10, "_section": "Life"}
    if shortlist.cluster_lead_key(spuc) < shortlist.cluster_lead_key(tel2):
        bad.append("fixing issuing broke relaying: SPUC's relay leads the Telegraph again")
    # ...even when the relay is the earlier of the two: relaying is never issuing.
    spuc_early = dict(spuc, published="2026-08-30T07:00:00+00:00", age_h=30.0)
    tel2_late = dict(tel2, published="2026-08-30T09:00:00+00:00", age_h=28.0)
    if shortlist.choose_cluster_lead([spuc_early, tel2_late])[0] is not tel2_late:
        bad.append("an early relay is promoted as if it issued the story")
    return bad



def test_common_words_do_not_cluster():
    r"""Words half the day shares are not evidence that two headlines are one story.

    Chris, 23.09.2026, marking up that morning's edition: "You missed all of these important
    stories?" Christianity Today's "Does Trump 2.0 Care About Religious Freedom Abroad?" (the
    Cissie Graham Lynch / IRF office piece) never reached the sheet. corroborate() had built
    an x19 "story" anchored on First Liberty's three-word "Reflecting on Religious Freedom":
    every headline containing "religious freedom" shared 2 of that anchor's 3 significant
    words, cleared the 0.55 ratio, and collapsed under one line - the Pakistan Ahmadi ruling,
    Trump appointing a pastor jailed in Turkey to USCIRF, Yom Kippur synagogue threats, a
    Fiji constitution story, the CT piece and 13 more. Eighteen unrelated stories, one line,
    and the one line's borrowed text was First Liberty on the Founders. same_story() had the
    same flaw per section: the CT piece was flagged a duplicate of "A book for those who care
    about religious freedom" on {about, care, freedom, religious}.

    The corpus is built so the phrase words are COMMON (as they were: "religiou" 31, "freedom"
    26, "care" 28, "about" 43 of 1,752 that morning). Genuine duplicates must still merge.
    """
    filler = ["Religious freedom report number %d from region %s" % (i, w)
              for i, w in enumerate("alpha bravo charlie delta echo foxtrot golf hotel india "
                                    "juliet kilo lima mike november oscar papa quebec romeo "
                                    "sierra tango uniform victor whisky xray yankee zulu".split())]
    filler += ["Why we care about %s this week" % w for w in
               "housing parks roads buses trains water power schools clinics libraries "
               "museums bridges ports airports canals farms fishing forests mines rivers "
               "lakes beaches".split()]
    pairs_apart = [
        ("Reflecting on Religious Freedom",
         "Rights body condemns Pakistan court ruling upholding ban on Ahmadi literature, "
         "warns of threat to religious freedom"),
        ("Reflecting on Religious Freedom",
         "Trump appoints pastor jailed in Turkey to US religious freedom commission"),
        ("A book for those who care about religious freedom",
         "Does Trump 2.0 Care About Religious Freedom Abroad?"),
    ]
    pairs_together = [
        ("Supreme Court declines to intervene in custody dispute between California parents "
         "and surrogate",
         "US Supreme Court won't intervene in custody dispute between California couple and "
         "surrogate"),
        ("Two men arrested over suspected terror plot to target Jewish community in Manchester",
         "Two arrested over suspected terrorist plot to target the Jewish community in "
         "Manchester"),
    ]
    bad = []
    for want, pairs in (("apart", pairs_apart), ("together", pairs_together)):
        for ha, hb in pairs:
            rows = [{"headline": h, "outlet": "o%d" % i, "_section": "Life", "_score": 5}
                    for i, h in enumerate(filler)]
            a = {"headline": ha, "outlet": "xa", "_section": "Life", "_score": 5}
            b = {"headline": hb, "outlet": "xb", "_section": "Life", "_score": 5}
            rows = [a] + rows + [b]
            corr = shortlist.corroborate(rows)
            merged_corr = corr[id(a)][1] is corr[id(b)][1]
            marks = shortlist.cluster_duplicates(rows)
            merged_dup = (id(a) in marks and id(b) in marks
                          and ("TAKE THIS ONE" in marks[id(a)]) != ("TAKE THIS ONE" in marks[id(b)]))
            for path, merged in (("corroborate", merged_corr), ("same_story", merged_dup)):
                if merged != (want == "together"):
                    bad.append("%s %s, want %s: %s | %s"
                               % (path, "merged" if merged else "apart", want, ha[:34], hb[:34]))
    return bad

def test_source_tier_not_substring():
    r"""SOURCE_TIER is matched by substring, and "the times" is a substring of others.

    Chris, 31.08.2026. "the times" matched "The Times of India" and "The Times of Israel",
    so both were scored as The Times of London: TIER_BUMP and the same tier_pos. 29 items on
    that one sweep. It surfaced while chasing why the Burnham-abstain cluster would not lead
    with the Telegraph - once SPUC's relay was demoted the lead went to The Times of India,
    which had beaten the Telegraph on a bump it should never have had.

    The rule: a SOURCE_TIER entry followed by " of " is a DIFFERENT masthead. Church Times,
    Christian Post and the rest are unaffected, and The Times itself must keep its place.
    """
    bad = []
    should = ["The Times", "Church Times", "The Christian Post", "The Telegraph", "Crux",
              "Catholic Herald", "The Critic", "spiked", "GB News"]
    should_not = ["The Times of India", "The Times of Israel", "The Times of India (cities)",
                  "Korea JoongAng Daily", "Hindustan Times"]
    for o in should:
        if shortlist.source_tier_pos(o) is None:
            bad.append("%s should be in SOURCE_TIER" % o)
    for o in should_not:
        if shortlist.source_tier_pos(o) is not None:
            bad.append("%s must NOT match SOURCE_TIER" % o)
    return bad


def test_publish_verify_parens():
    """publish.sh --verify must match hrefs whole, parentheses included, and nothing looser.

    25.09.2026. The check built its set of exported URLs with a bare-URL regex that stopped at
    ")", so the Jakarta Post link below - utm_source=(direct) - came back cut at "(direct" and
    was reported MISSING. The doc was byte-exact (a substring check found 183/183), but the run
    halted at 182/183 and finish_edition.sh stopped before marking. The fix reads hrefs out of
    the export instead, after html.unescape and unwrapping google.com/url?q=.

    Runs the Python heredoc straight out of publish.sh, so the test cannot drift from what
    ships. The negative cases pin that the fix did not buy its green by loosening the match:
    a truncated URL, a URL that is only a PREFIX of an exported one, and a URL present only as
    visible link text (not as an href) must all still fail.
    """
    import re
    import subprocess
    import tempfile
    src = open(os.path.join(HERE, "publish.sh")).read()
    m = re.search(r"<<'PY'\n(.*?)\nPY\n", src, re.S)
    if not m:
        return ["could not find the --verify heredoc in publish.sh"]
    script = m.group(1)
    jak = ("https://www.thejakartapost.com/indonesia/2026/09/25/tangerang-church-disruption-"
           "rekindles-fears-among-minorities?utm_source=(direct)&utm_medium=single_latest")
    # How the Docs HTML export writes it: redirector-wrapped, query percent-encoded, &amp;.
    jak_wrapped = ("https://www.google.com/url?q=https://www.thejakartapost.com/indonesia/"
                   "2026/09/25/tangerang-church-disruption-rekindles-fears-among-minorities"
                   "?utm_source%3D(direct)%26utm_medium%3Dsingle_latest&amp;sa=D&amp;"
                   "source=editors&amp;ust=1758800000000000&amp;usg=AOvVaw0abc")
    paren_path = "https://en.wikipedia.org/wiki/Tangerang_(city)"
    plain = "https://example.com/story?id=1&page=2"

    def verify(want_urls, doc_body):
        sent = "".join('<p><a href="%s">x</a></p>' % u.replace("&", "&amp;")
                       for u in want_urls)
        with tempfile.TemporaryDirectory() as d:
            dp, sp = os.path.join(d, "doc.html"), os.path.join(d, "sent.html")
            open(dp, "w").write("<html><body>%s</body></html>" % doc_body)
            open(sp, "w").write("<html><body>%s</body></html>" % sent)
            return subprocess.run([sys.executable, "-", dp, sp], input=script,
                                  capture_output=True, text=True)

    a = '<a class="c3" href="%s">link</a>'
    cases = [
        # (label, wanted, exported doc body, should pass)
        ("paren query, redirector-wrapped", [jak], a % jak_wrapped, True),
        ("paren query, bare href", [jak], a % jak.replace("&", "&amp;"), True),
        ("paren in path", [paren_path], a % paren_path, True),
        ("plain url, wrapped", [plain],
         a % "https://www.google.com/url?q=https://example.com/story?id%3D1%26page%3D2&amp;sa=D",
         True),
        ("genuinely missing", [jak, plain], a % jak_wrapped, False),
        ("truncated at the paren", [jak],
         a % "https://www.thejakartapost.com/indonesia/2026/09/25/tangerang-church-disruption-"
             "rekindles-fears-among-minorities?utm_source=", False),
        ("wanted is only a prefix of the export", ["https://example.com/story"],
         a % plain.replace("&", "&amp;"), False),
        ("present as link text only, href differs", [jak],
         '<a href="https://example.com/other">%s</a>' % jak.replace("&", "&amp;"), False),
    ]
    bad = []
    for label, want, body, ok in cases:
        proc = verify(want, body)
        if (proc.returncode == 0) != ok:
            bad.append("%s: expected %s, got rc=%d (%s)"
                       % (label, "pass" if ok else "MISSING", proc.returncode,
                          (proc.stdout + proc.stderr).strip().splitlines()[0][:80]
                          if (proc.stdout + proc.stderr).strip() else "no output"))
    return bad


def test_all_data_files_backed_up():
    r"""Every judgement/measurement file here must be in STATE_FILES or JUDGEMENT_FILES.

    Chris, 31.08.2026. The sibling test above walks only .py and .sh, so a missing .txt raised
    nothing - which is how rank_eval_log.txt came to have never been backed up by any of the
    three lists. It is the accumulated before/after of every scoring change ever made, it
    cannot be rebuilt without every historical version of importance(), and the only reason
    anyone noticed is that a push was being watched at the time. Widening the invariant from
    "every script" to "every file we could not rebuild" is the point.

    Three buckets, because a data file has three legitimate states and collapsing them is what
    let this hide:

      MISSING     it is ours, we could not rebuild it, and nothing backs it up. A real fault.
      DERIVED     regenerated from scratch every run, so backing it up is noise. Listed
                  explicitly with the command that rewrites it - an unexplained absence from
                  the backup lists must never be inferred to be this.
      ORPHAN      on disk, in no list, and read by no code. Reported separately rather than
                  ignored: silently tolerating it is how a stale copy of a live file sits next
                  to the real one for weeks. The bucket is EMPTY now; the case that built it
                  was briefing-sources.opml, 48K of older Feedly export that nothing
                  imported, beside the 72K sources.opml fetch_feeds.py actually reads.
    """
    import glob
    import re
    path = os.path.join(HERE, "state_sync.sh")
    if not os.path.isfile(path):
        return (["state_sync.sh itself is missing"], [])
    with open(path) as fh:
        src = fh.read()
    listed = set()
    for name in ("STATE_FILES", "JUDGEMENT_FILES"):
        m = re.search(r'%s="((?:[^"\\]|\\.)*)"' % name, src, re.S)
        if not m:
            return (["could not parse %s out of state_sync.sh" % name], [])
        listed |= set(m.group(1).replace("\\\n", " ").split())

    # DERIVED is collected from the scripts, not held here. Each writer declares its own
    # rewritten-every-run outputs as a module-level DERIVED_OUTPUTS tuple (compose.py has the
    # only one today), and this test reads those declarations. Chris, 31.08.2026: the previous
    # version kept the list in this file, where the path of least resistance for anyone hitting
    # a red run was to append to it - which is exactly how the gap it was written to catch
    # would come back.
    #
    # Parsed with ast, deliberately, not regex: a DECLARATION is reliably parseable where a
    # USAGE pattern is not. An earlier attempt inferred derivation by scanning for
    # open(NAME, "w") and found no access at all for 8 of the 19 data files, because they are
    # written through helpers. Inference was then abandoned for a stronger reason: the only
    # property a static pass could see - "written but never read back" - is FALSE for both
    # genuinely derived files. mark_published.py reads expected_urls.txt and composed.json;
    # archive_day.py reads composed.json. What makes them derived is that one command recreates
    # them whole from backed-up inputs, which no static analysis can establish. So this is a
    # declaration that cannot be made in the test, which is the honest guarantee available.
    import ast
    DERIVED = {}
    for script in sorted(glob.glob(os.path.join(HERE, "*.py"))):
        try:
            tree = ast.parse(open(script).read())
        except SyntaxError:
            continue
        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue
            if not any(getattr(t, "id", None) == "DERIVED_OUTPUTS" for t in node.targets):
                continue
            try:
                for name in ast.literal_eval(node.value):
                    DERIVED[name] = os.path.basename(script)
            except (ValueError, TypeError):
                pass

    ORPHANS = {}

    # Each declared derived file must have a WRITER. This is a deliberate stand-in for the real
    # guarantee - delete it, run the pipeline, confirm it comes back - which was costed on
    # 31.08.2026 and rejected for the fixture:
    #
    #   * rebuilding needs /tmp/today.json AND /tmp/picks.json, both ephemeral and gone by the
    #     next morning, plus network for link resolution, title verification and bylines. A
    #     dry-run compose took 4-5 minutes against this fixture's ~2 seconds offline.
    #   * worse, delete-then-rebuild DISARMS two guards to run. Without composed.json,
    #     mark_published.py stops refusing a stale run and marks every pick "including any a
    #     section cap dropped" - burning cap losers that should stay available. Without
    #     expected_urls.txt, the only check that catches an INVENTED url is gone (it was
    #     silently empty on 17.08.2026 and that is exactly what happened). A network flake
    #     mid-rebuild leaves both disarmed in a directory whose next command may be
    #     mark_published.py. A test must not be able to cause the fault it checks for.
    #
    # So this asserts the cheap half: the claim is plausible because something writes the file.
    # It catches the mis-declaration that matters - a file called derived that nothing rebuilds,
    # which would then be backed up nowhere. If the full check is ever wanted it belongs in a
    # separate script, run deliberately, against a throwaway COPY of this directory, moving
    # files aside rather than deleting them.
    #
    # Matched by looking at the ~40 chars after the filename literal rather than by parsing the
    # call, after three structural patterns failed: [^)]* breaks on the ")" inside
    # os.path.join(HERE_DIR, "composed.json"). That brittleness is the reason the declaration
    # lives beside the writer and this test only sanity-checks it.
    _py_src = {os.path.basename(f): open(f).read()
               for f in glob.glob(os.path.join(HERE, "*.py"))}

    def _writer_of(fname):
        needle = re.escape('"%s"' % fname) + "|" + re.escape("'%s'" % fname)
        for script, text in sorted(_py_src.items()):
            for m in re.finditer(needle, text):
                if re.match(r'\s*\)?\s*,\s*["\'][wa]', text[m.end():m.end() + 40]):
                    return script
        return None

    on_disk = {os.path.basename(p) for pat in ("*.txt", "*.json", "*.opml")
               for p in glob.glob(os.path.join(HERE, pat))}
    missing = sorted(on_disk - listed - set(DERIVED) - set(ORPHANS))
    # A file cannot be both backed up and declared throwaway: one of the two is a mistake, and
    # left alone it would read as deliberate to whoever finds it next.
    missing += sorted("%s is declared derived by %s AND listed in state_sync.sh - pick one"
                      % (f, DERIVED[f]) for f in DERIVED if f in listed)
    missing += sorted("%s is declared derived by %s but NO script writes it - if nothing "
                      "rebuilds it, it is not derived, it is unbacked"
                      % (f, DERIVED[f]) for f in DERIVED if not _writer_of(f))
    orphans = sorted(f for f in ORPHANS if os.path.isfile(os.path.join(HERE, f)))
    return (missing, orphans)


def test_boilerplate_scrub():
    """boilerplate.scrub removes site furniture and nothing else (27.09.2026).

    Measured on 18,276 cached openings: the Independent's login notice opened 346 of 346 of its
    entries, GB News's 60-word menu 232 of 232, and the sheet printed them as article text. The
    negative cases pin the three ways the first draft of the scrubber damaged real prose: a
    case-insensitive "COMMENTS" rule that took the noun out of "his comments", a learned
    6-gram that cut ADF's "the U.S. Court of Appeals for the" out of a sentence (hence
    MIN_RUN), and a punctuation tidy-up that rewrote text containing no furniture at all.
    """
    import boilerplate as bp
    bad = []
    prose = ("The Home Office initially rejected her asylum application, citing suspicions "
             "that the marriage was not legitimate, the tribunal heard on Thursday afternoon.")
    notice = ("Please refresh the page or navigate to another page on the site to be "
              "automatically logged in Please refresh your browser to be logged in")
    gb_menu = ("US Edition UK Edition Home GBN Shop YourSay YouDecide Support Us News Alerts "
               "Latest Puzzles Win Tickets News UK News US News Cost of Living Energy Bills "
               "I'm A Celeb! with Stephen and Anne You are about to be charged £0.00 *")
    cases = [
        ("independent notice only", "independent.co.uk/x", notice, None),
        ("independent notice + prose", "independent.co.uk/x", notice + " " + prose, prose),
        # The prose repeats either side of the menu, so drop_standfirst_echo keeps one copy.
        ("gb news menu, closed", "gbnews.com/x", prose + " " + gb_menu + " " + prose, prose),
        ("standfirst echo", "example.com/x",
         prose[:120] + " " + prose + " It continues with a second sentence of real detail.",
         prose + " It continues with a second sentence of real detail."),
        ("gb news menu, runs to end", "gbnews.com/x",
         prose + " US Edition UK Edition Home GBN Shop YourSay YouDecide Support Us News "
         "Alerts Latest Puzzles Win Tickets", prose),
        ("guardian fullscreen", "theguardian.com/x",
         "View image in fullscreen " + prose, prose),
    ]
    for label, key, text, want in cases:
        got = bp.scrub(key, text)
        if got != want:
            bad.append("%s: got %r" % (label, (got or "None")[:90]))
    # Untouched when nothing is furniture - byte-identical, not merely similar.
    plain = "He defended his comments , and said 0 people were hurt; the comments stood."
    plain = plain + " " + prose
    if bp.scrub("example.com/x", plain) is not plain:
        bad.append("text with no furniture was rewritten: %r" % bp.scrub("example.com/x", plain)[:90])
    # Learned/day furniture: host-scoped, run-length gated, opinion markers kept.
    furniture = ("EWTN News, Inc. is the world's largest Catholic news organization, comprised "
                 "of television, radio, print and digital media outlets")
    texts = [prose + " " + furniture + " story %d continues here with more words." % i
             for i in range(8)]
    grams = bp.learn_grams(texts, 0.4, 4)
    if bp.scrub("ncregister.com/x", texts[0], extra=grams) == texts[0]:
        bad.append("a 20-word recurring blurb was learned but not cut")
    court = ("ADF attorneys asked the U.S. Court of Appeals for the Ninth Circuit to act, "
             "arguing the rule was unconstitutional and harmed the athletes involved.")
    topics = ["a school board", "a florist", "a pregnancy centre", "a chaplain", "a baker",
              "a campus ministry", "a counsellor", "a wrestler"]
    short_grams = bp.learn_grams(
        ["Lawyers for %s filed with the U.S. Court of Appeals for the circuit number %d on "
         "a different day entirely." % (t, i) for i, t in enumerate(topics)], 0.4, 4)
    got = bp.scrub("adflegal.org/x", court, extra=short_grams)
    if "Court of Appeals" not in (got or ""):
        bad.append("a short recurring phrase was cut (MIN_RUN): %r" % (got or "None")[:90])
    op = "CP VOICES do not necessarily reflect the views of The Christian Post editors"
    if any("necessarily reflect" in g for g in bp.learn_grams(
            [op + " piece %d about something else entirely." % i for i in range(8)], 0.4, 4)):
        bad.append("an opinion marker was learned as furniture")
    return bad


def test_verify_links():
    """verify_links.py (finish_edition.sh --from) matches hrefs whole, parentheses included.

    Same cases as test_publish_verify_parens, run against the resume path's own verifier, so
    `--from mark` cannot mark against a doc a looser check would have waved through.
    """
    import tempfile
    import verify_links as vl
    jak = ("https://www.thejakartapost.com/indonesia/2026/09/25/tangerang-church-disruption-"
           "rekindles-fears-among-minorities?utm_source=(direct)&utm_medium=single_latest")
    jak_wrapped = ("https://www.google.com/url?q=https://www.thejakartapost.com/indonesia/"
                   "2026/09/25/tangerang-church-disruption-rekindles-fears-among-minorities"
                   "?utm_source%3D(direct)%26utm_medium%3Dsingle_latest&amp;sa=D&amp;usg=x")
    a = '<a href="%s">link</a>'
    cases = [
        ("paren query, wrapped", [jak], a % jak_wrapped, 0),
        ("paren query, bare", [jak], a % jak.replace("&", "&amp;"), 0),
        ("truncated at the paren", [jak],
         a % jak.split("(")[0], 1),
        ("prefix only", [jak + "&x=1"], a % jak.replace("&", "&amp;"), 1),
        ("visible text, no href", [jak], "<p>%s</p>" % jak, 1),
        ("nothing wanted", [], a % jak_wrapped, 1),
    ]
    bad = []
    for label, want, doc, rc in cases:
        sent = "".join('<a href="%s">x</a>' % u.replace("&", "&amp;") for u in want)
        with tempfile.TemporaryDirectory() as d:
            dp, sp = os.path.join(d, "doc.html"), os.path.join(d, "sent.html")
            open(dp, "w").write(doc)
            open(sp, "w").write(sent)
            import io
            import contextlib
            with contextlib.redirect_stdout(io.StringIO()):
                got = vl.main(["verify_links.py", dp, sp])
        if got != rc:
            bad.append("%s: exit %d, want %d" % (label, got, rc))
    return bad


def test_paywall_rechecked_after_decode():
    """A decoded Google News item is re-checked for a paywall (27.09.2026).

    Topic searches ("kw:... site:telegraph.co.uk") target no domain, so while the link was
    still a redirect is_paywalled() had nothing to go on: 50 items on 25.09.2026 - 22 Times,
    16 Telegraph, 5 Church Times - went to the text fetch as free pages.
    """
    import fetch_feeds as ff
    bad = []
    it = {"url": "https://news.google.com/rss/articles/CBMiabc", "paywalled":
          ff.is_paywalled("https://news.google.com/rss/articles/CBMiabc", "")}
    if it["paywalled"]:
        bad.append("fixture: a bare redirect should not look paywalled")
    it["url"] = "https://www.telegraph.co.uk/news/2026/09/24/story"
    ff.recheck_paywall(it)
    if not it["paywalled"]:
        bad.append("decoded Telegraph URL was not flagged paywalled")
    free = {"url": "https://www.bbc.co.uk/news/articles/x", "paywalled": True}
    ff.recheck_paywall(free)
    if not free["paywalled"]:
        bad.append("recheck_paywall cleared a flag; it must only ever set one")
    return bad


def test_bing_topic_routes():
    """Bing topic searches build the right query and credit the real outlet (27.09.2026)."""
    import fetch_feeds as ff
    bad = []
    u = ff.bing_url("kw:site:telegraph.co.uk migrants")
    if "site%3Asite" in u or "site%3Atelegraph.co.uk%20migrants" not in u:
        bad.append("kw: Bing query malformed: %s" % u)
    if "site%3Aewtn.co.uk" not in ff.bing_url("ewtn.co.uk"):
        bad.append("plain Bing site: query changed")
    for raw, want in [("The Telegraph (bing: church)", "The Telegraph"),
                      ("The Post (New Zealand)", "The Post (New Zealand)"),
                      ("The Independent (Asia)", "The Independent (Asia)")]:
        if ff.feed_outlet_label(raw) != want:
            bad.append("feed_outlet_label(%r) = %r" % (raw, ff.feed_outlet_label(raw)))
    return bad


def test_finish_edition_from_guards():
    """finish_edition.sh --from rejects what it cannot do, BEFORE touching anything (27.09.2026).

    The resume path skips compose and publish, so its argument guards are the only thing that
    stands between a typo and a half-run tail. Both cases below must exit 2 without reading
    /tmp/today.json - they fail at argument parsing, so this is safe to run any time.
    """
    import subprocess
    bad = []
    for args in (["--from", "bogus"], ["--from", "mark", "--dry-run"], ["--from"]):
        r = subprocess.run(["bash", os.path.join(HERE, "finish_edition.sh")] + args,
                           capture_output=True, text=True, timeout=30)
        if r.returncode != 2 or "==" in r.stdout:
            bad.append("%s -> exit %d, stdout %r" % (" ".join(args), r.returncode,
                                                      r.stdout[:60]))
    return bad


def test_event_sizes():
    """event_sizes links one NAMED event across wordings, and nothing else (27.09.2026).

    Built from 25.09.2026's real headlines: the FDA nominee's hearing arrived in wordings too
    different for word overlap, and the fix links them on "Overton" + an event word. The
    negatives are the three ways the first drafts chained unrelated stories: a title-case
    common noun ("Judge"), a capitalised legal word ("Amendment", 22.09.2026), and an
    institution ("Senate") shared by two different hearings.
    """
    import shortlist as sl
    heads = [
        "STAT+: Heidi Overton, Trump's pick for FDA head, faced questions at Senate hearing",
        "Dr. Heidi Overton appears before Senate committee for confirmation hearing",
        "Opinion | The deceptively high stakes of Heidi Overton's Senate hearing",
        "Senate hearing probes claims of Flock camera Fourth Amendment violations",
        "Parliament passes Transgender Persons Amendment Bill after heated debate",
        "On the 50th anniversary of the Hyde Amendment, what the vote meant",
        "Judge orders Trump to lift White House media ban on CNN and Politico",
        "Judge dismisses Ohio lawmakers' lawsuit challenging abortion amendment",
        "a judge said the ruling would stand, and the judge declined to comment",
        "the judge who heard the case said the judge's order stood",
    ]
    rows = [{"headline": h} for h in heads]
    size = sl.event_sizes(rows)
    got = [size[id(r)] for r in rows]
    bad = []
    if got[0] < 3 or got[1] < 3 or got[2] < 3:
        bad.append("the three Overton reports did not form one event: %s" % got[:3])
    if got[3] != 1:
        bad.append("a different Senate hearing joined the Overton event (%d)" % got[3])
    if got[4] != 1 or got[5] != 1:
        bad.append("'Amendment' chained two unrelated stories: %s" % got[4:6])
    if got[6] != 1 or got[7] != 1:
        bad.append("'Judge' linked two unrelated court stories: %s" % got[6:8])
    return bad


def test_feedly_parse():
    """The Church Times arrives through Feedly's stream of its RSS (27.09.2026).

    Pins the fields the sweep relies on: the publisher's canonical link (not a Feedly URL),
    a timezone-aware date so the window test works, the standfirst as the summary, and that
    an error body raises rather than looking like an empty feed.
    """
    import json as _json
    import fetch_feeds as ff
    bad = []
    body = _json.dumps({"id": "feed/https://www.churchtimes.co.uk/rss", "items": [{
        "title": "City of London churches sever ties with bishops",
        "published": 1790290380000,
        "alternate": [{"href": "https://www.churchtimes.co.uk/articles/2026/25-september/"
                               "news/uk/city-of-london-churches-sever-ties-with-bishops"}],
        "summary": {"content": "<p>THE Rector of St Helen&#8217;s, Bishopsgate, has "
                               "characterised the bishops...</p>"}}]}).encode()
    ents = ff.parse_feedly(body, "Church Times")
    e = ents[0] if ents else {}
    if not e.get("link", "").startswith("https://www.churchtimes.co.uk/articles/"):
        bad.append("link is not the publisher's: %r" % e.get("link"))
    if not e.get("date") or e["date"].tzinfo is None:
        bad.append("date missing or naive: %r" % e.get("date"))
    if "St Helen\u2019s" not in e.get("summary", "") or "<p>" in e.get("summary", ""):
        bad.append("summary not unescaped/stripped: %r" % e.get("summary", "")[:60])
    try:
        ff.parse_feedly(b'{"errorCode": 401, "errorMessage": "unauthorized"}', "x")
        bad.append("an error body parsed as an empty feed")
    except ValueError:
        pass
    if "streamId=feed%2Fhttps%3A%2F%2Fwww.churchtimes.co.uk%2Frss" not in ff.feedly_url(
            "https://www.churchtimes.co.uk/rss"):
        bad.append("feedly_url malformed: %s" % ff.feedly_url("https://www.churchtimes.co.uk/rss"))
    return bad


def test_batched_decode_mapping():
    """Batched Google decodes are matched by request id, never by position (27.09.2026).

    The response below is the shape Google returned live that day: rows out of request order
    (3, 1, 4) and request 2 - a lookup Google could not answer - present with no payload.
    Matching by position would give request 2 the URL of request 3.
    """
    import resolve as rv
    bad = []
    raw = (")]}'\n\n"
           '[["wrb.fr","Fbv4je",null,null,null,[3],"2"],'
           '["wrb.fr","Fbv4je","[\\"garturlres\\",\\"https://example.com/three?x=1\\",1]",'
           'null,null,null,"3"],'
           '["wrb.fr","Fbv4je","[\\"garturlres\\",\\"https://example.com/one\\",1]",'
           'null,null,null,"1"],'
           '["wrb.fr","Fbv4je","[\\"garturlres\\",\\"https://example.com/four(a)\\",1]",'
           'null,null,null,"4"],["di",12]]')
    got = rv.parse_batch_response(raw)
    want = {"1": "https://example.com/one", "3": "https://example.com/three?x=1",
            "4": "https://example.com/four(a)"}
    if got != want:
        bad.append("parse_batch_response: %r" % got)
    if "2" in got:
        bad.append("an unanswered request was given a URL")
    return bad


def test_decoded_link_tidy():
    """A decoded link gets the same tracker strip a feed link gets, and an AMP copy is
    swapped for the publisher's OWN canonical - read off the page, never constructed
    (27.09.2026).

    The 27.09 test sweep decoded 474 links: 4 carried utm_/ref= trackers that clean_url
    strips from every feed link, and 9 were AMP copies (Live Law, Verdictum, Deccan
    Chronicle, The Hindu, WION). An AMP URL keys differently from its canonical, so the
    same story from the outlet's feed and from Google did not dedupe. Rewriting /amp/ by
    pattern would be authoring a link; the page's rel=canonical is the publisher's own.
    """
    import resolve as rv
    bad = []
    # 1. Trackers go; an identifying query (?p=, ?id=) stays.
    for raw, want in (
            ("https://www.brusselstimes.com/belgium/2335327/pay/?utm_term=Autofeed&utm_medium=x",
             "https://www.brusselstimes.com/belgium/2335327/pay"),
            ("https://www.straitstimes.com/world/pope-leo?ref=latest",
             "https://www.straitstimes.com/world/pope-leo"),
            ("https://www.pressherald.com/?p=7729825", "https://www.pressherald.com/?p=7729825"),
            ("https://abcnews.com/Health/sues/story?id=136489875",
             "https://abcnews.com/Health/sues/story?id=136489875")):
        got = rv.tidy_decoded(raw, fetch=lambda u: "")
        if got != want:
            bad.append("tidy %s -> %s, want %s" % (raw, got, want))
    # 2. AMP -> the page's own canonical, same site only.
    amp = "https://www.livelaw.in/amp/high-court/uttarakhand-high-court/maintenance-551935"
    canon = "https://www.livelaw.in/high-court/uttarakhand-high-court/maintenance-551935"
    page = '<html><head><link rel="canonical" href="%s"/></head></html>' % canon
    if rv.tidy_decoded(amp, fetch=lambda u: page) != canon:
        bad.append("AMP copy was not swapped for its rel=canonical")
    hindu = "https://www.thehindu.com/news/national/trans-law/article71512778.ece/amp/"
    hpage = "<link href='https://www.thehindu.com/news/national/trans-law/article71512778.ece' rel='canonical'>"
    if rv.tidy_decoded(hindu, fetch=lambda u: hpage) != \
            "https://www.thehindu.com/news/national/trans-law/article71512778.ece":
        bad.append("trailing /amp/ with href-before-rel canonical not handled")
    # 3. ...and it keeps the AMP link rather than guess when the page will not say.
    for label, pg in (("no canonical", "<html></html>"),
                      ("fetch failed", None),
                      ("canonical on another site",
                       '<link rel="canonical" href="https://example.com/other"/>'),
                      ("canonical is an index", '<link rel="canonical" href="https://www.livelaw.in/"/>'),
                      ("canonical is still AMP",
                       '<link rel="canonical" href="https://www.livelaw.in/amp/x-1"/>')):
        def f(u, pg=pg):
            if pg is None:
                raise OSError("blocked")
            return pg
        if rv.tidy_decoded(amp, fetch=f) != amp:
            bad.append("AMP swapped although %s" % label)
    # 4. A non-AMP link is never fetched.
    calls = []
    rv.tidy_decoded("https://www.bbc.co.uk/news/articles/c62enegxyl9o",
                    fetch=lambda u: calls.append(u) or "")
    if calls:
        bad.append("a plain article link was fetched")
    return bad


def test_syndicated_credit():
    """A syndicated copy is used only when the partner credits the publisher (27.09.2026).

    Yahoo republishes some Telegraph journalism with JSON-LD provider "The Telegraph"; the
    same page shape carries other providers' stories too, and a similar headline from the
    Mail must never be shown on the sheet as the Telegraph's own words.
    """
    import json as _json
    import shortlist as sl
    def page(provider, desc):
        return ('<script type="application/ld+json">%s</script>'
                % _json.dumps({"@type": "NewsArticle", "provider": {"name": provider},
                               "publisher": {"name": "Yahoo News"}, "description": desc}))
    desc = "Zohran Mamdani has hit back at Benjamin Netanyahu after the Israeli prime minister attacked him."
    bad = []
    if sl.credited_description(page("The Telegraph", desc), "Telegraph") != desc:
        bad.append("a Telegraph-credited copy was not accepted")
    if sl.credited_description(page("Daily Mail", desc), "Telegraph") is not None:
        bad.append("a copy credited to another provider was accepted")
    if sl.credited_description("<html>no structured data</html>", "Telegraph") is not None:
        bad.append("a page with no JSON-LD was accepted")
    return bad


def test_refresh_petitions():
    """Looker rows -> petition_totals.json (02.10.2026). Invented ids, field names and counts:
    this repo is public, and the real source settings live in petition_source.json.

    signatures = new + existing + duplicated; concatenated objects parse as the tool returns
    them; a count that falls more than MAX_DROP is refused as a copying mistake; a row missing
    a field is refused, not read as zero.
    """
    import refresh_petitions as rp
    bad = []
    fields = {"id": "t.pid", "new": "t.new", "existing": "t.old", "duplicated": "t.dup"}
    raw = ('{"t.pid":"90001","t.dup":1000,"t.old":5000,"t.new":400}'
           '{"t.pid":"90002","t.dup":20,"t.old":300,"t.new":10}')
    rows = rp.parse_rows(raw)
    if len(rows) != 2:
        bad.append("concatenated rows parsed as %d, expected 2" % len(rows))
    held, rep, probs = rp.apply(rows, {}, fields, today="2026-10-02")
    if held.get("90001", {}).get("signatures") != 6400 or probs:
        bad.append("90001 summed to %r (expected 6,400): %r" % (held.get("90001"), probs))
    _, _, probs = rp.apply(rows, {"90001": {"signatures": 10000, "as_of": "2026-09-01"}}, fields)
    if not any("90001" in p for p in probs):
        bad.append("a count 36% below the held figure was not refused")
    _, _, probs = rp.apply([{"t.pid": "1", "t.new": 5}], {}, fields)
    if not probs:
        bad.append("a row missing the existing/duplicated fields was accepted")
    return bad


def test_sheet_fold():
    """fold_groups folds one event's lines and nothing else (02.10.2026, from the 01.10 sheet).

    Positives: the shield-law lawsuit, worded four ways. Negatives that the first two
    versions of the rule folded: the Nigerian blasphemy appeal (shares "supreme court ...
    hear" with the shield-law lead), and two different Burnham stories (an office-holder's
    name is not an event).
    """
    import shortlist as sl
    rows = [{"headline": h} for h in (
        "Multistate lawsuit asks Supreme Court to hear challenge to abortion 'shield laws'",
        "Red states ask U.S. Supreme Court to overturn California's abortion shield laws",
        "3 States Ask High Court To Block Abortion Shield Laws",
        "3 GOP states go to US Supreme Court to challenge 3 Democratic-led states' abortion 'shield' laws",
        "Lawyers urge Nigerian Supreme Court to hear case of young musician who nears seventh year in prison on blasphemy charge",
        # 02.10.2026 live sheet: this bridge chained the Nigerian appeal into the shield fold
        "Supreme Court to hear case on lawsuit that blocked Marian shrine plan in Kentucky",
        "Your guide to the California Congressional District 26 race: Irwin vs. Gallucci",
        "Your guide to L.A. City Charter Amendment DD",
        "Andy Burnham determined to prove John Swinney wrong for claiming he'd be the last Prime Minister",
        "Andy Burnham admits concern Man City owners will be forced to SELL after being found guilty")]
    groups = sl.fold_groups(rows)
    bad = []
    shield = next((g for g in groups if 0 in g), [])
    if sorted(shield) != [0, 1, 2, 3]:
        bad.append("shield-law fold was %r, expected the four shield-law lines" % shield)
    if any(4 in g for g in groups):
        bad.append("the Nigerian blasphemy appeal was folded into another event")
    if any(5 in g for g in groups):
        bad.append("the Marian shrine case was folded into the shield-law event")
    if any(6 in g and 7 in g for g in groups):
        bad.append("two unrelated 'Your guide to' pieces were folded together")
    if any(8 in g and 9 in g for g in groups):
        bad.append("two different Burnham stories were folded together")
    return bad


def test_five_uses_published_url():
    """slack_five must check the link a story was PUBLISHED with, not the feed's original.

    01.10.2026: Esther Rantzen's BBC lead arrived as a Google News redirect, compose.py
    resolved it to bbc.co.uk in memory and published that, today.json kept the redirect, and
    slack_five refused the lead as invented. composed.json now carries the published URLs.
    """
    import slack_five as sf
    bad = []
    gnews = "https://news.google.com/rss/articles/CBMiXEFVX3lx"
    bbc = "https://www.bbc.co.uk/news/articles/c4g4z255y30o"
    items = [{"headline": "Esther Rantzen dies aged 86", "outlet": "BBC", "url": gnews}]
    flat = [{"n": 0, "depth": 0, "note": ""}]
    picks, probs = sf.resolve(flat, items, {0: "Life"}, {bbc}, {0: bbc})
    if probs or not picks or picks[0]["url"] != bbc:
        bad.append("a resolved lead was refused or linked to the redirect: %r" % (probs,))
    _, probs = sf.resolve(flat, items, {0: "Life"}, {bbc}, {})
    if not probs:
        bad.append("with no published URL on record, the unpublished redirect was accepted")
    return bad


def test_action_desk():
    """The Slack five's Action Desk lines post with no human review (Chris, 02.10.2026), so
    the matching must refuse rather than guess. Built against stubbed parl-monitor data so it
    runs on any machine; the live desk is exercised by slack_five.py itself.

    - a vote card attaches only when the story NAMES its bill or Act on a 2+ word core. On
      the first live run "Abortion (Northern Ireland) Regulations" collapsed to "abortion" and
      tied a US shield-law story to the NI regulations.
    - petitions are candidates only: big enough (>= MIN_SIGNERS), recent (<= MAX_AGE_DAYS)
      and in the story's area. A 3-signer 2021 petition was the first live "match".
    - slack_five refuses a slot whose candidates have no decision, and an id that is not
      one of them; null attaches nothing; a valid id attaches the rendered line.
    - no desk line may carry a URL.
    """
    import datetime as _dt
    import action_desk as ad
    import slack_five as sf
    bad = []
    real = ad.Desk

    def stub():
        d = real.__new__(real)
        d.ok, d.reason, d.root = True, "", "stub"
        d.petitions_as_of = _dt.date.today()
        d.areas = lambda h, t: set()          # section mapping alone tags the story
        d.bills = [{"title": "Immigration and Asylum Bill", "house": "Commons",
                    "stage": "Committee stage", "next": "2026-10-13", "areas": [11]}]
        d.cards = [{"name": "Abortion decriminalisation", "area": 1,
                    "bill": "Crime and Policing Bill - New Clause 1",
                    "debate_match": ["Crime and Policing Bill"],
                    "status": "Agreed by the Commons 379-137 on 17 June 2025 and added to the Bill."},
                   {"name": "Abortion services in Northern Ireland", "area": 1,
                    "bill": "Abortion (Northern Ireland) Regulations",
                    "debate_match": ["Abortion (Northern Ireland)"], "status": "All agreed."}]
        recent = (_dt.date.today() - _dt.timedelta(days=100)).isoformat()
        old = (_dt.date.today() - _dt.timedelta(days=2000)).isoformat()
        d.petitions = [dict(p, words=ad._words(p["name"])) for p in (
            {"id": 1, "name": "Keep the Abortion Decriminalisation Clause Out of Law",
             "signatures": 25000, "areas": [1], "logged": recent, "launch": recent},
            {"id": 2, "name": "Abortion reversal - allow women real choice!",
             "signatures": 3, "areas": [1], "logged": recent, "launch": recent},
            {"id": 3, "name": "Stop abortion up to birth", "signatures": 50000,
             "areas": [1], "logged": recent, "launch": old},
            {"id": 4, "name": "Secure Our Borders", "signatures": 8000,
             "areas": [11], "logged": recent, "launch": recent})]
        return d

    d = stub()
    r = d.lookup("Government admits abortion up to birth is no longer a crime",
                 "An impact assessment on the Crime and Policing Act 2026 concedes ...", "Life")
    if not any(l.startswith("Vote: Abortion decriminalisation") for l in r["lines"]):
        bad.append("a story naming the Crime and Policing Act did not get its vote card")
    r2 = d.lookup("States sue to overturn abortion shield laws", "abortion pills by mail", "Life")
    if r2["lines"]:
        bad.append("a story naming no bill got %r (one-word core matched)" % r2["lines"])
    ids = [c["id"] for c in r["candidates"]]
    if ids != [1]:
        bad.append("petition candidates were %r, expected only the big recent area-1 one" % ids)
    r3 = d.lookup("One in, one out scheme scrapped", "small boat returns to France",
                  "Immigration & Asylum")
    if r3["lines"]:
        bad.append("a migration story that names no bill got a bill line: %r" % r3["lines"])
    r4 = d.lookup("MPs to amend the Immigration and Asylum Bill", "", "Immigration & Asylum")
    if not any("next sitting 13 October" in l for l in r4["lines"]):
        bad.append("a story naming the Immigration and Asylum Bill got no bill line")

    # Islam stories stay in their sections but reach areas 7 and 8 (Chris, 02.10.2026).
    d.petitions.append(dict({"id": 5, "name": "Defend the freedom to critique Islam",
                             "signatures": 40000, "areas": [8, 7],
                             "logged": d.petitions[0]["logged"],
                             "launch": d.petitions[0]["launch"]},
                            words=ad._words("Defend the freedom to critique Islam")))
    r5 = d.lookup("Preacher at London mosque urges men to beat their wives",
                  "Islamic community centre investigated by the Charity Commission",
                  "Politics, Government & Society")
    if 5 not in [c["id"] for c in r5["candidates"]]:
        bad.append("a mosque story outside the religion sections did not reach areas 7/8")
    if "islam" not in [w for c in r5["candidates"] if c["id"] == 5 for w in c["shared"]]:
        bad.append("'Islamic' in the story did not meet 'Islam' in the petition")

    ad.Desk = lambda *a, **k: stub()
    try:
        def picks(choice):
            p = {"n": 7, "depth": 0, "headline": "Government admits abortion up to birth",
                 "section": "Life", "desk": []}
            if choice != "unset":
                p["petition"] = choice
            else:
                p["petition"] = sf._UNSET
            return [p]
        text = {7: "the Crime and Policing Act 2026"}
        if not sf.attach_desk(picks("unset"), text):
            bad.append("a slot with candidates and no petition decision was not refused")
        if not sf.attach_desk(picks(999), text):
            bad.append("a petition id outside the candidates was not refused")
        pk = picks(None)
        if sf.attach_desk(pk, text) or any("petition" in l for l in pk[0]["desk"]):
            bad.append("petition null still attached a petition, or was refused")
        pk = picks(1)
        if sf.attach_desk(pk, text) or not any(l.startswith("Our petition: Keep the Abortion Decriminalisation")
                                               for l in pk[0]["desk"]):
            bad.append("a valid petition id did not attach its line")
        if any("http" in l or "www." in l for l in pk[0]["desk"]):
            bad.append("a desk line carried a URL")
        out = sf.render([dict(pk[0], url="https://example.org/a", outlet="X", note="")],
                        "https://docs.google.com/document/d/x/edit", "Friday 2 October", 1)
        if "    ↳ Our petition: Keep the Abortion Decriminalisation" not in out:
            bad.append("render did not nest the desk lines under the slot")
    finally:
        ad.Desk = real
    return bad


if __name__ == "__main__":
    # --known-red FILE softens the exit code for failures the file waives, and ONLY those.
    # Without the flag the behaviour is exactly what it always was: any red exits 1.
    kr = None
    if "--known-red" in sys.argv:
        i = sys.argv.index("--known-red")
        kr = sys.argv[i + 1] if i + 1 < len(sys.argv) else "known_red.txt"
    sys.exit(run(verbose="-v" in sys.argv, known_red=kr))
