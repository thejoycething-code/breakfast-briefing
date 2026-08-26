#!/usr/bin/env python3
"""Record the picked stories in seen.json — AFTER the doc is published and verified.

compose.py used to do this itself, at compose time. That was the wrong moment: on
14.08.2026 the compose succeeded, marked 249 stories as published, and the upload then
produced a doc with two dead links. Had the publish failed outright, those 249 stories
would have been burned — never offered again — for a doc that did not exist. Marking is
the last step of a successful publish, not a side effect of rendering HTML.

Run compose.py with --no-mark, publish, verify the links, then run this.

    python3 mark_published.py /tmp/today.json /tmp/picks.json

Idempotent: re-running marks the same keys with a fresh timestamp and cannot double-count.
"""
import argparse
import datetime as dt
import json
import os
import sys

HERE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE_DIR)
import fetch_feeds  # url_key / load_seen / save_seen, so dedup stays consistent
from compose import ORDER, normalize_picks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json_path")
    ap.add_argument("picks_path")
    ap.add_argument("--dry-run", action="store_true",
                    help="report what would be marked, write nothing")
    ap.add_argument("--urls", metavar="PATH",
                    default=os.path.join(HERE_DIR, "expected_urls.txt"),
                    help="the composed doc's final URLs (default: expected_urls.txt)")
    args = ap.parse_args()

    items = json.load(open(args.json_path))["items"]
    # Same normalization as compose.py, so a tiered picks file reads identically here.
    picks, _ = normalize_picks(json.load(open(args.picks_path)))

    unknown = [s for s in picks if s not in ORDER]
    if unknown:
        sys.stderr.write("refusing to mark: unknown section name(s) %s\n" % unknown)
        return 2

    # Same traversal as compose.py: ORDER, de-duplicated, first occurrence wins.
    chosen = []
    seen_idx = set()
    for section in ORDER:
        for i in picks.get(section, []):
            if i not in seen_idx and 0 <= i < len(items):
                seen_idx.add(i)
                chosen.append(i)

    # Prefer compose.py's own record of what survived. picks.json is what was ASKED for;
    # composed.json is what was published, and the two differ whenever a section cap bites.
    # Marking the difference as published is what stamped 24 unpublished stories on
    # 18.08.2026 - so the cap-dropped items are retired to cut.json instead, which the sweep
    # drops outright rather than flagging (Chris: if it didn't make the first cut it is not
    # good enough for the following day).
    cut_idx = []
    composed_path = os.path.join(HERE_DIR, "composed.json")
    if os.path.exists(composed_path):
        rec = json.load(open(composed_path))
        published = [i for s in ORDER for i in rec.get("composed", {}).get(s, [])]
        cut_idx = [i for s in ORDER for i in rec.get("cut_by_cap", {}).get(s, [])]
        stale = set(published) - set(chosen)
        if stale:
            sys.stderr.write("refusing to mark: composed.json holds %d item(s) absent from "
                             "%s - it is from a different run. Re-compose, or delete it to "
                             "fall back to picks.json.\n" % (len(stale), args.picks_path))
            return 2
        chosen = published
    else:
        sys.stderr.write("warning: composed.json not found - marking every pick, including "
                         "any a section cap dropped. Re-run compose.py to get an exact "
                         "record.\n")

    # Mark BOTH the raw feed URL and the doc's final URL. compose.py's resolver mutates
    # item["url"] in place, so it recorded resolved links; this script reloads today.json
    # and sees the raw redirects. Marking only one form leaves the other unmatched, and a
    # story reappears tomorrow depending on whether that day's sweep happened to resolve
    # it — 25 of today's 249 differed between the two forms. Union, not either/or.
    keys = {fetch_feeds.url_key(items[n]["url"]) for n in chosen}
    final = []
    if args.urls and os.path.exists(args.urls):
        final = [ln.strip() for ln in open(args.urls) if ln.strip()]
        if len(final) != len(chosen):
            sys.stderr.write("warning: %s has %d URLs but picks resolve to %d stories; "
                             "marking the union anyway\n"
                             % (args.urls, len(final), len(chosen)))
        keys |= {fetch_feeds.url_key(u) for u in final}
    else:
        sys.stderr.write("warning: %s not found — marking raw feed URLs only, so a "
                         "resolved duplicate could reappear tomorrow\n" % args.urls)

    cut_keys = {fetch_feeds.url_key(items[n]["url"]) for n in cut_idx}
    cut_keys -= keys          # a story published in one section is never "cut"

    if args.dry_run:
        sys.stderr.write("would mark %d stories (%d distinct url keys) and retire %d cut "
                         "by a cap (%d url keys)\n"
                         % (len(chosen), len(keys), len(cut_idx), len(cut_keys)))
        return 0

    stamp = dt.datetime.now(dt.timezone.utc).isoformat()
    db = fetch_feeds.load_seen()
    new = sum(1 for k in keys if k not in db)
    for k in keys:
        db[k] = stamp
    # Cut stories are marked seen as well as retired: if cut.json is ever lost the sweep
    # degrades to flag-and-keep rather than silently offering them as fresh.
    for k in cut_keys:
        db[k] = stamp
    fetch_feeds.save_seen(db)

    if cut_keys:
        cut_db = fetch_feeds.load_cut()
        for k in cut_keys:
            cut_db[k] = stamp
        fetch_feeds.save_cut(cut_db)

    sys.stderr.write("marked %d stories as published (%d url keys, %d new)\n"
                     % (len(chosen), len(keys), new))
    if cut_idx:
        sys.stderr.write("retired %d story(s) cut by a section cap (%d url keys) - these "
                         "will be dropped from later sweeps, not flagged\n"
                         % (len(cut_idx), len(cut_keys)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
