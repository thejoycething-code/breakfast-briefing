---
name: briefing-prefetch-and-resume
description: sweep prefetches article text during Google decode (sheet 17min -> ~2-5min); finish_edition.sh --from re-verifies before marking
metadata:
  node_type: memory
  type: project
  originSessionId: 21b59139-633e-4145-968c-96936ff4039b
  modified: 2026-09-27T00:27:40.577Z
---

27.09.2026: fetch_feeds.py's TextPrefetcher fetches openings/previews alongside the Google News decode (direct links queued at once, decoded ones via resolve_items' on_resolved callback) into the same caches the sheet reads. Test run: 902 texts fetched in-sweep, sheet 4:49 then ~2:05 after memoising sig_words/entities (ran_before was 5.1M entities() calls, 56s CPU) and skipping lede fetches for leads with a cached opening. `--no-prefetch` restores the old path.

`finish_edition.sh --from mark|tiers|archive|backup` resumes the tail and ALWAYS re-verifies the already-published doc first via verify_doc.sh/verify_links.py (href-to-href). Built after 25.09.2026, when publish.sh's regex stopped at ")" and halted the tail on a byte-exact doc.

**Why:** 48 min of waiting before any reading; a false verify alarm cost a hand-run tail.

**How to apply:** if the tail stops after publishing, fix the cause then `--from mark` — never hand-run marking. Also: decoded Google items now get `recheck_paywall()`; before, 50/day topic-search items (Times, Telegraph, Church Times) were treated as free pages. See [[briefing-finish-edition-tail]].

**27.09.2026 evening, decode made cheaper:** resolve_items now fetches signatures per item but looks them up 10 per batchexecute call (`BATCH_SIZE`); Google returns rows OUT OF ORDER with the request id in row[6], and an unanswered request is a row with a null payload — always map by id. Verified 21/21 identical to the single path, 33s -> 17s. fetch_feeds also skips decoding items that `reaches_a_section()` rejects (27% on 25.09); the header now reads `K still redirects (+J filler not decoded)` and only K is the health signal. Test sweep: 9m19s (vs 27-31m), though cache hits flatter it — Monday's 84h run is the real measure.
