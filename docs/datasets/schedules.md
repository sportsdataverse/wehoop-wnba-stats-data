# `schedules`

WNBA Stats Schedule from wehoop data repository — `leaguegamelog` (season-level).

| | |
|---|---|
| **Builder** | [`python/wnba_stats_08_schedules_creation.py`](../../python/wnba_stats_08_schedules_creation.py) |
| **Release tag** | [`wnba_stats_schedules`](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/wnba_stats_schedules) |
| **File stem** | `wnba_stats_schedule_{season}.{parquet,csv,rds}` |
| **Seasons built** | — |
| **Last published** | 2026-08-12 (newest release asset) |
| **Tag created** | 2023-04-03 |
| **Release assets** | 105 |

## Automation

`.github/workflows/daily_wnba_stats.yml` — nightly scrape + build + publish (draft additionally refreshes annually via `annual_wnba_stats_draft.yml`). Runs `scripts/daily_wnba_stats_python_processor.sh`; the stage-99 schedule master is restamped at the end of every run.

## Columns

| col_name | type | description |
|---|---|---|
| `season_id` | String | stats.wnba.com composite season id: season-type digit + year ("22023" = 2023 regular season). |
| `team_id` | Int64 | stats.wnba.com team id (Int64, e.g. 1611661313 = New York Liberty). |
| `team_abbreviation` | String | Three-letter team code ("NYL"). |
| `team_name` | String | Team nickname or full name as the source endpoint ships it. |
| `game_id` | String | stats.wnba.com game id, 10-char string carrying the "10" WNBA league prefix ("1022400001"); pinned Utf8 so it never round-trips through int. |
| `game_date` | String | Game date as the source ships it (calendar date, US Eastern; a Date column in the schedule master). |
| `matchup` | String | Matchup string from the log ("NYL @ LVA" away, "NYL vs. LVA" home). |
| `wl` | String | Result from the row team's perspective: "W" or "L". |
| `min` | Int64 | Team (or player) minutes in the log row. |
| `fgm` | Int64 | Field goals made. |
| `fga` | Int64 | Field goals attempted. |
| `fg_pct` | Float64 | Field-goal percentage (0-1). |
| `fg3m` | Int64 | Three-point field goals made. |
| `fg3a` | Int64 | Three-point field goals attempted. |
| `fg3_pct` | Float64 | Three-point percentage (0-1). |
| `ftm` | Int64 | Free throws made. |
| `fta` | Int64 | Free throws attempted. |
| `ft_pct` | Float64 | Free-throw percentage (0-1). |
| `oreb` | Int64 | Offensive rebounds. |
| `dreb` | Int64 | Defensive rebounds. |
| `reb` | Int64 | Total rebounds. |
| `ast` | Int64 | Assists. |
| `stl` | Int64 | Steals. |
| `blk` | Int64 | Blocks. |
| `tov` | Int64 | Turnovers. |
| `pf` | Int64 | Personal fouls. |
| `pts` | Int64 | Points. |
| `plus_minus` | Int64 | Point differential while on the floor (player rows) or final margin (team rows). |
| `video_available` | Int64 | 1 when the feed links video for the action/game row. |
| `season` | Int64 | Season the row belongs to, as a BARE calendar year ("2023") — the WNBA season fits one calendar year, unlike the NBA span form. |
| `season_type` | String | Season type the capture was made under ("Regular Season", "Playoffs", ...). |
| `player_id` | Int64 | stats.wnba.com person id of the player (Int64); joins rosters, boxscores, game logs and pbp (`person_id`). |
| `player_name` | String | Player display name as the stats API ships it ("Breanna Stewart"). |
| `fantasy_pts` | Float64 | WNBA fantasy points for the player log row (null on team rows). |
| `measure_type` | String | Grain marker of the yearly schedule file's mixed leaguegamelog capture: "t" rows are the two per-team game rows, "p" rows are player game logs. |
| `in_pbp` | Boolean | True when the game's play-by-play made it into a compiled season release. |
| `in_game_rosters` | Boolean | True when the game is present in the compiled game_rosters release. |
| `in_officials` | Boolean | True when the game is present in the compiled officials release. |
| `in_player_boxscores` | Boolean | True when the game is present in the compiled player_boxscores release. |
| `in_team_boxscores` | Boolean | True when the game is present in the compiled team_boxscores release. |

## Coverage

_Coverage is tracked per release asset on [`wnba_stats_schedules`](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/wnba_stats_schedules)._
