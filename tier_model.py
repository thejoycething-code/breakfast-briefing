#!/usr/bin/env python3
"""Option 4: learn tier (1/2/3/unpicked) from the archived editions.

Chris, 24.08.2026. Every archived edition carries an ordinal judgement of ~1,000 stories, so
the labels for a supervised model already exist as a by-product of publishing. This trains a
multinomial logistic regression on hashed text features and reports how well it predicts the
tiers, evaluated LEAVE-ONE-DAY-OUT so a day is never scored by a model that saw it.

Pure Python on purpose: numpy, scipy and sklearn are all absent on this machine, and adding a
dependency to the morning path for an experiment would be the wrong trade. It is a few hundred
features and a few thousand rows; plain loops are fast enough.

    python3 tier_model.py                # train + leave-one-day-out report
    python3 tier_model.py --top 25       # ...and show the most predictive features

READ THIS BEFORE TRUSTING A NUMBER FROM IT. Two limits are structural, not fixable by more
epochs:

  1. It learns MY past tiering, including its mistakes. On 24.08.2026 Chris listed 33 stories
     that should have run and 17 were in the sweep, unpicked - this model is trained to
     reproduce exactly that behaviour. High accuracy here means "agrees with what was done",
     which is the same trap rank_eval.py warns about in its own header, and is not the same
     thing as "would have picked the right stories".
  2. Four editions is a very small corpus (18-21.08.2026), and they are consecutive days of
     one news cycle, so the same running stories appear in several of them. Leave-one-day-out
     mitigates that but does not remove it: a model can score well by recognising a story it
     saw yesterday under a different headline.

So: useful as a SECOND OPINION that flags a story the scorer ranked low and past editions
suggest should be high. Not useful as an authority, and it must never silently reorder a sheet.

MEASURED 10.09.2026, AND IT DID NOT WORK. The second-opinion flag above was built and wired
into shortlist.py's sheet, then tested against that day's edition, and the wiring was removed
again. Recorded here so nobody spends the afternoon twice:

  - retrained on 18 editions (it had seen 4): pooled picked precision 0.34, recall 0.46.
  - on buried leads (sheet rank > 400) it flagged 55 of 1,178, and the curator had tiered 41
    of those 0. The sample was weak US procedural filler - a Maine Senate race explainer, a
    SCOTUSblog docket roundup, a Houston immigration attorney's indictment - i.e. stories the
    0 was right about. 55 markers a day of that is noise on a sheet that is already ~195k
    tokens, and noise is the specific thing the flag was supposed to cut through.
  - it MISSED the one case it was designed for. Index 417 that day (FoRB in Full, "How a
    harmless song reveals the quiet mechanics of India's majoritarian nation-building") sat
    at rank 1,165 of 1,178, was tiered 3, and the model did not flag it.
  - narrowing to ★ PRIMARY_SOURCE leads - the population the 24.08.2026 failure was actually
    about, when 17 of 33 missed stories were in the sweep unpicked - did not rescue it: there
    were 4 buried ★ leads, 2 of them tiered 0, and the model flagged NONE of them. 417 is not
    a ★ primary either, so even the right population would not have caught it.

The plumbing is kept: `--save` freezes weights to tier_model.json, `load()` reads them back
and `second_opinion()` scores buried leads. Nothing calls them. They are here so a future
attempt starts from a measurement rather than an intuition, and eval_week.sh deliberately
does NOT retrain, because a weekly job feeding no consumer is the same unwired smell this
module was criticised for in the first place.

What the evidence actually suggests, if anyone returns to it: the misses are concentrated in
sources whose text the sweep cannot read and in x1 primaries, and hashed bag-of-words over a
headline has nothing to work with in either case. The lever is more likely a source route
than a model.
"""

import argparse
import glob
import gzip
import json
import math
import os
import re

import shortlist

HERE = os.path.dirname(os.path.abspath(__file__))
ARCHIVE = os.path.join(HERE, "archive")
BUCKETS = 2 ** 14          # hashed feature space; ~16k is ample for a few thousand rows
CLASSES = ["none", "3", "2", "1"]
STOP = {"the", "and", "for", "with", "from", "that", "this", "has", "have", "was", "were",
        "will", "says", "said", "after", "over", "into", "out", "his", "her", "its", "not"}


def _tokens(text):
    words = [w for w in re.findall(r"[a-z']{3,}", (text or "").lower()) if w not in STOP]
    grams = list(words)
    grams += ["%s_%s" % (a, b) for a, b in zip(words, words[1:])]
    return grams


