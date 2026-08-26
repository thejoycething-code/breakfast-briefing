#!/usr/bin/env python3
"""Turn a Google News redirect into the publisher's own URL.

Two strategies, in this order:

1. **Ask Google.** The redirect page carries three signed parameters
   (`data-n-a-sg`, `data-n-a-ts`, `data-n-a-id`); POSTing them to
   news.google.com/_/DotsSplashUi/data/batchexecute returns the publisher URL
   Google itself would send the reader to. This is authoritative, not a guess.

   The docstring here used to say this route was dead, and on 18.08.2026 that was
   re-tested against a whole published edition: 114 of 114 redirects decoded, every
   one of them exactly right. What had been lost is the *signature* step — the old
   trick decoded the base64 in the URL, which genuinely stopped working; sending the
   page's own sg/ts triple does not.

   It is worth more than the hit rate suggests, because it is the only route that
   works for the two hardest cases:
     - Hosts that refuse our fetch (wng.org, telegraph.co.uk, thetimes.com,
       premierchristian.news, aei.org, liveaction.org...). The decode happens on
       Google's side, so a publisher blocking robots no longer costs us the link.
     - URLs no slug pattern can construct. wng.org files at
       /sift/<slug>-1786981243 with an opaque numeric suffix; Chris had to supply
       one of those by hand on 13.08.2026. Decoding returns it for free.

   A decoded URL is NOT passed through confirms(). Verification exists to catch a
   *guess*, and applying it here would throw away correct answers for exactly the
   blocked hosts this route was added to rescue.

2. **Guess and verify** (the original path, now a fallback). The feed names the
   publisher's domain in <source url="...">, and most outlets build article URLs
   from a slugified headline, so construct the likely URL and make the page prove
   it is this story:

    "Nigerian Court Rules Religious Police Cannot Arrest Christian Woman..."
    + adfinternational.org
    -> https://adfinternational.org/news/nigerian-court-rules-religious-police-...

Results are cached in resolved.json, because the same story often reappears in a
later sweep and a verified URL never changes.
"""

import concurrent.futures as futures
import datetime as dt
import html as html_mod
import json
import os
import re
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_feeds

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "resolved.json")

# Path shapes to try, most common first. {s} is the slug, {y}/{m}/{d} today's date.
PATTERNS = [
    "https://{d0}/{s}/",
    "https://{d0}/news/{s}/",
    "https://{d0}/article/{s}/",
    "https://{d0}/{y}/{m}/{dd}/{s}/",
    "https://{d0}/{y}/{m}/{s}/",
]


def slugify(text, max_words=0):
    s = re.sub(r"[’'‘]", "", text.lower())
    s = re.sub(r"&[a-z]+;", " ", s)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    if max_words:
        s = "-".join(s.split("-")[:max_words])
    return s


def load_cache():
    try:
        with open(CACHE) as fh:
            return json.load(fh)
    except (ValueError, OSError):
        return {}


def save_cache(cache):
    tmp = CACHE + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(cache, fh)
    os.replace(tmp, CACHE)


def _alive(url):
    """True if the URL actually serves a page."""
    try:
        fetch_feeds.fetch(url, retry_uas=1)
        return True
    except Exception:  # noqa: BLE001
        return False


BLOCKED = set()   # hosts that refused the verification fetch this run

_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
_OGTITLE_RE = re.compile(
    r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)', re.I)


def confirms(url, headline):
    """True only if `url` serves a real page whose own title is this story.

    Liveness is not enough and never was. Two bad links reached published briefings:
    dailypioneer.com and wng.org/article/nigerian-court-protects-christian-woman... — the
    real WORLD URL is /sift/...-1786558522, which no slug pattern would ever produce. They
    got through because a guessed URL only had to not raise: a 403 was indistinguishable
    from a hit, soft-404s answer 200, and match_in_index would accept any URL containing
    three of the headline's words, which is easily a *different* article on the same topic.

    So the page has to identify itself. Fetch it, read its <title>/og:title, and require
    real overlap with the headline. A guess that cannot prove it is discarded, and the item
    keeps its Google News redirect — an ugly link is always better than a wrong one.
    """
    try:
        body = fetch_feeds.fetch(url, retry_uas=1)
    except Exception as exc:  # noqa: BLE001
        # A block is not a verdict on the URL. wng.org answered 405 to this very check
        # minutes after answering it fine, so "unresolved" has two quite different causes
        # and they must be told apart when reading the run's output: one means the resolver
        # needs work, the other means the outlet is refusing robots and never will resolve.
        if re.search(r"40[35]|429|timed? ?out|timeout", str(exc), re.I):
            BLOCKED.add(url.split("/")[2] if "//" in url else url)
        return False
    if isinstance(body, bytes):
        body = body.decode("utf-8", "replace")
    m = _OGTITLE_RE.search(body) or _TITLE_RE.search(body)
    if not m:
        return False
    page = html_mod.unescape(re.sub(r"<[^>]+>", " ", m.group(1)))
    if re.search(r"page not found|not found|404|error", page, re.I) \
            and not re.search(r"not found", headline, re.I):
        return False

    def sig(text):
        return {w for w in re.findall(r"[a-z]{4,}", text.lower())
                if w not in STOP}

    want, got = sig(headline), sig(page)
    if len(want) < 3:
        return False
    shared = len(want & got)
    # The page title is usually the headline, sometimes with an outlet suffix or a
    # slightly different sub-edit, so require most of it rather than all.
    return shared >= max(3, int(round(len(want) * 0.6)))


