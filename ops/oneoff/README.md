# ops/oneoff

Dated one-off drivers, kept for the record rather than for re-running.

A script lands here when it repaired or migrated something once and has no
standing job: the recurring pipeline is the durable entrypoint, and re-running
one of these against today's data is at best a no-op. They are retained because
the defect they repaired, and the protocol they used, are worth being able to
read back.

The `orphan-scripts` gate exempts this directory (and `ops/init/`) for exactly
that reason — everything under `scripts/` and top-level `ops/` must be
referenced by a runbook or workflow, because there a script nobody references
is indistinguishable from a dead one.

| Script | What it did |
|---|---|
| `20260812_publish_draft_recapture.py` | published the rebuilt draft artifacts onto wnba_stats_draft under the cutover protocol |
