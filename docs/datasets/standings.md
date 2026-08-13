# `standings`

WNBA Stats League Standings V3 from wehoop data repository — `leaguestandingsv3` (season-level).

| | |
|---|---|
| **Builder** | [`python/wnba_stats_01_standings_creation.py`](../../python/wnba_stats_01_standings_creation.py) |
| **Release tag** | [`wnba_stats_standings`](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/wnba_stats_standings) |
| **File stem** | `standings_{season}.{parquet,csv,rds}` |
| **Seasons built** | — |
| **Last published** | 2026-07-29 (newest release asset) |
| **Tag created** | 2026-05-11 |
| **Release assets** | 8 |

## Automation

`.github/workflows/daily_wnba_stats.yml` — nightly scrape + build + publish (draft additionally refreshes annually via `annual_wnba_stats_draft.yml`). Runs `scripts/daily_wnba_stats_python_processor.sh`; the stage-99 schedule master is restamped at the end of every run.

## Columns

| col_name | type | description |
|---|---|---|
| `league_id` | String | stats.wnba.com league id ("10" = WNBA). |
| `season_id` | String | stats.wnba.com composite season id: season-type digit + year ("22023" = 2023 regular season). |
| `team_id` | Int64 | stats.wnba.com team id (Int64, e.g. 1611661313 = New York Liberty). |
| `team_city` | String | Team city name. |
| `team_name` | String | Team nickname or full name as the source endpoint ships it. |
| `team_slug` | String |  |
| `conference` | String |  |
| `conference_record` | String |  |
| `playoff_rank` | Int64 |  |
| `clinch_indicator` | String |  |
| `division` | String |  |
| `division_record` | String |  |
| `division_rank` | Int64 |  |
| `wins` | Int64 |  |
| `losses` | Int64 |  |
| `win_pct` | Float64 |  |
| `league_rank` | Int64 |  |
| `record` | String |  |
| `home` | String |  |
| `road` | String |  |
| `l10` | String |  |
| `last10_home` | String |  |
| `last10_road` | String |  |
| `ot` | String |  |
| `three_pts_or_less` | String |  |
| `ten_pts_or_more` | String |  |
| `long_home_streak` | Int64 |  |
| `str_long_home_streak` | String |  |
| `long_road_streak` | Int64 |  |
| `str_long_road_streak` | String |  |
| `long_win_streak` | Int64 |  |
| `long_loss_streak` | Int64 |  |
| `current_home_streak` | Int64 |  |
| `str_current_home_streak` | String |  |
| `current_road_streak` | Int64 |  |
| `str_current_road_streak` | String |  |
| `current_streak` | Int64 |  |
| `str_current_streak` | String |  |
| `conference_games_back` | Float64 |  |
| `division_games_back` | Float64 |  |
| `clinched_conference_title` | Int64 |  |
| `clinched_division_title` | Int64 |  |
| `clinched_playoff_birth` | Int64 |  |
| `clinched_play_in` | Int64 |  |
| `eliminated_conference` | Int64 |  |
| `eliminated_division` | Int64 |  |
| `ahead_at_half` | String |  |
| `behind_at_half` | String |  |
| `tied_at_half` | String |  |
| `ahead_at_third` | String |  |
| `behind_at_third` | String |  |
| `tied_at_third` | String |  |
| `score100_pts` | String |  |
| `opp_score100_pts` | String |  |
| `opp_over500` | String |  |
| `lead_in_fgpct` | String |  |
| `lead_in_reb` | String |  |
| `fewer_turnovers` | String |  |
| `points_pg` | Float64 |  |
| `opp_points_pg` | Float64 |  |
| `diff_points_pg` | Float64 |  |
| `vs_east` | String |  |
| `vs_atlantic` | String |  |
| `vs_central` | String |  |
| `vs_southeast` | String |  |
| `vs_west` | String |  |
| `vs_northwest` | String |  |
| `vs_pacific` | String |  |
| `vs_southwest` | String |  |
| `jan` | String |  |
| `feb` | String |  |
| `mar` | String |  |
| `apr` | String |  |
| `may` | String |  |
| `jun` | String |  |
| `jul` | String |  |
| `aug` | String |  |
| `sep` | String |  |
| `oct` | String |  |
| `nov` | String |  |
| `dec` | String |  |
| `score_80_plus` | String |  |
| `opp_score_80_plus` | String |  |
| `score_below_80` | String |  |
| `opp_score_below_80` | String |  |
| `total_points` | Int64 |  |
| `opp_total_points` | Int64 |  |
| `diff_total_points` | Int64 |  |
| `league_games_back` | Float64 |  |
| `playoff_seeding` | String |  |
| `clinched_post_season` | Int64 |  |
| `neutral` | String |  |
| `season` | Int64 | Season the row belongs to, as a BARE calendar year ("2023") — the WNBA season fits one calendar year, unlike the NBA span form. |
| `season_type` | String | First underscore-separated field of the raw capture's filename, which for a season-type-partitioned endpoint IS the season type: "regular-season" or "playoffs" (lower-case and hyphenated, not "Regular Season"). On rosters and coaches the captures are partitioned by TEAM, so this column repeats team_id and carries no season-type meaning -- a known defect, see those pages. |

## Coverage

_Coverage is tracked per release asset on [`wnba_stats_standings`](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/wnba_stats_standings)._
