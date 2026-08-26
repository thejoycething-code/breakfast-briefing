#!/usr/bin/env python3
"""Fill in missing bylines on picked items by reading the article page.

Chris flagged two commentary pieces in the 17.08.2026 edition that ran with no author
("Why is Cambridge platforming Islamic creationism?" — Andrew Gilligan; the Telegraph's
drag-queens column — Michael Deacon) and made the general point: "Spectator articles will
almost always have an author."

He is right, and the gap is structural rather than occasional. The Spectator has no RSS
anywhere, so it is index-scraped, and an index page carries headline, link and date but no
byline. Every Spectator item therefore arrives author-less. On the 17.08 edition that was
8 of the 13 commentary picks missing a byline.

The fix is to fetch the article itself for picked items only — the same shape as resolve.py,
and for the same reason: it is far too slow to do for a whole sweep, but 13 pages is seconds.
Results cache in authors.json so a rebuild of the same edition costs nothing.

LIMIT, and it is not fixable here: an item whose only URL is an unresolved news.google.com
redirect has no page to read. Telegraph, Times and WORLD reach us that way. For those,
bylines.txt takes a manual line — that is what Chris's own corrections land in.
"""

import concurrent.futures
import json
import os
import re
import sys

import fetch_feeds

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "authors.json")
OVERRIDES = os.path.join(HERE, "bylines.txt")

# Ordered best-first: a JSON-LD "author" object is far more reliable than a meta tag, which
# some CMSs fill with the section name or the publication itself.
PATTERNS = [
    r'"author"\s*:\s*\{[^}]*?"name"\s*:\s*"([^"]{2,60})"',
    r'"author"\s*:\s*\[\s*\{[^}]*?"name"\s*:\s*"([^"]{2,60})"',
    r'<meta[^>]+?name=["\']author["\'][^>]+?content=["\']([^"\']{2,60})["\']',
    r'<meta[^>]+?content=["\']([^"\']{2,60})["\'][^>]+?name=["\']author["\']',
    r'<meta[^>]+?property=["\']article:author["\'][^>]+?content=["\']([^"\']{2,60})["\']',
    r'"author"\s*:\s*"([^"]{2,60})"',
    r'\brel=["\']author["\'][^>]*>\s*([A-Z][\w.\'-]+(?: [A-Z][\w.\'-]+){1,3})\s*<',
]

# Things that look like a byline but are not one. Without this the Cosmos Institute feed
# yields "Cosmos Institute" as its own author, and several CMSs return "Staff" or "Editor".
NOT_A_BYLINE = re.compile(
    r"^\s*(staff|editor|editorial|admin|newsroom|news ?desk|guest|contributor|"
    r"correspondent|the [a-z ]+ team|press association|\w+ reporter|"
    # single-word section labels a CMS can leave in the author slot
    r"news|opinion|comment|home|features|world|politics|sport|business|"
    r"unknown|anonymous|author|writer|team|web ?team|wire|agencies|reuters|"
    r"associated press|\w+ ?desk)\s*$", re.I)


def _plausible(name, outlet=""):
    """A byline is two-to-four capitalised words that are not the outlet's own name."""
    name = re.sub(r"\s+", " ", (name or "").replace("&amp;", "&")).strip().strip(",;|")
    if not name or len(name) > 60 or "@" in name or name.startswith("http"):
        return None
    if NOT_A_BYLINE.match(name):
        return None
    # Strip a leading "By ".
    name = re.sub(r"^by\s+", "", name, flags=re.I).strip()
    # Some bylines carry a wire credit: "Tessa Gervasini/EWTN News". Keep the person.
    if "/" in name:
        head = name.split("/")[0].strip()
        if len(head.split()) >= 2:
            name = head
    words = name.split()
    # One word is allowed: the Spectator's diary runs under the pseudonym "Steerpike", and
    # a 2-word minimum silently dropped it. NOT_A_BYLINE below is what keeps single-word
    # junk ("Staff", "Opinion") out - the word count cannot do that job.
    # Up to six words, because two-author bylines are normal ("Scott Winship and Kevin
    # Corinth"). A 4-word cap rejected those outright.
    if not 1 <= len(words) <= 6:
        return None
    if any(ch.isdigit() for ch in name):
        return None
    # Every word must be capitalised EXCEPT the joiners and name particles that legitimately
    # appear lowercase - "and", and the "de/van/bin" in a surname.
    JOINERS = {"and", "&", "of", "de", "del", "der", "van", "von", "la", "le", "da",
               "di", "bin", "al", "the"}
    if not all(w[:1].isupper() for w in words
               if w[:1].isalpha() and w.lower() not in JOINERS):
        return None
    # ...but it cannot be joiners alone, and must start with a capital.
    if not name[:1].isupper():
        return None
    # "The Spectator" as the author of a Spectator piece is the CMS being unhelpful.
    if outlet and name.lower() in outlet.lower():
        return None
    return name


