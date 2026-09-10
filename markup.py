#!/usr/bin/env python3
"""Take Chris's markup of a PUBLISHED edition and turn it into something that accumulates.

Chris, 10.09.2026. Why this exists. The judgement loop only ever ran one way. Roughly a
quarter of a million tokens a day goes into tiering ~1,200 leads, and the only correction
channel was Chris hand-marking a DRAFT - 23.08, 24.08, 25.08, 31.08. Nothing recorded what he
would have changed in an edition that actually shipped, so the question that matters most
could not be asked at all: of the items the curator judged on a bare headline, which ones was
it wrong about? The archive knows what was picked and rank_eval knows how well the scorer
agrees with those picks, and neither knows where the picks themselves were wrong.

So: two lists, and three things done with them.

    python3 markup.py 20260910 --should-have 417,1265 --should-not 248
    python3 markup.py 20260910 --should-have 417 --write-testcases   # after reading them

  1. WHY was it missed. For each index, the diagnosis is printed from the archive: what tier
     it was given, its importance rank that day, whether it was a ★ primary source, whether
     anything of its text was readable, and which section it landed in. That is the part
     that turns "you missed this" into a fixable statement - a story missed at rank 900 with
     no readable text is a different bug from one missed at rank 12.

  2. The correction is RECORDED, in markup/<date>.json and in tiers.json. Chris's verdict
     replaces the curator's for that item, because it is the better label: tiers.json is what
     --new-only reads and what rank_eval scores against, so a correction that does not land
     there is a correction the pipeline forgets by morning.

  3. testcases lines are SUGGESTED, and only written with --write-testcases. Deliberately not
     automatic. testcases.txt is Chris's own corrections expressed as assertions, and the
     discipline that makes it work - a case is written RED before the rule is edited - depends
     on the case saying something true and specific. A "should have run" does not by itself
     say which rule was wrong: it could be the section, the suppression, the scorer's ranking
     or nothing at all. So this proposes the ABOVE pairs that the markup implies, names the
     alternative kinds where they look more likely, and leaves the choice to a human.

Nothing here touches an edition that has already published. It only changes the labels.
"""
import argparse
import gzip
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ARCHIVE = os.path.join(HERE, "archive")
MARKUP_DIR = os.path.join(HERE, "markup")
TESTCASES = os.path.join(HERE, "testcases.txt")
TIERS = os.path.join(HERE, "tiers.json")


def die(msg):
    sys.stderr.write("markup: %s\n" % msg)
    raise SystemExit(1)


def parse_list(spec):
    if not spec:
        return []
    out = []
    for part in str(spec).replace(" ", ",").split(","):
        if part:
            try:
                out.append(int(part))
            except ValueError:
                die("not an index: %r" % part)
    return out


def has_text(j):
    """judged.json records the literal string 'none' when nothing was readable, not a
    missing key - so `not j.get("text_id")` is False exactly when the answer is no."""
    return bool(j) and (j.get("text_id") or "none") != "none"


def load_edition(date):
    d = os.path.join(ARCHIVE, date)
    if not os.path.isdir(d):
        die("no archived edition %s. archive_day.py writes these; without one there is "
            "nothing to mark up, because /tmp/today.json is gone by the next morning." % date)
    sweep = os.path.join(d, "sweep.json.gz")
    if not os.path.exists(sweep):
        die("%s has no sweep.json.gz, so the indexes cannot be resolved" % d)
    with gzip.open(sweep, "rt", encoding="utf-8") as fh:
        items = json.load(fh)["items"]
    judged = []
    if os.path.exists(os.path.join(d, "judged.json")):
        judged = json.load(open(os.path.join(d, "judged.json"), encoding="utf-8"))
    composed = {}
    if os.path.exists(os.path.join(d, "composed.json")):
        composed = json.load(open(os.path.join(d, "composed.json"),
                                  encoding="utf-8")).get("composed", {})
    published = {}
    for section, idxs in composed.items():
        for n in idxs:
            published[int(n)] = section
    # judged.json is written in SHEET order, so the position in this list IS the
    # importance rank the curator read that morning. Keyed and ordered forms both returned:
    # sorting by index instead would report rank 154 for a story the sheet put 44th, which
    # is the difference between "missed near the top" and "missed at the bottom" - the whole
    # question the diagnosis exists to answer.
    return items, {j["i"]: j for j in judged}, published, judged


def diagnose(n, items, judged, published, rank_of):
    """Why this index ended up where it did. The point of the whole exercise."""
    if n < 0 or n >= len(items):
        return None, "no such index in that day's sweep"
    it = items[n]
    j = judged.get(n)
    bits = []
    bits.append("tier %s" % (j["tier"] if j else "not judged - never reached the sheet"))
    if n in published:
        bits.append("PUBLISHED in %s" % published[n])
    else:
        bits.append("not published")
    r = rank_of.get(n)
    bits.append("importance rank %s of %d" % (r if r is not None else "?", len(rank_of) or 0))
    if j and j.get("section"):
        bits.append("section %s" % j["section"])
    # The two conditions that most often explain a miss, both recorded at judging time.
    if j and not has_text(j):
        bits.append("NO READABLE TEXT - judged on the headline alone")
    if it.get("paywalled"):
        bits.append("paywalled")
    age = it.get("age_h")
    if age is not None:
        bits.append("%.0fh old" % age)
    return it, "; ".join(bits)


