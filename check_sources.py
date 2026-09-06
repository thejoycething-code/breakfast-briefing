#!/usr/bin/env python3
"""Source health check: which feeds are dead, and for how long.

Written 17.08.2026 after Live Action News turned out to have been unreachable for an unknown
length of time. Chris had flagged a Live Action euthanasia story as one the monitor missed;
it was not a ranking failure at all - the source had been returning HTTP 429 and nothing said
so. A dead source and a quiet news week look identical in the output, which is the whole
problem: silence is not evidence.

So this keeps a rolling record in source_health.json and reports how many CONSECUTIVE days a
source has produced nothing. One bad day is noise - a feed hiccups, a site reboots. Five in a
row is a source that has gone away and needs a new route.

    python3 check_sources.py                 # check, update history, print a report
    python3 check_sources.py --quiet         # only print problems (for the scheduled run)
    python3 check_sources.py --days 5        # what counts as "long enough to act on"

Exit status is 1 if any source has been failing for --days or more, so a scheduled run can
surface it rather than bury it.
"""

import argparse
import concurrent.futures
import datetime as dt
import json
import os
import re
import sys

import fetch_feeds

HERE = os.path.dirname(os.path.abspath(__file__))
HISTORY = os.path.join(HERE, "source_health.json")

# A challenge page is not a transient failure and never fixes itself with a retry, so it is
# worth naming separately in the report: it means "find another route", not "try again".
BOT_WALL = re.compile(r"HTTP (401|403|429)")


def probe(feed):
    """Return (name, url, ok, n_items, error). Never raises."""
    category, name, url, mode = feed[0], feed[1], feed[2], feed[3]
    try:
        raw = fetch_feeds.fetch(url)
    except Exception as exc:  # noqa: BLE001
        return name, url, mode, False, 0, str(exc)
    try:
        txt = raw.decode("utf-8", "replace")
    except Exception:  # noqa: BLE001
        return name, url, mode, False, 0, "undecodable"
    if mode.startswith("wpjson"):
        # A WordPress REST collection. Counting <item> on JSON reports every one as dead.
        try:
            n = len(fetch_feeds.parse_wpjson(raw, name))
        except Exception as exc:  # noqa: BLE001
            return name, url, mode, False, 0, "wpjson: %s" % str(exc)[:24]
        return name, url, mode, n > 0, n, "" if n else "0 items"
    if mode.startswith("scrape"):
        # Scrape sources are HTML index pages, not feeds. Counting <item> on one reports
        # every single one as dead - the first run of this check called The Spectator broken
        # on a day it had supplied eight stories.
        #
        # Counting article-shaped LINKS was the first fix and was wrong in the other
        # direction, which is how ADF International went eight editions contributing nothing
        # while this check called it healthy every morning (found 01.09.2026). Its newsroom
        # serves 773KB and 260 article links, so the link count said 260 and ok=True - but
        # the listing is JS-rendered with no <article> blocks and no datestamps, so
        # scrape_index extracted ZERO and the sweep got nothing. A proxy for "the page has
        # content" is not a measure of "the source contributes".
        #
        # So ask the extractor the sweep actually uses. By construction this can no longer
        # disagree with what the sweep sees, which is the only property that matters here.
        try:
            n = len(fetch_feeds.scrape_index(url))
        except Exception as exc:  # noqa: BLE001
            return name, url, mode, False, 0, "scrape: %s" % str(exc)[:24]
        return name, url, mode, n > 0, n, "" if n else "page fetches but yields 0 items"
    n = txt.count("<item") + txt.count("<entry")
    # A feed that parses but serves nothing is its own failure mode: the URL still 200s, so
    # nothing looks wrong, but the source has silently stopped contributing.
    return name, url, mode, n > 0, n, "" if n else "0 items"


