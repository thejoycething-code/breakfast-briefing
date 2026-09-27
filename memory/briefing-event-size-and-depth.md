---
name: briefing-event-size-and-depth
description: sheet eN = named-event size (display only, never merges); tiered text depth default 320; standfirst echo dropped
metadata:
  type: project
---
27.09.2026. corroborate() groups sheet lines on word overlap only, and same_story's entity links are barred for names in >12 headlines — i.e. exactly the biggest stories (Sheen 57, Politico 25, Overton 16). A MERGE on name+event word was tested and rejected: 1,302->1,290 lines, ~15% wrong merges, hid distinct features. Shipped instead: `event_sizes()` prints `eN` beside xN (shared proper name + event word, union-find). Name = capitalised and <30% lowercase that day, minus EVENT_NAME_STOP (institutions, roles, nationalities, "Amendment"...) and regions.py places. Top 25.09 events all correct: media ban 16, Sheen 14, Overton 12.

`--text-short 320` is the default: full 900 chars only for UK/IE, x>=2, e>=3 and ★ leads; sheet 1.12MB -> ~770KB. All 8 tier-1 picks that fell short were decidable from 320 chars. boilerplate.drop_standfirst_echo removes the og:description repeat (28% of openings, avg 275 chars).

**How to apply:** eN is a reading signal, not an importance input — feeding it into importance() needs rank_eval first. If a sheet looks thin on text, `--text-short 0` restores full depth. See [[briefing-text-scrubber]].
