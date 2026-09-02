# `game_rosters`

WNBA Stats Game Rosters from wehoop data repository — `boxscoresummaryv2` (game-level).

| | |
|---|---|
| **Builder** | [`python/wnba_stats_11_game_rosters_creation.py`](../../python/wnba_stats_11_game_rosters_creation.py) |
| **Release tag** | [`wnba_stats_game_rosters`](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/wnba_stats_game_rosters) |
| **File stem** | `game_rosters_{season}.{parquet,csv,rds}` |
| **Seasons built** | 1997–2026 (30 seasons) |
| **Last published** | 2026-09-02 (newest release asset) |
| **Tag created** | 2026-05-11 |
| **Release assets** | 95 |

## Automation

`.github/workflows/daily_wnba_stats.yml` — nightly scrape + build + publish (draft additionally refreshes annually via `annual_wnba_stats_draft.yml`). Runs `scripts/daily_wnba_stats_python_processor.sh`; the stage-99 schedule master is restamped at the end of every run.

## Columns

| col_name | type | description |
|---|---|---|
| `player_id` | Int64 | stats.wnba.com person id of the player (Int64); joins rosters, boxscores, game logs and pbp (`person_id`). |
| `first_name` | String |  |
| `last_name` | String |  |
| `jersey_num` | String |  |
| `team_id` | Int64 | stats.wnba.com team id (Int64, e.g. 1611661313 = New York Liberty). |
| `team_city` | String | Team city name. |
| `team_name` | String | Team nickname or full name as the source endpoint ships it. |
| `team_abbreviation` | String | Three-letter team code ("NYL"). |
| `season` | Int64 | Season the row belongs to, as a BARE calendar year ("2023") — the WNBA season fits one calendar year, unlike the NBA span form. |
| `game_id` | String | stats.wnba.com game id, 10-char string carrying the "10" WNBA league prefix ("1022400001"); pinned Utf8 so it never round-trips through int. |

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
| 2026 | 267 | 300 |
