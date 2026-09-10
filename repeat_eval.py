#!/usr/bin/env python3
"""Score the CROSS-DAY repeat check against the archive — does it catch what actually repeated?

Companion to rank_eval.py, and it exists for the same reason. shortlist.ran_before shipped on
27.08.2026 with CROSSDAY_OVERLAP=0.70 and CROSSDAY_WORDS=6, and those two numbers were set by
eyeballing one morning's fifty flags. That is precisely the "argued from one remembered
example" failure rank_eval.py was built to end, reproduced in a new function the same day.

    python3 repeat_eval.py                 # score the current matcher
    python3 repeat_eval.py --log "note"    # ...and append to repeat_eval_log.txt
    python3 repeat_eval.py --misses        # print what it missed and what it wrongly flagged

Workflow for a matching change: run it, note the numbers, make the change, run it again.


THE LABELS, and why there are three kinds
-----------------------------------------
The obvious idea - "a story published on two consecutive days under a different URL is a
positive" - is WRONG, and was discarded before this file was written. Two unrelated stories
published on consecutive days also have different URLs. That rule labels the entire cross
product.

So, three sources, weakest to strongest:

  GOLD    testcases.txt RANBEFORE / NOTRANBEFORE pairs. Chris's own judgement, written down,
          non-circular. Tiny (a dozen), and they have VETO: a change that improves every
          number below while breaking one gold pair is a regression, exactly as testcases.txt
          overrides rank_eval.py.

  URL     the same URL published in two different editions. Unambiguous - one URL is one
          article - genuinely cross-day, and completely independent of any matching code.
          Measures RECALL on the easy case: has the wording drifted so far the matcher can no
          longer see its own past self? Small but free.

  CLUSTER pairs of headlines that the WITHIN-DAY clusterer put in one cluster on one day,
          replayed as though they had appeared on different days. This is the large sample
          and the only one that tests the case that matters: same story, different outlets,
          different wording. Negatives are pairs from different clusters in the same section
          on the same day, which is the population the matcher must not confuse.

          CIRCULARITY, stated plainly because it would otherwise be hidden: these labels come
          from same_story, which shares sig_words and is_development_of with ran_before. It is
          not independent evidence. It is a large, cheap, consistent sample of the right SHAPE
          of pair, and it is the reason GOLD keeps the veto. A change that moves CLUSTER up
          while moving URL or GOLD down is not an improvement, it is overfitting to a
          relative of the thing being measured.
"""

import argparse
import collections
import datetime as dt
import itertools
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import history            # noqa: E402
import shortlist          # noqa: E402

LOG = os.path.join(HERE, "repeat_eval_log.txt")
CASES = os.path.join(HERE, "testcases.txt")
# Enough negatives to make precision meaningful without the pair count exploding: the cluster
# sample is quadratic in cluster size, so it is capped per day rather than taken whole.
NEG_PER_DAY = 400
SEED = 20260827


# The union entity index, built once over every headline the eval will compare. Production
# builds the same thing over today's corpus plus the recent editions; the point in both cases
# is that document frequency has to be measured over ONE corpus for "distinctive" to mean
# anything. Set by _build_index() before scoring.
ENTS = None


def _match(today_headline, past_headline, section="Life"):
    """Does ran_before link these two? One call site so every metric agrees."""
    return bool(shortlist.ran_before(
        {"headline": today_headline, "_section": section},
        [{"date": "20260101", "section": section,
          "headline": past_headline, "outlet": "x", "key": ""}],
        ents=ENTS))


def _build_index(*pairsets):
    """One index over every headline in every labelled set, so DF spans the whole window."""
    seen, corpus = set(), []
    for pairs in pairsets:
        for pair in pairs:
            for h in pair[:2]:
                if h not in seen:
                    seen.add(h)
                    corpus.append({"headline": h})
    return shortlist.entity_index(corpus)


# --- GOLD -----------------------------------------------------------------------------------

