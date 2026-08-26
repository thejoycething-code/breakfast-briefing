---
name: briefing-drive-upload-limit
description: Breakfast Briefing HTML over ~50KB cannot be published to Drive without corrupting links; only the MCP connector works and it needs inline text
metadata: 
  node_type: memory
  type: project
  originSessionId: 27657ad0-2695-4d20-9f9f-2d6fae03ad14
  modified: 2026-08-14T07:30:58.172Z
---

Publishing the Breakfast Briefing to Drive has no byte-exact path for large editions. The Google Drive MCP connector's `create_file` accepts only inline `textContent`/`base64Content` — it cannot read a local file — and the Drive REST API (via the `google-drive-api` skill) returns `401 authError`, so `scripts/` + multipart upload from disk is unavailable in this environment.

That forces hand-transcription of the composed HTML into the tool call. On 14.08.2026 the edition was 249 items / 87KB, of which ~50KB was 81 long Google News redirect URLs. Transcription corrupted exactly 2 of 249 URLs by one character each (`CBMipgF`→`CBMipoF`; `…c0040gGO`→`…c0400gGO`). Both were Google News redirects; both silently dead. The connector cannot edit a doc after creation, so they could not be fixed.

**Why:** base64 redirect blobs have no redundancy, so a single flipped character is undetectable by eye and produces a wrong-but-plausible link — exactly the failure `expected_urls.txt` exists to catch.

**How to apply:** always verify after publishing rather than trusting the upload. Read the doc back with `read_file_content` (its text export includes every URL, headline and source), extract `https?://\S+`, and diff against `href="…"` in the local `/tmp/briefing.html`; also check each headline and source string appears. Ignore `Word\&Way` mismatches — the export markdown-escapes `&`, so that is a false positive. A clean re-transcription is achievable: the second attempt on 14.08.2026 verified 249/249 URLs byte-exact, so on failure just republish and re-verify rather than accepting a broken doc.

**The connector cannot delete or trash either** — it has only create/copy/read/search/metadata/permissions. So a failed attempt leaves a junk doc with the same title that Chris must bin by hand, and the folder temporarily holds two same-titled docs. Republishing is therefore not free: warn him, and hand him both file IDs so he knows which to keep.

Do not waste time re-running the resolver to shrink the payload: it is deterministic and already maximal (a re-run produced a byte-identical file, same 81 redirects). WebFetch cannot resolve the redirects either — Google answers with a `consent.google.com` 302. If Drive REST auth is ever configured, switch to multipart upload from disk and the whole problem disappears. See [[breakfast-briefing]] and [[briefing-silent-suppression]].
