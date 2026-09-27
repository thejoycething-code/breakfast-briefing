---
name: parl-monitor-social-cut-defaults
description: "Debate video and article defaults (8 Sept 2026): tools/social_cut.py from sequence.md; 1080p archive pull found by words not offsets; spoken-word captions on one fixed point; per-speaker 9:16 crop; CitizenGO plates; article 800 words, no subheads, no org quote"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 8990c34a-d7d3-45f9-8650-9c152f231f17
  modified: 2026-09-08T10:24:23.725Z
---

Christopher, 2026-09-08, after the surrogacy debate montage: "adopt what we learnt
here with the video and the document as defaults moving forward". Now code and docs:
`tools/social_cut.py` + `src/socialcut.py` (driven by `sequence.md` in the pack),
`docs/debate-pack-social.md`, `docs/debate-article-brief.md`.

**Video defaults.** Campaigner writes the order and the spoken passages; the tool
never reorders. Footage pulled fresh from the parliamentlive.tv archive at 1080p,
one window per excerpt, each transcribed and the passage found by its words (the
archive clock is not the live stream's, and yt-dlp section offsets drift). Hard in
on the first word, 0.55s tail. Vertical = full-height 9:16 crop placed per speaker
(not a blurred letterbox). Captions = SPOKEN words, ≤2 lines of ≤30 chars, never
crossing a sentence, every card centred on (540,1600). Name plate 5.2s in principal
blue #4285F4 over ink #202124, white logo top-left, Helvetica Neue (Roboto not
installed; not downloaded without asking). No end card unless asked. Contact sheet
+ words-heard report before posting. PRU licence caution stays in the README.

**Article defaults.** RTL-style debate report, openly from our side: ~800 words,
continuous prose, no subheads, no organisation quote, Hansard wording verbatim,
every speaker linked to their Hansard contribution, one paragraph for the other
side, one for the Minister. Full version kept as article.md alongside.

**Why:** three rounds of corrections on 8 Sept (order, captions moving, end card,
blur vs crop, Hansard vs spoken) are all things a tool can default.
**How to apply:** for the next key debate run the flow in docs/debate-pack-social.md
and write the article to the brief; only ask about order and passages.
See [[parl-monitor-debate-pack]].

**Friday 11 Sept 2026 run (scheduled).** One-time scheduled task `tia-second-reading-debate-pack`
fires 18:30 London: builds the TIA Second Reading pack, pulls and transcribes the whole
sitting, writes a PROVISIONAL sequence.md from the pass (never confirms the checklist),
drafts article.md + article-800.md to the brief, commits, DMs Christopher. Retries itself
+90 min if Hansard is late, gives up after 22:00. Runs only while the desktop app is open.
`--draft` writes sequence.md from quotes.md; `--transcribe` caches whole-debate words;
template at docs/sequence-template.md.

