#!/usr/bin/env python3
"""Archive one edition's sweep, picks and published set — the ranking evaluation corpus.

Every edition produces something no other part of this pipeline keeps: an ordinal judgement
of ~1,000 stories. Tier 1/2/3 for the picks, nothing for the rest. That is a labelled
dataset, and until 18.08.2026 all of it was discarded by morning — /tmp/today.json and
/tmp/picks.json are ephemeral, composed.json is overwritten by the next run.

So every scoring change in this codebase has been argued from a single remembered example
(the papal letter above the jailed publisher; four Life stories at 53rd to 88th). testcases.txt
fixed that for classification and for ranking AXIOMS via ABOVE pairs, but an ABOVE pair cannot
express "this was the bigger story that day" - only a real day, with real labels, can.

Archiving is cheap and the corpus compounds: ~320KB a day, so a year of editions is ~115MB and
answers questions no fixture can. Run it after mark_published.py, i.e. only for editions that
actually published.

    python3 archive_day.py /tmp/today.json /tmp/picks.json

Writes archive/<YYYYMMDD>/{sweep.json.gz, picks.json, composed.json, manifest.json}. The date
comes from the sweep's own "generated" stamp, not the clock, so backfilling an older sweep
files it correctly. Refuses to overwrite an existing day without --force.
"""
import argparse
import datetime as dt
import gzip
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ARCHIVE = os.path.join(HERE, "archive")


def day_stamp(data):
    """YYYYMMDD from the sweep's own generated timestamp, falling back to today."""
    gen = data.get("generated") or ""
    try:
        return dt.datetime.fromisoformat(gen).strftime("%Y%m%d")
    except ValueError:
        return dt.date.today().strftime("%Y%m%d")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json_path", help="the sweep JSON (usually /tmp/today.json)")
    ap.add_argument("picks_path", help="the picks JSON (usually /tmp/picks.json)")
    ap.add_argument("--composed", default=os.path.join(HERE, "composed.json"),
                    help="compose.py's record of what published (default: composed.json)")
    ap.add_argument("--date", help="override the archive date (YYYYMMDD)")
    ap.add_argument("--leads", default="/tmp/leads.json",
                    help="the leads manifest from shortlist.py --leads-json. Archived as "
                         "judged.json: every lead with its tier, INCLUDING tier 0 for the "
                         "ones considered and passed over. picks.json alone records only "
                         "the yeses, so a replay cannot tell a rejected story from an "
                         "unseen one - which is the difference between scoring judgement "
                         "and scoring recall")
    ap.add_argument("--reasons", default="/tmp/reasons.json",
                    help="optional {index: reason} sidecar, archived alongside")
    ap.add_argument("--force", action="store_true", help="overwrite an existing archived day")
    ap.add_argument("--archive-dir", default=ARCHIVE,
                    help="where to write (default: archive/; overridden by the fixture)")
    args = ap.parse_args()
    archive_root = args.archive_dir

    data = json.load(open(args.json_path))
    picks_raw = json.load(open(args.picks_path))
    stamp = args.date or day_stamp(data)
    dest = os.path.join(archive_root, stamp)

    if os.path.exists(dest) and not args.force:
        sys.stderr.write("archive/%s already exists - pass --force to replace it\n" % stamp)
        return 2
    os.makedirs(dest, exist_ok=True)

    # The full sweep, not a reduced copy. A future scoring idea may need a field today's
    # scorer ignores - summaries were dead weight for weeks and are now the sheet's text -
    # and re-deriving a corpus is impossible once the sweep is gone.
    with open(args.json_path, "rb") as src, gzip.open(
            os.path.join(dest, "sweep.json.gz"), "wb", compresslevel=9) as out:
        shutil.copyfileobj(src, out)
    json.dump(picks_raw, open(os.path.join(dest, "picks.json"), "w"), indent=1)

    composed = None
    if os.path.exists(args.composed):
        composed = json.load(open(args.composed))
        json.dump(composed, open(os.path.join(dest, "composed.json"), "w"), indent=1)
    else:
        sys.stderr.write("warning: %s not found - archiving without the published set, so "
                         "this day cannot distinguish cap-cut picks from published ones\n"
                         % args.composed)

    # judged.json: the full labelled set, tier 0 included. This is the file a replay wants -
    # picks.json is the yeses only, and "not in picks" conflates "rejected" with "never a
    # lead", which are different labels and only one of them is a judgement.
    judged = None
    if os.path.exists(args.leads):
        leads = json.load(open(args.leads))
        tmap = {}
        for _s, spec in picks_raw.items():
            if isinstance(spec, dict):
                for t, idxs in spec.items():
                    for n in idxs:
                        tmap[n] = int(t)
            else:
                for n in spec:
                    tmap[n] = 2
        reasons = {}
        if os.path.exists(args.reasons):
            reasons = {int(k): v for k, v in json.load(open(args.reasons)).items()}
        judged = []
        for ld in leads:
            rec = dict(ld)
            rec["tier"] = tmap.get(ld["i"], 0)
            if reasons.get(ld["i"]):
                rec["reason"] = reasons[ld["i"]]
            judged.append(rec)
        json.dump(judged, open(os.path.join(dest, "judged.json"), "w"))
    else:
        sys.stderr.write("warning: %s not found - archiving without judged.json, so this "
                         "day records which stories were picked but not which were read "
                         "and passed over\n" % args.leads)

    tiered = any(isinstance(v, dict) for v in picks_raw.values())
    n_picked = sum(len(v) if isinstance(v, list) else sum(len(x) for x in v.values())
                   for v in picks_raw.values())
    manifest = {
        "date": stamp,
        "generated": data.get("generated"),
        "window_hours": data.get("window_hours"),
        "items": len(data.get("items", [])),
        "picked": n_picked,
        "tiered": tiered,
        "published": sum(len(v) for v in (composed or {}).get("composed", {}).values())
                     if composed else None,
        "cut_by_cap": sum(len(v) for v in (composed or {}).get("cut_by_cap", {}).values())
                      if composed else None,
        "feed_errors": len(data.get("errors", []) or []),
        "leads_judged": len(judged) if judged is not None else None,
        "reasons_given": sum(1 for r in judged if r.get("reason")) if judged else 0,
    }
    json.dump(manifest, open(os.path.join(dest, "manifest.json"), "w"), indent=1)

    kb = sum(os.path.getsize(os.path.join(dest, f)) for f in os.listdir(dest)) / 1024.0
    sys.stderr.write("archived %s: %d items, %d picked%s, %.0fKB -> archive/%s\n"
                     % (stamp, manifest["items"], n_picked,
                        " (tiered)" if tiered else " (flat, no tiers)", kb, stamp))
    return 0


if __name__ == "__main__":
    sys.exit(main())
