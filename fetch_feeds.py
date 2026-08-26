#!/usr/bin/env python3
"""Fetch Chris's news sources and emit a compact, deduped list of recent stories.

Backbone is sources.opml (a Feedly export). extra_feeds.txt adds corrected URLs,
outlets missing from the OPML, Google News fallbacks for feedless outlets, and a
disable list for dead feeds.

Items are kept only if their own publish timestamp falls inside the freshness
window, so the cutoff is exact rather than inferred. The window deliberately
overlaps the gap between runs (36h, 84h on Mondays) so nothing slips through;
duplicates are harmless because seen.json drops anything a previous edition used.

Sweeping does NOT mark items as seen — compose.py records the stories that actually
reach the published doc. Marking everything swept would burn the candidates that were
not chosen: on 12.08.2026 that silently consumed 538 unused stories.

Usage:
    python3 fetch_feeds.py                 # 36h (84h Mondays)
    python3 fetch_feeds.py --hours 24      # force a window
    python3 fetch_feeds.py --json out.json # dump structured results for shortlist.py
"""

import argparse
import concurrent.futures as futures
import datetime as dt
import email.utils
import gzip
import html as html_mod
import io
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
OPML = os.path.join(HERE, "sources.opml")
EXTRA = os.path.join(HERE, "extra_feeds.txt")
SEEN_DB = os.path.join(HERE, "seen.json")
CUT_DB = os.path.join(HERE, "cut.json")

UAS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Mozilla/5.0 (compatible; RSS Reader; +https://example.com)",
    "curl/8.4.0",
]
TIMEOUT = 15
WORKERS = 20
SEEN_RETENTION_DAYS = 21
MAX_PER_FEED = 60       # guard against one firehose feed dominating
DEADLINE = 210          # hard stop for the whole sweep, seconds

# Hosts that rate-limit when hit in parallel: space requests out by N seconds.
# Everything else is fetched with no artificial delay.
HOST_GAPS = {"news.google.com": 0.7, "www.theyworkforyou.com": 1.5,
             "theyworkforyou.com": 1.5, "www.bing.com": 1.0}
# Must exceed the WORST-CASE queue for the busiest host or feeds are silently abandoned, not
# delayed. Raised 12 -> 75 on 24.08.2026: news.google.com has a 0.7s gap and 80 of the 348
# feeds are Google News requests, so the tail of that queue waits ~56s - every feed behind the
# first ~17 was failing as "host-busy". It showed up the morning 13 sources were added, as 24
# failures instead of the usual handful, and the casualties were the keyword feeds that carry
# Life and Gender: "abortion", "assisted suicide", "euthanasia", "transgender",
# "same-sex marriage", "dignity in dying". A dropped feed and a quiet news day look identical
# in the output, which is exactly the confusion check_sources.py exists to prevent.
# If the Google feed count grows again, this has to grow with it: keep it above
# 0.7 * (number of news.google.com feeds).
MAX_HOST_WAIT = 75
MAX_PER_SCRAPE = 25     # index-scraped sources have no dates; cap what they add

# Paywalled outlets, matched on the article's own domain so that lookalike names
# ("The Times of India", "Bloomberg School of Public Health") are not caught.
# Flagged with £ in the output so the digest can append "(£)" automatically.
PAYWALLED_DOMAINS = {
    "telegraph.co.uk", "thetimes.com", "thetimes.co.uk", "wsj.com", "nytimes.com",
    "washingtonpost.com", "bloomberg.com", "bloomberglaw.com", "ft.com",
    "theaustralian.com.au", "smh.com.au", "theage.com.au", "spectator.com",
    "spectator.co.uk", "spectator.com.au", "thecritic.co.uk", "churchtimes.co.uk",
    "economist.com", "unherd.com", "heraldscotland.com", "statement.com",
    "theatlantic.com", "newstatesman.com", "couriermail.com.au",
    "dailytelegraph.com.au", "afr.com", "thetimes.ie",
    # marked (£) in Chris's own briefings
    "spiked-online.com", "thecatholicherald.com", "theherald.com.au",
}

PASS_CATEGORIES = {
    "Issues: Life", "Issues: Life keywords", "Issues: Religious Freedom",
    "Issues: Gender & Identity", "Issues: Marriage, family, gender and sexuality",
    "Issues: Education", "Issues: Islam", "Issues: Church & Society",
    "Advocacy: Christian", "Advocacy: Non-Christian", "Media: Christian",
    "Daily: Media monitors", "Hansard: Issues", "Supreme Court",
    "Think Tanks: Christian",
}
FILTER_CATEGORIES = {
    "Media: UK Mainstream", "Media: UK Periodicals", "Media: UK Politics",
    "Media: Alternative", "Media: US and World", "Comment: Secular",
    "Think Tanks: General & Policy", "Polls and statistics", "UN",
    "Council of Europe", "OSCE: Organization for Security and Co-operation in Europe",
    "Govt: News & Research", "Govt: Policy & Publications",
    "Northern Ireland Assembly", "Welsh Assembly",
}

