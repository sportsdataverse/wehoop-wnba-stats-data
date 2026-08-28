# wehoop-wnba-stats-data


## Women's Basketball Data Releases

[ESPN Women's College Basketball Schedules](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/espn_womens_college_basketball_schedules)

[ESPN Women's College Basketball PBP](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/espn_womens_college_basketball_pbp)

[ESPN Women's College Basketball Team Boxscores](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/espn_womens_college_basketball_team_boxscores)

[ESPN Women's College Basketball Player Boxscores](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/espn_womens_college_basketball_player_boxscores)

[ESPN WNBA Schedules](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/espn_wnba_schedules)

[ESPN WNBA PBP](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/espn_wnba_pbp)

[ESPN WNBA Team Boxscores](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/espn_wnba_team_boxscores)

[ESPN WNBA Player Boxscores](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/espn_wnba_player_boxscores)


## Data Repositories

[wehoop-wnba-raw data repository (source: ESPN)](https://github.com/sportsdataverse/wehoop-wnba-raw)

[wehoop-wnba-data repository (source: ESPN)](https://github.com/sportsdataverse/wehoop-wnba-data)

[wehoop-wnba-stats-data Repo (source: NBA Stats)](https://github.com/sportsdataverse/wehoop-wnba-stats-data)

[wehoop-wbb-raw data repository (source: ESPN)](https://github.com/sportsdataverse/wehoop-wbb-raw)

[wehoop-wbb-data repository (source: ESPN)](https://github.com/sportsdataverse/wehoop-wbb-data)


## Automation

This repo is refreshed by the `Update WNBA Stats Data` GitHub Actions workflow
(`.github/workflows/daily_wnba_stats.yml`), which calls
`scripts/daily_wnba_stats_R_processor.sh` to invoke the R generation scripts
under `R/`.

### Cron schedule (UTC)

The workflow runs once a day at **08:00 UTC**, offset one hour from the parallel
ESPN workflow in `wehoop-wnba-data` so the two jobs do not contend for the same
proxy pool. Four cron entries cover the WNBA calendar:

- `0 8 18-31 10 *` — daily, October 18 through 31 (preseason / season tip-off).
- `0 8 * 11-12 *` — daily, every day in November and December.
- `0 8 * 1-6 *`   — daily, every day from January through June (regular season).
- `0 8 1-12 7 *` — daily, July 1 through 12 (lead-up to the All-Star break).

### Triggers

- `repository_dispatch` event type: **`daily_wnba_stats_data`**.
- Manual run via the GitHub UI (Actions tab -> *Update WNBA Stats Data* ->
  *Run workflow*) or from the CLI:

  ```sh
  gh workflow run daily_wnba_stats.yml -f start_year=2024 -f end_year=2024
  ```

  When `start_year` / `end_year` are omitted the workflow defaults both to
  `wehoop::most_recent_wnba_season()`.

### Proxy list

The R generation scripts read a proxy list from `../../proxylist.csv` (relative
to the repository checkout). The workflow writes that file at job start from
the `WNBA_STATS_PROXY_LIST` GitHub Actions secret (CSV body with columns
`ip,port,login,password`). Set the secret on the repo to enable proxied calls
to the WNBA Stats API.

## Datasets

<!-- BEGIN GENERATED: datasets -->
| Script | Dataset | Release tag | Last published |
|---|---|---|---|
| [`python/wnba_stats_01_standings_creation.py`](python/wnba_stats_01_standings_creation.py) | [`standings`](docs/datasets/standings.md) | [`wnba_stats_standings`](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/wnba_stats_standings) | 2026-07-29 |
| [`python/wnba_stats_02_player_season_stats_creation.py`](python/wnba_stats_02_player_season_stats_creation.py) | [`player_season_stats`](docs/datasets/player_season_stats.md) | [`wnba_stats_player_season_stats`](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/wnba_stats_player_season_stats) | 2026-07-29 |
| [`python/wnba_stats_03_team_season_stats_creation.py`](python/wnba_stats_03_team_season_stats_creation.py) | [`team_season_stats`](docs/datasets/team_season_stats.md) | [`wnba_stats_team_season_stats`](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/wnba_stats_team_season_stats) | 2026-07-29 |
| [`python/wnba_stats_04_lineups_creation.py`](python/wnba_stats_04_lineups_creation.py) | [`lineups`](docs/datasets/lineups.md) | [`wnba_stats_lineups`](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/wnba_stats_lineups) | 2026-07-29 |
| [`python/wnba_stats_05_rosters_creation.py`](python/wnba_stats_05_rosters_creation.py) | [`rosters`](docs/datasets/rosters.md) | [`wnba_stats_rosters`](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/wnba_stats_rosters) | 2026-07-29 |
| [`python/wnba_stats_06_coaches_creation.py`](python/wnba_stats_06_coaches_creation.py) | [`coaches`](docs/datasets/coaches.md) | [`wnba_stats_coaches`](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/wnba_stats_coaches) | 2026-07-29 |
| [`python/wnba_stats_07_draft_creation.py`](python/wnba_stats_07_draft_creation.py) | [`draft`](docs/datasets/draft.md) | [`wnba_stats_draft`](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/wnba_stats_draft) | 2026-08-12 |
| [`python/wnba_stats_08_schedules_creation.py`](python/wnba_stats_08_schedules_creation.py) | [`schedules`](docs/datasets/schedules.md) | [`wnba_stats_schedules`](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/wnba_stats_schedules) | 2026-08-12 |
| [`python/wnba_stats_09_player_game_logs_creation.py`](python/wnba_stats_09_player_game_logs_creation.py) | [`player_game_logs`](docs/datasets/player_game_logs.md) | [`wnba_stats_player_game_logs`](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/wnba_stats_player_game_logs) | 2026-07-29 |
| [`python/wnba_stats_10_pbp_creation.py`](python/wnba_stats_10_pbp_creation.py) | [`pbp`](docs/datasets/pbp.md) | [`wnba_stats_pbp`](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/wnba_stats_pbp) | 2026-08-12 |
| [`python/wnba_stats_11_game_rosters_creation.py`](python/wnba_stats_11_game_rosters_creation.py) | [`game_rosters`](docs/datasets/game_rosters.md) | [`wnba_stats_game_rosters`](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/wnba_stats_game_rosters) | 2026-07-29 |
| [`python/wnba_stats_12_officials_creation.py`](python/wnba_stats_12_officials_creation.py) | [`officials`](docs/datasets/officials.md) | [`wnba_stats_officials`](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/wnba_stats_officials) | 2026-07-29 |
| [`python/wnba_stats_13_player_boxscores_creation.py`](python/wnba_stats_13_player_boxscores_creation.py) | [`player_boxscores`](docs/datasets/player_boxscores.md) | [`wnba_stats_player_boxscores`](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/wnba_stats_player_boxscores) | 2026-07-29 |
| [`python/wnba_stats_14_team_boxscores_creation.py`](python/wnba_stats_14_team_boxscores_creation.py) | [`team_boxscores`](docs/datasets/team_boxscores.md) | [`wnba_stats_team_boxscores`](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/wnba_stats_team_boxscores) | 2026-07-29 |
| [`python/wnba_stats_15_shots_creation.py`](python/wnba_stats_15_shots_creation.py) | [`shots`](docs/datasets/shots.md) | [`wnba_stats_shots`](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/wnba_stats_shots) | 2026-07-29 |
| [`python/wnba_stats_99_schedule_master_creation.py`](python/wnba_stats_99_schedule_master_creation.py) | [`schedule_master`](docs/datasets/schedule_master.md) | `wnba_stats/wnba_stats_schedule_master.parquet` (committed) | — |
| [`python/wnba_stats_99_schedule_master_creation.py`](python/wnba_stats_99_schedule_master_creation.py) | [`games_in_data_repo`](docs/datasets/games_in_data_repo.md) | `wnba_stats/wnba_stats_games_in_data_repo.parquet` (committed) | — |
<!-- END GENERATED: datasets -->

## Automation & status

<!-- BEGIN GENERATED: status -->

| workflow | schedule | last run |
|---|---|---|
| [![annual_wnba_stats_draft.yml](https://github.com/sportsdataverse/wehoop-wnba-stats-data/actions/workflows/annual_wnba_stats_draft.yml/badge.svg)](https://github.com/sportsdataverse/wehoop-wnba-stats-data/actions/workflows/annual_wnba_stats_draft.yml) | day 15 08:00 UTC in Apr; day 16 08:00 UTC in Apr | 2026-05-30 |
| [![daily_wnba_stats.yml](https://github.com/sportsdataverse/wehoop-wnba-stats-data/actions/workflows/daily_wnba_stats.yml/badge.svg)](https://github.com/sportsdataverse/wehoop-wnba-stats-data/actions/workflows/daily_wnba_stats.yml) | daily 07:00 UTC in May-Sep; days 1-20 07:00 UTC in Oct | 2026-08-27 |
| [![orphan_scripts.yml](https://github.com/sportsdataverse/wehoop-wnba-stats-data/actions/workflows/orphan_scripts.yml/badge.svg)](https://github.com/sportsdataverse/wehoop-wnba-stats-data/actions/workflows/orphan_scripts.yml) | on push / PR / dispatch | 2026-08-27 |
| [![tests.yml](https://github.com/sportsdataverse/wehoop-wnba-stats-data/actions/workflows/tests.yml/badge.svg)](https://github.com/sportsdataverse/wehoop-wnba-stats-data/actions/workflows/tests.yml) | on push / PR / dispatch | 2026-08-27 |
| [![wnba_models.yml](https://github.com/sportsdataverse/wehoop-wnba-stats-data/actions/workflows/wnba_models.yml/badge.svg)](https://github.com/sportsdataverse/wehoop-wnba-stats-data/actions/workflows/wnba_models.yml) | on push / PR / dispatch | never run |

<!-- END GENERATED: status -->
