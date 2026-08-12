# `draft`

WNBA Stats Draft History from wehoop data repository — `drafthistory` (season-level).

| | |
|---|---|
| **Builder** | [`python/wnba_stats_07_draft_creation.py`](../../python/wnba_stats_07_draft_creation.py) |
| **Release tag** | [`wnba_stats_draft`](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/wnba_stats_draft) |
| **File stem** | `draft_{season}.{parquet,csv,rds}` |
| **Seasons built** | — |
| **Last published** | 2026-08-12 (newest release asset) |
| **Tag created** | 2026-05-11 |
| **Release assets** | 95 |

## Automation

`.github/workflows/daily_wnba_stats.yml` — nightly scrape + build + publish (draft additionally refreshes annually via `annual_wnba_stats_draft.yml`). Runs `scripts/daily_wnba_stats_python_processor.sh`; the stage-99 schedule master is restamped at the end of every run.

## Columns

| col_name | type | description |
|---|---|---|
| `person_id` | Int64 | stats.wnba.com person id of the player (or official) the row describes; the same id space as player_id. |
| `player_name` | String | Player display name as the stats API ships it ("Breanna Stewart"). |
| `season` | Int64 | Season the row belongs to, as a BARE calendar year ("2023") — the WNBA season fits one calendar year, unlike the NBA span form. |
| `round_number` | Int64 |  |
| `round_pick` | Int64 |  |
| `overall_pick` | Int64 |  |
| `draft_type` | String |  |
| `team_id` | Int64 | stats.wnba.com team id (Int64, e.g. 1611661313 = New York Liberty). |
| `team_city` | String | Team city name. |
| `team_name` | String | Team nickname or full name as the source endpoint ships it. |
| `team_abbreviation` | String | Three-letter team code ("NYL"). |
| `organization` | String |  |
| `organization_type` | String |  |
| `player_profile_flag` | Int64 |  |

## Coverage

_Coverage is tracked per release asset on [`wnba_stats_draft`](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/wnba_stats_draft)._