KEYWORDS = [
    # Freedom & Liberty
    r"free speech", r"freedom of (speech|expression|religion|belief)", r"censor\w*",
    r"blasphem\w*", r"religious (freedom|liberty|hatred|discrimination)", r"persecut\w*",
    r"debank\w*", r"hate speech", r"non-crime hate", r"street preacher", r"chaplain",
    r"christian\w*", r"church(es)?", r"cathedral", r"bishop", r"archbishop",
    r"catholic", r"anglican", r"evangelical", r"islamophobi\w*", r"missionar\w*",
    r"conscientious objection", r"secular\w*", r"prayer", r"apostas\w*",
    r"anti-conversion", r"jimmy lai", r"vicar", r"parish", r"diocese", r"nun\b",
    # Marriage, Family & Education
    r"marriage", r"married", r"divorce", r"cohabit\w*", r"civil partnership",
    r"same-sex", r"parental rights", r"parents'? rights", r"birth ?rate\w*",
    r"fertility", r"demograph\w*", r"motherhood", r"fatherhood", r"family court",
    r"sex education", r"relationships education", r"\bRSE\b", r"curriculum",
    r"faith school", r"home ?school\w*", r"school library", r"safeguarding",
    r"adoption", r"foster care", r"polyamor\w*", r"polygam\w*", r"childless",
    # Gender, Identity & Sexuality
    r"trans(gender|sexual)?\b", r"gender", r"puberty blocker\w*", r"cross-sex hormone",
    r"single-sex", r"women'?s (sport|football|rugby|swimming)", r"detrans\w*",
    r"\bLGBT\w*\b", r"\bpride\b", r"non-?binary", r"\bEHRC\b", r"gender recognition",
    r"changing room", r"bathroom", r"conversion therapy", r"gender.critical",
    r"stonewall", r"drag queen", r"chestfeed\w*", r"biological (sex|male|female)",
    r"self-?id\b", r"gender dysphoria", r"gender clinic", r"tavistock", r"\bGRC\b",
    r"\bqueer\b", r"breastfeed\w*", r"strip.search", r"single sex", r"women only",
    r"\bwomxn\b", r"misgender\w*", r"deadnam\w*", r"sex change", r"\bintersex\b",
    r"employment tribunal", r"gender ideology", r"lesbian", r"\bgay\b", r"bisexual",
    # Life
    r"abortion", r"pro-?life", r"pro-?choice", r"assisted (dying|suicide)",
    r"euthanas\w*", r"\bMAID\b", r"surrogac\w*", r"surrogate", r"\bIVF\b",
    r"embryo\w*", r"mifepristone", r"abortion pill", r"buffer zone", r"palliative",
    r"hospice", r"unborn", r"foetus", r"fetus", r"foetal", r"end of life",
    r"right to die", r"\bBPAS\b", r"marie stopes", r"planned parenthood",
    r"pregnancy (centre|center|crisis)", r"gendercide", r"sex-selective",
    r"down'?s syndrome", r"disability abortion", r"egg freezing", r"assisted death",
    # Church & Society's politics remit, and Other. Both briefing sections existed with no
    # vocabulary here at all, so the generalist outlets on `filter` mode could never reach
    # them: the Mail passed 6 of 149 in-window items, the Guardian 2 of 104, and Other
    # filled up with the unfiltered commentary magazines because they were the only sources
    # able to get in. Measured 13.08.2026 after Chris asked why 737 candidates came out of
    # feeds serving 10,100 items. Keep this list in step with shortlist.OTHER_ALLOW, which
    # is the gate these items still have to clear later.
    r"politic\w*", r"government", r"minister", r"parliament", r"\bsenate\b", r"congress",
    r"white house", r"downing street", r"election", r"campaign", r"referendum",
    r"\bvote\w*", r"\bbill\b", r"legislat\w*", r"\blaw\b", r"legal", r"court", r"judge",
    r"ruling", r"tribunal", r"inquiry", r"prosecut\w*", r"\bprison\w*", r"police",
    r"migrant\w*", r"migration", r"asylum", r"immigration", r"deport\w*", r"border",
    r"welfare", r"benefits", r"\btax\w*", r"economy", r"budget", r"council", r"mayor",
    r"devolution", r"\bNHS\b", r"hospital", r"doctor", r"nurse", r"care home",
    r"social care", r"charity", r"protest", r"riot", r"extremis\w*", r"terror\w*",
    # Education outcomes - "pupils", "A-level" and "exam" were all missing, so results day
    # was invisible to us.
    r"pupil\w*", r"\bexams?\b", r"A-?levels?", r"GCSEs?", r"university", r"universities",
    r"student\w*", r"teacher\w*", r"headteacher", r"ofsted", r"\bschools?\b",
    # Spanish and Italian. Without these the prefilter silently discarded every item from
    # ACI Prensa, Actuall, InfoCatolica, La Nuova Bussola and Le Salon Beige before it ever
    # reached the classifier. Added 13.08.2026 with the matching classifier vocabulary.
    r"aborto", r"abortiv", r"provida", r"pro-?vida", r"no nacid", r"nascituro",
    r"eutanasia", r"suicidio asistido", r"suicidio assistito", r"cuidados paliativos",
    r"cure palliative", r"gestaci[oó]n subrogada", r"vientres? de alquiler",
    r"maternit[aà] surrogata", r"utero in affitto", r"embri[oó]n", r"embrione",
    r"matrimonio", r"divorcio", r"divorzio", r"familia", r"famiglia", r"natalidad",
    r"natalit[aà]", r"maternidad", r"maternit[aà]", r"patria potestad",
    r"educaci[oó]n sexual", r"educazione sessuale", r"adoctrinamiento", r"indottrinamento",
    r"transg[eé]nero", r"transexual", r"transessual", r"ideolog[ií]a de g[eé]nero",
    r"ideologia (del )?gender", r"cambio de sexo", r"cambio di sesso", r"g[eé]nero",
    r"\bLGTB\w*", r"homosexual", r"omosessual", r"lesbiana",
    r"libertad religiosa", r"libert[aà] religiosa", r"libertad de expresi[oó]n",
    r"libert[aà] di espressione", r"censura", r"blasfemia", r"bestemmia",
    r"persecuci[oó]n", r"perseguid", r"persecuzione", r"perseguitat", r"m[aá]rtir",
    r"iglesia", r"chiesa", r"cat[oó]lic", r"cattolic", r"obispo", r"vescovo",
    r"arzobispo", r"arcivescovo", r"sacerdote", r"p[aá]rroco", r"parroco",
    r"di[oó]cesis", r"diocesi", r"vaticano", r"cardenal", r"cardinale",
    r"cristian", r"evang[eé]lic", r"evangelic", r"laicismo", r"laicit[aà]",
    r"misa\b", r"messa\b", r"oraci[oó]n", r"preghiera",
]
KEYWORD_RE = re.compile("|".join(KEYWORDS), re.IGNORECASE)

SKIP_URL_PATTERNS = ("feedly.com/f/alert/", "feedly.com/email/", "feedly.com/web/",
                     "nitter.", "youtube.com/feeds", "gdata.youtube.com")

STRIP_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "ns_mchannel", "ns_campaign", "ito", "ICID", "fbclid", "gclid", "at_medium",
    "at_campaign", "CMP", "cmp", "utm_id", "ref", "sh", "oc", "guccounter",
}


# ---------------------------------------------------------------------------
# HTTP with 308 support + per-host throttling + UA rotation
# ---------------------------------------------------------------------------
class Redirect308(urllib.request.HTTPRedirectHandler):
    def http_error_308(self, req, fp, code, msg, headers):
        return self.http_error_301(req, fp, 301, msg, headers)


_OPENER = urllib.request.build_opener(Redirect308)
_host_lock = threading.Lock()
_host_next = {}


def _wait_for_host(url):
    """Space out requests to known rate-limiting hosts. Returns False to skip."""
    try:
        host = urllib.parse.urlsplit(url).netloc.lower()
    except ValueError:
        return True
    gap = HOST_GAPS.get(host)
    if not gap:
        return True
    with _host_lock:
        now = time.monotonic()
        ready = _host_next.get(host, 0.0)
        delay = max(0.0, ready - now)
        if delay > MAX_HOST_WAIT:
            return False
        _host_next[host] = max(now, ready) + gap
    if delay:
        time.sleep(delay)
    return True


def fetch(url, retry_uas=2, data=None, headers=None):
    """GET url, following 308s, retrying with an alternate UA on 403.

    Pass `data` (bytes) to POST instead - resolve.py needs it for Google's own
    URL-decode endpoint. `headers` overrides the defaults per request.
    """
    if url.startswith("http://"):
        url = "https://" + url[len("http://"):]
    last = None
    for ua in UAS[:retry_uas]:
        if not _wait_for_host(url):
            raise RuntimeError("host-busy")
        hdrs = {
            "User-Agent": ua,
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
            "Accept-Language": "en-GB,en;q=0.9",
            "Accept-Encoding": "gzip",
        }
        if headers:
            hdrs.update(headers)
        req = urllib.request.Request(url, data=data, headers=hdrs)
        try:
            with _OPENER.open(req, timeout=TIMEOUT) as resp:
                raw = resp.read()
                if resp.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
                return raw
        except urllib.error.HTTPError as exc:
            last = "HTTP %s" % exc.code
            if exc.code != 403:  # only a UA swap is worth retrying
                break
        except Exception as exc:  # noqa: BLE001
            last = type(exc).__name__
            break
    raise RuntimeError(last or "failed")


