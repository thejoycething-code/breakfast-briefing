# Saved sweeps

A raw sweep is the input to everything downstream: 1,600-odd candidates with headline, outlet,
url, author, dates and feed text. `archive/` stores finished EDITIONS (candidates plus the
tiers assigned); this stores the unjudged pool.

## What this is for

Regression-testing a rule change against a real day. `testcases.txt` proves a rule does what
it claims on a handful of headlines; a saved sweep shows what it does to fifteen hundred, which
is the only way to see the collateral. Every blast-radius figure quoted on 20.08.2026 - "34 of
1,581 items change region", "2 of 392 unsectioned move", "4 items move" - was measured this
way, and two of the day's bugs (New Mexico matching Latin America, Victor Davis Hanson matching
Australia) were found by it and by nothing else.

    cd ~/Downloads/breakfast-briefing
    gunzip -c sweeps/20260820-1318-sweep.json.gz > /tmp/s.json
    python3 shortlist.py /tmp/s.json | head -40          # or --sheet for the full read

## What this is NOT

It is not tomorrow's input, and it must never be used as one. The scheduled 6am run sweeps
fresh, deliberately: this file's 36-hour window closed at 13:18 on 20.08.2026, so anything
published after that is absent, and `seen.json` has since marked its stories as published. A
briefing built from a saved sweep would be a day stale and would repeat itself.

What genuinely carries over to the next run is the CACHES - resolved.json, authors.json,
ledes.json - which the sweep populated and state_sync.sh has already pushed. Those are the
expensive part (link resolution, byline reads, standfirst fetches), and they persist.

## Contents

    20260820-1318-sweep.json.gz   1,616 candidates, 335 feeds ok / 3 failed, 36h window.
                                  The first sweep taken after that day's rule changes, so it
                                  is the corpus that exercises all of them: the blocked-source
                                  bucket, the US place/actor split, country grouping, the
                                  per-feed window, the tag-override rule, and the two new
                                  Polish sources.
