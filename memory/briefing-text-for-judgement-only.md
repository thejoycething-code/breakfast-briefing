---
name: briefing-text-for-judgement-only
description: "Article text goes to the ranking sheet for the judge to read, never into importance() — regex over body text rewards commentary"
metadata: 
  node_type: memory
  type: project
  originSessionId: 56a31411-1c43-4503-ab50-1e5a9db75951
  modified: 2026-08-18T21:42:00.525Z
---

The ranking sheet carries article text since 18.08.2026: `> feed:` (the outlet's summary, when
it adds ≥3 significant words over the headline — 36% are headline-echo) and `> page:` (a
standfirst fetched by `fetch_feeds.fetch_lede()` for stories the feed left blind: no real
summary, direct link, not paywalled, cap 150/day, cached successes-only in `ledes.json`).

**Why text must never feed `importance()`:** measured on the 18.08 sweep, running OUTCOME/SCALE
over summaries "gained" outcome for 10% of stories and the sample was almost all wrong —
comment pieces *narrate* outcomes ("the court ruled… he argues"), so event-verbs in running
text invert the said-versus-happened axis and systematically promote commentary. Headlines work
because their verb IS the story's claim. Text is for the judgement pass; regexes stay on
headlines. Chris also explicitly rejected any velocity/recency proxy.

**How to apply:** read the text lines before tiering — they separate interviews with new
content from rehashes, and reports from commentary in a news headline. No text line = neither
source exists; judge on the headline and don't penalise the silence. `--no-ledes` skips
fetching for fast re-runs. Sheet is ~100k tokens on a heavy day (1.65× bare), still one pass.

The build also caught three substring bugs in `importance()` vocabulary (all fixed with
failing-first ABOVE pairs): bare `freed` matched "free**d**om" — every religious-freedom
headline had been collecting +8 outcome; ES/IT tokens without `\b` fired on English
(Se**nega**l, Con**firma**tion, appro**va**l, de**clara**tion, **fall**out); and `run_tests.py`
now smoke-tests `--sheet` in a subprocess because the fixture's pure-function cases stayed
green while `main()` was crashed by a refactor. Related: [[briefing-markup-becomes-testcase]],
[[briefing-ranking-single-pass]], [[briefing-gnews-decode]].
