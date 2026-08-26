# Cloud runbook — unattended Breakfast Briefing

You are running in a cloud container with no human watching. Make reasonable calls, never ask
questions, and state every judgement call in your final report.

**Use the cloud `bash` tool for everything. NEVER use `device_bash`** — that runs on Chris's
Mac, which may be switched off. Using it defeats the entire point of this routine.

`BRIEF.md` in this bundle is the authority on *what makes a good briefing* — sections, caps,
provenance, duplicate handling, the suppressed blocks, everything learned from Chris's
corrections. Read it and follow it. This file only covers what differs in the cloud.

## Differences from the local run

| Local brief says | In the cloud |
|---|---|
| Step 1: check Drive via the connector | `publish.sh` does it — its duplicate guard refuses an existing title |
| Step 5: `create_file` with textContent | `./publish.sh --verify` — uploads the real bytes |
| Step 6: read back and diff links | `--verify` already did it and exits non-zero on mismatch |
| State just exists on disk | Pulled from Drive at the start, pushed at the end |

## Order of operations

1. `./state_sync.sh pull` — already done by the trigger's setup block. Confirm all six state
   files are present before continuing. **If `seen.json` is missing, STOP and report**:
   without it the briefing republishes stories that already went out. A missing `cut.json` is
   less severe but still wrong — stories retired for losing to a section cap return as fresh
   candidates. Pull also bootstraps the six judgement files on a fresh container; if
   `testcases.txt` or `sources.opml` came back absent, STOP — a run without the source list
   is not this briefing.
2. `python3 fetch_feeds.py --json /tmp/today.json > /tmp/sweep.txt 2>&1; head -6 /tmp/sweep.txt`
   Do NOT pass `--mark`. On Mondays the window is 84h automatically.
3. `python3 check_sources.py --quiet` on Mondays, or whenever a beat looks thin. Report
   anything it names. This is the only thing that distinguishes a dead source from a quiet
   news week, and it only works because `source_health.json` was restored in step 1.
4. `python3 shortlist.py /tmp/today.json > /tmp/short.txt 2>&1` then read it.
5. `python3 shortlist.py /tmp/today.json --sheet > /tmp/sheet.txt 2>&1` and read the whole
   day in ONE pass. Tier every line yourself. Follow BRIEF.md on sections, caps and
   provenance.
6. Write `/tmp/picks.json`, then
   `mkdir -p out && python3 compose.py /tmp/today.json /tmp/picks.json --no-mark --md out/$(date +%Y%m%d)-breakfast-briefing.md > /tmp/briefing.html`
   Always `--no-mark`. Nothing is recorded as published until step 8.
7. `./publish.sh --verify`
   It uploads the bytes, refuses to duplicate an existing title, checks Drive stored a real
   Google Doc, then exports the doc and diffs every URL. **If it exits non-zero, STOP.** Do
   not mark, do not push state. Report what it said.
8. Only after step 7 succeeded:
   `python3 mark_published.py /tmp/today.json /tmp/picks.json`
9. `python3 archive_day.py /tmp/today.json /tmp/picks.json`
   Banks this edition's tier labels as ranking evaluation corpus. Not synced to Drive (the
   archive grows without bound and STATE_FILES is a flat file list), so on a stateless runner
   it is written and lost — say so rather than assuming the corpus grew.
10. `./state_sync.sh push`
   Twelve files now: six state, plus the six hand-written judgement files (testcases.txt,
   exclusions.txt, bylines.txt, link_fixes.txt, extra_feeds.txt, sources.opml).

**Steps 7→8→10 are an order, not a suggestion.** Push an unmarked `seen.json` and the day is
thrown away. Mark for a document that never published and those stories are burned — never
offered again. That is why marking is last, and why nothing is marked at compose time.
Archiving in step 9 is the one step whose failure costs only that day's labels.

## When to refuse

Publish anyway, but say so loudly, if a section is thin or some feeds failed. Only REFUSE to
publish if the sweep returns fewer than 60 candidates or more than 40 feeds failed — those
are the existing health thresholds and they mean the sweep itself is broken, not that the
news was quiet.

## Report at the end

Feeds ok/failed, candidates returned, how many carried a `[ran]` flag, items per section, the
link-diff result from `publish.sh --verify` (N/N), whether marking and state push both ran,
the document link, and anything that looked wrong. If you stopped early, say exactly where
and what the error was — a failed run that reports clearly costs one day; a failed run that
reports "done" costs the dedupe state.
