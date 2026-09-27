---
name: parl-monitor-5ca-election-mockups
description: "5CA results board (A declaration board + B hemicycle) built into tools/make_5ca_web.py on 17 Sept 2026 as a Results tab above the Sheets tab; change chips count MOVED only, never REASSESSED; C swingometer and D battleground remain mock-ups"
metadata: 
  node_type: memory
  type: project
  originSessionId: 729eaf76-25c8-4154-b0f2-a9d9e376525b
  modified: 2026-09-17T14:36:58.220Z
---

**Christopher picked A on top, B below, sheets on a second tab (17 Sept 2026); built the same day into `tools/make_5ca_web.py` (both houses, partner build drops flags, tiers, moves and since). Mock-ups A-D remain in** `docs/5ca-election-mockups.html`
in ~/parl-monitor (committed in 3e4995b8) holds four working views over the
live 14 Sept Commons sheets: A declaration board (headline numbers, 649-seat bar
with 325 line, five result cards with change chips, party split), B hemicycle
(649 seats, by placement or by party with a stance ring, W/T/±/moved highlights,
hover card), C swingometer (needle = with-us minus against over 649, ghost needle
= previous sheet, gain/loss movers ribbon, eleven mini dials), D battleground
card wall. Generator is a scratchpad script (build_mockups.py) that embeds the
DATASET pulled out of docs/5ca-sheets.html plus a CSV diff of the last two dated
sheets; a real build would live in tools/make_5ca_web.py's data model.

**Two findings that shape the real build:**
- Movement between the 31 Aug and 14 Sept sheets is honest only for Assisted
  dying (26 moves, the 11 Sept vote). Abortion 488, Parental rights 570, Free
  speech 516, Sex-based rights 363 moves are the 12 Sept sign-off wave
  (mostly 0>-- and ->--). A swing display needs a reason tag (vote / sign-off /
  re-scoring) or it will read as persuasion. `ca_member_state.movement` was all
  UNCHANGED on 12 Sept, so it cannot be the source yet.
- Change chips colour by whether the shift helps us, not by direction: a fall
  in the -- column is green.

Stance palette validated with the dataviz script: ++ #1B7F3B, + #7BC47F, 0
#C3C8CF, - #E58A86, -- #B80000 (CVD pass; grey↔light-green normal-vision ΔE
14.8, so glyphs always sit on the marks). Party colours are BBC's. Previewed via
`.claude/launch.json` in ~/Downloads/clacton-vercel (name parl-monitor-docs,
`sh -c cd docs && python3 -m http.server 8765`; `--directory` fails under the
sandbox with a getcwd PermissionError).

Related: [[parl-monitor-5ca-surfaces]], [[parl-monitor-vote-feeds-5ca]].

**How the build counts change (17 Sept 2026).** `stance.recent_moves(conn, area,
since)` reads ca_member_state for changed_at > today-7; only MOVED_UP/DOWN feed
the chips, REASSESSED is stated in a caption as "not counted", NEW listed. An
UNCHANGED re-run now carries the stored last move forward (the returned diff
still says UNCHANGED), because a same-day rebuild on 12 Sept had erased every
move. History before 12 Sept is gone: the Second Reading moves will never show.
Party parse fixed at the same time (`split_decision_maker`: first " (" opens
the suffix, first ", " splits party from seat; seats contain commas, parties
contain "(Co-op)"). The `.dm span` rule that turned W/T chips into full-width
bars is now `.dm .meta`. Another session committed half the work in 3e4995b8
(EU commit); the tool file and pages were left for Christopher to commit.
