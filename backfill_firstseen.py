#!/usr/bin/env python3
"""Seed firstseen.json from the archived sweeps.

Chris, 08.09.2026: "Backfill it from the archive". Without this the store starts empty, so
every dateless item looks first-seen-today and nothing ages out until tomorrow - the piece
that prompted the fix would have come back one more time. Every archived sweep records the
items that were OFFERED that day, which is precisely the population seen.json never knew
about, so the archive is the only place the true first sighting exists.

Idempotent: keeps the EARLIEST sighting per url_key, so re-running cannot move a date
forward. Dry by default.

    python3 backfill_firstseen.py            # report only
    python3 backfill_firstseen.py --write    # merge into firstseen.json
"""
import argparse
import datetime as dt
import glob
import gzip
import json
import os

import fetch_feeds

ARCHIVE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "archive")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="merge into firstseen.json")
    args = ap.parse_args()

    earliest = {}
    per_day = []
    for path in sorted(glob.glob(os.path.join(ARCHIVE, "2026*"))):
        day = os.path.basename(path)
        sweep = os.path.join(path, "sweep.json.gz")
        if not os.path.exists(sweep):
            continue
        try:
            with gzip.open(sweep, "rt", encoding="utf-8", errors="replace") as fh:
                items = (json.load(fh) or {}).get("items") or []
        except (ValueError, OSError) as exc:
            print("  %s: unreadable (%s)" % (day, exc))
            continue
        # The sweep's own run date, not now: a sighting is dated when it happened.
        stamp = dt.datetime.strptime(day, "%Y%m%d").replace(tzinfo=dt.timezone.utc).isoformat()
        n = 0
        for it in items:
            # age_h is None exactly when the item carried no publisher date - the population
            # this store exists for. Dated items already age out on their own date.
            if it.get("age_h") is not None:
                continue
            url = it.get("url") or ""
            if not url:
                continue
            key = fetch_feeds.url_key(url)
            if key not in earliest or stamp < earliest[key]:
                earliest[key] = stamp
            n += 1
        per_day.append((day, n))

    for day, n in per_day:
        print("  %s: %4d dateless item(s)" % (day, n))
    print("\n%d distinct dateless link(s) across %d edition(s)" % (len(earliest), len(per_day)))

    existing = fetch_feeds.load_firstseen()
    merged = dict(existing)
    added = moved = 0
    for k, v in earliest.items():
        if k not in merged:
            merged[k] = v
            added += 1
        elif v < merged[k]:
            merged[k] = v
            moved += 1
    print("existing store: %d | new: %d | pulled earlier: %d | result: %d"
          % (len(existing), added, moved, len(merged)))

    if not args.write:
        print("\n(dry run - pass --write to merge)")
        return 0
    fetch_feeds.save_firstseen(merged)
    print("\nwrote %s (%d entries after retention prune)"
          % (fetch_feeds.FIRSTSEEN_DB, len(fetch_feeds.load_firstseen())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