# ---------------------------------------------------------------------------
# Source loading
# ---------------------------------------------------------------------------
FEED_MODES = ("pass", "filter", "gnews", "gnewsf", "bing", "bingf",
              "scrapesrc", "scrapesrcf")
# Modes that keep only items matching the topical keyword list.
FILTERED_MODES = {"filter", "gnewsf", "bingf", "scrapesrcf"}


# Per-feed sweep window, keyed by outlet title (lowercased). Title is used rather than URL
# because it survives the gnews/bing URL rewriting in add() unchanged.
#
# Chris asked for FoRB in Full's Sevilla Rivera interview on 20.08.2026. Nothing was broken:
# the feed fetched fine and the piece was simply older than the 36h window by a few hours. A
# source that publishes a few times a week will miss that window most days, and
# check_sources.py cannot see it - it tracks whether a fetch SUCCEEDED, not whether a live
# source is going unrepresented. Widening the window globally would drag the whole sweep in,
# so it is per-source.
FEED_WINDOWS = {}
WINDOW_RE = re.compile(r"^window\s*=\s*(\d+)\s*h?$", re.I)


def feed_window_hours(field):
    """Hours declared by a `window=NNNh` field, or 0. Tolerant of junk: an unparseable
    field means the default window, never a crash in the 6am path."""
    m = WINDOW_RE.match((field or "").strip())
    return int(m.group(1)) if m else 0


def load_extra(path=EXTRA):
    feeds, scrapes, disabled, blocked = [], [], [], []
    FEED_WINDOWS.clear()
    if not os.path.exists(path):
        return feeds, scrapes, disabled, blocked
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split("|")]
            head = parts[0]
            if head == "disable" and len(parts) >= 2:
                disabled.append(parts[1])
            elif head == "block" and len(parts) >= 2:
                blocked.append(parts[1].lower())
            elif head == "scrape" and len(parts) >= 4:
                scrapes.append((parts[2], parts[3]))
            elif head in FEED_MODES and len(parts) >= 4:
                feeds.append((parts[1], parts[2], parts[3], head))
                # Optional 5th field. Backwards-compatible: every pre-existing line has four.
                if len(parts) >= 5:
                    w = feed_window_hours(parts[4])
                    if w:
                        FEED_WINDOWS[parts[2].strip().lower()] = w
    return feeds, scrapes, disabled, blocked


# Google News is edition-scoped: a GB/US edition barely indexes Indian or African
# reporting. Two abortion stories from India were missed on 12.08.2026 for exactly this
# reason, so a target may carry an "@CC" suffix to pick the edition, and "kw:" makes it a
# keyword search rather than a site: search.
def gnews_url(target, days=2):
    country = "GB"
    if "@" in target:
        target, country = target.rsplit("@", 1)
        country = country.strip().upper()
    if target.startswith("kw:"):
        query = "%s when:%dd" % (target[3:].strip(), days)
    else:
        query = "site:%s when:%dd" % (target, days)
    return ("https://news.google.com/rss/search?q=%s&hl=en-%s&gl=%s&ceid=%s:en"
            % (urllib.parse.quote(query), country, country, country))


def bing_url(domain):
    """Bing News site: search. Its links wrap the real publisher URL, which we
    unwrap in unwrap_link(), so these come out as direct links."""
    return ("https://www.bing.com/news/search?q=%s&format=RSS&count=40"
            % urllib.parse.quote("site:" + domain))


def unwrap_link(url):
    """Pull the publisher URL out of a Bing apiclick wrapper."""
    if "bing.com/news/apiclick" in url:
        q = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
        if q.get("url"):
            return q["url"][0]
    return url


# Nav pages and subscription blurb that site: searches drag in alongside articles.
JUNK_TITLE = re.compile(
    r"^\s*$|^(archive|subscribe|home|news|latest news|sign in|log in|contact)\b"
    r"|^subscribe to\b|indep[ei]ndent since|^the [\w' ]+ ?[-|] ?news, comment"
    r"|^[\w' ]{0,28}$(?<![?!.])", re.IGNORECASE)


def is_junk_title(title, outlet):
    t = (title or "").strip()
    if len(t) < 25:
        return True
    if re.fullmatch(r"[\W_]*", t):
        return True
    # headline that is just the outlet's own name / masthead blurb
    if outlet and t.lower().rstrip(" .|-") == outlet.lower().rstrip(" .|-"):
        return True
    return bool(re.match(r"^(archive|subscribe|sign in|log in)\b", t, re.I))


def is_paywalled(url, src_domain=""):
    """Check the article's own domain, falling back to the domain a site: search
    targeted (Google News links are opaque redirects, so the URL host is useless)."""
    for host in (outlet_from_url(url), (src_domain or "").lower().replace("www.", "")):
        if host and any(host == d or host.endswith("." + d)
                        for d in PAYWALLED_DOMAINS):
            return True
    return False


def load_feeds():
    extra, scrapes, disabled, blocked = load_extra()
    feeds, seen_urls = [], set()

    def add(category, title, url, mode, domain=""):
        url = (url or "").strip()
        if not url or not title:
            return
        if not mode.startswith(("gnews", "bing")):
            if any(p in url for p in SKIP_URL_PATTERNS):
                return
        # The disable check used to sit inside the branch above, so `disable | ...` silently
        # did nothing to a gnews/bing feed - the line looked applied and was not. Found on
        # 17.08.2026 trying to retire a Bing search for Church Times that returns no results.
        # Checked against the whole source list when this moved: exactly one feed is affected,
        # which is the intended one.
        if any(d and d in url for d in disabled):
            return
        key = url.lower().replace("http://", "https://")
        if key in seen_urls:
            return
        seen_urls.add(key)
        feeds.append((category, title, url, mode, domain))

    for category, title, target, mode in extra:  # extras first: they win dedup
        domain = ""
        if mode.startswith(("gnews", "bing")):
            domain = target.rsplit("@", 1)[0]
            if domain.startswith("kw:"):
                domain = ""
            target = gnews_url(target) if mode.startswith("gnews") else bing_url(target)
        elif mode.startswith("scrapesrc"):
            domain = urllib.parse.urlsplit(target).netloc
        add(category, title, target, mode, domain)

    body = ET.parse(OPML).getroot().find("body")
    for outline in body:
        category = (outline.get("title") or outline.get("text") or "").strip()
        if outline.get("type") == "rss":
            continue
        mode = ("pass" if category in PASS_CATEGORIES
                else "filter" if category in FILTER_CATEGORIES else None)
        if mode is None:
            continue
        for child in outline.iter("outline"):
            if child.get("type") == "rss":
                add(category, (child.get("title") or child.get("text") or "").strip(),
                    child.get("xmlUrl"), mode)
    return feeds, scrapes, blocked


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------
def _text(node):
    """Element text with HTML entities resolved - feeds routinely deliver &#8217;
    inside CDATA, which would otherwise reach the doc as literal characters."""
    if node is None:
        return ""
    return html_mod.unescape("".join(node.itertext())).strip()


