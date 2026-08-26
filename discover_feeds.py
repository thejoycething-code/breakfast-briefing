#!/usr/bin/env python3
"""Find real RSS feeds for outlets that only reached us via Google News.

Every Google News item carries its publisher's domain in <source url>. This takes
those domains and looks for the outlet's own feed — first by reading the <link
rel="alternate"> tags on its front page, then by trying common feed paths — and
verifies each candidate actually parses with items in it.

    python3 discover_feeds.py sweep.json            # report what it finds
    python3 discover_feeds.py sweep.json --write    # append working feeds to extra_feeds.txt

Adding these does not replace the Google News feeds: those stay as the safety net
for outlets that publish no feed at all.
"""

import argparse
import concurrent.futures as futures
import html as html_mod
import json
import os
import re
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_feeds

HERE = os.path.dirname(os.path.abspath(__file__))
EXTRA = os.path.join(HERE, "extra_feeds.txt")

FEED_LINK = re.compile(
    r'<link[^>]+type=["\']application/(?:rss|atom)\+xml["\'][^>]*>', re.I)
HREF = re.compile(r'href=["\']([^"\']+)["\']', re.I)
COMMON = ["/feed/", "/rss", "/rss.xml", "/feed.xml", "/index.xml", "/atom.xml",
          "/feeds/all.rss", "/news/feed/", "/rss/news.xml", "/?feed=rss2"]

# Aggregators, syndication mills and sites we deliberately never cite.
SKIP_DOMAINS = (
    "news.google.com", "msn.com", "yahoo.com", "einnews.com", "einpresswire.com",
    "facebook.com", "x.com", "twitter.com", "reddit.com", "flipboard.com",
    "newsbreak.com", "tradingview.com", "devdiscourse.com", "phys.org",
    "snopes.com", "beliefnet.com", "film-book.com", "legis1.com",
)


def candidates(domain):
    """Feed URLs to try for a domain, best guess first."""
    out = []
    for scheme_host in ("https://%s" % domain, "https://www.%s" % domain):
        try:
            html = fetch_feeds.fetch(scheme_host + "/", retry_uas=1)
        except Exception:  # noqa: BLE001
            continue
        doc = html.decode("utf-8", "replace")
        for tag in FEED_LINK.findall(doc)[:6]:
            m = HREF.search(tag)
            if m:
                href = html_mod.unescape(m.group(1))
                out.append(urllib.parse.urljoin(scheme_host + "/", href))
        break                                   # front page reachable; stop here
    out += ["https://%s%s" % (domain, p) for p in COMMON]
    seen, uniq = set(), []
    for u in out:
        if u not in seen:
            seen.add(u)
            uniq.append(u)
    return uniq[:12]


def find_feed(domain):
    for url in candidates(domain):
        try:
            entries = fetch_feeds.parse_feed(fetch_feeds.fetch(url, retry_uas=1))
        except Exception:  # noqa: BLE001
            continue
        dated = [e for e in entries if e.get("date")]
        if len(entries) >= 3 and dated:
            return url, len(entries)
    return None, 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json_path")
    ap.add_argument("--write", action="store_true",
                    help="append the working feeds to extra_feeds.txt")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    items = json.load(open(args.json_path))["items"]
    existing = open(EXTRA).read() + open(fetch_feeds.OPML).read()

    names, order = {}, []
    for it in items:
        if "news.google.com" not in it["url"]:
            continue
        dom = (it.get("publisher") or "").lower()
        if not dom or any(s in dom for s in SKIP_DOMAINS):
            continue
        if dom in existing:                      # already a source
            continue
        if dom not in names:
            names[dom] = it["outlet"] or dom
            order.append(dom)
    if args.limit:
        order = order[: args.limit]

    print("Google News publishers not yet subscribed directly: %d" % len(order))
    found, missing = [], []
    with futures.ThreadPoolExecutor(max_workers=12) as pool:
        for dom, (url, n) in zip(order, pool.map(find_feed, order)):
            (found if url else missing).append((dom, names[dom], url, n))

    print("feeds found: %d | none found: %d" % (len(found), len(missing)))
    for dom, name, url, n in found:
        print("  OK  %-34s %-58s %d items" % (name[:34], url[:58], n))

    if args.write and found:
        with open(EXTRA, "a") as fh:
            fh.write("\n# --- feeds for outlets that previously only reached us via "
                     "Google News ------\n")
            fh.write("# Discovered by discover_feeds.py on the 12.08.2026 round-up. The\n"
                     "# corresponding gnews/gnewsf entries above are deliberately kept: "
                     "they stay\n# as the safety net for outlets with no feed of their own.\n"
                     "# All are `filter` (keyword-matched) because most are general or "
                     "local news;\n# flip any single-issue outlet to `pass` if it is being "
                     "under-collected.\n")
            for dom, name, url, n in found:
                fh.write("filter | Media: US and World     | %-26s | %s\n"
                         % (name[:26].replace("|", "-"), url))
        print("\nappended %d feeds to extra_feeds.txt" % len(found))
        print("not found (still Google-only): %s"
              % ", ".join(d for d, _, _, _ in missing[:25]))


if __name__ == "__main__":
    main()
