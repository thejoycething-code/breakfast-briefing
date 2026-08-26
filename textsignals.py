#!/usr/bin/env python3
"""Structured signals read off an article's opening text.

Built 24.08.2026 (Chris: options 3 and 5). One extraction engine feeds two consumers:

  * the ranking sheet displays the flags, so the curator can see WHAT a piece is before
    tiering it (option 5);
  * importance() may read a bounded subset of them (option 3).

Why this exists, and why it is not keyword scoring over body text. That was tried on
18.08.2026 and rejected because it REWARDS COMMENTARY: an opinion piece about a court ruling
contains every keyword the report contains, plus more, so density over the body promotes the
essay above the story it is arguing about. This module inverts that. It does not count topic
words at all. It asks a small number of yes/no questions whose answers a curator would want,
and the most important one is precisely the distinction that defeated the old approach -
report or argument.

Deterministic and offline: no model call, no network. Everything here runs on text that
fetch_feeds.fetch_article_opening() already retrieved, so it costs nothing per run beyond the
fetch. That matters because only 56% of a day's candidates are fetchable at all (36% are
unresolved Google News redirects, 9% paywalled), so every signal has to degrade gracefully to
"unknown" rather than to a wrong answer. `signals()` returns None for anything it cannot see.

Run `python3 textsignals.py` for the self-test.
"""

import re

# --- report vs argument ---------------------------------------------------------------------
# First person, second person, and the modal vocabulary of persuasion. An opinion piece cannot
# help using these in its opening; a news report almost never does outside a quotation, which
# is why quoted spans are stripped before this is applied.
COMMENT_MARKERS = re.compile(
    r"\b(I |I'm|I've|my |we should|we must|we need to|let us|let's|you should|you can't"
    r"|surely|frankly|of course|make no mistake|the truth is|it is time|it's time"
    r"|the real question|what if|imagine |consider |arguably|to be fair|in my view"
    r"|nonsense|absurd|outrageous|disgraceful|shameful|hypocris)", re.I)
# Structural tells that sit in the standfirst of a column rather than a report.
COMMENT_STRUCTURE = re.compile(
    r"\b(opinion|comment|editorial|column|analysis|explainer|review|essay|letter to)\b", re.I)
# A report's opening attributes: someone said, a body ruled, a document was published.
REPORT_MARKERS = re.compile(
    r"\b(said|says|told|announced|confirmed|reported|according to|ruled|found|filed"
    r"|published|released|issued|voted|passed|signed|charged|sentenced|arrested"
    r"|has been|have been|was |were )", re.I)

# --- primary document -----------------------------------------------------------------------
# Does the piece rest on a document that exists, and name it? This is the textual half of the
# provenance rule the briefing already applies by outlet: an advocacy body's own release, a
# filing, a ruling, a formal letter. Naming one is a mark of a first-hand story.
PRIMARY_DOC = re.compile(
    r"\b(petition|lawsuit|complaint|court filing|filed suit|judgment|judgement|ruling"
    r"|opinion of the court|injunction|indictment|bill\b|amendment|statute|regulation"
    r"|report|study|survey|poll|open letter|letter to|statement|press release|communiqu"
    r"|resolution|treaty|directive|guidance|white paper|submission|affidavit"
    # Appellate and legislative instruments, added 24.08.2026: an appeal to a circuit court is
    # a filing, and missing it left "Idaho AG vows to fight for abortion ban" without the bump
    # while the stories around it collected one. Deliberately NOT a bare "appeal": the Pope
    # "appeals for international aid for Ebola victims" is a plea, not a document, and bare
    # "court" fires on almost every legal story and would push this toward universal - a +4
    # that applies to everything is worth nothing.
    r"|appealed to|appeals? (to|against) the|court of appeals?|appellate|certiorari"
    r"|\bwrit\b|motion to (dismiss|stay|compel|intervene)|executive order|ordinance"
    r"|\bveto\b|signed into law|struck down)\b", re.I)

