#!/usr/bin/env python3
"""Action Desk: what parl-monitor already knows about a Slack-five story.

Chris, 02.10.2026: "build it but I don't want to do any approvals, just include it". So
slack_five.py calls lookup() for every lead slot and the lines it returns go straight into
the post, nested under the story. Nothing here asks anyone anything.

Three kinds of line, at most one of each per story:

  Bill:      a LIVE bill from parl-monitor's bills board, with its stage and next date
  Vote:      a vote-tracker card for the bill or Act the story names, with its result
  Petition:  our own CitizenGO UK petition on the same subject, with its signer count

Matching is deliberately strict, because nobody reviews these lines before they post:

  1. The story is tagged with parl-monitor's own issue areas (src/filter.py over the
     headline and the sheet's text), so the Briefing and parl-monitor use ONE issue list.
  2. A candidate must share an area with the story AND be about the same thing:
       - a bill or vote card only when the story NAMES that bill or Act;
       - a petition only when it shares at least MIN_SHARED distinctive words with the
         story (generic campaign words such as "stop", "demand" and "government" do not
         count).
     An area match alone is never enough. Area 11 alone would attach every migration
     petition to every migration story, which reads as noise and invites a wrong link.
  3. No line carries a URL. Links in the five are only ever copied from the edition and
     checked against expected_urls.txt; nothing here has passed that check, so these are
     plain text.

If parl-monitor is not on this machine, or its database will not open, lookup() returns
nothing and status() says why. slack_five.py prints that loudly: a silent desk would look
exactly like "nothing matched".
"""
import datetime
import json
import os
import re
import sqlite3
import sys

PM_ROOT = os.environ.get("PARL_MONITOR", os.path.expanduser("~/parl-monitor"))

# Two distinctive shared words. Measured on the 1 October five: one word ("abortion",
# "police") matched unrelated petitions; two found the right one or none.
MIN_SHARED = 2

# Petition figures older than this get an "as of" date in the line, so a seven-week-old
# count is never presented as today's.
STALE_DAYS = 7

# Words that carry no subject. Petition titles are full of them ("Stop...", "Demand...",
# "Tell the Government..."), so without this list every petition overlaps every story.
GENERIC = set("""
a an the and or but of to in on at by for from with without into onto over under about
after before again against all any are as be been being both can could did do does doing
down during each few further had has have having he her here hers him his how i if is it
its just more most my no nor not now off once only other our out own same she should so
some such than that their them then there these they this those through too until up very
was we were what when where which while who whom why will would you your yours
stop demand sign tell say said says ask asks call calls urge urges must save protect
defend support back now again never ever still new news report reports reported
government govt minister ministers ministry uk britain british england english wales
scotland scottish ireland irish national state states law laws rule rules plan plans
petition campaign people public time times year years day days week weeks
one two three first last next just also even like make makes made
""".split())

_WORD = re.compile(r"[a-z][a-z'\-]{2,}")


def _words(text):
    """Distinctive words: lower-case, 4+ letters, crude plural fold, generic words out."""
    out = set()
    for w in _WORD.findall((text or "").lower().replace("’", "'")):
        w = w.strip("'-")
        if len(w) < 4 or w in GENERIC:
            continue
        if w.startswith("islam"):
            w = "islam"
        elif w.startswith("muslim"):
            w = "muslim"
        elif w.endswith("ies") and len(w) > 5:
            w = w[:-3] + "y"
        elif w.endswith("s") and not w.endswith("ss") and len(w) > 4:
            w = w[:-1]
        if w not in GENERIC:
            out.add(w)
    return out


def _named(core, low):
    """A bill/Act counts as named only on a 2+ word core: 'health' or 'abortion' alone would
    tie any health or abortion story to the Health Bill or the NI regulations (seen 02.10)."""
    return bool(core) and len(core.split()) >= 2 and core in low


def _core(name):
    """'Crime and Policing Bill - New Clause 1' -> 'crime and policing'."""
    name = (name or "").split(" - ")[0]
    name = re.sub(r"\[HL\]|\(.*?\)", "", name)
    name = re.sub(r"\b(Bill|Act|Regulations?)\b(\s+\d{4})?", "", name)
    return " ".join(name.lower().replace("’", "'").split())


def _clean_petition_name(name):
    name = re.sub(r":[a-z_]+:", "", name or "")              # Slack emoji codes
    return " ".join(name.split()).strip(" -")


