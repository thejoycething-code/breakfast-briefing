---
name: briefing-slack-links-copied
description: The never-author-links rule covers the Slack five too, not just the Doc; copy from expected_urls.txt
metadata:
  type: feedback
---

The Breakfast Briefing's "links are never authored, only copied" rule applies to the
**Step 10 Slack post**, not only to the composed Doc. On 31.08.2026 four of the five
Slack links were typed from memory and were fabricated: an invented BBC article ID
(`bbc.co.uk/news/articles/c5y7z9k2jd8o` for the real `bbc.com/.../c23xvv42rp1o`), a
wholly invented domain (`decisionmagazine.com/...` for `billygraham.org/decision-magazine/...`),
and two wrong path segments (Telegraph `/news/` for `/opinion/`, Christian Today
`/article/` for `/news/`). A correction had to be posted to #campaigns-en-gb.

**Why:** the pipeline's link guarantees stop at the Doc. compose.py resolves and
title-verifies, publish.sh --verify diffs every URL byte-exact, and expected_urls.txt
is the record — but the Slack message is composed by hand afterwards and nothing checks
it. `URLs 253/253 verified` says nothing about the five links in Slack.

**How to apply:** build the Slack five by looking each item's index up in
`/tmp/today.json` (or grepping `expected_urls.txt`) and pasting the `url` field verbatim
— the same discipline as [[briefing-cluster-provenance]] applies to headlines. Never
reconstruct a URL from an outlet name and a headline slug, however plausible the pattern:
the WORLD `wng.org/sift/...-1786558522` case is the standing proof that slugs are not
guessable. Verify before posting, not after.
