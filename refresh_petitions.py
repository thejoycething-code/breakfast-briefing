#!/usr/bin/env python3
"""Refresh the signer counts the Action Desk prints, from Looker (Chris, 02.10.2026).

parl-monitor's campaign_performance table is the desk's petition list, but its counts were
last logged on 13.08.2026, so every petition line read "as of 13 August". Looker has the live
numbers, but only through the Looker MCP inside a Claude session - there is no credential a
script could use. So the morning run queries Looker for the petitions it is about to attach,
saves the tool's raw result to a file, and this script turns that into petition_totals.json,
which action_desk.py lays over the stale table.

WHERE THE QUERY LIVES. This repo is public, so the Looker model, explore and field names are
not written here. They are in petition_source.json beside this script: gitignored, backed up
to Drive by state_sync.sh, restored by `./state_sync.sh pull`.

    python3 refresh_petitions.py --query 101,102      # print the Looker query to run
    python3 refresh_petitions.py /tmp/looker_petitions.json   # update petition_totals.json
    python3 refresh_petitions.py --show                # what is held

A petition's lifetime total is the sum of three signature measures (new, existing and
duplicated). Checked on 02.10.2026, that sum reproduced the campaigns team's own lifetime
figures to within a signature; new + existing alone came to about 72% of it.

Deliberately NOT written into parl-monitor's database. That store is a release asset with
lineage guards (a local write can be clobbered by, or block, the next store sync), and the
desk only needs an overlay. petition_totals.json is gitignored too: it holds real counts.

Input: the Looker tool's result pasted verbatim - one JSON object per row, either as a JSON
list or as concatenated objects. A sanity check refuses a count that FALLS more than
MAX_DROP against what is already held: lifetime signatures do not shrink, so a big drop is a
copying mistake, not news.
"""
import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOTALS = os.path.join(HERE, "petition_totals.json")
MAX_DROP = 0.05

SOURCE = os.path.join(HERE, "petition_source.json")


def load_source(path=SOURCE):
    """The private query settings. Exits with a clear message when they are missing."""
    try:
        return json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError) as exc:
        sys.exit("refresh_petitions: cannot read %s (%s). It is private and not in the repo; "
                 "restore it with ./state_sync.sh pull." % (os.path.basename(path), exc))


def parse_rows(text):
    """Looker rows from a JSON list, or from objects concatenated back to back."""
    text = text.strip()
    if not text:
        return []
    try:
        data = json.loads(text)
        return data if isinstance(data, list) else [data]
    except ValueError:
        pass
    rows, dec, i = [], json.JSONDecoder(), 0
    while i < len(text):
        m = re.compile(r"\s*").match(text, i)
        i = m.end()
        if i >= len(text):
            break
        obj, i = dec.raw_decode(text, i)
        rows.append(obj)
    return rows


def load_totals(path=TOTALS):
    try:
        return json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def apply(rows, held, fields, today=None, label=""):
    """(new held dict, report lines, problems). Pure, so run_tests can drive it.

    fields maps id/new/existing/duplicated to the source's own field names."""
    today = today or datetime.date.today().isoformat()
    F_NID, F_NEW, F_EXIST, F_DUP = (fields["id"], fields["new"], fields["existing"],
                                    fields["duplicated"])
    out, report, problems = dict(held), [], []
    for r in rows:
        missing = [f for f in (F_NID, F_NEW, F_EXIST, F_DUP) if f not in r]
        if missing:
            problems.append("row %r lacks %s - run the query that --query prints"
                            % (r, ", ".join(missing)))
            continue
        nid = str(r[F_NID]).strip()
        if not nid.isdigit():
            problems.append("row has no numeric petition id: %r" % (r,))
            continue
        sig = int(r[F_NEW] or 0) + int(r[F_EXIST] or 0) + int(r[F_DUP] or 0)
        prev = (held.get(nid) or {}).get("signatures")
        if prev and sig < prev * (1 - MAX_DROP):
            problems.append("%s: %s signers is %.0f%% below the %s already held. Lifetime "
                            "totals do not shrink; check the copy." % (
                                nid, "{:,}".format(sig), 100 * (1 - sig / prev),
                                "{:,}".format(prev)))
            continue
        out[nid] = {"signatures": sig, "new_members": int(r[F_NEW] or 0), "as_of": today,
                    "source": label}
        report.append("%s: %s signers%s" % (nid, "{:,}".format(sig),
                                            "" if not prev else " (was %s)" % "{:,}".format(prev)))
    return out, report, problems


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if argv[0] == "--query":
        if len(argv) < 2 or not re.fullmatch(r"\d+(,\d+)*", argv[1]):
            sys.exit("usage: refresh_petitions.py --query 101,102,...")
        q = load_source()["query"]
        print("Run with the %s tool:" % q.get("tool", "Looker"))
        print(json.dumps({"model": q["model"], "explore": q["explore"], "fields": q["fields"],
                          "filters": {q["filter_field"]: argv[1]}}, indent=1))
        return 0
    if argv[0] == "--show":
        for nid, v in sorted(load_totals().items(), key=lambda kv: -kv[1]["signatures"]):
            print("%-7s %9s  as of %s" % (nid, "{:,}".format(v["signatures"]), v["as_of"]))
        return 0
    src = load_source()
    rows = parse_rows(open(argv[0], encoding="utf-8").read())
    held, report, problems = apply(rows, load_totals(), src["fields"],
                                   label=src.get("source_label", ""))
    for line in report:
        print("refresh_petitions: %s" % line)
    if problems:
        for p in problems:
            sys.stderr.write("refresh_petitions: REFUSED %s\n" % p)
    if report:
        with open(TOTALS, "w", encoding="utf-8") as fh:
            json.dump(held, fh, indent=1, sort_keys=True)
    sys.stderr.write("refresh_petitions: %d updated, %d refused, %d held in %s\n"
                     % (len(report), len(problems), len(held), os.path.basename(TOTALS)))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
