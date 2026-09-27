#!/usr/bin/env python3
"""Strip site furniture from article text before the ranker reads it.

Why this exists (27.09.2026). fetch_feeds' extractor removes <nav>/<header>/<footer> and
filters paragraphs by a junk-word list, and that still let whole templates through as
"article text". Measured on the 18,276 cached openings that day:

  - 346 of 346 Independent openings began "Please refresh the page or navigate to another
    page on the site to be automatically logged in..."
  - 232 of 232 GB News openings began with its 60-word site menu ("US Edition UK Edition
    Home GBN Shop YourSay YouDecide...")
  - EWTN's "EWTN News, Inc. is the world's largest Catholic news organization..." (163),
    Anglican Ink's header (86), Newsweek's Trust Project blurb (149), the Federalist's share
    bar (108), the Guardian's "View image in fullscreen" (296)...

The sheet prints the first ~900 characters, so on those outlets the ranker was reading
furniture and the text-coverage line counted it as readable.

Three layers, cheapest to most general:

  1. LITERAL - short fixed phrases a learner cannot find (too few words, or the words
     around them change every article, e.g. "View image in fullscreen <headline>").
  2. LEARNED - per host, the 6-word runs that recur across a large share of that host's
     OWN articles (boilerplate.json, written by `python3 boilerplate.py --learn`). Keyed per
     host on purpose: site furniture repeats within one site, while shared wire copy repeats
     ACROSS sites on one day - so a cross-site repeat is never learned, and an AP story
     syndicated to twenty outlets keeps its text.
  3. DAY - the same test run over the leads of the day being ranked (see scrub_day), for
     furniture that changes daily and so never reaches the learned threshold: Fox News
     prints its "trending" sidebar headlines inside the article body.

Plus one structural rule: a run of 10+ consecutive Capitalised words with no punctuation
is a menu, not a sentence.

Never removes an opinion marker ("do not necessarily reflect the views..."): textsignals
reads those to tell comment from report, and losing them would relabel columns as news.

The caches (openings.json, previews.json) keep the RAW text. Scrubbing happens when text is
read, so the learner always has the furniture to learn from, and a change here applies to
every cached entry at once. One consequence worth knowing: tiers.text_id hashes the text
the sheet shows, so the first sheet after a scrub change reports affected leads as changed
under --new-only. That is correct - the text the judge sees did change - and it is one-off.
"""
import collections
import json
import os
import re
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
LEARNED_PATH = os.path.join(HERE, "boilerplate.json")
OPENINGS_CACHE = os.path.join(HERE, "openings.json")
PREVIEWS_CACHE = os.path.join(HERE, "previews.json")

N = 6                   # gram length for learned and day-level furniture
MIN_RUN = 10            # a learned or day-level cut must cover at least this many words
LEARN_MIN_DOCS = 5      # a host needs this many cached articles before anything is learned
LEARN_FLOOR = 0.20      # ...and a gram must appear in this share of them
DAY_MIN_DOCS = 4        # day-level: at least this many of the host's leads today
DAY_FLOOR = 0.40        # ...and in this share of them. Higher than LEARN_FLOOR because a
                        # day's articles from one host can genuinely share a quote.

# Kept even when it recurs: these mark a piece as opinion, which textsignals reads.
_KEEP = re.compile(r"necessarily reflect|views? (expressed|of the author)|opinions? expressed"
                   r"|\bopinion\b|\bcommentary\b|\banalysis\b", re.I)

