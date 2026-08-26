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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=0)
    args = ap.parse_args()
    days = load_days()
    if len(days) < 2:
        print("need at least 2 archived editions; found %d" % len(days))
        return 1
    print("editions: %s\n" % ", ".join(d for d, _ in days))
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
