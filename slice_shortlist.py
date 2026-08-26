#!/usr/bin/env python3
"""Split the day's candidates into slices for parallel review.

Ranking by keyword score decides which section an item belongs to but is a poor guide
to importance — a papal letter outscored a jailed Hong Kong publisher on 12.08.2026.
The fix Chris asked for is that every candidate is actually *read* and judged. Reading
850 items in one context is not practical, so this cuts them into slices that review
subagents take in parallel; each returns tier-ranked picks and the parent merges them.

    python3 slice_shortlist.py today.json --slices 8 --outdir /tmp/slices

Each slice file is self-contained: it carries the review brief, so a subagent needs no
other context. Items keep their original index, which is what compose.py consumes.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import regions
import shortlist as sl

BRIEF = """\
You are reviewing candidate stories for CitizenGO's daily "Breakfast Briefing" — a news
digest for a conservative Christian advocacy organisation working on life, family and
freedom across 30+ countries.

Read every line below and decide which stories belong in today's briefing. Judge each on
news value to that audience, not on keyword density.

INCLUDE
  - Substantive news: court rulings, legislation, official reports, arrests, deaths,
    institutional decisions, polling.
  - Argued commentary from outlets the team reads, even when the headline is allusive
    (spiked, The Critic, UnHerd, The Spectator, First Things, Public Discourse).
  - Persecution and religious-freedom reporting from anywhere in the world.
  - Multiple angles on a genuinely big story — two or three is fine and wanted.
  - A story that also ran yesterday, if it is still the running story. Repeats are allowed.

EXCLUDE
  - Press-release filler, listicles, devotional or saint-of-the-day pieces, fundraising
    appeals, broadcast schedules, celebrity and entertainment items, local crime with no
    wider significance, sports beyond the women's-category dispute.
  - Anything only tangentially connected to life, family, freedom, gender or the church.

PRECEDENCE
  - Where two lines cover the same story, prefer the higher-tier outlet: Telegraph, Times,
    Catholic Herald, Christian Today, Premier, Crux, spiked, The Spectator, LifeSiteNews,
    LifeNews, Live Action, SPUC, Right To Life, ICC, ADF, EWTN, OSV News, National Catholic
    Register, Catholic World Report, Bitter Winter, WORLD, The Critic, UnHerd, Reduxx.
  - Items marked ↗ link to a Google News redirect. Prefer an unmarked item on the same
    story; only take a ↗ if nothing direct covers it.
  - £ marks a paywalled outlet. Those are wanted, not avoided.

RETURN — nothing but lines in this exact form, best first, no preamble or commentary:
  <index> | <tier 1-3> | <six words on why>
Tier 1 = must appear in today's briefing. Tier 2 = include if there is room.
Tier 3 = weak, include only to fill a thin section. Omit anything you would not run.
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json_path")
    ap.add_argument("--slices", type=int, default=8)
    ap.add_argument("--outdir", default="/tmp/slices")
    args = ap.parse_args()

    items = json.load(open(args.json_path))["items"]
    rows = []
    for idx, it in enumerate(items):
        if sl.is_chaff(it["headline"], it["outlet"] or ""):
            continue
        section, score = sl.classify(it["headline"], it["outlet"] or "")
        if section is None:
            continue
        it["_i"] = idx
        it["_score"] = score
        it["_section"] = section
        rows.append(it)

    # Slice by section so each reviewer sees one subject and can compare like with like.
    by_section = {}
    for it in rows:
        by_section.setdefault(it["_section"], []).append(it)

    os.makedirs(args.outdir, exist_ok=True)
    plan, n = [], 0
    for section in sl.SECTION_NAMES:
        group = by_section.get(section, [])
        if not group:
            continue
        group.sort(key=lambda i: (-sl.rank_score(i), i["age_h"] or 0))
        # Reviewers see a spread of mastheads first rather than eight Critic pieces; the
        # overflow still follows, so nothing is hidden from the read.
        top, over = sl.diversify(group, 3)
        group = top + over
        marks = sl.cluster_duplicates(group)
        # split a large section across several reviewers
        per = max(60, -(-len(group) // max(1, args.slices)))
        for start in range(0, len(group), per):
            chunk = group[start:start + per]
            n += 1
            path = os.path.join(args.outdir, "slice%02d.txt" % n)
            with open(path, "w") as fh:
                fh.write(BRIEF)
                fh.write("\nSECTION: %s  (%d candidates%s)\n"
                         % (section, len(chunk),
                            ", part %d" % (start // per + 1) if len(group) > per else ""))
                fh.write("cols: index | region | headline | outlet | age\n\n")
                for it in chunk:
                    fh.write("%d | %s | %s | %s%s%s | %s%s%s\n" % (
                        it["_i"], regions.region(it["headline"], it["outlet"]),
                        it["headline"], it["outlet"],
                        " £" if it["paywalled"] else "",
                        " ↗" if "news.google.com" in it["url"] else "",
                        "new" if it["age_h"] is None else "%sh" % it["age_h"],
                        "  [ran %s]" % it["seen_on"][5:] if it.get("seen_on") else "",
                        marks.get(id(it), "")))
            plan.append((path, section, len(chunk)))

    print("%d candidates -> %d slices in %s" % (len(rows), len(plan), args.outdir))
    for path, section, count in plan:
        print("  %-28s %-32s %d items" % (os.path.basename(path), section, count))


if __name__ == "__main__":
    main()