LITERAL = re.compile(
    # GB News prints its whole site menu inside the article body, and the middle of it
    # (trending topics, presenters, shows) changes too often to be learned. Both ends are
    # fixed, so cut between them - non-greedy and length-capped, so a page missing the
    # closing marker loses nothing beyond the menu's plausible length.
    # Older pages have no closing marker and the menu runs to the end of what was fetched.
    r"US Edition UK Edition Home GBN Shop(?:.{0,2500}?You are about to be charged £0\.00 \*"
    r"|.*$)"
    # The Independent's login notice opened 346 of its 346 cached openings. Fixed text, so
    # it is listed here rather than left to the learner: the scrub must not depend on
    # boilerplate.json existing (a fresh clone has none).
    r"|Please refresh the page or navigate to another page on the site to be automatically "
    r"logged in(?: Please refresh your browser to be logged in)?"
    r"|Want to bookmark your favourite articles and stories to read or reference later\? "
    r"Start your Independent Membership today\."
    r"|View image in fullscreen"
    r"|\bAdd (?:[A-Z][\w.&'’-]*\s){1,5}(?:on|to) Google\b"
    r"|\bAdd (?:[A-Z][\w.&'’-]*\s){0,5}(?:as (?:a|your)|to your) preferred source\b"
    # Comment-count widgets. Case-SENSITIVE (scoped (?-i:)), because the pattern is compiled
    # with re.I and "comments" is an ordinary word: "his comments" lost its noun until this
    # was scoped (27.09.2026).
    r"|(?-i:(?<![A-Za-z])COMMENTS(?![A-Za-z]))|(?-i:\b\d+ Comments\b)|(?-i:\bComments:)"
    r"|(?-i:\bView (?:\d+ )?Comments\b)"
    r"|Catholic news, teaching, and commentary on the life of the Church [—-] from Rome to "
    r"the parish\.?"
    r"|We won'?t sell or share your personal information to inform the ads you see\. You may "
    r"still see interest-based ads if your information is sold or shared by other companies "
    r"or was sold or shared previously\."
    r"|to top close Video [A-Z][\w ]{0,30} [A-Z][a-z]+ \d{1,2}, \d{4} \d{0,2}:\d\d CLIP"
    r"|Loading the Audio Player\.\.\."
    r"|Your browser does not support the (?:audio|video) (?:element|tag)\."
    r"|\bSupport independent journalism\. Subscribe for \$\d+ for your first year\. Limited time\.",
    re.I)

# Share bars: four or more share-target words in a row.
_SHARE_WORD = (r"(?:Share(?: to apps)?|Facebook|Twitter(?: / X)?|X|LinkedIn|Email|Copy (?:URL|Link)"
               r"|WhatsApp|Reddit|Pinterest|Print|Flipboard|Bluesky|Telegram|Messenger|SMS"
               r"|Circle Icon)")
SHARE_BAR = re.compile(r"(?:\b%s\b[\s/|:]*){4,}" % _SHARE_WORD)

# Menus: 10+ consecutive capitalised tokens with no sentence punctuation between them.
MENU_RUN = re.compile(r"(?:(?<=\s)|^)(?:[A-Z][\w&'’-]*|&|\|)(?:\s+(?:[A-Z][\w&'’-]*|&|\|)){9,}"
                      r"(?=\s|$)")

_learned = None


def host_of(url_or_key):
    s = url_or_key or ""
    if "://" in s:
        s = urllib.parse.urlsplit(s).netloc
    return s.split("/")[0].lower().replace("www.", "")


def _load_learned():
    global _learned
    if _learned is None:
        try:
            raw = json.load(open(LEARNED_PATH))
            _learned = {h: set(g) for h, g in raw.get("hosts", {}).items()}
        except (OSError, ValueError):
            _learned = {}
    return _learned


def _grams(words):
    return [" ".join(words[i:i + N]) for i in range(len(words) - N + 1)]


_CUT = "\x00"    # marks where a literal/share/menu match was removed


def _cut(words, grams):
    """Drop every word covered by a gram in `grams`, and every _CUT marker."""
    kill = [w == _CUT for w in words]
    hit = [False] * len(words)
    for i, g in enumerate(_grams(words)):
        if g in grams:
            for j in range(i, i + N):
                hit[j] = True
    # A learned cut must be a RUN of at least MIN_RUN words. Furniture is long - a menu, a
    # login notice, a publisher blurb - while a site's own recurring phrasing is short: ADF's
    # releases repeat "the U.S. Court of Appeals for the" often enough to be learned, and
    # cutting it took the court out of the sentence (measured 27.09.2026). Short furniture is
    # the LITERAL list's job.
    i = 0
    while i < len(words):
        if not hit[i]:
            i += 1
            continue
        j = i
        while j < len(words) and hit[j]:
            j += 1
        if j - i >= MIN_RUN:
            for k in range(i, j):
                kill[k] = True
        i = j
    # A few words stranded BETWEEN two cuts are the menu's own joints ("Best of Britain"
    # breaks a capitalised run on "of"), not prose: GB News came out as "...policy of of to
    # watch A Spanish lawyer..." until these were dropped too.
    i = 0
    while i < len(words):
        if kill[i]:
            i += 1
            continue
        j = i
        while j < len(words) and not kill[j]:
            j += 1
        bounded = (i == 0 or kill[i - 1]) and j < len(words) and kill[j] and i > 0
        if bounded and j - i <= 3:
            for k in range(i, j):
                kill[k] = True
        i = j
    return [w for w, k in zip(words, kill) if not k]


