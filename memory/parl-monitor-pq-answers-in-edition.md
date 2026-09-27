---
name: parl-monitor-pq-answers-in-edition
description: The edition prints ministers' answers since 24 Sept 2026 — read back from the pq_detail archive, clustered on shared answer text because the API's groupedQuestions field is always empty
metadata:
  type: project
---

The Westminster edition's questions section carries the QUESTION and the
minister's ANSWER since 24 September 2026, and is headed "What ministers were
asked - and what they said". It was a four-column table (member, heading,
department, date), so a reader learned a question had been answered and
nothing about what either side said.

**Why:** Christopher, 24 Sept 2026 — "written questions needs to give
information as to the question and answer… renaming the question box to give
a better overview of the information gained."

**How to apply:**

- **`answerText` is NOT in the store.** Ingest saves `question_text` into
  `items.extra` (600 chars) and has never saved the answer. The only copy is
  `data/raw/*/pq_detail-<id>.json.gz`. `pqs.archive_map(raw_dir, ids)` reads
  it back in ONE pass; `run_weekly.sections_from_store` fills `answer_text` /
  `holding` onto `pq_rows` and `pq_background`. The row key is the bare id —
  `items.id` is `pq:1939248`, the archive file is `pq_detail-1939248`.
- **A collector nothing reads is not a working collector.**
  `backfill_pq_text.py` had archived answers since 6 Sept and NOTHING ever
  read one back; it was also never scheduled, so coverage decayed to 56% —
  every question answered after the 6th had none to show. It now runs in
  `sunday-pull.yml` (`--limit 400`, archive-only, safe beside the store lock).
  Check coverage by comparing edition qids against the archive, not by
  trusting that a tool exists.
- **Departments answer related questions with ONE reply, and the API's
  `groupedQuestions` field is empty on every record** (checked over 5,452).
  So `digest._cluster` groups on the answer TEXT. Without it, one Cheshire
  and Merseyside paragraph printed five times under Assisted dying, and a
  reply reading "the information requested in HL3448, HL3450, and HL3451"
  printed four times as though it answered each separately — 18 of 44 rows
  were a repeat. Clustering cut the section 23.7KB → 13.2KB.
- **Never paraphrase an answer.** `digest._trim` shortens by DELETING from
  the end and marking the cut; a generated precis would be words put in a
  minister's mouth. See [[parl-monitor-pq-full-text]] for the same rule about
  never inventing a parliamentarian's words.
- **`_ASK_PREAMBLE`** strips "To ask the Secretary of State for X," etc.
  Rebuilt against 1,500 archived questions after two misses: the Church
  Commissioners form ("To ask the hon. Member for Battersea, representing…")
  and every Lords question using a CURLY apostrophe in "His Majesty's".
  Verify a change by measuring how many of 1,500 still carry a preamble AND
  how many are emptied by the strip.
- The **companion page** (`partner.build_questions_page`) carries both in
  full, because the edition trims both and points there. Pipes in an answer
  are escaped — an answer quoting a table would shift every later cell left.

Related: [[parl-monitor-pq-full-text]], [[parl-monitor-edition-recess-shape]].