def parse_date(value):
    if not value:
        return None
    value = value.strip()
    try:
        d = email.utils.parsedate_to_datetime(value)
        if d is not None:
            return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)
    except (TypeError, ValueError, IndexError):
        pass
    iso = re.sub(r"Z$", "+00:00", value)
    iso = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", iso)
    for cand in (iso, iso.split(".")[0], iso.split(".")[0] + "+00:00"):
        try:
            d = dt.datetime.fromisoformat(cand)
            return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)
        except ValueError:
            continue
    return None


DC = "{http://purl.org/dc/elements/1.1/}"
NS = {"atom": "http://www.w3.org/2005/Atom"}


CTRL_CHARS = re.compile(rb"[\x00-\x08\x0b\x0c\x0e-\x1f]")
BARE_AMP = re.compile(rb"&(?!(?:amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)")


def sanitise_xml(raw):
    """Repair the two things that break real-world feeds: invalid UTF-8 bytes
    (UnHerd has one mid-CDATA) and unescaped ampersands."""
    raw = raw.decode("utf-8", "replace").encode("utf-8")
    raw = CTRL_CHARS.sub(b"", raw)
    return BARE_AMP.sub(b"&amp;", raw)


def parse_feed(raw):
    raw = raw.lstrip()
    if raw[:1] != b"<":
        idx = raw.find(b"<")
        raw = raw[idx:] if idx > -1 else raw
    if raw[:9].lower().startswith(b"<!doctype") or raw[:5].lower() == b"<html":
        raise ValueError("html-not-feed")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        root = ET.fromstring(sanitise_xml(raw))
    tag = root.tag.split("}")[-1]
    out = []
    if tag == "rss" or root.find("channel") is not None:
        channel = root.find("channel")
        feed_title = _text(channel.find("title")) if channel is not None else ""
        for it in (channel.findall("item") if channel is not None else []):
            link = _text(it.find("link")) or _text(it.find("guid"))
            src = it.find("source")
            out.append({
                "title": _text(it.find("title")),
                "link": link,
                "date": parse_date(_text(it.find("pubDate")) or _text(it.find(DC + "date"))),
                "author": _text(it.find(DC + "creator")) or _text(it.find("author")),
                "source": _text(src) if src is not None else "",
                "source_url": (src.get("url") or "") if src is not None else "",
                "feed_title": feed_title,
                # The publisher's own topic labels. Chris's markup on 15.08.2026 showed these
                # agree with his section judgement in 8 of 8 cases where the keyword classifier
                # disagreed with him - spiked files the Jason Arday pieces under "Identity
                # Politics", the Edwina Currie piece under "Immigration". Free, already in the
                # feed, and the publisher's judgement rather than my regex.
                "categories": [c for c in (_text(x) for x in it.findall("category")) if c],
                "summary": re.sub(r"<[^>]+>", " ",
                                  _text(it.find("description")) or "")[:400].strip(),
            })
    else:
        feed_title = _text(root.find("atom:title", NS))
        for e in root.findall("atom:entry", NS):
            link = ""
            for ln in e.findall("atom:link", NS):
                if ln.get("rel", "alternate") == "alternate":
                    link = ln.get("href", "")
                    break
            out.append({
                "title": _text(e.find("atom:title", NS)),
                "link": link,
                "date": parse_date(_text(e.find("atom:published", NS))
                                   or _text(e.find("atom:updated", NS))),
                "author": _text(e.find("atom:author/atom:name", NS)),
                "source": "",
                "source_url": "",
                "feed_title": feed_title,
                "categories": [x.get("term") for x in e.findall("atom:category", NS)
                               if x.get("term")],
                "summary": re.sub(r"<[^>]+>", " ",
                                  _text(e.find("atom:summary", NS)) or "")[:400].strip(),
            })
    return out


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------
def clean_url(url):
    url = (url or "").strip()
    if not url:
        return ""
    try:
        p = urllib.parse.urlsplit(url)
    except ValueError:
        return url
    q = [(k, v) for k, v in urllib.parse.parse_qsl(p.query, keep_blank_values=True)
         if k not in STRIP_PARAMS]
    return urllib.parse.urlunsplit((p.scheme or "https", p.netloc,
                                    p.path.rstrip("/") or "/",
                                    urllib.parse.urlencode(q), ""))


def url_key(url):
    try:
        p = urllib.parse.urlsplit(url)
    except ValueError:
        return url.lower()
    return p.netloc.lower().replace("www.", "") + p.path.rstrip("/").lower()


STOP = {"the", "and", "for", "with", "that", "from", "have", "has", "was", "are",
        "will", "says", "said", "over", "after", "into", "amid", "his", "her",
        "their", "its", "new", "not", "but", "who", "what", "how", "why"}


def title_key(title, n=8):
    t = re.sub(r"[^a-z0-9 ]", " ", (title or "").lower())
    words = [w for w in t.split() if len(w) > 3 and w not in STOP]
    return " ".join(sorted(words[:n]))


def strip_outlet_suffix(title, source=""):
    """Google News appends the outlet: "Headline - Outlet" or "Headline | Outlet".

    Takes the LAST separator, then validates the tail as a masthead instead of trusting the
    pattern. Two bugs on 19.08.2026 made the validation necessary. Chris spotted the first in
    the published edition: the old capture group was ``[^\\-|]{2,45}``, which EXCLUDES hyphens,
    so a hyphenated masthead could never be stripped - "spiked-online.com" shipped, and so
    would NBC 5 Dallas-Fort Worth, Austin American-Statesman and times-standard.com. 48 items
    in that day's sweep still carried a suffix.

    Merely allowing hyphens then exposed the second: "Pope Leo XIV - the first year" strips to
    "Pope Leo XIV", and the Washington Post's "Opinion | Trump and Iran" strips to "Opinion"
    with the real headline mistaken for the outlet. A headline is longer than its own masthead
    - that is the cheap invariant separating the two, and it does the work the hyphen ban was
    accidentally doing.

    When the feed states the source it wins outright, no heuristic needed.
    """
    t = (title or "").strip()
    src = (source or "").strip()
    outermost = ""
    # Suffixes STACK. Google News appends its own " - <source>" to a title that already ended
    # in the publisher's name, so one pass leaves the inner one behind: the raw title was
    # "...believers – EWTN Great Britain - EWTN UK", the " - " pass matched the stated source
    # exactly, returned, and the en-dash half shipped in the 20.08.2026 edition. Strip until
    # nothing more comes off, bounded so a pathological title cannot spin.
    #
    # Only the OUTERMOST suffix is returned: that is the one Google added and the one the
    # outlet name is taken from. The feed's stated source likewise applies to that pass only.
    for _ in range(3):
        t, tail = _strip_one_suffix(t, src, allow_lowercase=not outermost)
        if not tail:
            break
        outermost = outermost or tail
        src = ""
    return t, outermost