def drop_standfirst_echo(text, words=8, window=700):
    """If the text repeats its own opening within `window` chars, keep only the repeat.

    fetch_article_opening puts og:description first and then the body, and the description
    is usually the first paragraph cut short - so the text says its first sentence twice.
    Measured 27.09.2026: 28% of cached openings did, wasting 275 chars on average, which in
    the sheet's 320-char short tier is nearly the whole allowance. The body copy is kept
    because it runs on where the description stops.
    """
    w = text.split()
    if len(w) < words * 3:
        return text
    head = " ".join(w[:words])
    j = text.find(head, len(head))
    if 0 < j < window:
        return text[j:]
    return text


def scrub(url_or_key, text, extra=None):
    """Return `text` with site furniture removed, or None if nothing real is left.

    `extra` is an optional set of day-level grams for this host (see scrub_day).
    """
    if not text:
        return text
    mark = " %s " % _CUT
    t = LITERAL.sub(mark, text)
    t = SHARE_BAR.sub(mark, t)
    t = MENU_RUN.sub(mark, t)
    words = t.split()
    grams = set(_load_learned().get(host_of(url_or_key), ()))
    if extra:
        grams |= extra
    kept = _cut(words, grams)
    if len(kept) == len(words) and _CUT not in words:
        out = text                   # nothing was furniture: only the echo can change it
    else:
        out = " ".join(kept).strip()
    out = drop_standfirst_echo(out)
    return out if len(out) >= 80 else None


def learn_grams(texts, floor, min_docs):
    """6-grams recurring in at least `floor` of `texts` (and in `min_docs` of them)."""
    if len(texts) < min_docs:
        return set()
    df = collections.Counter()
    for t in texts:
        df.update(set(_grams(t.split())))
    need = max(min_docs, floor * len(texts))
    return {g for g, n in df.items() if n >= need and not _KEEP.search(g)}


def day_grams(items, text_of):
    """Per-host furniture learned from one day's leads. {host: set(grams)}.

    `text_of(item)` returns the raw text for an item (or None).
    """
    by_host = collections.defaultdict(list)
    for it in items:
        t = text_of(it)
        if t:
            by_host[host_of(it.get("url"))].append(t)
    return {h: g for h, texts in by_host.items()
            for g in [learn_grams(texts, DAY_FLOOR, DAY_MIN_DOCS)] if g}


def learn(paths=(OPENINGS_CACHE, PREVIEWS_CACHE)):
    """Rebuild boilerplate.json from the text caches. Returns {host: n_grams}."""
    by_host = collections.defaultdict(list)
    for p in paths:
        try:
            cache = json.load(open(p))
        except (OSError, ValueError):
            continue
        for k, t in cache.items():
            if k.startswith("__") or not isinstance(t, str):
                continue
            by_host[host_of(k)].append(t)
    hosts = {}
    for h, texts in by_host.items():
        g = learn_grams(texts, LEARN_FLOOR, LEARN_MIN_DOCS)
        if g:
            hosts[h] = sorted(g)
    tmp = LEARNED_PATH + ".tmp"
    with open(tmp, "w") as fh:
        json.dump({"n": N, "floor": LEARN_FLOOR, "min_docs": LEARN_MIN_DOCS,
                   "hosts": hosts}, fh)
    os.replace(tmp, LEARNED_PATH)
    global _learned
    _learned = None
    return {h: len(g) for h, g in hosts.items()}


if __name__ == "__main__":
    if "--learn" in sys.argv:
        got = learn()
        print("learned furniture for %d host(s), %d gram(s) -> %s"
              % (len(got), sum(got.values()), LEARNED_PATH))
    else:
        print(__doc__)