# --- first report vs update -----------------------------------------------------------------
# Deliberately close to shortlist.DEVELOPMENT, which exists for the same reason: Chris,
# 17.08.2026, "her giving the baby back is new detail compared to what we had before". An
# update carries an outcome verb; a first report announces the event.
UPDATE_MARKERS = re.compile(
    r"\b(again|renewed|latest|continues|has now|now says|reversed|overturned|upheld"
    r"|appealed|appeal|following (the|its|his|her|their)|after (the|his|her|their)"
    r"|in response to|responding to|update|second|third|another)\b", re.I)

# --- jurisdiction ---------------------------------------------------------------------------
# Named explicitly IN THE TEXT, which is a different question from regions.region(): that
# infers a region from headline and outlet, and is what the briefing orders sections by. This
# says whether the article itself tells you where it happened - a story that never names a
# place is usually comment, or a wire brief too thin to place.
JURISDICTIONS = [
    ("UK", r"\b(United Kingdom|Britain|British|England|Scotland|Wales|Northern Ireland"
           r"|Westminster|Holyrood|Stormont)\b"),
    ("Ireland", r"\b(Ireland|Irish|Dublin|Oireachtas|Dail)\b"),
    ("United States", r"\b(United States|U\.S\.|US |American|Washington|Congress|Supreme Court"
                      r"|White House|federal)\b"),
    ("Europe", r"\b(European Union|Brussels|France|French|Germany|German|Spain|Spanish|Italy"
               r"|Italian|Poland|Polish|Portugal|Netherlands|Sweden|Swedish|Vatican)\b"),
    ("Africa", r"\b(Nigeria|Nigerian|Kenya|Ghana|Uganda|Cameroon|Zambia|Sudan|Ethiopia"
               r"|South Africa|Tanzania|Mozambique)\b"),
    ("Asia", r"\b(India|Indian|China|Chinese|Pakistan|Vietnam|Indonesia|Japan|Korea"
             r"|Hong Kong|Philippines|Singapore|Nepal|Bangladesh)\b"),
    ("Middle East", r"\b(Israel|Israeli|Iran|Iranian|Iraq|Syria|Lebanon|Turkey|Turkish"
                    r"|Gaza|West Bank|Saudi)\b"),
    ("Latin America", r"\b(Mexico|Mexican|Brazil|Brazilian|Colombia|Argentina|Chile|Peru"
                      r"|Nicaragua|Venezuela|Bolivia|Ecuador|Cuba)\b"),
    ("Australia", r"\b(Australia|Australian|Sydney|Melbourne|Canberra|New Zealand)\b"),
    ("Canada", r"\b(Canada|Canadian|Ottawa|Ontario|Quebec)\b"),
]
JURISDICTIONS = [(name, re.compile(pat)) for name, pat in JURISDICTIONS]

QUOTED = re.compile(r"[“\"'][^”\"']{15,}[”\"']")


def _unquoted(text):
    """Text with quoted spans removed.

    A report quoting a campaigner saying "this is outrageous" is still a report. Without this
    the comment markers fire on the quotation and every well-sourced story reads as a column -
    which would have reproduced the 18.08.2026 failure in a new place.
    """
    return QUOTED.sub(" ", text or "")


def signals(headline, text):
    """Return a dict of signals, or None when there is not enough text to judge.

    None is a first-class answer. 44% of a day's candidates have no fetchable page, and a
    guess for those would be worse than a blank: it would rank them against each other on
    noise. Callers must treat None as "unknown", never as "false".
    """
    if not text or len(text) < 80:
        return None
    body = _unquoted(text)
    blob = ((headline or "") + ". " + body)

    comment_hits = len(COMMENT_MARKERS.findall(body)) + \
        2 * len(COMMENT_STRUCTURE.findall((headline or "") + " " + body[:120]))
    report_hits = len(REPORT_MARKERS.findall(body))
    # Two-sided so a long discursive opening cannot out-shout a well-attributed one purely on
    # length. Ties go to "report": the briefing is a news digest and mislabelling a report as
    # comment would demote real news, the more expensive error of the two.
    kind = "comment" if comment_hits > report_hits else "report"

    places = [name for name, pat in JURISDICTIONS if pat.search(blob)]
    return {
        "kind": kind,
        "comment_score": comment_hits,
        "report_score": report_hits,
        "primary_doc": bool(PRIMARY_DOC.search(blob)),
        "stage": "update" if UPDATE_MARKERS.search(body) else "first",
        "jurisdictions": places,
        "placed": bool(places),
        "words": len(body.split()),
    }


