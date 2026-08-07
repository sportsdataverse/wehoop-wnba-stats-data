# `pbp`

WNBA Stats Play-by-Play from wehoop data repository — `playbyplayv3` (game-level).

| | |
|---|---|
| **Builder** | [`python/wnba_stats_10_pbp_creation.py`](../../python/wnba_stats_10_pbp_creation.py) |
| **Release tag** | [`wnba_stats_pbp`](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/wnba_stats_pbp) |
| **File stem** | `play_by_play_{season}.{parquet,csv,rds}` |
| **Seasons built** | 1997–2026 (30 seasons) |
| **Last published** | 2026-07-29 (newest release asset) |
| **Tag created** | 2023-04-03 |
| **Release assets** | 8 |

## Automation

`.github/workflows/daily_wnba_stats.yml` — nightly scrape + build + publish (draft additionally refreshes annually via `annual_wnba_stats_draft.yml`). Runs `scripts/daily_wnba_stats_python_processor.sh`; the stage-99 schedule master is restamped at the end of every run.

## Columns

| col_name | type | description |
|---|---|---|
| `action_number` | Int64 | Ordinal of the action within the game as numbered by the stats feed; monotone but not gapless (video-only actions are skipped). |
| `clock` | String | Game clock at the action in ISO-8601 duration form ("PT08M12.00S"). |
| `period` | Int64 | Period number (1-4; 5+ = overtime). |
| `team_id` | Int64 | stats.wnba.com team id (Int64, e.g. 1611661313 = New York Liberty). |
| `team_tricode` | String | Three-letter team code as the v3 endpoints name it ("NYL"). |
| `person_id` | Int64 | stats.wnba.com person id of the player (or official) the row describes; the same id space as player_id. |
| `player_name` | String | Player display name as the stats API ships it ("Breanna Stewart"). |
| `player_name_i` | String | Abbreviated player name ("B. Stewart"). |
| `x_legacy` | Int64 | Shot x-coordinate in the legacy stats coordinate frame (tenths of feet from the basket centerline; null for non-shots). |
| `y_legacy` | Int64 | Shot y-coordinate in the legacy coordinate frame (tenths of feet from the baseline; null for non-shots). |
| `shot_distance` | Int64 | Shot distance in feet (0 for non-shots). |
| `shot_result` | String | "Made" / "Missed" for shot actions; empty otherwise. |
| `is_field_goal` | Int64 | 1 when the action is a field-goal attempt, else 0. |
| `score_home` | String | Home score after the action (string; carried forward between scores). |
| `score_away` | String | Away score after the action (string; carried forward between scores). |
| `points_total` | Int64 | Points the acting team has scored through this action. |
| `location` | String | Which side the acting team is on: "h" (home) or "v" (visitor). |
| `description` | String | Human-readable action narrative from the feed. |
| `action_type` | String | Action family ("Made Shot", "Rebound", "Turnover", "Foul", ...). |
| `sub_type` | String | Action detail within the family ("Jump Shot", "Offensive", ...). |
| `video_available` | Int64 | 1 when the feed links video for the action/game row. |
| `shot_value` | Int64 | Point value of a shot attempt (2 or 3; 1 for free throws, 0 for non-shots). |
| `action_id` | Int64 | Feed-internal id of the action row. |
| `game_id` | String | stats.wnba.com game id, 10-char string carrying the "10" WNBA league prefix ("1022400001"); pinned Utf8 so it never round-trips through int. |
| `season` | Int64 | Season the row belongs to, as a BARE calendar year ("2023") — the WNBA season fits one calendar year, unlike the NBA span form. |

## Coverage

| season | games built | games known |
|---:|---:|---:|
| 1997 | 115 | 115 |
| 1998 | 158 | 158 |
| 1999 | 203 | 203 |
| 2000 | 272 | 272 |
| 2001 | 274 | 274 |
| 2002 | 273 | 273 |
| 2003 | 257 | 257 |
| 2004 | 240 | 240 |
| 2005 | 238 | 238 |
| 2006 | 257 | 257 |
| 2007 | 241 | 241 |
| 2008 | 259 | 259 |
| 2009 | 241 | 241 |
| 2010 | 220 | 220 |
| 2011 | 223 | 223 |
| 2012 | 223 | 223 |
| 2013 | 221 | 221 |
| 2014 | 222 | 222 |
| 2015 | 225 | 225 |
| 2016 | 220 | 220 |
| 2017 | 219 | 219 |
| 2018 | 221 | 221 |
| 2019 | 220 | 220 |
| 2020 | 147 | 147 |
| 2021 | 209 | 209 |
| 2022 | 239 | 239 |
| 2023 | 260 | 260 |
| 2024 | 262 | 262 |
| 2025 | 310 | 310 |
| 2026 | 202 | 202 |
