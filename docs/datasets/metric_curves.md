# `metric_curves`

WNBA Stats Metric Curves from wehoop data repository — `derived` (derived-level).

FG% by shot distance -- league, team and player curves per season, computed by `sportsdataverse.metric_curves` from the committed `wnba_stats_shots`. One row per (season, entity, bucket): 1-ft bins from 0 to 35 ft, then 35-50 and 50-95 ft (`x_lo` inclusive, `x_hi` exclusive), each carrying `attempts`, `successes` (makes) and `rate = successes / attempts`; an empty bucket is absent, never a zero row. Attempts are regular-season and playoff shots only (`season_type_id` 2 and 4, read off the game id's type digit -- the committed WNBA shots carry no other game type). Ids are stats.wnba.com ids as text with `id_source = "wnba_stats"`: `entity_id` is the `team_id` / `person_id` (null on the league row), `team_id` on a player row is the team of most of that player's attempts. `down` and `epa_per_att` are null on every row (the cross-league contract's football-only columns). Span 1997-present, the shots' own span (seasons are calendar years).

| | |
|---|---|
| **Builder** | [`python/wnba_stats_17_metric_curves_creation.py`](../../python/wnba_stats_17_metric_curves_creation.py) |
| **Release tag** | [`wnba_stats_metric_curves`](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/wnba_stats_metric_curves) |
| **File stem** | `metric_curves_{season}.{parquet,csv,rds}` |
| **Seasons built** | — |
| **Last published** | — (newest release asset) |
| **Tag created** | — |
| **Release assets** | — |

## Automation

`.github/workflows/daily_wnba_stats.yml` — nightly scrape + build + publish (draft additionally refreshes annually via `annual_wnba_stats_draft.yml`). Runs `scripts/daily_wnba_stats_python_processor.sh`; the stage-99 schedule master is restamped at the end of every run.

## Columns

| col_name | type | description |
|---|---|---|
| `season` | Int64 | Season the row belongs to, as a BARE calendar year ("2023") — the WNBA season fits one calendar year, unlike the NBA span form. |
| `entity_type` | String | Which aggregate the row is: "league" (every counted attempt that season), "team" or "player". |
| `entity_id` | String | stats.wnba.com id of the entity as TEXT -- the team_id on a team row, the person_id on a player row, null on the league row. |
| `entity_name` | String | Label for the entity: the team tricode ("NYL") on a team row, the shooter's name as the pbp ships it on a player row; null on the league row. |
| `team_id` | String | stats.wnba.com team id (e.g. 1611661313 = New York Liberty). |
| `id_source` | String | Namespace of `entity_id` / `team_id` on this row -- "wnba_stats" here; the cross-league contract carries "espn", "gsis" and "nba_stats" elsewhere. |
| `metric` | String | Curve name: "fg_pct_by_shot_distance" (field-goal percentage by shot distance in feet). |
| `down` | Int64 | Null on every row: the second axis of the football-only success_by_down_distance curve, carried for the cross-league contract. |
| `x_lo` | Float64 | Bucket lower edge in feet, inclusive: 1-ft bins from 0 to 35, then 35 and 50. |
| `x_hi` | Float64 | Bucket upper edge in feet, exclusive: x_lo + 1 below 35 ft, then 50 and 95. |
| `attempts` | Int64 | Field-goal attempts in the bucket -- regular-season and playoff shots (season_type_id 2 and 4, the game id's type digit). An empty bucket is absent, never a zero row. |
| `successes` | Int64 | Made field goals in the bucket. |
| `rate` | Float64 | successes / attempts, one exact division (no smoothing or prior). |
| `epa_per_att` | Float64 | Null on every row: shots carry no EPA. Populated on the football twins of this contract. |

## Coverage

_Coverage is tracked per release asset on [`wnba_stats_metric_curves`](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/wnba_stats_metric_curves)._
