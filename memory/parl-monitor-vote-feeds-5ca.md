---
name: parl-monitor-vote-feeds-5ca
description: "After a signed-off division (12 Sept 2026): tracker:signed stances outrank the model; both lobbies = abstention; present-but-absent ledgered from the day's other divisions (tellers voted); WAVERING needs two good votes; TARGETED from campaign_performance names; former Aye voters capped at +; flags internal only"
metadata:
  type: project
---

Built the night after the Terminally Ill Adults Second Reading (11 Sept 2026,
defeated 270–286, division 2428). Christopher: "Do all of 1. The machine …
files should go to drive and not live on Slack."

**What a sign-off unlocks.** `trackerledger.apply_signed_stances` writes ±2 for
both lobbies (`tracker:signed`), and the human sign-off beats any model score
(68 refs corrected on 12 Sept, incl. nine June 2025 report-stage refs the model
had at 0). A member in both lobbies gets one `:both` event, stance 0. For each
Commons tracker division, `record_absences` ledgers `:absent` for anyone who
voted in the day's other divisions but not ours; tellers count as voted (2428:
two true absentees, Onn and Stewart). The day's divisions are archived as
`division_cdetail-<id>.json.gz`; the Votes API LIST endpoint was 404, the detail
endpoint fine.

**WAVERING** (`stance.wavering`): two or more votes for our side on the area
(safeguard amendments count), or two of {good votes, majority < 5,000, recent
words not hostile}. Measured on the Second Reading: safeguards≥2 → 24% moved or
stayed away vs 16% base; majority alone 13% (no signal). Predicted Myer (3/4)
and Daby (2/4). **TARGETED**: regex over campaign_performance names ("Tell
<Name>:", "Urge <Name> to") → 20 members; `tools/campaign_targets.py`. Campaign
log is a by-hand weekly refresh (Max / Looker export), no credential in CI.
**Cap**: `stance_overrides.yaml caps:` with `when_any: [Second Reading, Third
Reading]` → nobody who voted Aye at a reading sits at ++ (21 capped).

**Why:** the five flippers (Daby, Myer, Ryan, Goldman, Savage) were all visible in
advance as conflicting or safeguard-voters; Freeman and Lowe were Nov 2024 targets.
**How to apply:** the internal 5CA web sheet shows W/T/± chips and a Wavering
toggle; the partner build drops flags AND tiers (our targets are ours). Between
votes run `tools/since_last_vote.py --area N --write`; during a debate
`tools/live_debate.py --dm`. Match areas as a JSON list, never LIKE '%2%' (that
is area 12 too). See [[parl-monitor-debate-pack]], [[parl-monitor-division-brief-and-spoke]],
[[parl-monitor-one-pack-one-session]].

**Measured 13 Sept 2026 (tools/evaluate_5ca.py, banked in data/5ca-eval/).** On 2428 the
coded WAVERING/CONFLICT flags did not beat the base once staying away counts as
movement (17% vs 19%); the hand-worked 24% was the narrower safeguards-two-plus list.
Treat the flag as a watch list until narrowed. On 2071 the + column was 23% our way:
+ means "might". Run evaluate_5ca after every sign-off; it is the only thing that
scores the sheet.

**The cap is one-directional, and that inflates ++ (found 21 Sept 2026).** The
`caps:` rule stops a former Aye voter reaching ++, but nothing stops a former
*No* voter reaching ++ when they did not vote in the division being scored.
Placement follows the most recent directional vote and an absence is not
counted against it. On the 21 Sept assisted-dying sheet that put 18 members at
++ who were absent on 11 Sept 2026 and were promoted on their June 2025 Third
Reading vote: Labour 12, Conservative 4, Reform 1, plus the Speaker, who cannot
vote at all. Headline ++ read 285 when only 267 had voted our way on the day,
and Labour read 157 against 155 who actually voted No, which is the tell — ++
exceeding the No lobby is the cheap check for this.

**Why:** ++ means "will definitely vote with us", and a member who missed the
decisive division is the opposite of that; they are the contact list. Christopher
caught it by eye off the Labour row before it went to the cluster.

**How to apply:** until the generator counts absence, cross-tab any published ++
column against `cv_votes` for the scored division before quoting it, and move
absentees to +. The same inflation is present in all eleven topic sheets dated
2026-09-21; only assisted dying has been corrected, in the Q3 England report.
Two individual placements on that sheet are also wrong at source: Bambos
Charalambous is + but was a teller for the Ayes, Gareth Snell is -- but voted No.
See [[intel-reports-verified-from-store]].