def _strip_one_suffix(title, source="", allow_lowercase=True):
    """One pass of strip_outlet_suffix; see there for why this is split out.

    allow_lowercase is False on repeat passes: a masthead is capitalised or a domain, and
    without that guard "Israel-Gaza war - live updates - BBC" loses "live updates" on the
    second pass. The first pass still allows it, because spiked-online.com, ucanews.com and
    times-standard.com are real outlets that reach us entirely in lower case.
    """
    t = (title or "").strip()
    src = (source or "").strip()
    # En and em dash added 20.08.2026, AFTER the existing two so nothing already passing
    # changes: "Burnham must rule out assisted dying – once and for all - spiked-online.com"
    # still resolves on " - " first and never reaches the dash forms. Chris spotted
    # "...persecution of believers – EWTN Great Britain" in the 20.08 edition; an en dash is
    # what EWTN's own feed uses, and no dash form was in this list.
    for sep in (" - ", " | ", " – ", " — "):
        head, found, tail = t.rpartition(sep)
        if not found:
            continue
        head, tail = head.strip(), tail.strip()
        if not head or not (2 <= len(tail) <= 45):
            continue
        if src and tail.lower() == src.lower():
            return head, tail
        if len(tail) >= len(head) or len(tail.split()) > 6:
            continue
        # An article followed by a LOWERCASE word reads as running prose, not a name. The
        # case must be checked: "The Guardian" and "The Times" are mastheads and must strip,
        # while "the first year" and "and its aftermath" must not.
        if re.match(r"(the|a|an|and|for|its|his|her|their|to|of|in|on|with)\s+[a-z]", tail):
            continue
        if re.search(r"[.!?,;:]\s", tail):
            continue
        if not allow_lowercase and not (tail[:1].isupper() or "." in tail):
            continue
        return head, tail
    return t, ""


def outlet_from_url(url):
    try:
        host = urllib.parse.urlsplit(url).netloc.lower()
    except ValueError:
        return ""
    return re.sub(r"^(www|rss|feeds|amp|wp)\.", "", host)


# ---------------------------------------------------------------------------
# Scrape index pages -> {title_key: direct_url} for resolving gnews links
# ---------------------------------------------------------------------------
A_TAG = re.compile(r'<a\b[^>]*href="([^"\s]+)"[^>]*>(.*?)</a>', re.I | re.S)
TAGS = re.compile(r"<[^>]+>")
LABEL = re.compile(r"^(report|news|opinion|commentary|analysis|feature|video)\s+", re.I)

# Modern sites wrap a whole card - kicker, date, headline, excerpt, "Read More" - in a single
# <a>. Taking all of the anchor's text then yields a headline like "Press Release July 9, 2026
# European Parliament strongly condemns... Read More". ADF International is the case that
# exposed it (17.08.2026), but card-wrapped links are everywhere, so prefer the card's own
# heading when there is one.
CARD_HEADING = re.compile(r"<h[1-4]\b[^>]*>(.*?)</h[1-4]>", re.I | re.S)
# A date printed inside the card. Recovering it matters more than tidiness: scrapesrc sources
# are otherwise dateless, so every link absent from seen.json counts as new and a whole
# archive of old press releases enters as today's news.
CARD_DATE = re.compile(
    r"\b(\d{1,2}\s+)?(January|February|March|April|May|June|July|August|September|October"
    r"|November|December)\s+(\d{1,2},\s*)?(\d{4})\b", re.I)
READ_MORE = re.compile(r"\s*(read more|continue reading|full story)\s*$", re.I)


def parse_card_date(text):
    """Parse the human date printed on an index card, e.g. "August 13, 2026".

    parse_date() covers RFC-2822 and ISO, which is everything a feed serves and none of what
    a rendered page shows, so scraped cards need their own small parser.
    """
    for fmt in ("%B %d, %Y", "%d %B %Y", "%B %Y", "%b %d, %Y", "%d %b %Y"):
        try:
            return dt.datetime.strptime(text, fmt).replace(tzinfo=dt.timezone.utc)
        except ValueError:
            continue
    return None


def scrape_index(url):
    """Extract {headline: (direct_url, date_or_None)} from an outlet's index page."""
    doc = fetch(url).decode("utf-8", "replace")
    host = urllib.parse.urlsplit(url).netloc
    found = {}
    for href, inner in A_TAG.findall(doc):
        if href.startswith(("#", "mailto:", "javascript:")):
            continue
        full = clean_url(urllib.parse.urljoin(url, href))
        if urllib.parse.urlsplit(full).netloc != host:
            continue
        slug = urllib.parse.urlsplit(full).path.rstrip("/").rsplit("/", 1)[-1]
        if slug.count("-") < 2:
            continue
        # Pull the date out before the heading narrows what we are looking at: the date
        # usually sits in the card's meta row, a sibling of the heading rather than inside it.
        when = None
        dm = CARD_DATE.search(html_mod.unescape(TAGS.sub(" ", inner)))
        if dm:
            when = parse_card_date(re.sub(r"\s+", " ", dm.group(0)).strip())
        heading = CARD_HEADING.search(inner)
        raw = heading.group(1) if heading else inner
        txt = html_mod.unescape(TAGS.sub(" ", raw))
        txt = LABEL.sub("", re.sub(r"\s+", " ", txt).strip()).rstrip(". ")
        txt = READ_MORE.sub("", txt).strip()
        if len(txt) < 25:
            continue
        found.setdefault(txt, (full, when))
    return found


def build_link_index(scrapes):
    """Title-keyed map used to swap Google News redirects for direct links."""
    index = {}

    def one(entry):
        try:
            return {title_key(t): u for t, (u, _when) in scrape_index(entry[1]).items()}
        except Exception:  # noqa: BLE001
            return {}

    with futures.ThreadPoolExecutor(max_workers=8) as pool:
        for part in pool.map(one, scrapes):
            index.update(part)
    return index


_OG_DESC_RE = re.compile(
    r'<meta[^>]+(?:property|name)=["\'](?:og:|twitter:)?description["\'][^>]+content=["\']([^"\']+)', re.I)
_META_FIRST_RE = re.compile(
    r'<meta[^>]+content=["\']([^"\']{60,})["\'][^>]+(?:property|name)=["\'](?:og:|twitter:)?description["\']', re.I)
_PARA_RE = re.compile(r"<p[^>]*>(.*?)</p>", re.I | re.S)


def fetch_lede(url, max_len=300):
    """The article's own standfirst: og:description if substantial, else the first real <p>.

    For the ranking sheet, and only for stories whose feed supplied no usable summary - the
    lede is the one line of body text worth a fetch. Returns None on any failure: a lede is
    an enrichment, never a dependency, so no caller should have to guard it.
    """
    try:
        body = fetch(url, retry_uas=1)
        if isinstance(body, bytes):
            body = body.decode("utf-8", "replace")
    except Exception:  # noqa: BLE001
        return None
    m = _OG_DESC_RE.search(body) or _META_FIRST_RE.search(body)
    text = m.group(1) if m and len(m.group(1)) >= 60 else ""
    if not text:
        for para in _PARA_RE.findall(body[:60000]):
            plain = re.sub(r"<[^>]+>", " ", para)
            plain = re.sub(r"\s+", " ", plain).strip()
            if len(plain) >= 80:
                text = plain
                break
    if not text:
        return None
    text = re.sub(r"\s+", " ", html_mod.unescape(text)).strip()
    # A cookie banner or soft-404 is worse than nothing - it silently misdescribes the story.
    if re.search(r"cookies?|javascript|subscribe to continue|page not found|access denied",
                 text, re.I):
        return None
    return text[:max_len] or None