def suggest_cases(missed, wrong, items, judged, published):
    """ABOVE pairs the markup implies, plus a nudge to the kind that may fit better."""
    lines, notes = [], []
    ran_low = [n for n in published
               if (judged.get(n) or {}).get("tier") in (2, 3)]
    ran_low.sort(key=lambda n: -(judged.get(n) or {}).get("tier", 0))
    for n in missed:
        if n >= len(items):
            continue
        hl = (items[n].get("headline") or "").strip()
        j = judged.get(n) or {}
        if not j:
            notes.append("%s never reached the sheet at all, so ABOVE cannot express the "
                         "miss - the rule that was wrong is the suppression or the section "
                         "match. Look at SUPPRESS/KEEP or SECTION instead." % n)
            continue
        if not has_text(j):
            notes.append("%s was judged with no readable text, so an ABOVE pair asserts "
                         "something the scorer could not have known. Worth asking whether "
                         "the fix is a source route, not a ranking rule." % n)
        peer = next((p for p in ran_low if p != n
                     and (judged.get(p) or {}).get("section") == j.get("section")), None)
        if peer is None:
            notes.append("%s has no lower-tiered peer published in %s, so there is no honest "
                         "ABOVE pair to make from this edition." % (n, j.get("section")))
            continue
        lines.append("ABOVE | %s | %s" % (hl, (items[peer].get("headline") or "").strip()))
    for n in wrong:
        if n < len(items):
            notes.append("%s ran and should not have. ABOVE cannot say that; the useful case "
                         "is usually SUPPRESS, or an ABOVE with this headline on the RIGHT "
                         "of a story that deserved the slot." % n)
    return lines, notes


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("date", help="YYYYMMDD of an archived edition")
    ap.add_argument("--should-have", default="", help="indexes that should have run")
    ap.add_argument("--should-not", default="", help="indexes that should not have run")
    ap.add_argument("--note", default="", help="Chris's reasoning, stored with the record")
    ap.add_argument("--write-testcases", action="store_true",
                    help="append the suggested cases to testcases.txt (read them first)")
    ap.add_argument("--dry-run", action="store_true", help="change nothing")
    args = ap.parse_args(argv)

    missed, wrong = parse_list(args.should_have), parse_list(args.should_not)
    if not missed and not wrong:
        die("nothing to record: pass --should-have and/or --should-not")

    items, judged, published, in_order = load_edition(args.date)
    # Importance rank as the sheet ordered it that day, so "missed at rank 900" is sayable.
    rank_of = {j["i"]: i + 1 for i, j in enumerate(in_order)}

    print("== %s: %d item(s) swept, %d judged, %d published"
          % (args.date, len(items), len(judged), len(published)))
    print()
    records = []
    for kind, idxs in (("should_have_run", missed), ("should_not_have_run", wrong)):
        for n in idxs:
            it, why = diagnose(n, items, judged, published, rank_of)
            if it is None:
                die("%s: %s" % (n, why))
            print("%-16s %-5s %s" % (kind, n, (it.get("headline") or "")[:66]))
            print("%22s %s" % ("", why))
            print("%22s %s" % ("", (it.get("outlet") or "")))
            records.append({"i": n, "verdict": kind, "headline": it.get("headline"),
                            "outlet": it.get("outlet"), "url": it.get("url"),
                            "why": why, "section": (judged.get(n) or {}).get("section"),
                            "tier_was": (judged.get(n) or {}).get("tier"),
                            "published": n in published})
    print()

    lines, notes = suggest_cases(missed, wrong, items, judged, published)
    if lines:
        print("== suggested testcases (READ THESE - they are proposals, not conclusions)")
        for l in lines:
            print("  %s" % l)
    if notes:
        print()
        print("== where an ABOVE pair would be the wrong assertion")
        for nt in notes:
            print("  - %s" % nt)
    print()

    if args.dry_run:
        print("dry run: nothing written.")
        return 0

    os.makedirs(MARKUP_DIR, exist_ok=True)
    path = os.path.join(MARKUP_DIR, "%s.json" % args.date)
    prev = []
    if os.path.exists(path):
        try:
            prev = json.load(open(path, encoding="utf-8")).get("corrections", [])
        except ValueError:
            prev = []
    json.dump({"date": args.date, "note": args.note,
               "corrections": prev + records,
               "suggested_testcases": lines},
              open(path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("recorded %s (%d correction(s) total)"
          % (os.path.relpath(path, HERE), len(prev) + len(records)))

    # tiers.json is what --new-only reads and what rank_eval scores against, so a correction
    # that does not land there is one the pipeline forgets by morning. Chris's verdict
    # replaces the curator's: it is the better label, which is the whole point.
    moved = 0
    if os.path.exists(TIERS):
        store = json.load(open(TIERS, encoding="utf-8"))
        for rec in records:
            j = judged.get(rec["i"]) or {}
            key = j.get("key")
            if not key or key not in store:
                continue
            want = 1 if rec["verdict"] == "should_have_run" else 0
            entry = store[key]
            if isinstance(entry, dict):
                if entry.get("tier") != want:
                    entry["tier"] = want
                    entry["corrected_by"] = "markup %s" % args.date
                    moved += 1
            elif entry != want:
                store[key] = {"tier": want, "corrected_by": "markup %s" % args.date}
                moved += 1
        json.dump(store, open(TIERS, "w", encoding="utf-8"))
    print("tiers.json: %d verdict(s) overridden by the markup" % moved)

    if args.write_testcases and lines:
        with open(TESTCASES, "a", encoding="utf-8") as fh:
            fh.write("\n# markup %s%s\n"
                     % (args.date, (" - " + args.note) if args.note else ""))
            fh.write("# Written RED first, before any rule is edited: that ordering is what "
                     "stops the fix being a special case for one headline.\n")
            for l in lines:
                fh.write("%s\n" % l)
        print("appended %d case(s) to testcases.txt - RUN run_tests.py NOW. They are meant "
              "to be RED until the rule is fixed." % len(lines))
    elif lines:
        print("testcases NOT written. Read the suggestions above, then re-run with "
              "--write-testcases if they say something true.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
