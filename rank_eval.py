#!/usr/bin/env python3
"""Score importance() against the archived editions — does it rank what Chris kept, on top?

The question this answers, which nothing else in the pipeline could: if I change the scorer,
does the briefing's ranking get BETTER or merely different? Every archived day carries an
ordinal judgement of ~1,000 stories (tier 1/2/3 for picks, nothing for the rest), so a
proposed change can be replayed against every day at once instead of argued from one
remembered example.

    python3 rank_eval.py                  # score the current importance()
    python3 rank_eval.py --log "note"     # ...and append the result to rank_eval_log.txt

Workflow for a scoring change: run it, note the numbers, make the change, run it again. A
change that moves concordance down is a regression however good its reasoning sounded. Pair
it with testcases.txt, which holds the AXIOMS (outcome beats process); this holds the
day-relative judgement an ABOVE pair cannot express.

Labels, from picks.json and composed.json:

    3  picked tier 1     "must run"
    2  picked tier 2     "if there is room"
    1  picked tier 3     "filler for a thin section"
    0  not picked        the day's other ~600 placed, non-chaff candidates

A pick cut by a section cap KEEPS its tier: the cap is a volume constraint, not a verdict on
the story, so treating cut items as rejected would teach the scorer the wrong lesson. Flat
(pre-tier) picks files score every pick as 2, which still measures picked-versus-unpicked.

Metrics:

  concordance   over every pair of stories with DIFFERENT labels, the fraction importance()
                orders correctly (ties score 0.5). 0.50 is coin-flip, 1.00 perfect. This is
                the headline number: it is exactly "does the scorer agree with Chris".
  top-40        of the 40 highest-scoring stories, the fraction that were picked at all.
                Approximates the reading experience - the top of the sheet should not be
                full of things nobody wanted.
  tier-1 recall of the tier-1 stories, the fraction that reach the top decile by score.
                Catches the failure Chris named on 13.08.2026, four must-run stories ranked
                53rd to 88th.

WHAT CONCORDANCE IS NOT, established the hour this script was written. Replaying the three
substring bugs fixed on 18.08.2026 back into the scorer moved concordance the WRONG way:
restoring bare "freed" (which matched "freedom", handing +8 outcome to every religious-freedom
headline) scored +0.0031. The bug was accidentally a good predictor, because religious freedom
is a core beat and its stories get picked. So:

    concordance measures AGREEMENT WITH THE CURATOR'S REVEALED PREFERENCE, not correctness.
    A spurious feature that correlates with a favoured beat will score well.

Which means testcases.txt has veto power over this script, never the other way round. ABOVE
pairs encode axioms - an outcome outranks a process, "freedom" is not an outcome - and a change
that breaks one is wrong however much concordance it buys. Use this script to choose between
changes that are ALREADY defensible, and to catch changes that sound good and measure badly.

Read the absolute number with the same care. 0.607 on the first archived edition is only
modestly above the 0.500 a random scorer gets, and that is roughly correct: picks are made from
the sheet's article text, provenance rules, geographic balance and cross-section judgement, none
of which importance() models. It is a reading-order heuristic, not a curator. The number is
useful comparatively, between two scorers on the same corpus - not as a grade.

Flat (pre-tier) editions only separate picked from unpicked, which is a blunt two-level signal.
Tiered editions give four levels and a much sharper measurement, so early baselines should be
re-read once tiered days accumulate.
"""
import argparse
import glob
import gzip
import json
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fetch_feeds
import shortlist
from compose import ORDER, normalize_picks

ARCHIVE = os.path.join(HERE, "archive")
LOG = os.path.join(HERE, "rank_eval_log.txt")


def load_day(path):
    """Return (manifest, items, labels) for one archived day, or None if unusable."""
    man_path = os.path.join(path, "manifest.json")
    sweep_path = os.path.join(path, "sweep.json.gz")
    picks_path = os.path.join(path, "picks.json")
    if not all(os.path.exists(p) for p in (man_path, sweep_path, picks_path)):
        return None
    manifest = json.load(open(man_path))
    with gzip.open(sweep_path, "rt", encoding="utf-8") as fh:
        items = json.load(fh)["items"]
    picks, tiers = normalize_picks(json.load(open(picks_path)))

    # Same candidate basis as compose.py and the sheet: placed, not chaff. Anything the
    # classifier never placed was not a ranking decision, so it is not a ranking label.
    shortlist.SWEEP_WINDOW_H = manifest.get("window_hours") or 36
    for it in items:
        section, score = shortlist.classify(it["headline"], it.get("outlet") or "",
                                            it.get("categories"))
        it["_section"] = section
        it["_score"] = score
    rows = [it for it in items if it.get("_section")
            and not shortlist.is_chaff(it["headline"], it.get("outlet") or "",
                                       it.get("categories"))]
    shortlist.stamp_corroboration(rows)
    # Option 3's text signals, so a weight change is actually measurable here. Computed from
    # whatever text the archive holds (feed summary, plus any cached opening) - deliberately
    # NOT re-fetching: the eval must replay the day as it was, and a fetch today would give
    # the scorer information the morning did not have.
    # The cache is optional; the module is not. These were in one try/except and a missing
    # openings.json therefore disabled the signals altogether - which is why an option-3
    # weight change first measured as EXACTLY no difference on all four days. An inert
    # experiment reporting "no effect" is worse than one that fails loudly.
    import textsignals
    try:
        openings = json.load(open(os.path.join(HERE, "openings.json")))
    except (ValueError, OSError):
        openings = {}
    if textsignals:
        for it in rows:
            it["_sig"] = textsignals.signals(
                it["headline"],
                openings.get(fetch_feeds.url_key(it["url"]))
                or shortlist.real_summary(it))

    labels = {}
    for section in ORDER:
        for n in picks.get(section, []):
            tier = tiers.get(section, {}).get(n, 2)
            labels[n] = {1: 3, 2: 2, 3: 1}.get(tier, 2)
    return manifest, items, rows, labels


