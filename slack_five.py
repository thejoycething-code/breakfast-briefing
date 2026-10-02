#!/usr/bin/env python3
"""Build and validate the Step 10 Slack five. Generated, not hand-typed.

Chris, 10.09.2026. Why this exists: the Doc's 300-odd links are protected by the resolver's
title-verification, expected_urls.txt and publish.sh's byte-exact diff, and NONE of that
touched the five links in the Slack post, because those were the only ones composed by hand
afterwards. On 31.08.2026 four of the five were fabricated - an invented BBC article ID, an
invented domain for Decision Magazine, two wrong path segments - and a correction had to be
posted to the channel. "URLs N/N verified" said nothing about them, because it never saw them.

So the five stops being prose and becomes an artefact with the same guarantee as the Doc:

  1. Every pick must be an index that ACTUALLY PUBLISHED in today's edition (composed.json).
     A cap loser or a story that never made the Doc is refused - the post must not point at
     something the reader cannot find when they open it.
  2. Every URL is copied from the edition's own data and then checked against
     expected_urls.txt. A URL that is not in that file was invented, which is the exact
     definition the pipeline already uses for the Doc.
  3. Every headline and outlet is copied too. Nothing about a story is retyped.
  4. Repeats are checked against the LAST N FIVES, not the last N editions. The Doc's rule
     that a running story may legitimately run again does not carry over here: the five is a
     far narrower window, so a repeat is far more visible (Chris, 31.08.2026 - Paivi
     Rasanen's visa story was put up again after running several times and was cut).
  5. What was posted is recorded in five/<date>.json, so the corrections Chris makes to this
     list can accumulate into something. Until now they could not: the Doc gets tiers.json,
     archive/ and rank_eval, and the five - five items out of three hundred, and the only
     part of the morning most of the channel reads - got no record at all.

It does NOT post. Posting is slack_send_message through the connector, which has no
credential here. The split is deliberate: this writes the text and the record, and the
caller posts the emitted text VERBATIM. Retyping any part of it puts back exactly the
hand-copying step this removes.

    python3 slack_five.py --spec /tmp/five.json --doc-url URL      # build, validate, record
    python3 slack_five.py --spec /tmp/five.json --doc-url URL --dry-run   # no record written
    python3 slack_five.py --history                                # what the last fives ran

The spec is JSON, a list of up to ~6 slots, each a lead index plus optional nested items:

    [{"n": 1059,
      "note": "Second Reading is *tomorrow, Friday 11 September*.",
      "under": [{"n": 290, "note": "Lois McLatchie Miller on ..."}]},
     {"n": 987, "note": "Four women waive anonymity ..."}]

`note` is your own words and is the only free text in the whole file - it can say anything
except a URL, which is refused, because a URL in a note is a URL nobody checked.

ACTION DESK (02.10.2026, action_desk.py). Under each lead slot the post also carries what
parl-monitor knows: the live bill and the recorded vote when the story names them (attached
automatically), and our own petition on the subject. The petition is chosen in the spec,
by id only, from the candidates the desk lists for that slot:

    {"n": 222, "note": "...", "petition": 12345}      # attach petition 12345
    {"n": 52,  "note": "...", "petition": null}       # none of the candidates fits

A slot with candidates and no "petition" key is refused, and the refusal prints the
candidates. An id that is not among them is refused too. Its text is rendered from
parl-monitor's data, never typed. Chris asked for no approval step, so none of this asks;
`--no-desk` turns it off if parl-monitor is broken on the day.
"""
import argparse
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIVE_DIR = os.path.join(HERE, "five")
COMPOSED = os.path.join(HERE, "composed.json")
EXPECTED = os.path.join(HERE, "expected_urls.txt")

# How many past fives to check a pick against. Deliberately longer than the Doc's 7-edition
# window: the five is ~5 items against the Doc's ~300, so the same story recurring inside a
# fortnight is conspicuous in a way it is not in the Doc.
FIVE_HISTORY = 10

CHANNEL = "#campaigns-en-gb"      # C9RH217PZ. Never #campaigns-en_gb-alerts (C8RC23N56).


def die(msg):
    sys.stderr.write("slack_five: %s\n" % msg)
    raise SystemExit(1)


def load_items(path):
    data = json.load(open(path, encoding="utf-8"))
    if isinstance(data, dict) and "items" in data:
        data = data["items"]
    return data