def byline(html, outlet=""):
    for pat in PATTERNS:
        for hit in re.findall(pat, html, re.I | re.S):
            got = _plausible(hit, outlet)
            if got:
                return got
    return None


def load_overrides(path=OVERRIDES):
    """'match | Author' per line; match is a case-insensitive substring of URL or headline.

    For the articles no fetch can reach — Chris tells me the author, and it sticks.
    """
    out = []
    if not os.path.exists(path):
        return out
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "|" not in line:
                continue
            match, _, name = line.partition("|")
            if match.strip() and name.strip():
                out.append((match.strip().lower(), name.strip()))
    return out


def _load_cache():
    try:
        with open(CACHE) as fh:
            return json.load(fh)
    except Exception:  # noqa: BLE001
        return {}


def enrich(items, workers=8, use_cache=True, is_commentary=None):
    """Fill item['author'] in place. Returns (filled, overridden, unreachable)."""
    overrides = load_overrides()
    cache = _load_cache() if use_cache else {}

    def needs(it):
        return not (it.get("author") or "").strip()

    filled = overridden = 0
    todo = []
    for it in items:
        if not needs(it):
            continue
        hay = ((it.get("url") or "") + " " + (it.get("headline") or "")).lower()
        for match, name in overrides:
            if match in hay:
                it["author"] = name
                # A hand-written byline is Chris saying "this is a comment piece and here is
                # who wrote it". is_commentary() cannot see that: the Telegraph column he
                # flagged reaches us as a Google redirect, so there is no /opinion/ in the
                # URL and the Telegraph is not a commentary-only outlet. Without this flag
                # credit() silently drops the very name he supplied.
                it["byline_forced"] = True
                overridden += 1
                break
        else:
            if is_commentary is not None and not is_commentary(it):
                continue
            todo.append(it)

    # No page to read: the item is only a Google News redirect.
    unreachable = [it for it in todo if "news.google.com" in (it.get("url") or "")]
    fetchable = [it for it in todo if it not in unreachable]

    hits = {}
    for it in list(fetchable):
        u = it["url"]
        if u in cache:
            if cache[u]:
                it["author"] = cache[u]
                filled += 1
            fetchable.remove(it)

    def work(it):
        try:
            html = fetch_feeds.fetch(it["url"]).decode("utf-8", "replace")
        except Exception:  # noqa: BLE001
            return it["url"], None
        return it["url"], byline(html, it.get("outlet") or "")

    if fetchable:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            for url, name in pool.map(work, fetchable):
                hits[url] = name
        for it in fetchable:
            name = hits.get(it["url"])
            if name:
                it["author"] = name
                filled += 1

    if use_cache and hits:
        cache.update(hits)
        try:
            with open(CACHE, "w") as fh:
                json.dump(cache, fh, indent=0, sort_keys=True)
        except Exception:  # noqa: BLE001
            pass

    return filled, overridden, len(unreachable)


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        try:
            page = fetch_feeds.fetch(arg).decode("utf-8", "replace")
            print("%s -> %s" % (arg, byline(page)))
        except Exception as exc:  # noqa: BLE001
            print("%s -> FAILED (%s)" % (arg, exc))