def gold_pairs():
    """Chris's own RANBEFORE / NOTRANBEFORE assertions, read straight out of testcases.txt."""
    out, skipped = [], []
    try:
        with open(CASES) as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                kind, _, rest = line.partition("|")
                kind = kind.strip()
                if kind not in ("RANBEFORE", "NOTRANBEFORE"):
                    continue
                today, _, past = rest.partition("::was::")
                # Strip run_tests' ::entity:: marker. It tells THAT harness to build a
                # two-document index for the case; here the index is always on, because that
                # is what production does. Leaving the marker in the string made it a word in
                # the comparison, which is how it first showed up as a phantom GOLD failure.
                # ::entity:: cases are excluded from GOLD, not merely unmarked. They assert
                # that the ENTITY ARM fires, and whether it fires depends on the document
                # frequency of a token in whatever corpus is loaded - so the same pair can be
                # correct here and correct-but-opposite in run_tests' two-document index, and
                # neither is wrong. A veto has to be corpus-independent or it is not a veto.
                # run_tests still checks these at the pair level; what they cannot do is
                # overrule a measurement whose whole subject is the corpus.
                if "::entity::" in past:
                    skipped.append(today.strip())
                    continue
                # ::sections:: is the same bug one marker later (10.09.2026). It was added on
                # 08.09.2026 so run_tests could assert the cross-section case, repeat_eval was
                # not taught about it, and the marker text became words in the comparison -
                # exactly as ::entity:: had. The result was two GOLD failures that were not
                # real, reported as a VETO, every time the job ran.
                #
                # Unlike ::entity:: these are NOT excluded: the section is genuinely
                # irrelevant here, because ran_before stopped guarding on it on 10.09.2026,
                # so the pair is corpus-independent and belongs in the veto. Only the marker
                # goes.
                #
                # Split on the generic "::" rather than this one name, so the next marker
                # someone adds cannot repeat the bug a third time. run_tests asserts the same
                # property from the outside.
                past = past.split("::")[0]
                if past.strip():
                    out.append((today.strip(), past.strip(), kind == "RANBEFORE"))
    except OSError:
        pass
    if skipped:
        sys.stderr.write("gold: %d corpus-dependent (::entity::) case(s) excluded from the "
                         "veto; run_tests covers them at pair level\n" % len(skipped))
    return out


# --- URL ------------------------------------------------------------------------------------

def url_pairs():
    """The same URL published in two editions: (later headline, earlier headline)."""
    seen, out = {}, []
    for date, path in sorted(_days()):
        for row in _published(path):
            key = history.url_key(row.get("url") or "")
            if not key:
                continue
            if key in seen and seen[key][1] != row["headline"]:
                out.append((row["headline"], seen[key][1], row.get("_section")))
            elif key in seen:
                out.append((row["headline"], seen[key][1], row.get("_section")))
            seen[key] = (date, row["headline"])
    return out


# --- CLUSTER --------------------------------------------------------------------------------

def cluster_pairs():
    """Positives from inside one day's clusters; negatives from across them.

    Rebuilds the clustering for each archived day from its own sweep, so the labels are the
    ones that day actually used rather than a re-derivation under today's rules.
    """
    rng = random.Random(SEED)
    pos, neg = [], []
    for date, path in sorted(_days()):
        rows = _sweep(path)
        if not rows:
            continue
        placed = [it for it in rows if it.get("_section")]
        clusters = collections.defaultdict(list)
        for it in placed:
            lead = it.get("_corr_lead_of")
            if lead is not None:
                clusters[lead].append(it["headline"])
        for lead, heads in clusters.items():
            if len(heads) < 2:
                continue
            for a, b in itertools.combinations(sorted(set(heads))[:6], 2):
                pos.append((a, b, None))
        by_section = collections.defaultdict(list)
        for lead, heads in clusters.items():
            if heads:
                by_section[_section_of(rows, lead)].append(heads[0])
        for section, heads in by_section.items():
            rng.shuffle(heads)
            for a, b in list(itertools.combinations(heads, 2))[:NEG_PER_DAY]:
                neg.append((a, b, section))
    return pos, neg


