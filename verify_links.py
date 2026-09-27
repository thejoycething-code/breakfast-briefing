#!/usr/bin/env python3
"""Compare every href in a composed briefing against the hrefs in a Docs HTML export.

    python3 verify_links.py <exported doc .html> <composed briefing .html>

Exits 0 when every composed link is present in the doc byte-for-byte, 1 otherwise.

Href-to-href, whole. The first version of this check (inline in publish.sh) pulled bare URLs
out of the export with https?://[^\\s)\\]>"]+ and so cut every URL at its first ")": on
25.09.2026 a Jakarta Post link carrying utm_source=(direct) was reported MISSING from a doc
that held it exactly, and the tail stopped at 182/183. Docs' export HTML-escapes hrefs and
wraps some in a google.com/url?q= redirector; both are undone per href before comparing.
"""
import html
import re
import sys
from urllib.parse import unquote


def doc_targets(exported):
    """The set of real link targets in a Docs HTML export."""
    out = set()
    for h in re.findall(r'href="([^"]*)"', exported):
        h = html.unescape(h)
        m = re.match(r"https://www\.google\.com/url\?q=([^&]+)", h)
        out.add(unquote(m.group(1)) if m else h)
    return out


def wanted(composed):
    return [html.unescape(u) for u in re.findall(r'href="([^"]*)"', composed)]


def main(argv):
    if len(argv) != 3:
        sys.stderr.write(__doc__)
        return 2
    got = doc_targets(open(argv[1], encoding="utf-8", errors="replace").read())
    want = wanted(open(argv[2], encoding="utf-8", errors="replace").read())
    bad = [u for u in want if u not in got]
    print("  URLs %d/%d verified, %d corrupted" % (len(want) - len(bad), len(want), len(bad)))
    for u in bad[:20]:
        print("    MISSING:", u[:110])
    return 1 if bad or not want else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
