---
name: parl-monitor-pq-full-text
description: The PQ search endpoint truncates questionText at ~255 chars and carries no answer; the detail endpoint has both — archived as pq_detail-<id>.json.gz since 6 Sept 2026; retag PQs only when coverage ≥95%
metadata:
  type: project
---

**The flaw (found 6 Sept 2026 while retagging for taxonomy v1.6):**
`questions-statements-api.parliament.uk/.../questions?searchTerm=…` returns each
question with `questionText` cut at ~255 characters and NO `answerText`. The
sweep archived only that payload, so every downstream reader of a PQ —
`stance.build_text_map`, 5CA quotes, the member roll, `retag_passages.py` —
read a stub. A retag on stubs would have CLEARED 34 correctly tagged rows
("Religion: Education" etc.) whose matching phrase was past the cut.

**The fix:** `src/ingest/pqs.fetch_question(client, id)` reads the per-question
detail endpoint (full question + minister's answer) and archives
`pq_detail-<id>.json.gz` — inside the `pq_*` glob so readers need not know.
`run_weekly._store_pq_questions` calls `pqs.complete()` for each KEPT question
(one extra call per match, not per search result). `build_text_map` keeps the
longer text per id and appends `Answer: …` because the ingest filter matched
on the answer too. `tools/backfill_pq_text.py` fills history: archive-only,
never opens the store, resumable, ~4,029 questions at 0.2 s each.

**Rule:** `retag_passages.py --kind pq --apply` refuses below 95% detail
coverage (`pq_detail_coverage`). Re-derivation is authoritative only when it
reads at least what the ingest read.

**Recall limit, noted 6 Sept:** the ingest filter runs on the SEARCH STUB before
the detail fetch, so a question whose only matching phrase lies past the
~255-char cut is never fetched or stored. Fixing it means fetching detail for
every search result (~240 calls/week, under a minute) — a decision, not made.

**Dispatch trap:** `gh workflow run sunday-pull.yml` after the scheduled Sunday
run is a NO-OP ("already pulled … use --force"); it proves nothing. The
workflow has no force input. Pin ingest changes with unit tests instead.

Related: [[parl-monitor-store-guard]], [[taxonomy-v16-areas]].
