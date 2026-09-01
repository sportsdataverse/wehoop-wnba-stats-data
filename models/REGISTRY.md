# Model registry

One row per model dataset this repo publishes (Track C step 1). Compute-on-
demand model dataset — no fitted booster artifacts; the engines are the same
sdv-py RAPM/adj-RAPM/DARKO machinery behind `nba_player_impact`, fed WNBA
possessions. Each publish writes `wnba_player_impact_card.json`, the metadata
authority. `tests/test_model_registry.py` keeps this table in lockstep.

| model | artifact(s) | release tag | training data | fitting script | gates at publish | last publish | cadence |
|---|---|---|---|---|---|---|---|
| WNBA player impact (RAPM / adj-RAPM / DARKO-style engines, consolidated) | `wnba_player_impact_{season}.parquet`, 30 seasons + `wnba_player_impact_card.json` — **91 assets** | `wnba_player_impact` | this repo's possessions trees (offline raw store; pre-2005 team logs repaired from player sums — see the 2026-07-28 publish notes) | `wnba_model_publish/builders.py::build_wnba_player_impact` | engine parity with the NBA twin + card-recorded per-run diagnostics — numeric floors: TODO (not yet encoded as publish-blocking gates) | 2026-07-29 | `wnba_models.yml` — dispatch-only BY DESIGN (rate-budgeted; stats.wnba.com hangs on datacenter IPs, multi-season runs go residential; `dry_run` defaults true) |

Known data caveats (inherited, recorded so nobody rediscovers them):
- `gamerotation` was captured for only 27/220 games in 2010 → pre-~2015
  lineups sparse by design (a `-raw` sweep decision).
- Pre-2005 WNBA team logs were garbage upstream and are repaired from player
  sums in the build.

## Operability (Track C steps 2–6)

- `models/manifest.yaml` — single home for the model/stage list (guarded by `tests/test_model_manifest.py`).
- One model = one numbered pipeline, flat in `python/` beside the data stages; run subsets with `scripts/wnba_models.sh`.
- Compute-on-demand / enrichment surfaces: no fitted artifacts to commit, no fingerprint skip (living upstream inputs), card sidecars carry per-publish metadata.
- Engine individualization (2026-09-01): stages `wnba_model_01_possessions` … `wnba_model_07_darko` run ONE engine each with parquet handoffs (`build_out/impact_engines/`); `wnba_model_08_impact` is the consolidated build+publish and remains the production path.