def score_day(items, rows, labels):
    """Concordance, top-40 precision and tier-1 recall for one day."""
    # _i is stamped by shortlist.main(), not present in a raw sweep, so index by position.
    pos = {id(it): i for i, it in enumerate(items)}
    scored = [(shortlist.importance(it), labels.get(pos[id(it)], 0)) for it in rows]
    if not scored:
        return None
    # Pairwise concordance over differing labels. ~500k pairs on a full day, fast enough that
    # an exact figure beats a sampled one.
    conc = ties = total = 0
    for idx, (sa, la) in enumerate(scored):
        for sb, lb in scored[idx + 1:]:
            if la == lb:
                continue
            total += 1
            # The score of the BETTER-labelled story must exceed the other's.
            hi, lo = (sa, sb) if la > lb else (sb, sa)
            if hi > lo:
                conc += 1
            elif hi == lo:
                ties += 1
    ranked = sorted(scored, key=lambda p: -p[0])
    top40 = sum(1 for _s, lab in ranked[:40] if lab > 0) / min(40, len(ranked))
    decile = max(1, len(ranked) // 10)
    t1 = [lab for _s, lab in scored if lab == 3]
    t1_in_decile = (sum(1 for _s, lab in ranked[:decile] if lab == 3) / len(t1)) if t1 else None
    return {
        "concordance": (conc + 0.5 * ties) / total if total else 0.0,
        "pairs": total,
        "top40": top40,
        "tier1_recall": t1_in_decile,
        "candidates": len(scored),
        "labelled": sum(1 for _s, lab in scored if lab > 0),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=0, help="only the N most recent editions")
    ap.add_argument("--log", metavar="NOTE", help="append the result to rank_eval_log.txt")
    ap.add_argument("--archive-dir", default=ARCHIVE,
                    help="where to read editions from (default: archive/)")
    args = ap.parse_args()

    paths = sorted(glob.glob(os.path.join(args.archive_dir, "2*")))
    if args.days:
        paths = paths[-args.days:]
    if not paths:
        sys.stderr.write("no archived editions in %s - run archive_day.py after a publish\n"
                         % args.archive_dir)
        return 2

    print("%-10s %6s %7s %6s  %11s %7s %8s" % (
        "day", "cands", "labelled", "tiers", "concordance", "top-40", "t1-recall"))
    results, dropped = [], 0
    for path in paths:
        loaded = load_day(path)
        if not loaded:
            print("%-10s  (incomplete archive, skipped)" % os.path.basename(path))
            continue
        manifest, items, rows, labels = loaded
        res = score_day(items, rows, labels)
        if not res:
            continue
        dropped += max(0, (manifest.get("picked") or 0) - res["labelled"])
        results.append(res)
        print("%-10s %6d %7d %6s  %10.3f %7.2f %8s" % (
            manifest["date"], res["candidates"], res["labelled"],
            "yes" if manifest.get("tiered") else "no", res["concordance"], res["top40"],
            "%.2f" % res["tier1_recall"] if res["tier1_recall"] is not None else "n/a"))

    if not results:
        return 1
    mean_conc = statistics.mean(r["concordance"] for r in results)
    mean_top = statistics.mean(r["top40"] for r in results)
    print("\n%d edition(s): concordance %.3f | top-40 precision %.2f"
          % (len(results), mean_conc, mean_top))
    if dropped:
        print("note: %d pick(s) sat outside the candidate basis and carry no label - picks "
              "rescued from the suppressed buckets were never sheet leads." % dropped)
    if len(results) == 1:
        print("One edition is a baseline, not a trend. The measurement itself is exact - same"
              "\ncorpus, same labels, so re-running gives the identical number and ANY"
              "\ndifference between two scorers on this day is real. What is unproven from one"
              "\nday is whether it GENERALISES: a random scorer scores 0.500 here with a"
              "\nseed-to-seed spread of 0.027, so day structure alone can move the number by"
              "\n~0.05. Treat a single-day gain under that as promising, not banked.")
    if args.log:
        with open(LOG, "a") as fh:
            fh.write("%s\tdays=%d\tconcordance=%.4f\ttop40=%.3f\t%s\n"
                     % (max(r for r in [os.path.basename(p) for p in paths]),
                        len(results), mean_conc, mean_top, args.log))
        print("logged to rank_eval_log.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
