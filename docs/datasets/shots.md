# `shots`

WNBA Stats Shots from wehoop data repository — `derived` (derived-level).

| | |
|---|---|
| **Builder** | [`python/wnba_stats_15_shots_creation.py`](../../python/wnba_stats_15_shots_creation.py) |
| **Release tag** | [`wnba_stats_shots`](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/wnba_stats_shots) |
| **File stem** | `shots_{season}.{parquet,csv,rds}` |
| **Seasons built** | — |
| **Last published** | 2026-09-02 (newest release asset) |
| **Tag created** | 2026-05-11 |
| **Release assets** | 95 |

## Automation

`.github/workflows/daily_wnba_stats.yml` — nightly scrape + build + publish (draft additionally refreshes annually via `annual_wnba_stats_draft.yml`). Runs `scripts/daily_wnba_stats_python_processor.sh`; the stage-99 schedule master is restamped at the end of every run.

## Columns

| col_name | type | description |
|---|---|---|
| `game_id` | String | stats.wnba.com game id, 10-char string carrying the "10" WNBA league prefix ("1022400001"); pinned Utf8 so it never round-trips through int. |
| `season` | Int64 | Season the row belongs to, as a BARE calendar year ("2023") — the WNBA season fits one calendar year, unlike the NBA span form. |
| `period` | Int64 | Period number (1-4; 5+ = overtime). |
| `clock` | String | Game clock at the action in ISO-8601 duration form ("PT08M12.00S"). |
| `team_id` | Int64 | stats.wnba.com team id (Int64, e.g. 1611661313 = New York Liberty). |
| `team_tricode` | String | Three-letter team code as the v3 endpoints name it ("NYL"). |
| `person_id` | Int64 | stats.wnba.com person id of the player (or official) the row describes; the same id space as player_id. |
| `player_name` | String | Player display name as the stats API ships it ("Breanna Stewart"). |
| `action_type` | String | Action family ("Made Shot", "Rebound", "Turnover", "Foul", ...). |
| `sub_type` | String | Action detail within the family ("Jump Shot", "Offensive", ...). |
| `shot_result` | String | "Made" / "Missed" for shot actions; empty otherwise. |
| `shot_value` | Int64 | Point value of a shot attempt (2 or 3; 1 for free throws, 0 for non-shots). |
| `shot_distance` | Int64 | Shot distance in feet (0 for non-shots). |
| `x_legacy` | Int64 | Shot x-coordinate in the legacy stats coordinate frame (tenths of feet from the basket centerline; null for non-shots). |
| `y_legacy` | Int64 | Shot y-coordinate in the legacy coordinate frame (tenths of feet from the baseline; null for non-shots). |
| `description` | String | Human-readable action narrative from the feed. |
| `score_home` | String | Home score after the action (string; carried forward between scores). |
| `score_away` | String | Away score after the action (string; carried forward between scores). |

## Coverage

_Coverage is tracked per release asset on [`wnba_stats_shots`](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/wnba_stats_shots)._