# Option 1 (Chris, 24.08.2026): the standfirst alone is one sentence, and one sentence cannot
# tell a report from an argument. This returns the standfirst PLUS the opening body paragraphs,
# which is where the inverted pyramid puts the news - a report's first 150 words state what
# happened, an essay's first 150 words are still clearing its throat. Deliberately NOT the full
# article: a mean page is ~4,760 words including boilerplate, so full text for a day's 1,056
# fetchable candidates is ~6-7M tokens, and the tail of an article is where commentary lives -
# the exact material that made body-text keyword scoring reward opinion on 18.08.2026.
# Blocks that are never article prose. Stripped before paragraph extraction rather than
# filtered afterwards: on 25.08.2026, 17% of cached openings carried nav or script residue
# ("Log In Subscribe The Christian Post", "'); } else { $(this).addClass(...)"), and every
# one of them came from markup a content-based filter can only guess at after the fact.
# Removing the container is exact where matching the text is not.
_CHROME_BLOCK_RE = re.compile(
    r"<(script|style|noscript|nav|header|footer|aside|form|figcaption)\b[^>]*>.*?</\1\s*>",
    re.I | re.S)

# Nav furniture that survives inside <p>. Kept deliberately literal - these are strings a
# newsroom template emits, not words a reporter writes. "newsletter"/"sign up" were already
# here before 25.08.2026 and stay, even though they can appear in real prose: a paragraph
# that mentions them is nearly always the signup box.
_PARA_JUNK_RE = re.compile(
    r"cookies?|javascript|subscribe to continue|sign up|newsletter"
    r"|all rights reserved|follow us on"
    r"|outdated browser|please upgrade your browser|log ?in|sign in"
    r"|toggle menu|skip to (?:main )?content|search for:"
    r"|terms of (?:service|use)|privacy policy|share this (?:article|story)"
    r"|advertisement|most read|related articles?|read more:", re.I)

# Script residue that reaches the text layer when JS is inlined without a <script> wrapper.
# Detected structurally - punctuation density no sentence of English has.
_CODEY_RE = re.compile(r"[{}();]\s*[{}();]|\$\(|=>|function\s*\(|\.addClass|var\s+\w+\s*=")


def _is_prose(plain):
    """True when a paragraph reads like article text rather than page furniture."""
    if len(plain) < 80:
        return False
    if _PARA_JUNK_RE.search(plain):
        return False
    if _CODEY_RE.search(plain):
        return False
    # A real paragraph is mostly letters and spaces. Menus and data dumps are not.
    letters = sum(c.isalpha() or c.isspace() for c in plain)
    return letters / len(plain) >= 0.80


# Sites that serve an empty app shell to a plain HTTP fetch and build the article in the
# browser. Free to read, not paywalled, no 403 - the text is public and we simply cannot
# parse it without running their JavaScript. Rendering these is not defeating anything.
#
# Explicitly an allowlist, and PAYWALLED ITEMS ARE NEVER RENDERED (see the guard in
# fetch_article_rendered). A headless browser pointed at a site that answers 403 or demands
# payment is a way past an access control, which is a different act from this one and not
# one this pipeline does. Chris, 25.08.2026: the Telegraph and The Australian stay out.
JS_RENDERED_HOSTS = ("brusselstimes.com", "tvpworld.com")

_CHROME_PATHS = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser",
)


def _chrome():
    for p in _CHROME_PATHS:
        if os.path.exists(p):
            return p
    return None


def needs_rendering(url, paywalled=False):
    """True only for a free, known client-rendered host."""
    if paywalled:
        return False
    host = urllib.parse.urlparse(url or "").netloc.lower()
    return any(host == h or host.endswith("." + h) for h in JS_RENDERED_HOSTS)


def fetch_article_rendered(url, timeout=90):
    """Article HTML after the page's own JavaScript has run, via headless Chrome.

    Added 25.08.2026 for brusselstimes.com and tvpworld.com, both of which return the same
    app shell for every path - /feed, /amp and the article URL are byte-identical - so there
    is no RSS to read and no API to call. Chrome is already installed and --dump-dom needs
    no extra dependency; if it is absent this returns None and the caller carries on.

    Never called for a paywalled item: see needs_rendering.
    """
    exe = _chrome()
    if not exe:
        return None
    try:
        out = subprocess.run(
            [exe, "--headless", "--disable-gpu", "--no-sandbox",
             "--blink-settings=imagesEnabled=false", "--disable-extensions",
             "--virtual-time-budget=8000", "--dump-dom", url],
            capture_output=True, timeout=timeout).stdout
        return out.decode("utf-8", "replace") or None
    except Exception:  # noqa: BLE001
        return None


def fetch_article_preview(url, max_len=600, paras=2):
    """The public preview of a PAYWALLED article: og:description + the opening paragraphs.

    Added 25.08.2026, for the ~9% of leads behind a paywall. Those were skipped entirely
    before, so the commentary outlets Chris picks from most - Spectator, Telegraph, Times,
    Critic, UnHerd - reached the ranker as bare headlines. That is the asymmetry
    TEXT_SIGNAL_WEIGHT was zeroed for on 18.08.2026: judging on text you can only read for
    the outlets that don't charge is a penalty on being readable.

    Deliberately capped far below fetch_article_opening, and the cap is the point, not a
    performance choice. Several metered paywalls (Spectator, UnHerd, Catholic Herald tested
    on 25.08.2026) ship the WHOLE article in the HTML and hide it behind a client-side
    overlay - 4,400 chars were there for the taking. Taking them would be circumventing the
    paywall whether or not any trick is involved. What this returns instead is the preview
    the publisher already exposes to search engines and social cards, plus the opening any
    reader sees before the wall. That is enough to rank a story and not enough to read it.

    Outlets that refuse programmatic access are left alone. The Telegraph answers 402
    Payment Required on its RSS; a 402 is a price, not an obstacle to route around.
    """
    try:
        body = fetch(url, retry_uas=1)
        if isinstance(body, bytes):
            body = body.decode("utf-8", "replace")
    except Exception:  # noqa: BLE001
        return None
    chunks = []
    m = _OG_DESC_RE.search(body) or _META_FIRST_RE.search(body)
    if m and len(m.group(1)) >= 60 and not _PARA_JUNK_RE.search(m.group(1)):
        chunks.append(m.group(1))
    body = _CHROME_BLOCK_RE.sub(" ", body)
    for para in _PARA_RE.findall(body[:200000]):
        plain = re.sub(r"<[^>]+>", " ", para)
        plain = re.sub(r"\s+", " ", plain).strip()
        if not _is_prose(plain) or plain in chunks:
            continue
        chunks.append(plain)
        if len(chunks) >= paras + 1:
            break
    text = re.sub(r"\s+", " ", html_mod.unescape(" ".join(chunks))).strip()
    if not text or len(text) < 60:
        return None
    if re.search(r"page not found|access denied|are you a robot|enable javascript",
                 text, re.I):
        return None
    return text[:max_len]