# The Briefing's sections, mapped onto parl-monitor's areas (the shared issue list). Used
# alongside the keyword tagger because parliamentary vocabulary misses news wording: "one in,
# one out migrant scheme" reaches no area-11 term ("migrant" is not "migration").
SECTION_AREAS = {
    "Life": {1, 2, 10, 13},
    "Gender, Identity & Sexuality": {3, 4, 5},
    "Free Speech & Civil Liberties": {7},
    "Religious Freedom & Persecution": {8},
    "Church & Religion": {8},
    "Marriage, Family & Education": {6, 9},
    "Immigration & Asylum": {11},
}

# Islam stories (Chris, 02.10.2026): no section of their own - they stay in whichever Briefing
# section they land in - but for this lookup they belong to areas 7 and 8, and to 9 when the
# story is about marriage. These terms are the desk's ONLY, deliberately not added to
# parl-monitor's taxonomy.yaml: that list drives parliamentary triage, and "mosque" there would
# start filing every planning question about a mosque under freedom of religion.
EXTRA_AREA_TERMS = [
    (re.compile(r"\b(islam\w*|muslims?|mosques?|sharia|imams?|hijab|niqab|burqa|jihad\w*|"
                r"islamis\w*|blasphem\w*)\b", re.I), {7, 8}),
    (re.compile(r"\b(cousin marriage|polygam\w*|sharia councils?|forced marriage|nikah)\b",
                re.I), {9}),
]

# Petitions offered as candidates: big enough to be worth an update, recent enough to be live.
MIN_SIGNERS = 1000
MAX_AGE_DAYS = 730
MAX_CANDIDATES = 8


