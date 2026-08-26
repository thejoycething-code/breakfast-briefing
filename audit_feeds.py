#!/usr/bin/env python3
"""Per-feed yield audit: where do the day's candidates actually come from, and what is
being thrown away before anyone sees it?

Chris, 13.08.2026: "Is 737 candidates correct? I'd have thought those feeds would generate
thousands? How are we truncating media like the BBC and the Mail?" That is a question the
sweep could not answer, because it reports only what survived. This reports the losses.

For every configured feed it shows four numbers:

    feed    items the feed served at all
    dated   items carrying a usable date (undated ones are kept as "new" by the sweep)
    win     items inside the freshness window
    pass    items that also cleared the keyword filter, for feeds in `filter` mode

The gap between `win` and `pass` is the keyword filter's cost, and the gap between `feed`
and `win` is feed depth - a high-volume outlet whose RSS holds 40 items cannot tell you what
it published 30 hours ago, however wide the window is set.

    python3 audit_feeds.py                 # every feed, sorted by what the filter drops
    python3 audit_feeds.py --hours 36
    python3 audit_feeds.py --mainstream    # just the big generalist outlets
"""

import argparse
import concurrent.futures as futures
import datetime as dt
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_feeds as f

MAINSTREAM = ("bbc", "guardian", "telegraph", "times", "mail", "independent", "express",
              "mirror", "sun", "metro", "sky", "itv", "gb news", "spectator", "new york",
              "washington", "cnn", "fox", "nbc", "cbs", "abc", "reuters", "associated",
              "politico", "hill", "axios", "newsweek", "usa today", "wall street")


def audit_one(entry, hours):
    name, target, mode = entry[1], entry[2], entry[3]
    row = {"name": name, "mode": mode, "feed": 0, "dated": 0, "win": 0,
           "pass": 0, "note": ""}
    if mode in ("gnews", "gnewsf", "bing", "bingf", "scrape", "scrapesrc",
                "scrapesrcf", "disable", "block"):
        row["note"] = "via %s" % mode        # constructed URLs, not a fixed feed
        return row
    try:
        items = f.parse_feed(f.fetch(target, retry_uas=2))
    except Exception as exc:                 # noqa: BLE001
        row["note"] = "unreachable: %s" % str(exc)[:40]
        return row
    now = dt.datetime.now(dt.timezone.utc)
    row["feed"] = len(items)
    for it in items:
        d = it.get("date")
        if not isinstance(d, dt.datetime):
            continue
        row["dated"] += 1
        age = (now - d).total_seconds() / 3600.0
        if -2880 <= age <= hours:            # future dates are clamped by the sweep
            row["win"] += 1
            if f.KEYWORD_RE.search(it.get("title") or ""):
                row["pass"] += 1
    if mode == "pass":
        row["pass"] = row["win"]             # unfiltered: everything in-window counts
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=int, default=36)
    ap.add_argument("--mainstream", action="store_true")
    ap.add_argument("--workers", type=int, default=12)
    args = ap.parse_args()

    feeds, _, _ = f.load_feeds()
    if args.mainstream:
        feeds = [x for x in feeds if any(m in x[1].lower() for m in MAINSTREAM)]

    rows = []
    with futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for row in pool.map(lambda e: audit_one(e, args.hours), feeds):
            rows.append(row)

    live = [r for r in rows if r["feed"]]
    tot_feed = sum(r["feed"] for r in live)
    tot_win = sum(r["win"] for r in live)
    tot_pass = sum(r["pass"] for r in live)
    filtered = [r for r in live if r["mode"] == "filter"]
    fw = sum(r["win"] for r in filtered)
    fp = sum(r["pass"] for r in filtered)

    print("%d feeds audited (%d served items, %d constructed/other)"
          % (len(rows), len(live), len(rows) - len(live)))
    print("items served by all feeds          %5d" % tot_feed)
    print("  inside the %dh window            %5d   (%d lost to feed depth)"
          % (args.hours, tot_win, tot_feed - tot_win))
    print("  surviving the keyword filter     %5d   (%d dropped by keywords)"
          % (tot_pass, tot_win - tot_pass))
    if fw:
        print("\nkeyword filter, on the %d 'filter' feeds only: %d of %d in-window items "
              "pass (%.0f%%)" % (len(filtered), fp, fw, 100.0 * fp / fw))

    print("\nBiggest keyword-filter losses (in-window items dropped):")
    for r in sorted(live, key=lambda r: -(r["win"] - r["pass"]))[:18]:
        if r["win"] - r["pass"] <= 0:
            break
        print("  %-34s %-7s feed=%-4d win=%-4d pass=%-4d dropped=%d"
              % (r["name"][:34], r["mode"], r["feed"], r["win"], r["pass"],
                 r["win"] - r["pass"]))

    shallow = [r for r in live if r["feed"] and r["win"] == r["feed"] and r["feed"] >= 20]
    if shallow:
        print("\nFeeds where EVERY served item is inside the window - the feed is probably "
              "truncating\nolder stories, so the real %dh output is larger than this:"
              % args.hours)
        for r in sorted(shallow, key=lambda r: -r["feed"])[:12]:
            print("  %-34s %-7s feed=%-4d all within window" % (r["name"][:34], r["mode"],
                                                                r["feed"]))

    bad = [r for r in rows if r["note"].startswith("unreachable")]
    if bad:
        print("\nUnreachable (%d):" % len(bad))
        for r in bad:
            print("  %-34s %s" % (r["name"][:34], r["note"]))


if __name__ == "__main__":
    main()
