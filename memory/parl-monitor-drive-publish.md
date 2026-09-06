---
name: parl-monitor-drive-publish
description: Brief-sheets Drive upload — the auth outage, the adopt-existing recovery, and Drive search's token-prefix trap
metadata:
  type: project
---

The parl-monitor brief-sheets Drive upload silently self-skipped in every CI
run until 31 Aug 2026: the `GOOGLE_SERVICE_ACCOUNT_JSON` GitHub secret held a
non-JSON copy of the key ("Expecting value: line 1 column 1" on a non-empty
value = base64 or mangled). The upload step never fails the weekly run by
design, so nothing went red — the outage was visible only in one log line.

**How to apply:**
- The known-good key lives at `config/google-service-account.json`
  (git-ignored, local). Reset the CI secret with
  `gh secret set GOOGLE_SERVICE_ACCOUNT_JSON < config/google-service-account.json`
  — never print or paste the key. `tools/publish_briefs_to_drive.py`'s
  loader now accepts plain JSON *or* base64, and names the failure otherwise.
- A pending brief_log row whose generated CSVs died with an old runner can
  never re-upload (one-brief-ever means no regeneration): the publisher now
  **adopts** the newest existing Drive sheet for the subject instead of
  retrying forever. SEND was the type case — on Drive since 23 Aug, row
  pending until adoption healed it.
- Drive's `name contains` search is **token-prefix matching**: a needle
  truncated mid-word matches nothing (a 60-char cut returned zero files
  where the whole-word form found them). Always truncate search needles at
  word boundaries.
- run_monday's tool-output relay only surfaces detail lines matching its
  caveat regex — six successful uploads once hid behind one failure head
  line. Outcome words (published/FAILED/adopted/no generated) now pass; if
  a tool's per-item results ever vanish from the log again, check that
  filter first.

Distinct from [[briefing-drive-upload-limit]], which is the Breakfast
Briefing project's Docs pipeline, not this one.

**Shared-drive 404 trap (2026-08-31):** every Drive API call on a file in
the shared drive MUST carry `supportsAllDrives=true` or the API returns
404 "File not found" for a file that exists. trash_drive_sheet lacked it
and swallowed the 404 into a console line, so every rejected brief's
sheet stayed live in Drive since the rejection loop existed (all five
checked, all five unbinned). When a Drive call 404s on a file you know
exists, check the flag before believing the 404.
