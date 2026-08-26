#!/usr/bin/env python3
"""Write the day's judgement into tiers.json, so a later pass need not re-derive it.

    python3 shortlist.py /tmp/today.json --sheet --leads-json /tmp/leads.json > /tmp/sheet.txt
    ...
    python3 record_tiers.py /tmp/leads.json /tmp/picks.json [--reasons /tmp/reasons.json]

Records every LEAD the sheet showed, not just the picks:

    tier 1/2/3   as filed in picks.json
    tier 0       on the sheet, not picked - the explicit "considered and rejected"

Tier 0 is the reason this exists. Without it a re-run cannot tell a story it rejected from
one it never saw, so it re-reads the whole day. With it, `shortlist.py --sheet --new-only`
emits just the leads that are genuinely new or whose text has changed.

Takes the LEADS MANIFEST rather than the sweep, so it cannot disagree with the sheet about
what counted as a lead. Rebuilding that list here would mean two copies of the clustering
and section logic, and the day they drift is the day stories go silently unrecorded and
stay "new" forever.

Run it alongside archive_day.py, i.e. only after a verified publish - the same rule, for the
same reason. Recording tiers for a draft that never shipped would suppress those stories from
tomorrow's --new-only sheet on the strength of a judgement nobody acted on.

--reasons takes an optional {"<item index>": "one line"} sidecar. compose.py never sees it,
so adding notes cannot break a build. Most stories will never have one and that is fine.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tiers  # noqa: E402


def tier_map(picks):
    """index -> tier, from picks.json in either the tiered or the old flat format."""
    out = {}
    for _section, spec in picks.items():
        if isinstance(spec, dict):
            for t, idxs in spec.items():
                for n in idxs:
                    out[n] = int(t)
        else:
            for n in spec:
                out[n] = 2
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("leads_path", help="the manifest from shortlist.py --leads-json")
    ap.add_argument("picks_path")
    ap.add_argument("--reasons", help="optional {index: reason} sidecar")
    ap.add_argument("--date", default="", help="YYYYMMDD stamp to record against")
    ap.add_argument("--db", default=tiers.TIERS_DB)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    leads = json.load(open(args.leads_path))
    tmap = tier_map(json.load(open(args.picks_path)))
    reasons = {}
    if args.reasons and os.path.exists(args.reasons):
        reasons = {int(k): v for k, v in json.load(open(args.reasons)).items()}

    db = tiers.load(args.db)
    before = len([k for k in db if k != "__schema__"])
    n0 = n123 = 0
    for ld in leads:
        t = tmap.get(ld["i"], 0)
        rec = {"tier": int(t), "text_id": ld.get("text_id", "none")}
        r = reasons.get(ld["i"])
        if r:
            rec["reason"] = r
        for k in ("section", "headline", "outlet"):
            if ld.get(k):
                rec[k] = ld[k]
        if args.date:
            rec["date"] = args.date
        db[ld["key"]] = rec
        n123 += 1 if t else 0
        n0 += 0 if t else 1
    if not args.dry_run:
        tiers.save(db, args.db)
    after = len([k for k in db if k != "__schema__"])
    sys.stderr.write(
        "%s %d lead(s): %d picked (tier 1-3), %d considered and passed over (tier 0). "
        "store %d -> %d stories.\n"
        % ("would record" if args.dry_run else "recorded",
           len(leads), n123, n0, before, after))
    return 0


if __name__ == "__main__":
    sys.exit(main())
