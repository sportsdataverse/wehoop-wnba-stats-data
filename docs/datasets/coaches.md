# `coaches`

WNBA Stats Coaches from wehoop data repository — `commonteamroster` (season-level).

| | |
|---|---|
| **Builder** | [`python/wnba_stats_06_coaches_creation.py`](../../python/wnba_stats_06_coaches_creation.py) |
| **Release tag** | [`wnba_stats_coaches`](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/wnba_stats_coaches) |
| **File stem** | `coaches_{season}.{parquet,csv,rds}` |
| **Seasons built** | — |
| **Last published** | 2026-07-29 (newest release asset) |
| **Tag created** | 2026-05-11 |
| **Release assets** | 8 |

## Automation

`.github/workflows/daily_wnba_stats.yml` — nightly scrape + build + publish (draft additionally refreshes annually via `annual_wnba_stats_draft.yml`). Runs `scripts/daily_wnba_stats_python_processor.sh`; the stage-99 schedule master is restamped at the end of every run.

## Columns

| col_name | type | description |
|---|---|---|
| `team_id` | Int64 | stats.wnba.com team id (Int64, e.g. 1611661313 = New York Liberty). |
| `season` | Int64 | Season the row belongs to, as a BARE calendar year ("2023") — the WNBA season fits one calendar year, unlike the NBA span form. |
| `coach_id` | Int64 |  |
| `first_name` | String |  |
| `last_name` | String |  |
| `coach_name` | String |  |
| `is_assistant` | Int64 |  |
| `coach_type` | String |  |
| `sort_sequence` | String |  |
| `sub_sort_sequence` | Int64 |  |
| `season_type` | String | Season type the capture was made under ("Regular Season", "Playoffs", ...). |

## Coverage

_Coverage is tracked per release asset on [`wnba_stats_coaches`](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/wnba_stats_coaches)._