def fetch_article_opening(url, max_len=4000, paras=10):
    """Standfirst + the first `paras` substantial body paragraphs. None on any failure.

    Depth raised from 1200 chars / 3 paragraphs on 25.08.2026 (Chris: rank on the article
    text, not the headline). 29% of openings cached at the old depth hit the 1200 cap, so
    the text most likely to be truncated was the text with most to say. What a ranker needs
    is usually in the first half-dozen paragraphs - the fact a headline hides, like whether
    a school attacker was an immigrant - so this fetches deep, not whole.
    """
    body = None
    if needs_rendering(url):
        body = fetch_article_rendered(url)
    if body is None:
        try:
            body = fetch(url, retry_uas=1)
            if isinstance(body, bytes):
                body = body.decode("utf-8", "replace")
        except Exception:  # noqa: BLE001
            return None
    chunks = []
    m = _OG_DESC_RE.search(body) or _META_FIRST_RE.search(body)
    if m and len(m.group(1)) >= 60 and not _PARA_JUNK_RE.search(m.group(1)):
        chunks.append(m.group(1))
    body = _CHROME_BLOCK_RE.sub(" ", body)
    for para in _PARA_RE.findall(body[:400000]):
        plain = re.sub(r"<[^>]+>", " ", para)
        plain = re.sub(r"\s+", " ", plain).strip()
        if not _is_prose(plain):
            continue
        if plain not in chunks:
            chunks.append(plain)
        if len(chunks) >= paras + 1:
            break
    text = re.sub(r"\s+", " ", html_mod.unescape(" ".join(chunks))).strip()
    if not text or len(text) < 80:
        return None
    if re.search(r"page not found|access denied|are you a robot|enable javascript",
                 text, re.I):
        return None
    return text[:max_len]


# ---------------------------------------------------------------------------
# Seen store
# ---------------------------------------------------------------------------
def load_seen():
    try:
        with open(SEEN_DB) as fh:
            return json.load(fh)
    except (ValueError, OSError):
        return {}


def save_seen(seen):
    cutoff = (dt.datetime.now(dt.timezone.utc)
              - dt.timedelta(days=SEEN_RETENTION_DAYS)).isoformat()
    pruned = {k: v for k, v in seen.items() if v >= cutoff}
    tmp = SEEN_DB + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(pruned, fh)
    os.replace(tmp, SEEN_DB)


# --- cut store -------------------------------------------------------------
# Stories that were picked but did not survive a section cap. These are DROPPED from
# later sweeps outright, not kept and flagged like published ones.
#
# Chris, 18.08.2026: "if they didn't make the first cut they're not good enough for the
# following day's briefing". The 13.08 rule that a repeat is the curator's choice is about
# stories that actually ran - a running story can legitimately continue. A story that lost
# to the cap is a quality judgement already made, and re-reading it every morning only
# spends attention on news that has since aged.
#
# Kept separate from seen.json on purpose: same key space, different meaning, so neither
# store has to encode two states in one timestamp, and losing this file degrades to the old
# flag-and-keep behaviour rather than to something wrong.
def load_cut():
    try:
        with open(CUT_DB) as fh:
            return json.load(fh)
    except (ValueError, OSError):
        return {}


