---
name: parl-monitor-one-pack-one-session
description: Two Claude sessions worked the same debate pack on 11 Sept 2026 and their renders raced on identical output paths; a closed lid stalled every background job for two hours
metadata:
  type: feedback
---

On 11 Sept 2026 Christopher had two Claude Code sessions open on ~/parl-monitor. The
first built the TIA pack at 16:58 and committed it at 17:13; its background speech_cut
and social_cut kept running (ppid 1, old shell snapshot) while my session filled the
checklist, rewrote sequence.md and started its own render. Both renders wrote to
clips/hd and clips/final under the same names. I stopped the stray render (it was
cutting the superseded eight-speaker draft) and said so.

**Why:** social_cut and speech_cut key outputs on speaker slug and pack folder, never on
the sequence that produced them, so two renders cannot coexist. And whisper at 17
threads per process on 12 cores means two renders each run slower than one run twice.

**How to apply:** before touching a pack, `ps -eo pid,ppid,lstart,command | grep -E
"speech_cut|social_cut|debate_"` and check `git log -3` for a fresh commit from another
session. Check `pmset -g log | grep -E "Sleep|Wake"` before diagnosing a "two-hour"
stall: the lid was shut 17:30-19:18. Run whisper jobs one at a time.
