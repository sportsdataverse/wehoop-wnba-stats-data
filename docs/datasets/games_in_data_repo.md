# `games_in_data_repo`

Stage-99 schedule-master artifact (spec D34/D36): only games present in at least one compilation — the numerator, what consumers join against. The ``in_*`` flag set is derived from the dataset registry, never hand-listed. Republished on [`wnba_stats_schedules`](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/wnba_stats_schedules) alongside the yearly schedule files.

| | |
|---|---|
| **Builder** | [`python/wnba_stats_99_schedule_master_creation.py`](../../python/wnba_stats_99_schedule_master_creation.py) |
| **Committed at** | `wnba_stats/wnba_stats_games_in_data_repo.parquet` |

## Automation

`.github/workflows/daily_wnba_stats.yml` — nightly scrape + build + publish (draft additionally refreshes annually via `annual_wnba_stats_draft.yml`). Runs `scripts/daily_wnba_stats_python_processor.sh`; the stage-99 schedule master is restamped at the end of every run.

## Columns

| col_name | type | description |
|---|---|---|
| `away_team_abbreviation` | String | Away team three-letter code. |
| `away_team_id` | Int64 | stats.wnba.com team id of the away team. |
| `away_team_name` | String | Away team name. |
| `away_team_score` | Int64 | Away final (or current) score. |
| `game_date` | Date | Game date as the source ships it (calendar date, US Eastern; a Date column in the schedule master). |
| `game_id` | String | stats.wnba.com game id, 10-char string carrying the "10" WNBA league prefix ("1022400001"); pinned Utf8 so it never round-trips through int. |
| `home_team_abbreviation` | String | Home team three-letter code. |
| `home_team_id` | Int64 | stats.wnba.com team id of the home team. |
| `home_team_name` | String | Home team name. |
| `home_team_score` | Int64 | Home final (or current) score. |
| `in_game_rosters` | Boolean | True when the game is present in the compiled game_rosters release. |
| `in_officials` | Boolean | True when the game is present in the compiled officials release. |
| `in_pbp` | Boolean | True when the game's play-by-play made it into a compiled season release. |
| `in_player_boxscores` | Boolean | True when the game is present in the compiled player_boxscores release. |
| `in_team_boxscores` | Boolean | True when the game is present in the compiled team_boxscores release. |
| `season` | String | Season the row belongs to, as a BARE calendar year ("2023") — the WNBA season fits one calendar year, unlike the NBA span form. |
| `season_type_id` | String | Leading digit of season_id encoding the season type (2 = regular season, 4 = playoffs). |

## Coverage

_6,969 games across 30 seasons (committed)._