class Desk:
    """Loaded once per run; lookup() is called per story."""

    def __init__(self, root=PM_ROOT):
        self.root = root
        self.ok = False
        self.reason = ""
        self.petitions_as_of = None
        try:
            self._load()
            self.ok = True
        except Exception as exc:                            # any failure: desk is off, loudly
            self.reason = "%s: %s" % (type(exc).__name__, exc)

    def _load(self):
        db = os.path.join(self.root, "data", "parl-monitor.db")
        if not os.path.exists(db):
            raise FileNotFoundError("no parl-monitor database at %s" % db)
        if self.root not in sys.path:
            sys.path.insert(0, self.root)
        from src import filter as pmf                        # parl-monitor's own matcher
        import yaml
        cfg = os.path.join(self.root, "config")
        self._pmf = pmf
        self.taxonomy = pmf.load_taxonomy(os.path.join(cfg, "taxonomy.yaml"))
        self.watchlist = pmf.load_watchlist(os.path.join(cfg, "watchlist.yaml"))
        tracker = yaml.safe_load(open(os.path.join(cfg, "vote_tracker.yaml"), encoding="utf-8"))
        self.cards = [c for c in (tracker.get("issues") or []) if c.get("status")]

        con = sqlite3.connect("file:%s?mode=ro" % db, uri=True)
        try:
            self.bills = [dict(zip(("title", "house", "stage", "next", "areas"), r)) for r in
                          con.execute("SELECT title, house, stage, next_key_date, areas "
                                      "FROM bills_board WHERE status = 'live'")]
            self.petitions = [dict(zip(("id", "name", "signatures", "areas", "logged",
                                        "launch"), r))
                              for r in con.execute(
                                  "SELECT petition_id, name, signatures, areas, logged_at, "
                                  "launch_date "
                                  "FROM campaign_performance WHERE signatures > 0")]
        finally:
            con.close()
        for b in self.bills:
            b["areas"] = _int_list(b["areas"])
        for p in self.petitions:
            p["areas"] = _int_list(p["areas"])
            p["name"] = _clean_petition_name(p["name"])
            p["words"] = _words(p["name"])
        # Fresh counts from Looker (refresh_petitions.py, 02.10.2026) laid over the table's
        # 13.08.2026 figures, per petition. A count is only ever replaced by a newer one.
        self.refreshed = 0
        try:
            totals = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                 "petition_totals.json"), encoding="utf-8"))
        except (OSError, ValueError):
            totals = {}
        for p in self.petitions:
            t = totals.get(str(p["id"]))
            if t and (t.get("as_of") or "") >= (p["logged"] or "")[:10]:
                p["signatures"] = t["signatures"]
                p["logged"] = t["as_of"]
                self.refreshed += 1
        logged = [p["logged"] for p in self.petitions if p["logged"]]
        if logged:
            self.petitions_as_of = datetime.date.fromisoformat(max(logged)[:10])

    def status(self):
        if not self.ok:
            return "ACTION DESK UNAVAILABLE (%s) - the five posts without it" % self.reason
        msg = "action desk: %d live bills, %d vote cards, %d petitions (%d with Looker counts)" % (
            len(self.bills), len(self.cards), len(self.petitions), getattr(self, "refreshed", 0))
        if self.petitions_as_of:
            age = (datetime.date.today() - self.petitions_as_of).days
            msg += ", petition figures from %s" % self.petitions_as_of.isoformat()
            if age > STALE_DAYS:
                msg += (" (%d days old; a line says 'as of' unless refresh_petitions.py has a "
                        "fresh Looker count for that petition)" % age)
        return msg

    def areas(self, headline, text):
        res = self._pmf.filter_item(self.taxonomy, self.watchlist, headline or "", text or "")
        return set(res.issue_areas)

    def lookup(self, headline, text="", section=""):
        """{"lines": [str], "candidates": [petition dict]} for one story.

        lines      - bill and vote lines, attached automatically: the story names the bill.
        candidates - our petitions in the story's areas, best first. NOT attached here: a
                     word match cannot tell a live campaign from a near-miss, so the run picks
                     one by id (or none) in the spec, and slack_five renders it from this data.
        """
        out = {"lines": [], "candidates": []}
        if not self.ok:
            return out
        story = " ".join(((headline or ""), (text or ""))).replace("\u2019", "'")
        low = story.lower()
        areas = self.areas(headline, text) | SECTION_AREAS.get(section, set())
        for rx, extra in EXTRA_AREA_TERMS:
            if rx.search(story):
                areas |= extra
        if not areas:
            return out

        for b in self.bills:
            core = _core(b["title"])
            if set(b["areas"]) & areas and _named(core, low):
                when = b["next"] if b["next"] and b["next"] != "TBA" else ""
                line = "Bill: %s, %s %s" % (b["title"], b["house"], (b["stage"] or "").lower())
                if when:
                    line += ", next sitting %s" % _nice_date(when)
                out["lines"].append(line)
                break

        for c in self.cards:
            if c.get("area") not in areas:
                continue
            names = [c.get("bill")] + list(c.get("debate_match") or [])
            if any(_named(_core(n), low) for n in names if n):
                out["lines"].append("Vote: %s. %s" % (c["name"], _first_sentence(c["status"])))
                break

        today = datetime.date.today()
        sw = _words(story)
        cands = []
        for p in self.petitions:
            if not (set(p["areas"]) & areas) or p["signatures"] < MIN_SIGNERS:
                continue
            try:
                age = (today - datetime.date.fromisoformat((p["launch"] or "")[:10])).days
            except ValueError:
                continue
            if age > MAX_AGE_DAYS:
                continue
            shared = sorted(p["words"] & sw)
            cands.append(dict(p, shared=shared, age_days=age))
        cands.sort(key=lambda p: (-len(p["shared"]), p["age_days"]))
        out["candidates"] = cands[:MAX_CANDIDATES]
        out["lines"] = [l for l in out["lines"] if not re.search(r"https?://|www\.", l)]
        return out

    def petition_line(self, p):
        """Per petition: "as of" appears only when THIS petition's count is stale."""
        line = "Our petition: %s · %s signers" % (p["name"], "{:,}".format(p["signatures"]))
        try:
            when = datetime.date.fromisoformat((p.get("logged") or "")[:10])
        except ValueError:
            when = self.petitions_as_of
        if when and (datetime.date.today() - when).days > STALE_DAYS:
            line += " (as of %s)" % _nice_date(when.isoformat())
        return line


def _int_list(raw):
    if not raw:
        return []
    try:
        v = json.loads(raw) if isinstance(raw, str) else raw
    except ValueError:
        v = re.findall(r"\d+", str(raw))
    if isinstance(v, (int, str)):
        v = [v]
    return [int(x) for x in v if str(x).strip().isdigit()]


def _nice_date(iso):
    try:
        d = datetime.date.fromisoformat(iso[:10])
    except ValueError:
        return iso
    return "%d %s" % (d.day, d.strftime("%B"))


def _first_sentence(text):
    text = " ".join((text or "").split())
    m = re.match(r"(.+?[.;])(\s|$)", text)
    return (m.group(1) if m else text).rstrip(";") .rstrip(".") + "."


if __name__ == "__main__":
    # python3 action_desk.py "headline" ["text"]  - try a story by hand
    d = Desk()
    print(d.status(), file=sys.stderr)
    r = d.lookup(sys.argv[1] if len(sys.argv) > 1 else "", sys.argv[2] if len(sys.argv) > 2 else "",
                 sys.argv[3] if len(sys.argv) > 3 else "")
    for l in r["lines"]:
        print(l)
    for p in r["candidates"]:
        print("  candidate %s  %s  (%s signers; shares %s)"
              % (p["id"], p["name"][:70], p["signatures"], ", ".join(p["shared"]) or "-"))