def save_cut(cut):
    cutoff = (dt.datetime.now(dt.timezone.utc)
              - dt.timedelta(days=SEEN_RETENTION_DAYS)).isoformat()
    pruned = {k: v for k, v in cut.items() if v >= cutoff}
    tmp = CUT_DB + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(pruned, fh)
    os.replace(tmp, CUT_DB)


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=int, default=None)
    ap.add_argument("--json", metavar="PATH")
    ap.add_argument("--mark", action="store_true",
                    help="record every swept item as seen. Rarely wanted: marking is "
                         "compose.py's job, so that only PUBLISHED stories are "
                         "suppressed and unused candidates stay available tomorrow")
    ap.add_argument("--no-mark", action="store_true",
                    help="accepted and ignored; not marking is now the default")
    ap.add_argument("--include-seen", action="store_true")
    ap.add_argument("--no-resolve", action="store_true",
                    help="skip scraping index pages to resolve Google News links")
    ap.add_argument("--no-decode", action="store_true",
                    help="skip asking Google to decode the redirects that index scraping "
                         "could not resolve. Roughly 10 minutes on a heavy day; skipping it "
                         "sends ~40%% of leads to the ranker with no article text")
    ap.add_argument("--decode-workers", type=int, default=8,
                    help="concurrency for redirect decoding (default 8)")
    args = ap.parse_args()

    # 36h by default so nothing slips through the gap between runs; the overlap is
    # harmless because seen.json drops anything a previous edition already used.
    # Mondays reach back to Friday morning to cover the weekend.
    now = dt.datetime.now(dt.timezone.utc)
    hours = args.hours or (84 if now.weekday() == 0 else 36)
    cutoff = now - dt.timedelta(hours=hours)

    feeds, scrapes, blocked = load_feeds()
    seen = {} if args.include_seen else load_seen()

    link_index = {} if args.no_resolve else build_link_index(scrapes)
    items, errors = [], []
    started = time.monotonic()

    with futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        jobs = {pool.submit(fetch, url): (cat, title, url, mode, dom)
                for cat, title, url, mode, dom in feeds}
        timed_out = 0
        for job in futures.as_completed(jobs):
            cat, ftitle, furl, mode, fdom = jobs[job]
            # A source may declare a longer window than the sweep's. Never a SHORTER one:
            # max() keeps Monday's 84h from being cut back to a source's 48h.
            fwin = FEED_WINDOWS.get((ftitle or "").strip().lower(), 0)
            fcutoff = (now - dt.timedelta(hours=max(fwin, hours))) if fwin else cutoff
            if time.monotonic() - started > DEADLINE:
                job.cancel()
                timed_out += 1
                continue
            try:
                if mode.startswith("scrapesrc"):
                    # No RSS at all: read the index page. Where the card prints a date we
                    # now use it; where it does not, freshness still comes from the
                    # seen-cache diff (new link = new story).
                    entries = [{"title": t, "link": u, "date": when, "author": "",
                                "source": ftitle, "feed_title": ftitle}
                               for t, (u, when) in scrape_index(furl).items()]
                else:
                    entries = parse_feed(job.result())
            except Exception as exc:  # noqa: BLE001
                reason = str(exc) if isinstance(exc, (RuntimeError, ValueError)) \
                    else type(exc).__name__
                errors.append((ftitle, furl, reason[:24]))
                continue
            dateless = mode.startswith("scrapesrc")
            limit = MAX_PER_SCRAPE if dateless else MAX_PER_FEED
            kept_here = 0
            for e in entries:
                if kept_here >= limit:
                    break
                if not e["title"] or not e["link"]:
                    continue
                # A scraped card that prints its own date is treated exactly like a feed
                # item: honour the window. Only genuinely undated cards fall back to the
                # seen-cache diff. Without this an index page hands over its whole archive
                # as "new" - ADF International's newsroom put June and July press releases
                # into the 17.08.2026 sweep that way.
                if dateless and e["date"] is not None:
                    if e["date"] > now:
                        e["date"] = now
                    elif e["date"] < fcutoff:
                        continue
                if not dateless:
                    if e["date"] is None:
                        continue
                    # Magazines date pieces to a future issue (The Critic runs weeks
                    # ahead). A feed only lists what already exists, so treat a future
                    # date as "just published" rather than throwing the item away.
                    if e["date"] > now:
                        if (e["date"] - now).days > 120:
                            continue
                        e["date"] = now
                    elif e["date"] < fcutoff:
                        continue
                is_g = "news.google.com" in furl
                # Pass the feed's stated source: when it is present the tail can be matched
                # exactly instead of guessed, which is the only fully reliable path.
                # Runs for EVERY feed as of 20.08.2026, not just Google News. The EWTN
                # suffix Chris flagged came off a DIRECT feed, so the is_g guard meant it was
                # never even tested. The length and prose guards inside do the safety work.
                headline, suffix = strip_outlet_suffix(e["title"], e.get("source") or "")
                if mode in FILTERED_MODES and not KEYWORD_RE.search(headline):
                    continue
                link = clean_url(unwrap_link(e["link"]))
                outlet = (e["source"] or (suffix if is_g else "")
                          or ftitle or outlet_from_url(link))
                outlet = re.sub(r"\s+", " ", outlet).strip()[:44]
                if is_junk_title(headline, outlet):
                    continue
                blob = (outlet + " " + link).lower()
                if any(b in blob for b in blocked):
                    continue
                items.append({
                    "category": cat, "feed": ftitle, "gnews": is_g,
                    "publisher": outlet_from_url(e.get("source_url") or ""),
                    "headline": re.sub(r"\s+", " ", headline).strip(),
                    "url": link, "outlet": outlet,
                    "author": re.sub(r"\s+", " ", e["author"] or "").strip()[:40],
                    "paywalled": is_paywalled(link, fdom),
                    "published": (e["date"].astimezone(dt.timezone.utc).isoformat()
                                  if e["date"] else now.isoformat()),
                    "age_h": (None if dateless else
                              round((now - e["date"]).total_seconds() / 3600, 1)),
                    # Publisher topic labels, carried through for the classifier.
                    "categories": [c for c in (e.get("categories") or [])
                                   if c and c.lower() != "uncategorized"][:8],
                    "summary": (e.get("summary") or "")[:300],
                })
                kept_here += 1
        if timed_out:
            errors.append(("(%d feeds unfinished at deadline)" % timed_out, "-", "deadline"))

    # Resolve Google News redirects to direct publisher URLs. Two sources: the
    # scraped index pages, plus every direct link already in this sweep (free -
    # the same story often arrives via both a real feed and a Google alert).
    for it in items:
        if not it["gnews"]:
            link_index.setdefault(title_key(it["headline"]), it["url"])
    resolved = 0
    for it in items:
        if it["gnews"]:
            direct = link_index.get(title_key(it["headline"]))
            if direct and "news.google.com" not in direct:
                it["url"] = direct
                resolved += 1

    # Then ask Google itself for whatever title-matching could not reach.
    #
    # Until 25.08.2026 the two lines above WERE the sweep's whole resolver: a redirect
    # became a publisher URL only if the same headline happened to arrive via a second
    # feed. That resolved 140 of 722 on 25.08, and the batchexecute decoder - which
    # resolves 100% on test - ran nowhere but compose.py, on the ~250 items already
    # picked. So ranking saw 388 leads as bare redirects, and a redirect has no page to
    # fetch: those stories reached the ranker as headlines, and the decoder that could
    # have fixed it only ran after they had already been judged.
    #
    # Costs roughly 1.2s per redirect at this concurrency, so ~10 minutes on a heavy day.
    # That is real, and it buys two things: article text for the ranker, and a dedup pass
    # below that can now match a redirect against the direct link to the same story.
    # resolve_items caches successes only - never failures (see its comment).
    decoded = 0
    if not args.no_decode:
        import resolve as _resolve   # local: resolve imports this module
        still = [it for it in items if "news.google.com" in it["url"]]
        if still:
            decoded, _ = _resolve.resolve_items(
                still, workers=args.decode_workers)

    # Dedup: direct links beat Google redirects; then newest wins.
    items.sort(key=lambda i: ("news.google.com" in i["url"], i["published"]))
    cut = load_cut()
    by_url, by_title, kept, already, cut_out = set(), set(), [], 0, 0
    for it in items:
        uk, tk = url_key(it["url"]), title_key(it["headline"])
        if uk in by_url or (tk and tk in by_title):
            continue
        # Lost to a section cap in an earlier edition: drop, do not flag. See load_cut().
        if uk in cut:
            cut_out += 1
            by_url.add(uk)
            if tk:
                by_title.add(tk)
            continue
        if uk in seen:
            already += 1
            it["seen_on"] = (seen[uk] or "")[:10]   # keep it, but flagged
        by_url.add(uk)
        if tk:
            by_title.add(tk)
        kept.append(it)

    unresolved = sum(1 for i in kept if "news.google.com" in i["url"])
    kept.sort(key=lambda i: (i["category"], i["published"]))

    out = sys.stdout
    out.write("BREAKFAST BRIEFING FEED SWEEP\n")
    out.write("generated %s | window last %dh (since %s)\n"
              % (now.strftime("%Y-%m-%d %H:%M UTC"), hours,
                 cutoff.strftime("%a %d %b %H:%M UTC")))
    out.write("feeds %d ok / %d failed | %d fresh -> %d after dedup "
              "| %d already published in an earlier edition (kept, flagged) "
              "| %d dropped as cut by an earlier cap "
              "| gnews: %d matched to a direct link, %d decoded via Google, "
              "%d still redirects\n"
              % (len(feeds) - len(errors), len(errors), len(items), len(kept),
                 already, cut_out, resolved, decoded, unresolved))
    out.write("paywalled items (marked £, use \"(£)\" after the outlet name): %d\n"
              % sum(1 for i in kept if i["paywalled"]))
    out.write("cols: N | headline | url | outlet | author | age  "
              "(£ = paywalled, age 'new' = no date, fresh since last run)\n\n")

    n, current = 0, None
    for it in kept:
        if it["category"] != current:
            current = it["category"]
            out.write("### %s\n" % current)
        n += 1
        out.write("%d | %s | %s | %s%s | %s | %s\n" % (
            n, it["headline"], it["url"],
            it["outlet"], " £" if it["paywalled"] else "",
            it["author"] or "-",
            "new" if it["age_h"] is None else "%sh" % it["age_h"]))

    if errors:
        out.write("\n### Unreachable feeds (%d)\n" % len(errors))
        for ftitle, furl, why in sorted(errors):
            out.write("- %s [%s] %s\n" % (ftitle[:40], why, furl[:72]))

    if args.json:
        with open(args.json, "w") as fh:
            json.dump({"generated": now.isoformat(), "window_hours": hours,
                       "items": kept, "errors": errors}, fh, indent=1)

    if args.mark:
        stamp = now.isoformat()
        for it in kept:
            seen[url_key(it["url"])] = stamp
        save_seen(seen)


if __name__ == "__main__":
    main()
