# `player_boxscores`

WNBA Stats Player Boxscores from wehoop data repository — `boxscoretraditionalv3` (game-level).

| | |
|---|---|
| **Builder** | [`python/wnba_stats_13_player_boxscores_creation.py`](../../python/wnba_stats_13_player_boxscores_creation.py) |
| **Release tag** | [`wnba_stats_player_boxscores`](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/wnba_stats_player_boxscores) |
| **File stem** | `player_boxscores_{season}.{parquet,csv,rds}` |
| **Seasons built** | 1997–2026 (30 seasons) |
| **Last published** | 2026-07-29 (newest release asset) |
| **Tag created** | 2023-04-03 |
| **Release assets** | 3 |

## Automation

`.github/workflows/daily_wnba_stats.yml` — nightly scrape + build + publish (draft additionally refreshes annually via `annual_wnba_stats_draft.yml`). Runs `scripts/daily_wnba_stats_python_processor.sh`; the stage-99 schedule master is restamped at the end of every run.

## Columns

| col_name | type | description |
|---|---|---|
| `team_id` | Int64 | stats.wnba.com team id (Int64, e.g. 1611661313 = New York Liberty). |
| `team_name` | String | Team nickname or full name as the source endpoint ships it. |
| `team_tricode` | String | Three-letter team code as the v3 endpoints name it ("NYL"). |
| `side` | String |  |
| `person_id` | Int64 | stats.wnba.com person id of the player (or official) the row describes; the same id space as player_id. |
| `first_name` | String |  |
| `family_name` | String |  |
| `name_i` | String |  |
| `player_slug` | String |  |
| `position` | String |  |
| `comment` | String |  |
| `jersey_num` | String |  |
| `minutes` | String |  |
| `field_goals_made` | Int64 |  |
| `field_goals_attempted` | Int64 |  |
| `field_goals_percentage` | Float64 |  |
| `three_pointers_made` | Int64 |  |
| `three_pointers_attempted` | Int64 |  |
| `three_pointers_percentage` | Float64 |  |
| `free_throws_made` | Int64 |  |
| `free_throws_attempted` | Int64 |  |
| `free_throws_percentage` | Float64 |  |
| `rebounds_offensive` | Int64 |  |
| `rebounds_defensive` | Int64 |  |
| `rebounds_total` | Int64 |  |
| `assists` | Int64 |  |
| `steals` | Int64 |  |
| `blocks` | Int64 |  |
| `turnovers` | Int64 |  |
| `fouls_personal` | Int64 |  |
| `points` | Int64 |  |
| `plus_minus_points` | Float64 |  |
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