STOP = {"with", "from", "that", "this", "have", "will", "over", "into", "about",
        "after", "says", "said", "amid", "than", "then", "they", "their", "there",
        "been", "more", "most", "some", "such", "what", "when", "where", "which",
        "would", "could", "should", "news", "here"}


_index_cache = {}


def publisher_index(domain):
    """Scrape a publisher's front page once and keep its links. Cheaper than
    probing many URL shapes per story, and it catches outlets whose slugs don't
    follow the headline."""
    if domain in _index_cache:
        return _index_cache[domain]
    found = {}
    try:
        # scrape_index returns {headline: (url, date)}; the resolver only wants the URL.
        # It gained the date on 17.08.2026 and this second consumer was missed - compose
        # died on 'tuple' object has no attribute 'lower' rather than silently resolving
        # nothing, which is the good failure mode but still a failure.
        found = {t: u for t, (u, _when) in
                 fetch_feeds.scrape_index("https://%s/" % domain).items()}
    except Exception:  # noqa: BLE001
        pass
    _index_cache[domain] = found
    return found


def match_in_index(headline, domain):
    idx = publisher_index(domain)
    if not idx:
        return None
    want = fetch_feeds.title_key(headline)
    if want:
        for text, url in idx.items():
            if fetch_feeds.title_key(text) == want:
                return url
    # fall back to slug overlap: the article URL usually contains most of the slug
    words = [w for w in slugify(headline).split("-") if len(w) > 4][:6]
    if len(words) >= 3:
        for url in idx.values():
            low = url.lower()
            if sum(1 for w in words if w in low) >= max(3, len(words) - 2):
                return url
    return None


BATCHEXECUTE = "https://news.google.com/_/DotsSplashUi/data/batchexecute"

_SG_RE = re.compile(r'data-n-a-sg="([^"]+)"')
_TS_RE = re.compile(r'data-n-a-ts="([^"]+)"')
_AID_RE = re.compile(r'data-n-a-id="([^"]+)"')
_GARTURL_RE = re.compile(r'\[\\"garturlres\\",\\"(https?:[^\\"]+)')

# The inner request Google's own page sends. Opaque on purpose: the "X" placeholders
# are locale/consent fields it does not read for a URL lookup.
_GARTURLREQ = ('["garturlreq",[["X","X",["X","X"],null,null,1,1,"US:en",null,1,null,'
               'null,null,null,null,0,1],"X","X",1,[1,1,1],1,1,null,0,0,null,0],'
               '"%s",%s,"%s"]')


def decode_gnews(url):
    """The publisher URL behind a Google News redirect, straight from Google, or None.

    Authoritative rather than constructed, so the caller must not verify the result
    against the headline - see the module docstring.
    """
    try:
        body = fetch_feeds.fetch(url, retry_uas=1)
        if isinstance(body, bytes):
            body = body.decode("utf-8", "replace")
        sg, ts = _SG_RE.search(body), _TS_RE.search(body)
        if not (sg and ts):
            return None
        aid = _AID_RE.search(body)
        # Older redirect forms carry the id only in the path.
        aid = aid.group(1) if aid else url.rstrip("/").split("/")[-1].split("?")[0]
        inner = _GARTURLREQ % (aid, ts.group(1), sg.group(1))
        payload = [[["Fbv4je", inner, None, "1"]]]
        data = urllib.parse.urlencode(
            {"f.req": json.dumps(payload)}).encode()
        raw = fetch_feeds.fetch(
            BATCHEXECUTE, data=data,
            headers={"Content-Type":
                     "application/x-www-form-urlencoded;charset=utf-8"},
            retry_uas=1)
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", "replace")
        m = _GARTURL_RE.search(raw)
        return m.group(1).rstrip("/") if m else None
    except Exception:  # noqa: BLE001
        return None


