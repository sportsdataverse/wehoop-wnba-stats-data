# `rosters`

WNBA Stats Rosters from wehoop data repository — `commonteamroster` (season-level).

| | |
|---|---|
| **Builder** | [`python/wnba_stats_05_rosters_creation.py`](../../python/wnba_stats_05_rosters_creation.py) |
| **Release tag** | [`wnba_stats_rosters`](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/wnba_stats_rosters) |
| **File stem** | `rosters_{season}.{parquet,csv,rds}` |
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
| `league_id` | String | stats.wnba.com league id ("10" = WNBA). |
| `player` | String |  |
| `nickname` | String |  |
| `player_slug` | String |  |
| `num` | String |  |
| `position` | String |  |
| `height` | String |  |
| `weight` | String |  |
| `birth_date` | String |  |
| `age` | Float64 |  |
| `exp` | String |  |
| `school` | String |  |
| `player_id` | Int64 | stats.wnba.com person id of the player (Int64); joins rosters, boxscores, game logs and pbp (`person_id`). |
| `how_acquired` | String |  |
| `supplemental_status` | Int64 |  |
| `season_type` | String | Season type the capture was made under ("Regular Season", "Playoffs", ...). |

## Coverage

_Coverage is tracked per release asset on [`wnba_stats_rosters`](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/wnba_stats_rosters)._
