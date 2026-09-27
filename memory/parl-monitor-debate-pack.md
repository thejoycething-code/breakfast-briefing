---
name: parl-monitor-debate-pack
description: "Debate pack (7 Sept 2026): tools/debate_pack.py builds roundup/checklist/quotes/shotlist for one debate and downloads clips by wall-clock window from parliamentlive.tv; onside is a human check, never the pass's verdict"
metadata: 
  node_type: memory
  type: project
  originSessionId: 8990c34a-d7d3-45f9-8650-9c152f231f17
  modified: 2026-09-07T16:02:12.874Z
---

Christopher, 2026-09-07: round-up of a key debate, onside quotes, full clips, and a
check for who was and was not onside (for a video montage).

**Shape.** `src/debatepack.py` + `tools/debate_pack.py`. Build:
`--date D --find TERM [--venue "Westminster Hall"] [--event <parliamentlive url|guid>]`
or `--debate <hansard ext id>`. Folder `data/packs/<date>-<slug>/`: roundup.md,
checklist.md (`### speaker: <member_id>` + `ONSIDE: yes|no`), quotes.md, shotlist.csv,
pack.json (cache: directions, manifest, spans), README (PRU licence line), clips/
(gitignored). `--pack F --apply` re-renders after the checklist; `--pack F --download`
clips confirmed speakers only; `--download-debate --from HH:MM --to HH:MM` whole window.

**Facts measured.** Hansard debate items carry sparse clocks (Timestamp items +
some Timecode, Europe/London); speech length = words/2.5 + 6s, capped by next clock
(the "next clock" rule credited an intervener with 290 min). Minister attribution puts
the name in brackets after the office. parliamentlive.tv: front page lists TODAY's
events by venue (date param ignored; past days need a pasted event link); yt-dlp's
extractor yields the HLS master `…/index.m3u8?start=…Z`; `start=&end=` returns just
that window (2-min → 121s). Quality ids 300/850/1300/3000 = 180/360/576/1080p.
Tooling: yt-dlp at ~/Library/Python/3.9/bin, ffmpeg via `imageio-ffmpeg` (pip;
no Homebrew on the Mac). Direction = `stance.classify_live` over each speaker's
joined text, ~1 call per 20 speakers, cached in pack.json (41 speakers = 3 calls).

**How to apply:** first run on today's surrogacy debate once Hansard publishes
(text lands a few hours after the House rises; the tool says "try again later").
Onside quotes and clips follow the CHECKLIST, not the pass. See
[[parl-monitor-division-brief-and-spoke]], [[parl-monitor-build]].
