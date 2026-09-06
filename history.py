"""What actually appeared in recent editions, read back off the archive.

Built 27.08.2026, when Chris asked for story clustering across days. The reason it was
needed is worth keeping in front of whoever reads this next.

`seen.json` records a URL and the date it ran, and shortlist.py turns that into the [ran DD]
flag. That only ever caught a repeat when the publisher reused the URL. On 25.08.2026 Right
To Life published "Assisted suicide - Just over 2 weeks left"; we ran it. On 27.08 they
republished the identical article at the same slug with "-2" appended, and to a URL-keyed
store that is a story nobody has ever seen - so it arrived with no flag and went into the
edition. The [ran] flag was never as reliable as it looked.

So this module answers a different question: not "have we published this URL" but "what
stories have we published lately", in a form that can be compared as prose. shortlist.ran_before
does the comparing; everything here is plumbing.

Deliberately NOT a new state file. The archive is already the record of what was published
(archive_day.py writes it, and it is the only copy of a day's judgement), so deriving the
index from it cannot drift out of step with the editions themselves the way a parallel cache
would. The cost is reading a few hundred KB of gzip per run, which is under a second.

The `composed` list is what the reader joins against, NOT `picks`. A pick that a section cap
cut never reached the document, and a story we chose but did not print has not run.
"""

import datetime as dt
import glob
import gzip
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ARCHIVE = os.path.join(HERE, "archive")

# A week. A campaign peg recurs within days - Right To Life's countdown, a march, a bill's
# second reading - and past that a story returning is usually a new development rather than
# the same piece again. Cheap to widen if a repeat slips through at 8 days.
HISTORY_DAYS = 7


def _editions(days, before=None, archive_dir=ARCHIVE):
    """Dated edition directories, newest first, excluding `before` itself."""
    found = []
    for path in glob.glob(os.path.join(archive_dir, "[0-9]" * 8)):
        date = os.path.basename(path)
        if before and date >= before:
            continue
        found.append((date, path))
    return sorted(found, reverse=True)[:days]


def load_history(days=HISTORY_DAYS, before=None, archive_dir=ARCHIVE):
    """[{date, section, headline, outlet, key}] for stories that ACTUALLY APPEARED.

    `before` is a YYYYMMDD string - today's date - so an edition never counts itself as its
    own history. Re-running a past day works the same way: pass that day and it sees only
    what came before it, which is what made the 25.08 -> 27.08 case reproducible at all.

    Every failure here is non-fatal and silent by design at the item level, but the CALLER is
    expected to report how many editions were loaded. A history that silently came back empty
    would turn this whole feature into a no-op that still looks like it is working, which is
    the same class of bug as a suppression nobody prints.
    """
    out = []
    for date, path in _editions(days, before, archive_dir):
        composed = os.path.join(path, "composed.json")
        sweep = os.path.join(path, "sweep.json.gz")
        if not (os.path.exists(composed) and os.path.exists(sweep)):
            continue
        try:
            with open(composed) as fh:
                sections = (json.load(fh) or {}).get("composed") or {}
            with gzip.open(sweep, "rt") as fh:
                blob = json.load(fh)
            rows = blob.get("items") if isinstance(blob, dict) else blob
        except (OSError, ValueError, KeyError):
            continue
        if not rows:
            continue
        for section, idxs in sections.items():
            for n in idxs:
                try:
                    row = rows[n]
                except (IndexError, TypeError, KeyError):
                    continue
                headline = (row.get("headline") or "").strip()
                if not headline:
                    continue
                out.append({
                    "date": date,
                    "section": section,
                    "headline": headline,
                    "outlet": row.get("outlet") or "",
                    "key": url_key(row.get("url") or ""),
                })
    return out


def editions_loaded(days=HISTORY_DAYS, before=None, archive_dir=ARCHIVE):
    """Dates that load_history could actually read - for the line the caller prints."""
    dates = []
    for date, path in _editions(days, before, archive_dir):
        if (os.path.exists(os.path.join(path, "composed.json"))
                and os.path.exists(os.path.join(path, "sweep.json.gz"))):
            dates.append(date)
    return dates


def url_key(url):
    """Same normalisation mark_published.py uses, so the two stores can be compared."""
    u = re.sub(r"^https?://(www\.)?", "", (url or "").strip().lower())
    return u.rstrip("/").split("?")[0].split("#")[0]


def edition_date(data):
    """YYYYMMDD from the SWEEP's own "generated" stamp, never the clock.

    Same convention as archive_day.py, and for the same reason: re-running an older sweep has
    to see the history that existed then, not the history that exists now. Without this a
    re-run of 27.08 would find 27.08's own edition in its past and flag every story as a
    repeat of itself.
    """
    gen = (data or {}).get("generated") or ""
    try:
        return dt.datetime.fromisoformat(gen).strftime("%Y%m%d")
    except (TypeError, ValueError):
        return dt.date.today().strftime("%Y%m%d")
