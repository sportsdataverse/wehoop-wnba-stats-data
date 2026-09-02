# Model registry

One row per model dataset this repo publishes (Track C step 1). Compute-on-
demand model dataset — no fitted booster artifacts; the engines are the same
sdv-py RAPM/adj-RAPM/DARKO machinery behind `nba_player_impact`, fed WNBA
possessions. Each publish writes `wnba_player_impact_card.json`, the metadata
authority. `tests/test_model_registry.py` keeps this table in lockstep.

| model | artifact(s) | release tag | training data | fitting script | gates at publish | last publish | cadence |
|---|---|---|---|---|---|---|---|
| WNBA player impact (RAPM / adj-RAPM / DARKO-style engines, consolidated) | `wnba_player_impact_{season}.parquet`, 30 seasons + `wnba_player_impact_card.json` + `wnba_player_impact_spm_coefficients.json` (additive sidecar) — **91 assets published; 92 after the next publish** | `wnba_player_impact` | this repo's possessions trees (offline raw store; pre-2005 team logs repaired from player sums — see the 2026-07-28 publish notes) | `wnba_model_publish/builders.py::build_wnba_player_impact` | **five numeric floors, publish-blocking** (`wnba_model_publish/gates.py`; table below) — evaluated on every `impact` invocation, report written into the card sidecar under `publish_gates` | 2026-07-29 | `wnba_models.yml` — dispatch-only BY DESIGN (rate-budgeted; stats.wnba.com hangs on datacenter IPs, multi-season runs go residential; `dry_run` defaults true) |

Known data caveats (inherited, recorded so nobody rediscovers them):
- `gamerotation` was captured for only 27/220 games in 2010 → pre-~2015
  lineups sparse by design (a `-raw` sweep decision).
- Pre-2005 WNBA team logs were garbage upstream and are repaired from player
  sums in the build.

## Publish floors (`wnba_model_publish/gates.py`)

Every floor sits strictly BELOW the value observed on the 2026-07-29 published
release across all 30 seasons (1997–2026), measured 2026-09-01 with

```sh
python -m wnba_model_publish gates --from-release --json-out gates.json
```

Floors were **re-measured on WNBA data, not inherited from the NBA twin**: a
~40-game season leaves far less signal in each RAPM fit, and the forward
floors land at roughly half the NBA's as a result. A floor is a regression
detector, not a target: **never lower one to make a publish pass** — debug the
build, and a re-derivation must record the new observation beside the constant.

| gate | floor | observed (min across seasons) | NBA twin's floor | what it catches |
|---|---:|---:|---:|---|
| `rs_rows_min` | 80 | 98 (1997, the 28-game inaugural season) | 400 | a season that silently lost its population |
| `r_rapm_adj_min` | 0.65 | 0.751 (2023) | 0.75 | the SPM prior overwriting RAPM instead of shrinking it |
| `r_spm_rapm_min` | 0.18 | 0.237 (2026) | 0.22 | SPM no longer fitting the target it was trained on |
| `r_rapm_yoy_min` | 0.10 | 0.146 (2004) | 0.24 | the panel losing player-level persistence |
| `r_darko_fwd_min` | 0.05 | 0.080 (2004) | 0.20 | the projection decoupling from next-season RAPM |

**No oracle gates here, deliberately.** The NBA twin also gates concurrent
validity against published Ryan Davis RAPM / Dunks & Threes EPM CSVs; no
comparable public WNBA player-impact metric is available to this repo, so
rather than ship an always-SKIPPED gate that could be mistaken for coverage,
the family is absent and the five internal floors carry the publish decision.
(The pre-2026-09-01 registry and writeup claimed these engines were
proxy-validated against oracle CSVs "beating the minutes baseline ~10%" — that
was inherited from the NBA twin and never held for the WNBA.)

## Operability (Track C steps 2–6)

- `models/manifest.yaml` — single home for the model/stage list (guarded by `tests/test_model_manifest.py`).
- One model = one numbered pipeline, flat in `python/` beside the data stages; run subsets with `scripts/wnba_models.sh`.
- Compute-on-demand / enrichment surfaces: no fitted artifacts to commit, no fingerprint skip (living upstream inputs), card sidecars carry per-publish metadata.
- Additive artifact (2026-09-01): `wnba_player_impact_spm_coefficients.json` — one record per season with the fitted offense/defense SPM coefficient vectors, feature names, the fit population's feature SDs, and the train-time fit metrics. Written by the build; rebuildable from published seasons + the committed raw store with `python -m wnba_model_publish spm-coefficients --seasons 1997:2026 --raw-store-dir <wehoop-wnba-stats-raw>/wnba_stats/json --out docs/models` (offline by contract — a store miss raises rather than falling through to stats.wnba.com).
- Engine individualization (2026-09-01): stages `wnba_model_01_possessions` … `wnba_model_07_darko` run ONE engine each with parquet handoffs (`build_out/impact_engines/`); `wnba_model_08_impact` is the consolidated build+publish and remains the production path.
