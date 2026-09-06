---
name: parl-monitor-log-relay
description: run_monday.py relays a tool's first line only, bins indented lines as noise, and lifts the rest only if they name a caveat word
metadata:
  type: project
---

`run_monday.py` relays each build tool's output like this: drop lines that are
INDENTED (or contain "warning:"), print the first surviving line as the head,
then print later lines ONLY if they match `\bNOT\b|missing|no recorded|gap|
stale|gaps|published|FAILED|adopted|no generated`.

**Why:** a tool that opens with an output path, indents its caveats, or words
them without one of those tokens is invisible in an unattended run — which is
the only way these runs are ever read. Three dry runs were needed to get one
new tool's output to survive: first only "-> ms-votes.html" was carried, then
Wales's summary but not NI's, then both plus the suppression line.

**How to apply:** a tool run from `run_monday.py` puts EVERYTHING that matters
in one unindented first line (all nations/targets in that one line), and words
any suppression notice with a caveat token — "missing" is the natural one.
Indent only the output paths. Test by simulating the relay, not by asserting
line order. Pairs with [[briefing-silent-suppression]].