def features(item, section):
    """Hashed bag of words from headline, outlet, section and the cheap structural signals.

    Text only - no corroboration, no importance(). The point of the experiment is to find out
    what the TEXT alone predicts; mixing in the existing scorer's own output would just measure
    the scorer twice.
    """
    feats = {}
    for tok in _tokens(item.get("headline")):
        feats[hash("h:" + tok) % BUCKETS] = feats.get(hash("h:" + tok) % BUCKETS, 0) + 1
    for tok in _tokens(item.get("summary"))[:40]:
        feats[hash("s:" + tok) % BUCKETS] = feats.get(hash("s:" + tok) % BUCKETS, 0) + 1
    for key in ("o:" + (item.get("outlet") or "").lower(),
                "sec:" + (section or "?"),
                "pay:%d" % int(bool(item.get("paywalled"))),
                "gn:%d" % int("news.google.com" in (item.get("url") or ""))):
        feats[hash(key) % BUCKETS] = 1.0
    norm = math.sqrt(sum(v * v for v in feats.values())) or 1.0
    return {k: v / norm for k, v in feats.items()}


def load_days():
    """[(day, [(features, label), ...])] from every archived edition."""
    days = []
    for path in sorted(glob.glob(os.path.join(ARCHIVE, "*"))):
        day = os.path.basename(path)
        sweep_p = os.path.join(path, "sweep.json.gz")
        picks_p = os.path.join(path, "picks.json")
        if not (os.path.exists(sweep_p) and os.path.exists(picks_p)):
            continue
        with gzip.open(sweep_p, "rt") as fh:
            items = json.load(fh)["items"]
        picks = json.load(open(picks_p))
        tier_of = {}
        for section, spec in picks.items():
            if isinstance(spec, dict):
                for tier, nums in spec.items():
                    for n in nums:
                        tier_of[n] = str(tier)
            else:
                for n in spec:
                    tier_of[n] = "2"
        # TARGET LEAKAGE, found 24.08.2026 and fixed here. The section used to be read from
        # picks.json, which means it existed ONLY for items that were picked - the "sec:"
        # feature was therefore a direct encoding of the label. That is what produced the
        # first run's precision 0.93 / recall 0.96: the model was reading the answer. The
        # section now comes from the classifier, exactly as it would at prediction time on a
        # story nobody has judged yet.
        rows = []
        for idx, it in enumerate(items):
            label = tier_of.get(idx, "none")
            section, _score = shortlist.classify(
                it["headline"], it.get("outlet") or "", it.get("categories"))
            rows.append((features(it, section), label))
        days.append((day, rows))
    return days


