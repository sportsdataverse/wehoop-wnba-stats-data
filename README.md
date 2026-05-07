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
