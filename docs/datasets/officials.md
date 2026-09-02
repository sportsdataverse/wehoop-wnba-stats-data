# `officials`

WNBA Stats Officials from wehoop data repository — `boxscoresummaryv2` (game-level).

| | |
|---|---|
| **Builder** | [`python/wnba_stats_12_officials_creation.py`](../../python/wnba_stats_12_officials_creation.py) |
| **Release tag** | [`wnba_stats_officials`](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/wnba_stats_officials) |
| **File stem** | `officials_{season}.{parquet,csv,rds}` |
| **Seasons built** | 2004–2026 (23 seasons) |
| **Last published** | 2026-09-02 (newest release asset) |
| **Tag created** | 2026-05-11 |
| **Release assets** | 74 |

## Automation

`.github/workflows/daily_wnba_stats.yml` — nightly scrape + build + publish (draft additionally refreshes annually via `annual_wnba_stats_draft.yml`). Runs `scripts/daily_wnba_stats_python_processor.sh`; the stage-99 schedule master is restamped at the end of every run.

## Caveats

**Officials coverage begins in 2004.** stats.wnba.com publishes no officiating crew for 1997, 2000 or 2003 at all, and only a handful of stray games for 1998 (2 of 158), 1999 (1 of 203), 2001 (2 of 274) and 2002 (1 of 273) — those build into a well-formed 3-6 row frame that looks like a season and is not one, so they are deliberately not published. From 2004 coverage is complete: every game carries its three officials (240 of 240 games in 2004). The floor is enforced by `first_season` on the dataset registry entry, so a build for an earlier season is refused rather than silently shipped.

## Columns

| col_name | type | description |
|---|---|---|
| `official_id` | Int64 | stats.wnba.com person id of the game official. |
| `first_name` | String |  |
| `last_name` | String |  |
| `jersey_num` | String |  |
| `season` | Int64 | Season the row belongs to, as a BARE calendar year ("2023") — the WNBA season fits one calendar year, unlike the NBA span form. |
| `game_id` | String | stats.wnba.com game id, 10-char string carrying the "10" WNBA league prefix ("1022400001"); pinned Utf8 so it never round-trips through int. |

## Coverage

| season | games built | games known |
|---:|---:|---:|
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
| 2026 | 300 | 300 |

_Seasons before 2004 are not built or published; see Caveats._