def train(rows, epochs=14, lr=0.5, l2=1e-4):
    """Multinomial logistic regression by SGD. Returns {class: {feature: weight}}."""
    w = {c: {} for c in CLASSES}
    b = {c: 0.0 for c in CLASSES}
    # Class weighting: 'none' outnumbers tier 1 by roughly 40:1, and without this the model
    # learns to answer 'none' every time and score 90% while being useless.
    counts = {}
    for _f, lab in rows:
        counts[lab] = counts.get(lab, 0) + 1
    total = sum(counts.values())
    cw = {c: (total / (len(CLASSES) * counts.get(c, 1))) for c in CLASSES}
    order = list(range(len(rows)))
    for ep in range(epochs):
        # Deterministic shuffle: no Math.random equivalent needed and reruns must match.
        order = order[len(order) // 3:] + order[:len(order) // 3]
        for i in order:
            feats, lab = rows[i]
            scores = {}
            for c in CLASSES:
                wc = w[c]
                scores[c] = b[c] + sum(v * wc.get(k, 0.0) for k, v in feats.items())
            mx = max(scores.values())
            exp = {c: math.exp(s - mx) for c, s in scores.items()}
            z = sum(exp.values())
            for c in CLASSES:
                p = exp[c] / z
                g = (p - (1.0 if c == lab else 0.0)) * cw[lab] * lr
                if g:
                    wc = w[c]
                    for k, v in feats.items():
                        wc[k] = wc.get(k, 0.0) * (1 - l2) - g * v
                    b[c] -= g
    return w, b


def predict(w, b, feats):
    scores = {c: b[c] + sum(v * w[c].get(k, 0.0) for k, v in feats.items()) for c in CLASSES}
    return max(scores, key=scores.get), scores


MODEL_FILE = os.path.join(HERE, "tier_model.json")

# Only a lead the sheet has already buried is worth a second opinion. Flagging a story the
# corroboration order already put near the top tells the reader nothing they were not about
# to read anyway; the failure this is for is the opposite one - 24.08.2026, when Chris listed
# 33 stories that should have run, 17 were in that day's sweep unpicked, and most were ★
# primary sources that are x1 by definition and therefore sink in a corroboration-ordered
# sheet of 2,400 lines.
BURIED_AFTER = 400


def save(w, b, path=MODEL_FILE, note=""):
    """Freeze the trained weights so the morning path never trains anything.

    Training on 18 editions takes minutes, which has no place in a 6am path with a deadline.
    So eval_week.sh trains weekly and writes this file, and shortlist.py only ever loads it.
    A model older than the archive it was trained on is not a correctness problem here - the
    flag is advisory and the file records its own provenance so a stale one is visible.
    """
    keep = {c: {str(k): round(v, 6) for k, v in w[c].items() if abs(v) > 1e-4}
            for c in CLASSES}
    json.dump({"classes": CLASSES, "buckets": BUCKETS, "b": b, "w": keep,
               "trained_on": sorted(d for d, _ in load_days()), "note": note,
               "buried_after": BURIED_AFTER},
              open(path, "w", encoding="utf-8"))
    return path


def load(path=MODEL_FILE):
    """(w, b, meta) or (None, None, None). Never raises: this is advisory, not load-bearing."""
    try:
        d = json.load(open(path, encoding="utf-8"))
        if d.get("buckets") != BUCKETS or d.get("classes") != CLASSES:
            return None, None, None      # feature space changed under the saved weights
        w = {c: {int(k): v for k, v in d["w"].get(c, {}).items()} for c in d["classes"]}
        return w, d["b"], d
    except Exception:
        return None, None, None


def second_opinion(items, sections, path=MODEL_FILE):
    """{index: predicted tier} for leads the model rates 1 or 2 that the sheet has buried.

    Deliberately NOT a reordering and deliberately not a filter. tier_model.py's own header
    says why: it learns MY past tiering including its mistakes, so "agrees with what was done"
    is not "would have picked the right stories", and it must never silently reorder a sheet.
    Measured 10.09.2026 over 18 editions: picked precision 0.34, recall 0.46. That is far too
    weak to decide anything and quite good enough to say "look again at this one".

    `sections` maps index -> section; `items` is index -> item dict.
    """
    w, b, meta = load(path)
    if w is None:
        return {}, None
    cutoff = (meta or {}).get("buried_after", BURIED_AFTER)
    out = {}
    for rank, (n, it) in enumerate(items):
        if rank < cutoff:
            continue
        pred, _ = predict(w, b, features(it, sections.get(n)))
        if pred in ("1", "2"):
            out[n] = pred
    return out, meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=0)
    ap.add_argument("--save", nargs="?", const=MODEL_FILE, default=None,
                    help="train on ALL editions and freeze the weights to FILE "
                         "(default %s) for shortlist.py's second-opinion flag" % MODEL_FILE)
    ap.add_argument("--note", default="", help="provenance note stored in the saved model")
    args = ap.parse_args()
    days = load_days()
    if len(days) < 2:
        print("need at least 2 archived editions; found %d" % len(days))
        return 1
    print("editions: %s\n" % ", ".join(d for d, _ in days))

    if args.save:
        # Trained on EVERY edition, which is right for the saved model and wrong for the
        # report below: the report holds a day out so a day is never scored by a model that
        # saw it. Both are printed so the two numbers are never confused for each other.
        w, b = train([r for _d, rs in days for r in rs])
        path = save(w, b, args.save, args.note)
        print("saved %s trained on all %d edition(s)" % (path, len(days)))
        print("It is a SECOND OPINION, not an authority - see this module's docstring. The "
              "leave-one-day-out report below is what says how much to trust it.\n")

    print("%-10s %7s %7s %9s %9s %9s" % ("held-out", "rows", "picked", "picked-P", "picked-R",
                                         "tier1-R"))
    agg = [0, 0, 0, 0]
    for held, rows in days:
        train_rows = [r for d, rs in days if d != held for r in rs]
        w, b = train(train_rows)
        tp = fp = fn = t1_hit = t1_tot = 0
        for feats, lab in rows:
            pred, _ = predict(w, b, feats)
            actual_pick = lab != "none"
            pred_pick = pred != "none"
            if pred_pick and actual_pick:
                tp += 1
            elif pred_pick:
                fp += 1
            elif actual_pick:
                fn += 1
            if lab == "1":
                t1_tot += 1
                t1_hit += 1 if pred_pick else 0
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        t1r = t1_hit / t1_tot if t1_tot else float("nan")
        agg = [agg[0] + tp, agg[1] + fp, agg[2] + fn, agg[3] + t1_tot]
        print("%-10s %7d %7d %9.2f %9.2f %9.2f"
              % (held, len(rows), tp + fn, prec, rec, t1r))
    P = agg[0] / (agg[0] + agg[1]) if agg[0] + agg[1] else 0
    R = agg[0] / (agg[0] + agg[2]) if agg[0] + agg[2] else 0
    print("\npooled: picked precision %.2f, recall %.2f" % (P, R))
    print("Read the module docstring before acting on these: the model is trained to agree\n"
          "with past picks, and 4 consecutive editions share running stories.")
    if args.top:
        w, b = train([r for _d, rs in days for r in rs])
        print("\n(feature weights are hashed, so they are not human-readable by design -\n"
              " --top reports magnitudes only, as a sanity check that learning happened)")
        for c in ("1", "2"):
            mags = sorted(w[c].values(), key=abs, reverse=True)[:args.top]
            print("  class %s: top |weight| %.3f .. %.3f over %d features"
                  % (c, abs(mags[0]) if mags else 0, abs(mags[-1]) if mags else 0, len(w[c])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