def load_history():
    try:
        with open(HISTORY) as fh:
            return json.load(fh)
    except Exception:  # noqa: BLE001
        return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=3,
                    help="consecutive failing days before a source is called broken")
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--quiet", action="store_true", help="print only problems")
    ap.add_argument("--today", help="ISO date override (the scripts cannot call date.today "
                                    "in some contexts; mostly for testing)")
    args = ap.parse_args()

    today = args.today or dt.date.today().isoformat()
    feeds = fetch_feeds.load_feeds()[0]
    hist = load_history()

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for r in pool.map(probe, feeds):
            results.append(r)

    broken, walled, recovered = [], [], []
    for name, url, mode, ok, n, err in results:
        rec = hist.get(url) or {"name": name, "fails": 0, "since": None, "last_error": ""}
        rec["name"] = name
        if ok:
            if rec["fails"] >= args.days:
                recovered.append((name, rec["fails"]))
            rec["fails"] = 0
            rec["since"] = None
            rec["last_error"] = ""
            rec["last_ok"] = today
        else:
            # Only count one failure per day, so re-running the check does not inflate it.
            if rec.get("last_checked") != today:
                rec["fails"] = rec.get("fails", 0) + 1
            rec["since"] = rec.get("since") or today
            rec["last_error"] = err
            if rec["fails"] >= args.days:
                (walled if BOT_WALL.search(err) else broken).append(
                    (name, rec["fails"], rec["since"], err, mode))
        rec["last_checked"] = today
        hist[url] = rec

    # Drop records for feeds that have left the list.
    #
    # Added 06.09.2026. This probes only the URLs load_feeds() returns today, so a record for
    # a retired URL is never updated, never reported and never in the exit code - it just
    # sits at whatever it last was. Sixteen had built up, three frozen at fails=3, including
    # Live Action News on its old liveaction.org/news/feed route. All three were fine on a
    # new route, but reading the file by hand said they were three days dead: the one file
    # you open to ask "has a source gone quiet?" was misreporting exactly that.
    #
    # This discards a retired feed's history, which is the right trade - a record nothing
    # probes is not history, and it rebuilds from fails=0 if the URL ever comes back.
    probed = {r[1] for r in results}
    pruned = sorted((hist[u].get("name") or "?", u) for u in set(hist) - probed)
    for _name, url in pruned:
        del hist[url]

    try:
        with open(HISTORY, "w") as fh:
            json.dump(hist, fh, indent=1, sort_keys=True)
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write("could not write %s: %s\n" % (HISTORY, exc))

    live = sum(1 for r in results if r[3])
    if not args.quiet:
        print("%d sources checked, %d returned items, %d did not"
              % (len(results), live, len(results) - live))

    if walled:
        print("\nBLOCKED - the site refuses automated access. Retrying will not help; these "
              "need a different route or an accepted gap:")
        for name, fails, since, err, mode in sorted(walled, key=lambda x: -x[1]):
            print("  %-32s %-14s failing %d day(s), since %s" % (name, err, fails, since))
    if broken:
        print("\nBROKEN - failing for %d+ consecutive days:" % args.days)
        for name, fails, since, err, mode in sorted(broken, key=lambda x: -x[1]):
            print("  %-32s %-24s failing %d day(s), since %s"
                  % (name, err[:24], fails, since))
    if recovered:
        print("\nRECOVERED since the last check:")
        for name, was in recovered:
            print("  %-32s (had been failing %d day(s))" % (name, was))
    # Unconditional, like walled/broken/recovered above: a record leaving the health file is
    # a change to the file you would check for a silent source, so it must not be silent.
    if pruned:
        print("\nPRUNED - %d record(s) for feed(s) no longer in the list:" % len(pruned))
        for name, url in pruned:
            print("  %-32s %s" % (name[:32], url[:70]))
    if not (walled or broken) and not args.quiet:
        print("\nNo source has been failing for %d+ days." % args.days)

    return 1 if (walled or broken) else 0


if __name__ == "__main__":
    sys.exit(main())