def crossday_suspects(limit=30000):
    """Cluster leads from DIFFERENT days, same section: the real cross-day population.

    Deliberately NOT called a negative set, because it cannot be one. Some of these pairs
    genuinely ARE the same running story - that is the whole thing being detected - so the
    number this produces is a FLAG RATE and an upper bound on false positives, never a clean
    FPR. It is here because the CLUSTER negatives are all same-day pairs, and same-day is not
    the population the matcher runs against: two stories five days apart in one section have
    more chance to look alike than two on one morning. A config whose flag rate here jumps
    while CLUSTER recall barely moves is finding noise, whatever its precision looks like.
    """
    rng = random.Random(SEED)
    by_day = {}
    for date, path in sorted(_days()):
        rows = _sweep(path)
        if not rows:
            continue
        clusters = collections.defaultdict(list)
        for it in rows:
            lead = it.get("_corr_lead_of")
            if lead is not None:
                clusters[lead].append(it)
        by_day[date] = [(v[0].get("_section"), v[0]["headline"]) for v in clusters.values()]
    days = sorted(by_day)
    out = []
    for i, a in enumerate(days):
        for b in days[i + 1:]:
            for sec_a, ha in by_day[a]:
                for sec_b, hb in by_day[b]:
                    if sec_a and sec_a == sec_b:
                        out.append((ha, hb, sec_a))
    rng.shuffle(out)
    return out[:limit]


# --- archive plumbing -----------------------------------------------------------------------

def _days():
    import glob
    return [(os.path.basename(p), p)
            for p in glob.glob(os.path.join(history.ARCHIVE, "[0-9]" * 8))]


def _published(path):
    """Published rows for one archived edition, each stamped with its section."""
    import gzip
    comp = os.path.join(path, "composed.json")
    sweep = os.path.join(path, "sweep.json.gz")
    if not (os.path.exists(comp) and os.path.exists(sweep)):
        return []
    try:
        sections = (json.load(open(comp)) or {}).get("composed") or {}
        blob = json.load(gzip.open(sweep, "rt"))
        rows = blob.get("items") if isinstance(blob, dict) else blob
    except (OSError, ValueError):
        return []
    out = []
    for section, idxs in sections.items():
        for n in idxs:
            try:
                row = dict(rows[n])
            except (IndexError, TypeError):
                continue
            row["_section"] = section
            out.append(row)
    return out


def _sweep(path):
    """A day's full sweep with sections and clusters recomputed as that day saw them."""
    import gzip
    sweep = os.path.join(path, "sweep.json.gz")
    if not os.path.exists(sweep):
        return []
    try:
        blob = json.load(gzip.open(sweep, "rt"))
        rows = blob.get("items") if isinstance(blob, dict) else blob
    except (OSError, ValueError):
        return []
    for it in rows:
        section = shortlist.classify(it.get("headline") or "", it.get("outlet") or "",
                                     it.get("categories"))[0]
        it["_section"] = section
    placed = [it for it in rows if it.get("_section")]
    _stamp_clusters(placed)
    return placed


def _stamp_clusters(rows):
    """Write _corr_lead_of onto each row: the id of the row leading its cluster."""
    words = {id(it): shortlist.sig_words(it["headline"]) for it in rows}
    ents = shortlist.entity_index(rows)
    leads = []
    for it in rows:
        wa = words[id(it)]
        ta = shortlist.ent_tokens(it["headline"])
        placed_in = None
        for lead in leads:
            wb = words[id(lead)]
            shared = {e for e in (ta & shortlist.ent_tokens(lead["headline"])) if e in ents}
            if shortlist.same_story(it, lead, wa, wb, shared):
                placed_in = lead
                break
        if placed_in is None:
            leads.append(it)
            it["_corr_lead_of"] = id(it)
        else:
            it["_corr_lead_of"] = id(placed_in)


def _section_of(rows, lead_id):
    for it in rows:
        if id(it) == lead_id:
            return it.get("_section")
    return None


