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


# The article's OWN section, from structured markup rather than page text. Chris, 28.08.2026:
# Brussels Signal's "From Pakistan to Nigeria" is a comment piece whose byline was dropped,
# and the masthead cannot be listed as commentary because the same sweep carries its straight
# news. Read here because this is where the page is already open.
#
# Ordered most reliable first, and body class LAST: it is a WordPress convention rather than a
# standard, but it is the only marker brusselssignal.eu actually publishes.
SECTION_META = re.compile(
    r'<meta[^>]+?(?:property|name)=["\']article:section["\'][^>]+?'
    r'content=["\']([^"\']{2,40})["\']', re.I)
SECTION_META_REV = re.compile(
    r'<meta[^>]+?content=["\']([^"\']{2,40})["\'][^>]+?'
    r'(?:property|name)=["\']article:section["\']', re.I)
SECTION_LD = re.compile(r'"articleSection"\s*:\s*"([^"]{2,40})"', re.I)
SECTION_BODYCLASS = re.compile(r'<body[^>]*\bclass=["\']([^"\']{0,400})["\']', re.I)


def page_section(html):
    """The article's own section, lowercased, or None when the page declares none.

    None is a real answer and must not be read as either "news" or "comment": most sites
    publish no marker at all, and guessing from page TEXT is what was measured and rejected -
    the word "Opinion" in a site's nav menu is indistinguishable from its section label once
    the HTML is stripped.
    """
    for rx in (SECTION_META, SECTION_META_REV, SECTION_LD):
        m = rx.search(html or "")
        if m:
            return m.group(1).strip().lower()
    m = SECTION_BODYCLASS.search(html or "")
    if m:
        cats = re.findall(r"\bcategory-([a-z0-9-]{2,30})\b", m.group(1), re.I)
        if cats:
            return cats[0].lower()
    return None


def enrich(items, workers=8, use_cache=True, is_commentary=None):
    """Fill item['author'] and item['_page_section'] in place.

    Returns (filled, overridden, unreachable).

    `is_commentary` is accepted and DELIBERATELY NOT used to skip fetching any more. It used
    to gate which pages were opened at all, which made the whole thing circular once the
    commentary decision started depending on the page: compose asked "is this commentary?" to
    decide whether to look, and the answer was on the page it had declined to open. Fetch
    first, decide after. On the 28.08.2026 picks that is 123 pages rather than 13 - every
    picked item that is missing a byline, which is the set worth opening regardless.
    """
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
            todo.append(it)

    # No page to read: the item is only a Google News redirect.
    unreachable = [it for it in todo if "news.google.com" in (it.get("url") or "")]
    fetchable = [it for it in todo if it not in unreachable]

    hits = {}
    for it in list(fetchable):
        u = it["url"]
        if u in cache:
            # Legacy entries are a bare name (or None); current ones carry the section too.
            entry = cache[u]
            name, sect = ((entry.get("author"), entry.get("section"))
                          if isinstance(entry, dict) else (entry, None))
            if name:
                it["author"] = name
                filled += 1
            if sect:
                it["_page_section"] = sect
            fetchable.remove(it)

    def work(it):
        try:
            html = fetch_feeds.fetch(it["url"]).decode("utf-8", "replace")
        except Exception:  # noqa: BLE001
            return it["url"], None, None
        return it["url"], byline(html, it.get("outlet") or ""), page_section(html)

    if fetchable:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            for url, name, sect in pool.map(work, fetchable):
                hits[url] = {"author": name, "section": sect}
        for it in fetchable:
            got = hits.get(it["url"]) or {}
            if got.get("author"):
                it["author"] = got["author"]
                filled += 1
            if got.get("section"):
                it["_page_section"] = got["section"]

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
