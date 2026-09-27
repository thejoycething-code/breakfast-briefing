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

**11 Sept 2026, TIA Second Reading (negatived 270-286, division 2428).** When the House
divided, ONSIDE is filled from the vote record, not read from words: No on "That the Bill
now be read a Second time" = onside; each checklist block carries a `- vote:` line; a
scratch script did all 75 (46 yes / 29 no). The pass had misread Hoare and Leigh (both voted
No) as against us. `divisions()` puts the result at the head of roundup.md and in the writer's
input. Draft `limit=8` silently hid 14 cuttable speakers (fixed: listed at the foot with
passage). Writer's brief ranked by longest single contribution dropped the opener (37
interruptions) and the Minister; now pinned, rest by total words. MAX_TOKENS 8000 → 16000
(thinking counts); transport timeout scales with max_tokens. The report's "N MPs spoke
against" counts only the 16 in the brief: correct the count sentence by hand (46 of 75).
Reel sequence chosen: Fenton-Glynn, Bradley, Lockhart, Ahmed, Dalton, Duffield.
See [[parl-monitor-one-pack-one-session]].
Later on 11 Sept: probes are cached by speaker+ordinal, so a span fix left stale probes
(now `probe_is_stale` refetches); speech_cut anchored the START of 19/19 clips but the END
of only 3 (Ahmed): 16 fell back to Hansard time, so check trim_bounds' end search before
trusting tails. Chris widened the brief that evening: 46 confirmed against, pick the BEST
speeches by a system (peer session's tools/pick_speeches.py), cut reel + full speeches, post
report and clips to #campaigns-en-gb. Commits 1643eeca, 6cb6f690.
Outcome, 12 Sept 01:45: peer session finished the pack. Selector picked eight speeches
(selection.md); reel re-cut with all eight placed (0.78-0.97, 5m55s); 17 full-speech clips
with both ends anchored (forward-widening + tail-after-head fix, 73d6aea6); report
published to #campaigns-en-gb as canvas F0C1FGS7J12 with a Best speeches section; one
DM to Chris. My six-speaker 16:9 set moved to clips/previous. Open: Slack files:write
scope so clips can be attached to the canvas post.
12 Sept: caption blackouts on 5/17 speech clips (Dalton 125-400s uncaptioned) came from
per-card alignment forced monotone; now one sequence match of all card tokens to heard
words (`_card_times_monotone`). `speech_cut --recaption [--aspect 4:5] --only "Name"`
re-burns parts on disk without fetching; parts are matched by speaker+clock, newest wins.
Measure a track's health by summing caption gaps >3s in the .ass before sending a clip.

**12 Sept 2026 order of work** (docs/debate-pack-social.md "Order of work"): live_debate
during → debate_pack → checklist `--from-vote <division>` → pick_speeches (batches of 8,
verbatim check) → social_cut then speech_cut (clock self-check first, interventions
merged into one clip) → debate_report → `--publish --with-clips` puts footage on Drive
("Debate footage / <date> <title>", Automated Briefs shared drive) and posts the canvas
with the link. Slack carries links, never bytes (bot has no files:write, by decision).
Then sign off the division: see [[parl-monitor-vote-feeds-5ca]].

**17 Sept 2026, Immigration and Asylum Bill.** Asked for a 17 Sept pack: the Commons
was not sitting (16-17 Sept), so the immigration business was the Public Bill Committee's
two oral-evidence sittings on 15 Sept (Hansard section PBC, ext ids 4b4a09da… first,
852cb4e5… second; parliamentlive 3f328b6e… 9.25am, 9b7f7aa9… 2.01pm). Two matching
titles means `--find` refuses; pass `--debate`. Evidence-session shape: Hansard files the
witness's answer under the questioning MP, so "the minister's line" and quotes carry
witness words, and the pass reads MPs off their questions (it called Kohler, LD, "with us"
while his words attacked the Bill). Onside stays a human call. The next PBC sitting is
13 Oct. Bug found and fixed (uncommitted at the time): `tools/debate_pack.py` closed the
store without `commit()`, so debate-pack rows in api_spend were rolled back on every run
since 7 Sept; the 17 Sept second-sitting call's usage is lost. A peer session's
`eu_speeches.py --days 120` held one write transaction for ~13 min, which is longer than
the 120s busy timeout; a scratch wrapper kept spend in a side file and replayed it.

**17 Sept 2026, flagging without a person.** Christopher asked for the whole pack
process to run "whenever a debate happens". The evening task (18:30 weekdays) already
did everything from the flag on; the flag was the hand step. Now three sources write
`config/debate_watch.yaml` (field `source: hand|auto|bill|same-day`): Monday's
`run_monday.py` runs `debate_watch.py suggest --write` (week-ahead items in
AUTO_CATEGORIES on our ground; statements/questions listed, not flagged) and refreshes
flagged bills; `add-bill <bills-api id>` writes one watch per future stage sitting
(committee sittings `min_speakers: 8`, read by the evening task as "| min N");
scheduled task `debate-day-net` at 16:45 weekdays runs `net` and flags today's
debates Hansard shows with 8+ speakers, DMs only when it flags. A hand `add` outranks
the automatic sources. Traps found: the week-ahead gives a bill committee's sitting an
EMPTY description with the bill's name on the committee dict; a refresh that called
`add()` over existing bill watches stripped their notes (now `only_new`). The Bills API
listed the immigration committee to 3 Nov when the week-ahead showed it to 15 Oct.
Flagged: the Immigration and Asylum Bill's seven remaining committee sittings
(13 Oct–3 Nov), area 11. The evening task's SKILL.md was edited in place (min N,
two sittings on one day). Still human: our side for an untracked bill, ONSIDE with
no division, and publishing (approval DM gate, by decision).