def flag_string(sig):
    """Compact display form for the ranking sheet. '' when unknown."""
    if not sig:
        return ""
    bits = [sig["kind"]]
    if sig["primary_doc"]:
        bits.append("doc")
    if sig["stage"] == "update":
        bits.append("update")
    if sig["jurisdictions"]:
        bits.append("/".join(sig["jurisdictions"][:2]))
    else:
        bits.append("unplaced")
    return " ".join(bits)


CASES = [
    # (headline, text, expected kind, expected primary_doc)
    ("Bishop Keenan urges support for religious freedom petition",
     "Bishop John Keenan has urged people to support a petition calling for greater "
     "protection for those persecuted because of their faith. Bishop John Keenan, President "
     "of the Bishops' Conference of Scotland, said he wanted to encourage people to back the "
     "call to action for all those suffering around the world for their faith.",
     "report", True),
    ("National Media Skip Extreme Pro-Abortion Law in Massachusetts",
     "The “mainstream” media called it nothing. You couldn't find that story on ABC, "
     "CBS, NBC, PBS, or NPR. What about print? Make no mistake, this is a choice. Surely "
     "the truth is that they did not want you to know.",
     "comment", False),
    ("Federal appeals court upholds ban on ICE arrests at some houses of worship",
     "A federal appeals court on Monday upheld an injunction blocking immigration agents "
     "from making arrests at houses of worship. The ruling was issued by the Fourth Circuit, "
     "which found that the policy was likely unlawful. The Department of Homeland Security "
     "said it was reviewing the judgment.",
     "report", True),
    # Chris, 24.08.2026: this one "should stay along with the Massachusetts piece". It left the
    # top of Life when TEXT_SIGNAL_WEIGHT went to 4 - not demoted as comment (it reads as a
    # report, correctly) but LEFT BEHIND, because stories around it gained the primary_doc
    # bump and an appellate filing did not qualify for it. An appeal to a circuit court is
    # about as primary a document as this briefing handles.
    ("Idaho AG vows to fight for abortion ban blocked by leftist judge",
     "Attorney General Raul Labrador appealed to the Ninth Circuit to uphold Idaho's abortion "
     "ban after a federal judge 'replaced' state law with his own standard, broad enough to "
     "treat a C-section as a reason for an abortion.",
     "report", True),
    # Control for the same change: an argument that merely MENTIONS a court must not collect
    # the bump. Without this the fix would just widen primary_doc until it fires on everything,
    # which makes a +4 that applies to almost every story worth exactly nothing.
    ("The Catholic Church Must Excommunicate Mass. Governor Who Signed Until-Birth Abortion Law",
     "Today, cats have far more protection in Massachusetts than unborn humans. I have said "
     "before that we must be honest about what this means. Surely the bishops can see it.",
     "comment", False),
    ("Why the right will not unite",
     "I have argued before that Reform and the Conservatives have fundamentally different "
     "approaches to power. We must be honest: of course the two will not merge. The real "
     "question is what happens next, and frankly nobody knows.",
     "comment", False),
]


def _selftest():
    ok = fail = 0
    for headline, text, want_kind, want_doc in CASES:
        sig = signals(headline, text)
        if sig is None:
            print(f"  FAIL (no signals) {headline[:52]}")
            fail += 1
            continue
        for label, got, want in (("kind", sig["kind"], want_kind),
                                 ("primary_doc", sig["primary_doc"], want_doc)):
            if got == want:
                ok += 1
            else:
                fail += 1
                print(f"  FAIL {label}: got {got!r} want {want!r} | {headline[:46]}")
        print(f"  {flag_string(sig):38s} | {headline[:46]}")
    # None must be returned, not guessed, when there is nothing to read.
    for empty in (None, "", "too short"):
        if signals("x", empty) is None:
            ok += 1
        else:
            fail += 1
            print(f"  FAIL: expected None for {empty!r}")
    print(f"\n{ok} passed, {fail} failed")
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