# --- DEVELOPMENT collisions -----------------------------------------------------------------

def dev_collisions():
    """Pairs word overlap would merge that is_development_of blocks, ranked by cause.

    The maintenance tool for DEVELOPMENT. That list is hand-written and always incomplete, and
    both ways it can be wrong are invisible from inside it: a noun reading invents a stage
    difference, and a missing synonym invents one too. Neither shows up in recall over a
    corpus, because the pairs simply never merge and nothing counts what was lost.

    This scan counts exactly that. Run against the archive on 27.08.2026 it found 20 blocked
    pairs, ranked by the verb pair responsible - and the ranking is what made the fix small:
    13 of the 20 were INFLECTION (win/wins, return/returns, resign/resignation), which needs
    no semantic judgement at all. After stemming plus three evidence-backed synonym classes it
    reports 1, which is an arrest/charge pair left blocked on purpose.

    Re-run it whenever the archive has grown. A new verb pair appearing near the top is a
    synonym class worth adding; a rising total means DEVELOPMENT has drifted behind the
    vocabulary the feeds actually use.
    """
    freq = collections.Counter()
    examples, total = {}, 0
    for date, path in sorted(_days()):
        rows = _sweep(path)
        if not rows:
            continue
        inv, words = collections.defaultdict(list), {}
        for i, it in enumerate(rows):
            words[i] = shortlist.sig_words(it["headline"])
            for w in words[i]:
                inv[w].append(i)
        seen = set()
        for w, ids in inv.items():
            if len(ids) > 60:          # a word this common yields no candidate pairs worth it
                continue
            for i, j in itertools.combinations(ids, 2):
                if (i, j) in seen:
                    continue
                seen.add((i, j))
                a, b = rows[i], rows[j]
                if a.get("_section") != b.get("_section"):
                    continue
                wa, wb = words[i], words[j]
                shared = wa & wb
                small = min(len(wa), len(wb))
                if not (len(shared) >= shortlist.CROSSDAY_WORDS
                        or (small >= shortlist.CROSSDAY_MIN_WORDS
                            and len(shared) / small >= shortlist.CROSSDAY_OVERLAP)):
                    continue
                da = shortlist._dev_matches(a["headline"])
                db = shortlist._dev_matches(b["headline"])
                if da and db and not (da & db):
                    key = tuple(sorted((tuple(sorted(da)), tuple(sorted(db)))))
                    freq[key] += 1
                    total += 1
                    examples.setdefault(key, (a["headline"][:74], b["headline"][:74]))
    lines = ["DEV COLLISIONS - %d pair(s) that word overlap would merge and "
             "is_development_of blocks" % total,
             "(27.08.2026 baseline: 20 before the stem/class fix, 1 after - an arrest/charge "
             "pair left blocked deliberately)"]
    if not freq:
        lines.append("  none")
    for key, n in freq.most_common(20):
        lines.append("  %3dx  %-24s vs %-24s" % (n, "/".join(key[0]), "/".join(key[1])))
        ex = examples[key]
        lines.append("        %s" % ex[0])
        lines.append("        %s" % ex[1])
    return "\n".join(lines), total


# --- scoring --------------------------------------------------------------------------------

