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

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import shortlist   # noqa: E402
import regions     # noqa: E402
import compose     # noqa: E402
import fetch_feeds # noqa: E402

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


def run(verbose=False):
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
                outlet, author = parts[0], (parts[1] if len(parts) > 1 else "")
                url = parts[2] if len(parts) > 2 else ""
                line_out = compose.credit({"outlet": outlet, "author": author, "url": url})
                shown = ("| " + author) in line_out
                got = "shown" if shown else "hidden"
                ok = (got == expected.lower())
                detail = "%s -> %s" % (outlet[:24], line_out)
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
            elif kind == "OUTLET":
                got = compose.tidy_outlet(parts[0])
                ok = (got == expected)
                detail = "%s -> %s" % (parts[0][:34], got)
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

    print("\n%d passed, %d failed, %d total" % (passed, len(failed), passed + len(failed)))
    for n, msg in failed:
        # n is a line number for a testcases.txt case and a label ("smoke") for the built-in
        # assertions. This printed with %d until 24.08.2026, so ANY smoke failure crashed the
        # reporter with a TypeError instead of reporting the failure - the one moment the
        # harness exists for. Found by deliberately breaking the new self-block assertion.
        print("  FAIL  %-9s %s" % ("line %d" % n if isinstance(n, int) else n, msg))
    return 1 if failed else 0



def _shell_scripts():
    """The repo's shell scripts, in a stable order."""
    import glob
    return sorted(glob.glob(os.path.join(HERE, "*.sh")))


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

if __name__ == "__main__":
    sys.exit(run(verbose="-v" in sys.argv))