def published_index(composed_path=COMPOSED):
    """{index: section} for everything that actually reached the Doc.

    cut_by_cap is deliberately NOT included. A cap loser is retired, is not in the reader's
    Doc, and linking one from the announcement would point at a story that is not there.
    """
    d = json.load(open(composed_path, encoding="utf-8"))
    out = {}
    for section, idxs in d.get("composed", {}).items():
        for n in idxs:
            out[int(n)] = section
    return out


def published_urls(composed_path=COMPOSED):
    """{index: url as published} from composed.json, {} for a composed.json written before
    02.10.2026. Preferred over today.json, whose url is the feed's original (often a Google
    News redirect) because compose.py resolves links in memory, not on disk."""
    try:
        d = json.load(open(composed_path, encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {int(k): v for k, v in (d.get("urls") or {}).items() if v}


def expected_urls(path=EXPECTED):
    if not os.path.exists(path):
        return None
    urls = set(l.strip() for l in open(path, encoding="utf-8") if l.strip())
    # 17.08.2026: this file was once written 1 byte long, so the invented-URL check was
    # silently unavailable. An empty file is a broken check, not a passing one.
    return urls or None


def load_fives(days=FIVE_HISTORY):
    """Past fives as ran_before-shaped history records, newest first."""
    out = []
    for path in sorted(glob.glob(os.path.join(FIVE_DIR, "2*.json")), reverse=True)[:days]:
        try:
            rec = json.load(open(path, encoding="utf-8"))
        except (ValueError, IOError):
            continue
        date = rec.get("date") or os.path.basename(path)[:8]
        for it in rec.get("items", []):
            out.append({"date": date, "headline": it.get("headline") or "",
                        "outlet": it.get("outlet") or "", "url": it.get("url") or "",
                        # One constant pseudo-section. The five has no sections, and
                        # ran_before's same-section guard would otherwise reject every pair.
                        "section": "_five", "key": ""})
    return out


def check_repeats(picks, history):
    """[(pick, past)] for picks whose STORY already ran in a past five."""
    try:
        import shortlist
    except ImportError:                                    # pragma: no cover
        return []
    hits = []
    for p in picks:
        item = {"headline": p["headline"], "_section": "_five"}
        past = shortlist.ran_before(item, history)
        if past:
            hits.append((p, past))
            continue
        # Same URL is a repeat whatever the prose does; ran_before compares prose only.
        for h in history:
            if h.get("url") and h["url"] == p["url"]:
                hits.append((p, h))
                break
    return hits


def outlet_name(item):
    """Reuse compose.py's outlet logic so the five and the Doc credit a story identically."""
    try:
        import compose
        return compose.outlet_of(item)
    except Exception:                                      # pragma: no cover
        return (item.get("outlet") or "").strip()


_UNSET = object()


def flatten(spec):
    """Spec -> flat [{n, depth, note}], preserving order."""
    flat = []
    for slot in spec:
        if not isinstance(slot, dict) or "n" not in slot:
            die("each slot needs an \"n\": got %r" % (slot,))
        flat.append({"n": int(slot["n"]), "depth": 0, "note": slot.get("note", ""),
                     "petition": slot.get("petition", _UNSET)})
        for sub in slot.get("under", []) or []:
            if not isinstance(sub, dict) or "n" not in sub:
                die("each nested item needs an \"n\": got %r" % (sub,))
            flat.append({"n": int(sub["n"]), "depth": 1, "note": sub.get("note", "")})
    return flat


def resolve(flat, items, pub, exp, urls=None):
    """Attach verbatim headline/outlet/url, refusing anything unpublished or invented."""
    problems, picks = [], []
    for f in flat:
        n = f["n"]
        if n < 0 or n >= len(items):
            problems.append("%s: no such index in the sweep" % n)
            continue
        if n not in pub:
            problems.append(
                "%s: NOT IN THE PUBLISHED DOC - %r (%s). A cap loser or an unpicked story; "
                "the announcement must not link something the reader cannot find."
                % (n, (items[n].get("headline") or "")[:60], outlet_name(items[n])))
            continue
        if re.search(r"https?://", f["note"] or ""):
            problems.append("%s: note contains a URL. Notes are prose; links come from the "
                            "edition data, never from a note." % n)
            continue
        it = items[n]
        url = ((urls or {}).get(n) or it.get("url") or "").strip()
        if not url:
            problems.append("%s: no url in the edition data" % n)
            continue
        if exp is not None and url not in exp:
            problems.append("%s: url is not in expected_urls.txt, i.e. compose.py never "
                            "emitted it - that is the definition of invented: %s"
                            % (n, url[:100]))
            continue
        picks.append({"n": n, "depth": f["depth"], "note": f["note"],
                      "petition": f.get("petition", _UNSET), "desk": [],
                      "headline": (it.get("headline") or "").strip(),
                      "outlet": outlet_name(it), "url": url,
                      "section": pub[n], "paywalled": bool(it.get("paywalled")),
                      "age_h": it.get("age_h")})
    return picks, problems


def attach_desk(picks, by_text):
    """Fill p["desk"] for every lead slot. Returns problems; [] means go ahead.

    Bill and vote lines attach automatically. A petition attaches only when the spec names one
    of this slot's candidates by id, and a slot with candidates must say which (or null).
    """
    import action_desk
    desk = action_desk.Desk()
    sys.stderr.write("slack_five: %s\n" % desk.status())
    if not desk.ok:
        return []
    problems = []
    for p in picks:
        if p["depth"] != 0:
            continue
        r = desk.lookup(p["headline"], by_text.get(p["n"], ""), p["section"])
        p["desk"] = list(r["lines"])
        cands = {c["id"]: c for c in r["candidates"]}
        choice = p.get("petition", _UNSET)
        if choice is _UNSET:
            if cands:
                problems.append(
                    "%s: set \"petition\" to one of these ids, or null if none is about this "
                    "story:\n%s" % (p["n"], "\n".join(
                        "      %-6s %s (%s signers; shares: %s)"
                        % (c["id"], c["name"][:80], "{:,}".format(c["signatures"]),
                           ", ".join(c["shared"]) or "-") for c in r["candidates"])))
            continue
        if choice is None:
            continue
        try:
            choice = int(choice)
        except (TypeError, ValueError):
            problems.append("%s: petition must be an id or null, got %r" % (p["n"], choice))
            continue
        if choice not in cands:
            problems.append("%s: petition %s is not one of this slot's candidates (%s)"
                            % (p["n"], choice, ", ".join(str(i) for i in cands) or "none"))
            continue
        p["desk"].append(desk.petition_line(cands[choice]))
    for p in picks:
        p.pop("petition", None)
    return problems


def render(picks, doc_url, date_label, total):
    """Slack mrkdwn. Shape fixed by Step 10: one opening line, the five, one closing line."""
    short = re.sub(r"^https?://", "", doc_url)
    short = (short[:46] + "…/edit") if len(short) > 52 else short
    out = [":coffee: *Breakfast Briefing — %s* is out (automated): <%s|%s>"
           % (date_label, doc_url, short), "", "Top five for the UK:", ""]
    slot = 0
    for p in picks:
        link = "<%s|%s>" % (p["url"], p["headline"])
        note = p["note"].strip()
        # A note that opens lower-case is a continuation of the credit ("- spiked, on
        # Nottingham's new powers"); one that opens upper-case is its own sentence. Both
        # shapes appear in the posts Chris has kept, so honour whichever was written.
        if note:
            tail = "%s %s" % ("," if note[:1].islower() else ".", note)
        else:
            tail = "."
        if p["depth"] == 0:
            slot += 1
            out.append("%d. *%s* — %s%s" % (slot, link, p["outlet"], tail))
            for line in p.get("desk") or []:
                out.append("    ↳ %s" % line)
        else:
            out.append("    ◦ %s — %s%s" % (link, p["outlet"], tail))
    out.append("")
    out.append("%d stories across nine sections in the Doc — worth a scroll for the rest."
               % total)
    return "\n".join(out)


def pre_check(args):
    """--pre: validate the five BEFORE compose, so the Doc can open with it (02.10.2026).

    Every pick must be tier 1 in picks.json. Tier 1 is the one tier no section cap cuts, so a
    five checked here cannot later point at a story the Doc dropped. The URL check waits for
    the real run after publish, when expected_urls.txt exists for this edition.
    """
    if not args.spec:
        die("--pre needs --spec")
    picks_spec = json.load(open(args.picks, encoding="utf-8"))
    pub, tier1 = {}, set()
    for section, tiers in picks_spec.items():
        if isinstance(tiers, list):
            tiers = {"2": tiers}
        for tier, ns in tiers.items():
            for n in ns:
                pub[int(n)] = section
                if str(tier) == "1":
                    tier1.add(int(n))
    items = load_items(args.today)
    flat = flatten(json.load(open(args.spec, encoding="utf-8")))
    picks, problems = resolve(flat, items, pub, None, {})
    for p in picks:
        if p["n"] not in tier1:
            problems.append("%s: not tier 1 in %s. Make every five pick tier 1 so no cap can "
                            "cut it from the Doc: %r" % (p["n"], args.picks, p["headline"][:60]))
    if not problems and not args.no_desk:
        try:
            texts = {m["i"]: m.get("text") or "" for m in
                     json.load(open(args.leads, encoding="utf-8"))}
        except (OSError, ValueError):
            texts = {}
        problems = attach_desk(picks, texts)
    if problems:
        sys.stderr.write("slack_five --pre: %d problem(s):\n" % len(problems))
        for p in problems:
            sys.stderr.write("  %s\n" % p)
        return 1
    repeats = check_repeats(picks, load_fives())
    if repeats:
        sys.stderr.write("slack_five --pre: %d pick(s) already ran in a past five:\n"
                         % len(repeats))
        for p, past in repeats:
            sys.stderr.write("  %s  %r\n      ran %s as %r (%s)\n"
                             % (p["n"], p["headline"][:64], past["date"],
                                past["headline"][:64], past["outlet"]))
        if not args.allow_repeat:
            sys.stderr.write("slack_five --pre: refusing; --allow-repeat if deliberate.\n")
            return 1
    print(render(picks, "https://docs.google.com/document/d/(published-doc)/edit",
                 "(preview)", len(pub)))
    sys.stderr.write("slack_five --pre: OK. compose.py --five %s will open the Doc with these. "
                     "After publish, run slack_five.py with the same --spec and --doc-url.\n"
                     % args.spec)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build and validate the Slack five.")
    ap.add_argument("--spec", help="JSON spec of picks")
    ap.add_argument("--doc-url", help="the published Doc's URL")
    ap.add_argument("--today", default="/tmp/today.json")
    ap.add_argument("--composed", default=COMPOSED)
    ap.add_argument("--date", help="YYYYMMDD, defaults to today")
    ap.add_argument("--date-label", help="e.g. 'Thursday 10 September'")
    ap.add_argument("--dry-run", action="store_true",
                    help="validate and print, write no record")
    ap.add_argument("--history", action="store_true",
                    help="print what the last %d fives ran, then exit" % FIVE_HISTORY)
    ap.add_argument("--allow-repeat", action="store_true",
                    help="post anyway when a pick already ran in a past five")
    ap.add_argument("--leads", default="/tmp/leads.json",
                    help="the sheet's leads manifest; its text is shown beside any slot "
                         "that has no note, as material to write one from")
    ap.add_argument("--pre", action="store_true",
                    help="BEFORE compose: check the spec against /tmp/picks.json (every pick "
                         "must be tier 1, so no cap can cut it), settle the Action Desk "
                         "decisions and the repeat check. Writes nothing. compose.py --five "
                         "then prints the same five at the top of the Doc")
    ap.add_argument("--picks", default="/tmp/picks.json")
    ap.add_argument("--no-desk", action="store_true",
                    help="leave out the Action Desk lines (parl-monitor broken on the day)")
    args = ap.parse_args(argv)

    if args.history:
        hist = load_fives()
        if not hist:
            print("no five/ records yet - this is the first run, so nothing to compare against")
            return 0
        for h in hist:
            print("%s  %-26s %s" % (h["date"], h["outlet"][:26], h["headline"][:78]))
        return 0

    if args.pre:
        return pre_check(args)
    if not args.spec or not args.doc_url:
        die("--spec and --doc-url are both required (or use --history)")

    import datetime
    date = args.date or datetime.date.today().strftime("%Y%m%d")
    if args.date_label:
        label = args.date_label
    else:
        d = datetime.datetime.strptime(date, "%Y%m%d")
        # Not %-d: that is a glibc/BSD extension and this has to survive being run anywhere.
        label = "%s %d %s" % (d.strftime("%A"), d.day, d.strftime("%B"))

    items = load_items(args.today)
    pub = published_index(args.composed)
    exp = expected_urls()
    if exp is None:
        sys.stderr.write("slack_five: WARNING - expected_urls.txt missing or empty, so the "
                         "invented-URL check is UNAVAILABLE. Report that.\n")

    picks, problems = resolve(flatten(json.load(open(args.spec, encoding="utf-8"))),
                              items, pub, exp, published_urls(args.composed))
    if problems:
        sys.stderr.write("slack_five: %d problem(s), nothing written:\n" % len(problems))
        for p in problems:
            sys.stderr.write("  %s\n" % p)
        return 1

    try:
        by_text = {m["i"]: m.get("text") or "" for m in
                   json.load(open(args.leads, encoding="utf-8"))}
    except (OSError, ValueError):
        by_text = {}
    if not args.no_desk:
        problems = attach_desk(picks, by_text)
        if problems:
            sys.stderr.write("slack_five: %d Action Desk problem(s), nothing written:\n"
                             % len(problems))
            for p in problems:
                sys.stderr.write("  %s\n" % p)
            return 1

    # Material for empty notes (27.09.2026). Printed, never inserted: a note is the writer's
    # own words, and text copied from the manifest could carry a URL or a paywalled passage.
    try:
        by_i = {m["i"]: m for m in json.load(open(args.leads, encoding="utf-8"))}
    except (OSError, ValueError):
        by_i = {}
    for p in picks:
        if (p["note"] or "").strip():
            continue
        m = by_i.get(p["n"])
        if m and m.get("text"):
            sys.stderr.write("slack_five: %s has no note. What the sheet read (%s):\n    %s\n"
                             % (p["n"], m.get("text_from") or "text", m["text"][:420]))
        else:
            sys.stderr.write("slack_five: %s has no note, and the sheet had no text for it - "
                             "the headline is all there is.\n" % p["n"])

    leads = [p for p in picks if p["depth"] == 0]
    if not leads:
        die("no lead picks in the spec")
    if len(leads) > 6:
        sys.stderr.write("slack_five: WARNING - %d slots. Step 10 is a five; a longer list "
                         "reads as a second Doc.\n" % len(leads))

    stale = [p for p in picks if (p.get("age_h") or 0) > 36.5]
    for p in stale:
        sys.stderr.write("slack_five: WARNING - %s is %.0fh old (%s). The five leads the "
                         "channel's day; check it is still the live version.\n"
                         % (p["n"], p["age_h"], p["outlet"]))

    repeats = check_repeats(picks, load_fives())
    if repeats:
        sys.stderr.write("slack_five: %d pick(s) already ran in a past five:\n" % len(repeats))
        for p, past in repeats:
            sys.stderr.write("  %s  %r\n      ran %s as %r (%s)\n"
                             % (p["n"], p["headline"][:64], past["date"],
                                past["headline"][:64], past["outlet"]))
        if not args.allow_repeat:
            sys.stderr.write("slack_five: refusing. The Doc's rule that a running story may "
                             "run again does NOT carry over to the five - prefer a genuinely "
                             "new development. --allow-repeat if this is deliberate.\n")
            return 1
        sys.stderr.write("slack_five: --allow-repeat given: continuing.\n")

    text = render(picks, args.doc_url, label, len(pub))
    print(text)

    if args.dry_run:
        sys.stderr.write("slack_five: dry run, no record written.\n")
        return 0

    os.makedirs(FIVE_DIR, exist_ok=True)
    path = os.path.join(FIVE_DIR, "%s.json" % date)
    json.dump({"date": date, "channel": CHANNEL, "doc_url": args.doc_url,
               "doc_items": len(pub), "text": text,
               "items": [{k: p[k] for k in
                          ("n", "depth", "note", "headline", "outlet", "url", "section",
                           "paywalled", "desk")}
                         for p in picks]},
              open(path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    sys.stderr.write("slack_five: %d link(s), all published and in expected_urls.txt\n"
                     % len(picks))
    sys.stderr.write("slack_five: recorded %s\n" % os.path.relpath(path, HERE))
    sys.stderr.write("slack_five: POST THE TEXT ABOVE VERBATIM to %s. Retyping any part of "
                     "it restores the hand-copying this replaces.\n" % CHANNEL)
    return 0


if __name__ == "__main__":
    sys.exit(main())