def score(show_misses=False, use_entities=True):
    global ENTS
    gold = gold_pairs()
    gold_fail = [(a, b, want) for a, b, want in gold if _match(a, b) != want]

    urls = url_pairs()
    url_hit = [p for p in urls if _match(p[0], p[1], p[2] or "Life")]

    pos, neg = cluster_pairs()
    ENTS = _build_index(gold, urls, pos, neg) if use_entities else None
    # Recomputed with the index in place - GOLD and URL must be scored under the same
    # settings as CLUSTER or the three numbers are not comparable.
    gold_fail = [(a, b, want) for a, b, want in gold if _match(a, b) != want]
    url_hit = [p for p in urls if _match(p[0], p[1], p[2] or "Life")]
    tp = [p for p in pos if _match(p[0], p[1])]
    fp = [p for p in neg if _match(p[0], p[1], p[2] or "Life")]
    xday = crossday_suspects()
    xflag = [p for p in xday if _match(p[0], p[1], p[2] or "Life")]

    recall = len(tp) / len(pos) if pos else 0.0
    fpr = len(fp) / len(neg) if neg else 0.0
    precision = len(tp) / max(1, len(tp) + len(fp))
    f1 = 2 * precision * recall / max(1e-9, precision + recall)

    lines = [
        "GOLD    %d/%d testcases pairs agree%s"
        % (len(gold) - len(gold_fail), len(gold),
           "   *** VETO: %d FAILING ***" % len(gold_fail) if gold_fail else ""),
        "URL     %d/%d  same-URL cross-day repeats recovered  (recall %.3f)"
        % (len(url_hit), len(urls), len(url_hit) / max(1, len(urls))),
        "CLUSTER recall %.3f (%d/%d)   false-positive rate %.3f (%d/%d)"
        % (recall, len(tp), len(pos), fpr, len(fp), len(neg)),
        "CLUSTER precision %.3f   F1 %.3f" % (precision, f1),
        "XDAY    flag rate %.4f (%d/%d) on real cross-day same-section pairs"
        % (len(xflag) / max(1, len(xday)), len(xflag), len(xday))
        + "   -- an upper bound on FP, not an FPR: some are genuine repeats",
        "thresholds: overlap>=%.2f  words>=%d  min-words>=%d  entity-words>=%s"
        % (shortlist.CROSSDAY_OVERLAP, shortlist.CROSSDAY_WORDS,
           shortlist.CROSSDAY_MIN_WORDS,
           shortlist.CROSSDAY_ENTITY_WORDS if use_entities else "off"),
        "entity index: %s" % ("%d distinctive token(s), MIN_DF=%d MAX_DF=%d"
                              % (len(ENTS), shortlist.ENTITY_MIN_DF, shortlist.ENTITY_MAX_DF)
                              if ENTS else "OFF (word overlap only)"),
    ]
    if show_misses:
        missed = [p for p in pos if p not in tp][:15]
        lines.append("\n-- MISSED (same story, not linked) --")
        lines += ['   %s\n   -> %s' % (a[:88], b[:88]) for a, b, _ in missed]
        lines.append("\n-- WRONGLY LINKED (different stories) --")
        lines += ['   %s\n   -> %s' % (a[:88], b[:88]) for a, b, _ in fp[:15]]
        if gold_fail:
            lines.append("\n-- GOLD FAILURES --")
            lines += ['   want %s: %s\n   -> %s'
                      % ("MATCH" if w else "NO MATCH", a[:80], b[:80])
                      for a, b, w in gold_fail]
    return "\n".join(lines), bool(gold_fail)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", metavar="NOTE", help="append the result to repeat_eval_log.txt")
    ap.add_argument("--misses", action="store_true", help="show examples of both error kinds")
    ap.add_argument("--no-entities", action="store_true",
                    help="score the word-overlap arm alone, for a before/after")
    ap.add_argument("--collisions", action="store_true",
                    help="scan the archive for pairs is_development_of wrongly blocks")
    args = ap.parse_args()
    if args.collisions:
        report, total = dev_collisions()
        print(report)
        if args.log:
            with open(LOG, "a") as fh:
                fh.write("\n=== %s  %s\n%s\n"
                         % (dt.date.today().isoformat(), args.log, report))
            print("\nlogged to %s" % os.path.basename(LOG))
        return 0
    report, vetoed = score(show_misses=args.misses, use_entities=not args.no_entities)
    print(report)
    if args.log:
        with open(LOG, "a") as fh:
            fh.write("\n=== %s  %s\n%s\n"
                     % (dt.date.today().isoformat(), args.log, report))
        print("\nlogged to %s" % os.path.basename(LOG))
    return 1 if vetoed else 0


if __name__ == "__main__":
    sys.exit(main())