def _looks_truncated(url):
    """A structurally incomplete URL: dangling separator, or a query key with no value.

    Added 20.08.2026. The docstring on decode_gnews says the caller must not verify what
    Google returns, and that held until Google itself returned a truncated payload for the
    Supreme Court trans-sports ruling:

        https://abcnews.com/Politics/supreme-court-upholds-.../story?id

    - the query value is missing, and the host is not even ABC's (abcnews.go.com). It was
    caught by the dead-link gate, which refused to write the whole briefing over it, on the
    day's biggest story. So the decode is still trusted by default, but a decode that looks
    structurally broken now has to prove itself the same way a constructed URL does.
    """
    try:
        p = urllib.parse.urlsplit(url)
    except ValueError:
        return True
    if not p.scheme or not p.netloc or "." not in p.netloc:
        return True
    if url.rstrip().endswith(("?", "&", "=", "/?")):
        return True
    if p.query and any("=" not in kv for kv in p.query.split("&") if kv):
        return True
    return False


def resolve_one(headline, publisher, when=None, gnews_url=None):
    """Best-effort publisher URL for a Google News item, or None."""
    if gnews_url:
        hit = decode_gnews(gnews_url)
        # A well-formed decode is authoritative and is NOT verified (see decode_gnews). A
        # malformed one falls through to the other routes, and if they fail too the caller
        # keeps the redirect - an ugly link beats a wrong one.
        if hit and _looks_truncated(hit) and not confirms(hit, headline):
            hit = None
        if hit:
            return hit
    if not publisher:
        return None
    hit = match_in_index(headline, publisher)
    if hit and confirms(hit, headline):
        return hit.rstrip("/")
    day = when or dt.date.today()
    parts = {"d0": publisher, "y": "%04d" % day.year,
             "m": "%02d" % day.month, "dd": "%02d" % day.day}
    # Full slug first, then progressively shorter - outlets often truncate.
    slugs = [slugify(headline)]
    words = slugs[0].split("-")
    for n in (12, 9, 7):
        if len(words) > n:
            cand = "-".join(words[:n])
            if cand not in slugs:
                slugs.append(cand)
    for slug in slugs:
        for pat in PATTERNS:
            url = pat.format(s=slug, **parts)
            # A constructed URL must prove it is this story, not merely respond.
            if confirms(url, headline):
                return url.rstrip("/")
    return None


def resolve_items(items, workers=8, use_cache=True):
    """Fill in item["url"] for Google News links where a direct URL is found.
    Returns (resolved_count, unresolved_list)."""
    cache = load_cache() if use_cache else {}
    todo = [it for it in items if "news.google.com" in it.get("url", "")]
    resolved, unresolved, fresh = 0, [], {}

    def work(it):
        key = "%s|%s" % (it.get("publisher", ""), slugify(it["headline"], 12))
        if key in cache:
            return it, cache[key], True
        when = None
        try:
            when = dt.datetime.fromisoformat(it["published"]).date()
        except (KeyError, ValueError):
            pass
        return it, resolve_one(it["headline"], it.get("publisher", ""), when,
                               gnews_url=it["url"]), False

    with futures.ThreadPoolExecutor(max_workers=workers) as pool:
        for it, url, cached in pool.map(work, todo):
            key = "%s|%s" % (it.get("publisher", ""), slugify(it["headline"], 12))
            # Cache successes only. A cached *failure* is permanent: it pins the
            # miss to that headline forever, so a later run cannot benefit from a
            # transient block clearing or from the resolver getting better. That is
            # not hypothetical - on 18.08.2026 the batchexecute decoder went in and
            # changed nothing, because all 81 of that morning's misses were already
            # cached as None and never re-attempted. Retrying a miss costs one fetch.
            if not cached and url:
                fresh[key] = url
            if url:
                it["url"] = url
                it["resolved"] = True
                resolved += 1
            else:
                unresolved.append(it)

    if use_cache and fresh:
        cache.update(fresh)
        save_cache(cache)
    return resolved, unresolved


if __name__ == "__main__":
    # quick check: resolve.py sweep.json  -> reports the hit rate
    data = json.load(open(sys.argv[1]))
    items = data["items"]
    g = [i for i in items if "news.google.com" in i["url"]]
    sample = g[: int(sys.argv[2])] if len(sys.argv) > 2 else g
    n, miss = resolve_items(sample)
    print("attempted %d | resolved %d (%.0f%%) | unresolved %d"
          % (len(sample), n, 100.0 * n / max(len(sample), 1), len(miss)))
    for it in sample[:12]:
        mark = "OK " if it.get("resolved") else "-- "
        print("  %s %-46s %s" % (mark, (it.get("publisher") or "?")[:44],
                                 it["url"][:92]))
