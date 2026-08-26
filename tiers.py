#!/usr/bin/env python3
"""Persistent record of what the ranker DECIDED about each story, keyed by url_key.

Built 25.08.2026, after a re-run of the 24.08 edition re-read all 1,112 leads to discover
that ~216 already had recorded tiers and the other ~896 had an implicit "no" that nothing
had written down. Chris: "Why does that cost repeat when you have the data?"

The gap this fills: picks.json records which items were tiered 1/2/3, as bare indexes into
one day's sweep. It cannot answer the only question a second pass actually needs -

    "have I already judged this story, and what did I decide?"

- because an index is meaningless against a different sweep, and because a story that was
  read and rejected leaves no trace at all. So every re-run re-derives judgement it already
  made, and the daily run re-judges the ~30 stories carried over from yesterday from scratch.

What is stored, per url_key:

    tier     1/2/3 as picked, or 0 for "was on the sheet and not picked" - the implicit
             no, made explicit. 0 is the whole point: without it, "considered and rejected"
             and "never seen" are the same absence.
    reason   optional one-line rationale. Only ever supplied for a minority of stories;
             absent is normal and means "no note", not "no reason".
    text_id  short hash of the article text the decision was made ON. A story whose text
             later arrives (a redirect decoded, a paywall preview added) is a NEW decision,
             not a settled one - see stale(). This is what stops the store from freezing a
             headline-only judgement in place once the text finally shows up.
    section, headline, outlet, date - for auditing by eye. Nothing reads them.

Deliberately keyed by url_key, not by index or headline: url_key survives across sweeps and
is what seen.json/resolved.json/openings.json already key on, so the stores line up.

NOT a substitute for seen.json. seen.json answers "did we publish this" and suppresses it;
this answers "did we judge this, and on what evidence". A tier-0 story is still available
to publish tomorrow - it was passed over, not used up.
"""
import hashlib
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
TIERS_DB = os.path.join(HERE, "tiers.json")
SCHEMA = 1


def text_id(text):
    """Short stable hash of the text a judgement was made on. Empty text -> 'none'."""
    t = (text or "").strip()
    if not t:
        return "none"
    return hashlib.sha1(t[:2000].encode("utf-8", "replace")).hexdigest()[:12]


def load(path=TIERS_DB):
    try:
        db = json.load(open(path))
    except (ValueError, OSError):
        return {"__schema__": SCHEMA}
    if db.get("__schema__") != SCHEMA:
        return {"__schema__": SCHEMA}
    return db


def save(db, path=TIERS_DB):
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(db, fh)
    os.replace(tmp, path)


def stale(db, key, text):
    """True when this story needs judging again.

    Unjudged, or judged on materially different evidence. The second half matters more than
    it looks: on 25.08.2026 the share of leads with article text went from 26% to 87% in one
    morning, so a store built the day before would have been full of headline-only verdicts
    that deserved revisiting. A decision made blind is not a decision to stand on.
    """
    rec = db.get(key)
    if not rec:
        return True
    return rec.get("text_id") != text_id(text)


def record(db, key, tier, text=None, reason=None, **meta):
    rec = {"tier": int(tier), "text_id": text_id(text)}
    if reason:
        rec["reason"] = reason
    for k in ("section", "headline", "outlet", "date"):
        if meta.get(k):
            rec[k] = meta[k]
    db[key] = rec
    return rec


def counts(db):
    out = {}
    for k, v in db.items():
        if k == "__schema__":
            continue
        out[v.get("tier", 0)] = out.get(v.get("tier", 0), 0) + 1
    return out
