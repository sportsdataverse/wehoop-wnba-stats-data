# Program V D26d cutover -- REPLACE MANIFEST

- generated: `2026-08-12T02:48:38Z`
- mode: **DRY RUN (nothing uploaded)**
- gate (section 10.3): **FAIL -- PUBLISH BLOCKED**
- release repo: `sportsdataverse/sportsdataverse-data`
- seasons: 1997-2026 (30) calendar-year

## Target map

| family | tag | asset | shadowed legacy asset | collision |
|---|---|---|---|---|
| `schedule` | `wnba_stats_schedules` | `wnba_schedule_{season}.parquet` | `wnba_stats_schedule_{season+0}.parquet` | no |
| `play_by_play` | `wnba_stats_pbp` | `wnba_play_by_play_{season}.parquet` | `play_by_play_{season+0}.parquet` | no |
| `possessions` | `wnba_stats_possessions` | `wnba_possessions_{season}.parquet` | `-` | no |
| `lineups` | `wnba_stats_lineups` | `wnba_lineups_{season}.parquet` | `lineups_{season+0}.parquet` | **YES** |

> **COLLISION -- `lineups` -> `wnba_stats_lineups`**: wnba_stats_lineups already carries the season-level leaguedashlineups dataset (lineups_{season}.csv/.parquet/.rds from stage 04) -- a different dataset from the v3 per-game lineups. Resolve with --tag lineups=<tag>.

## Summary per tag

| tag | NEW | REPLACE | UNCHANGED | upload bytes |
|---|---:|---:|---:|---:|
| `wnba_stats_lineups` | 30 | 0 | 0 | 1.67 MB |
| `wnba_stats_pbp` | 30 | 0 | 0 | 48.67 MB |
| `wnba_stats_possessions` | 30 | 0 | 0 | 10.64 MB |
| `wnba_stats_schedules` | 30 | 0 | 0 | 0.26 MB |
| **total** | 120 | 0 | 0 | 61.24 MB |

## WOULD BE DESTROYED (existing remote assets overwritten)

_none -- every planned asset name is new on its tag._

## SURVIVES UN-REPLACED (still served to load_wnba_*() after this cutover)

30 remote asset(s) on the target tags are not touched by this plan.

| tag | asset | bytes | updated |
|---|---|---:|---|
| `wnba_stats_lineups` | `lineups_2026.csv` | 13.47 MB | 2026-07-29T07:25:58Z |
| `wnba_stats_lineups` | `lineups_2026.parquet` | 0.74 MB | 2026-07-29T07:26:01Z |
| `wnba_stats_lineups` | `lineups_2026.rds` | 1.17 MB | 2026-07-29T07:26:06Z |
| `wnba_stats_lineups` | `package_function.json` | 0.00 MB | 2026-07-12T09:36:10Z |
| `wnba_stats_lineups` | `package_function.txt` | 0.00 MB | 2026-07-12T09:36:10Z |
| `wnba_stats_lineups` | `timestamp.json` | 0.00 MB | 2026-07-12T09:36:10Z |
| `wnba_stats_lineups` | `timestamp.txt` | 0.00 MB | 2026-07-12T09:36:10Z |
| `wnba_stats_lineups` | `wnba_stats_lineups_in_data_repo.csv` | 0.00 MB | 2026-07-12T09:36:10Z |
| `wnba_stats_pbp` | `package_function.json` | 0.00 MB | 2026-07-16T15:12:00Z |
| `wnba_stats_pbp` | `package_function.txt` | 0.00 MB | 2026-07-16T15:12:00Z |
| `wnba_stats_pbp` | `play_by_play_2026.csv` | 13.60 MB | 2026-07-29T07:26:33Z |
| `wnba_stats_pbp` | `play_by_play_2026.parquet` | 1.49 MB | 2026-07-29T07:26:37Z |
| `wnba_stats_pbp` | `play_by_play_2026.rds` | 1.69 MB | 2026-07-29T07:26:42Z |
| `wnba_stats_pbp` | `timestamp.json` | 0.00 MB | 2026-07-16T15:12:00Z |
| `wnba_stats_pbp` | `timestamp.txt` | 0.00 MB | 2026-07-16T15:12:00Z |
| `wnba_stats_pbp` | `wnba_stats_pbp_in_data_repo.csv` | 0.00 MB | 2026-07-16T15:12:00Z |
| `wnba_stats_schedules` | `package_function.json` | 0.00 MB | 2026-07-28T10:04:41Z |
| `wnba_stats_schedules` | `package_function.txt` | 0.00 MB | 2026-07-28T10:04:41Z |
| `wnba_stats_schedules` | `timestamp.json` | 0.00 MB | 2026-07-28T10:04:40Z |
| `wnba_stats_schedules` | `timestamp.txt` | 0.00 MB | 2026-07-28T10:04:40Z |
| `wnba_stats_schedules` | `wnba_stats_schedule_2025.csv` | 0.09 MB | 2026-05-12T06:44:07Z |
| `wnba_stats_schedules` | `wnba_stats_schedule_2025.parquet` | 0.03 MB | 2026-05-12T06:44:07Z |
| `wnba_stats_schedules` | `wnba_stats_schedule_2025.rds` | 0.02 MB | 2026-05-12T06:44:07Z |
| `wnba_stats_schedules` | `wnba_stats_schedule_2026.csv` | 0.75 MB | 2026-07-29T07:27:11Z |
| `wnba_stats_schedules` | `wnba_stats_schedule_2026.parquet` | 0.10 MB | 2026-07-29T07:27:12Z |
| `wnba_stats_schedules` | `wnba_stats_schedule_2026.rds` | 0.11 MB | 2026-07-29T07:27:14Z |
| `wnba_stats_schedules` | `wnba_stats_schedule_master.csv` | 0.05 MB | 2026-07-16T15:11:54Z |
| `wnba_stats_schedules` | `wnba_stats_schedule_master.parquet` | 0.03 MB | 2026-07-16T15:11:54Z |
| `wnba_stats_schedules` | `wnba_stats_schedule_master.rds` | 0.01 MB | 2026-07-16T15:11:54Z |
| `wnba_stats_schedules` | `wnba_stats_schedules_in_data_repo.csv` | 0.00 MB | 2026-07-16T15:11:57Z |

## Gate (section 10.3)

**FAIL -- publish is blocked.** 6 unexplained finding(s). Explain each, then re-run with one `--allow-diff SEASON:FAMILY` per explained case. There is no blanket override.

| season:family | verdict | detail |
|---|---|---|
| `1997:play_by_play` | DIFF | staged_games=115 raw_captured=115 uncompiled=0 phantom=0 min_events=295 scores_vs_sched=115 score_mismatch=5 |
| `1998:play_by_play` | DIFF | staged_games=157 raw_captured=158 uncompiled=1 phantom=0 min_events=335 scores_vs_sched=157 score_mismatch=2 uncompiled_sample=['1029800096'] |
| `1999:play_by_play` | DIFF | staged_games=203 raw_captured=203 uncompiled=0 phantom=0 min_events=40 scores_vs_sched=203 score_mismatch=1 |
| `2000:play_by_play` | DIFF | staged_games=272 raw_captured=272 uncompiled=0 phantom=0 min_events=44 scores_vs_sched=272 score_mismatch=2 |
| `2006:play_by_play` | DIFF | staged_games=256 raw_captured=257 uncompiled=1 phantom=0 min_events=333 scores_vs_sched=256 score_mismatch=1 uncompiled_sample=['1020600130'] |
| `2018:play_by_play` | DIFF | staged_games=220 raw_captured=221 uncompiled=1 phantom=0 min_events=334 scores_vs_sched=220 score_mismatch=0 uncompiled_sample=['1021800162'] |

### Allowlisted (explained) diffs

_none -- no `--allow-diff` was passed._

## Full plan

| season | family | tag | asset | local bytes | rows | remote bytes | remote updated | verdict |
|---:|---|---|---|---:|---:|---:|---|---|
| 1997 | schedule | `wnba_stats_schedules` | `wnba_schedule_1997.parquet` | 0.01 MB | 115 | - | - | NEW |
| 1997 | play_by_play | `wnba_stats_pbp` | `wnba_play_by_play_1997.parquet` | 0.77 MB | 47,583 | - | - | NEW |
| 1997 | possessions | `wnba_stats_possessions` | `wnba_possessions_1997.parquet` | 0.16 MB | 17,451 | - | - | NEW |
| 1997 | lineups | `wnba_stats_lineups` | `wnba_lineups_1997.parquet` | 0.01 MB | 11,556 | - | - | NEW |
| 1998 | schedule | `wnba_stats_schedules` | `wnba_schedule_1998.parquet` | 0.01 MB | 158 | - | - | NEW |
| 1998 | play_by_play | `wnba_stats_pbp` | `wnba_play_by_play_1998.parquet` | 1.04 MB | 63,658 | - | - | NEW |
| 1998 | possessions | `wnba_stats_possessions` | `wnba_possessions_1998.parquet` | 0.21 MB | 23,533 | - | - | NEW |
| 1998 | lineups | `wnba_stats_lineups` | `wnba_lineups_1998.parquet` | 0.01 MB | 10,948 | - | - | NEW |
| 1999 | schedule | `wnba_stats_schedules` | `wnba_schedule_1999.parquet` | 0.01 MB | 203 | - | - | NEW |
| 1999 | play_by_play | `wnba_stats_pbp` | `wnba_play_by_play_1999.parquet` | 1.30 MB | 79,679 | - | - | NEW |
| 1999 | possessions | `wnba_stats_possessions` | `wnba_possessions_1999.parquet` | 0.25 MB | 29,027 | - | - | NEW |
| 1999 | lineups | `wnba_stats_lineups` | `wnba_lineups_1999.parquet` | 0.02 MB | 16,909 | - | - | NEW |
| 2000 | schedule | `wnba_stats_schedules` | `wnba_schedule_2000.parquet` | 0.01 MB | 272 | - | - | NEW |
| 2000 | play_by_play | `wnba_stats_pbp` | `wnba_play_by_play_2000.parquet` | 1.73 MB | 105,417 | - | - | NEW |
| 2000 | possessions | `wnba_stats_possessions` | `wnba_possessions_2000.parquet` | 0.32 MB | 38,139 | - | - | NEW |
| 2000 | lineups | `wnba_stats_lineups` | `wnba_lineups_2000.parquet` | 0.03 MB | 34,265 | - | - | NEW |
| 2001 | schedule | `wnba_stats_schedules` | `wnba_schedule_2001.parquet` | 0.01 MB | 274 | - | - | NEW |
| 2001 | play_by_play | `wnba_stats_pbp` | `wnba_play_by_play_2001.parquet` | 1.74 MB | 105,957 | - | - | NEW |
| 2001 | possessions | `wnba_stats_possessions` | `wnba_possessions_2001.parquet` | 0.32 MB | 38,039 | - | - | NEW |
| 2001 | lineups | `wnba_stats_lineups` | `wnba_lineups_2001.parquet` | 0.02 MB | 22,667 | - | - | NEW |
| 2002 | schedule | `wnba_stats_schedules` | `wnba_schedule_2002.parquet` | 0.01 MB | 273 | - | - | NEW |
| 2002 | play_by_play | `wnba_stats_pbp` | `wnba_play_by_play_2002.parquet` | 1.73 MB | 105,276 | - | - | NEW |
| 2002 | possessions | `wnba_stats_possessions` | `wnba_possessions_2002.parquet` | 0.33 MB | 38,256 | - | - | NEW |
| 2002 | lineups | `wnba_stats_lineups` | `wnba_lineups_2002.parquet` | 0.02 MB | 21,300 | - | - | NEW |
| 2003 | schedule | `wnba_stats_schedules` | `wnba_schedule_2003.parquet` | 0.01 MB | 257 | - | - | NEW |
| 2003 | play_by_play | `wnba_stats_pbp` | `wnba_play_by_play_2003.parquet` | 1.62 MB | 99,349 | - | - | NEW |
| 2003 | possessions | `wnba_stats_possessions` | `wnba_possessions_2003.parquet` | 0.31 MB | 36,082 | - | - | NEW |
| 2003 | lineups | `wnba_stats_lineups` | `wnba_lineups_2003.parquet` | 0.02 MB | 17,955 | - | - | NEW |
| 2004 | schedule | `wnba_stats_schedules` | `wnba_schedule_2004.parquet` | 0.01 MB | 240 | - | - | NEW |
| 2004 | play_by_play | `wnba_stats_pbp` | `wnba_play_by_play_2004.parquet` | 1.51 MB | 92,441 | - | - | NEW |
| 2004 | possessions | `wnba_stats_possessions` | `wnba_possessions_2004.parquet` | 0.31 MB | 33,451 | - | - | NEW |
| 2004 | lineups | `wnba_stats_lineups` | `wnba_lineups_2004.parquet` | 0.03 MB | 12,375 | - | - | NEW |
| 2005 | schedule | `wnba_stats_schedules` | `wnba_schedule_2005.parquet` | 0.01 MB | 238 | - | - | NEW |
| 2005 | play_by_play | `wnba_stats_pbp` | `wnba_play_by_play_2005.parquet` | 1.49 MB | 91,502 | - | - | NEW |
| 2005 | possessions | `wnba_stats_possessions` | `wnba_possessions_2005.parquet` | 0.31 MB | 33,290 | - | - | NEW |
| 2005 | lineups | `wnba_stats_lineups` | `wnba_lineups_2005.parquet` | 0.03 MB | 15,656 | - | - | NEW |
| 2006 | schedule | `wnba_stats_schedules` | `wnba_schedule_2006.parquet` | 0.01 MB | 257 | - | - | NEW |
| 2006 | play_by_play | `wnba_stats_pbp` | `wnba_play_by_play_2006.parquet` | 1.74 MB | 104,864 | - | - | NEW |
| 2006 | possessions | `wnba_stats_possessions` | `wnba_possessions_2006.parquet` | 0.36 MB | 39,384 | - | - | NEW |
| 2006 | lineups | `wnba_stats_lineups` | `wnba_lineups_2006.parquet` | 0.03 MB | 16,832 | - | - | NEW |
| 2007 | schedule | `wnba_stats_schedules` | `wnba_schedule_2007.parquet` | 0.01 MB | 241 | - | - | NEW |
| 2007 | play_by_play | `wnba_stats_pbp` | `wnba_play_by_play_2007.parquet` | 1.67 MB | 101,161 | - | - | NEW |
| 2007 | possessions | `wnba_stats_possessions` | `wnba_possessions_2007.parquet` | 0.35 MB | 38,191 | - | - | NEW |
| 2007 | lineups | `wnba_stats_lineups` | `wnba_lineups_2007.parquet` | 0.02 MB | 12,039 | - | - | NEW |
| 2008 | schedule | `wnba_stats_schedules` | `wnba_schedule_2008.parquet` | 0.01 MB | 259 | - | - | NEW |
| 2008 | play_by_play | `wnba_stats_pbp` | `wnba_play_by_play_2008.parquet` | 1.82 MB | 109,761 | - | - | NEW |
| 2008 | possessions | `wnba_stats_possessions` | `wnba_possessions_2008.parquet` | 0.38 MB | 40,514 | - | - | NEW |
| 2008 | lineups | `wnba_stats_lineups` | `wnba_lineups_2008.parquet` | 0.03 MB | 16,643 | - | - | NEW |
| 2009 | schedule | `wnba_stats_schedules` | `wnba_schedule_2009.parquet` | 0.01 MB | 241 | - | - | NEW |
| 2009 | play_by_play | `wnba_stats_pbp` | `wnba_play_by_play_2009.parquet` | 1.71 MB | 101,779 | - | - | NEW |
| 2009 | possessions | `wnba_stats_possessions` | `wnba_possessions_2009.parquet` | 0.35 MB | 38,097 | - | - | NEW |
| 2009 | lineups | `wnba_stats_lineups` | `wnba_lineups_2009.parquet` | 0.03 MB | 14,521 | - | - | NEW |
| 2010 | schedule | `wnba_stats_schedules` | `wnba_schedule_2010.parquet` | 0.01 MB | 220 | - | - | NEW |
| 2010 | play_by_play | `wnba_stats_pbp` | `wnba_play_by_play_2010.parquet` | 1.56 MB | 91,581 | - | - | NEW |
| 2010 | possessions | `wnba_stats_possessions` | `wnba_possessions_2010.parquet` | 0.32 MB | 34,797 | - | - | NEW |
| 2010 | lineups | `wnba_stats_lineups` | `wnba_lineups_2010.parquet` | 0.02 MB | 11,444 | - | - | NEW |
| 2011 | schedule | `wnba_stats_schedules` | `wnba_schedule_2011.parquet` | 0.01 MB | 223 | - | - | NEW |
| 2011 | play_by_play | `wnba_stats_pbp` | `wnba_play_by_play_2011.parquet` | 1.57 MB | 90,663 | - | - | NEW |
| 2011 | possessions | `wnba_stats_possessions` | `wnba_possessions_2011.parquet` | 0.31 MB | 34,652 | - | - | NEW |
| 2011 | lineups | `wnba_stats_lineups` | `wnba_lineups_2011.parquet` | 0.02 MB | 8,314 | - | - | NEW |
| 2012 | schedule | `wnba_stats_schedules` | `wnba_schedule_2012.parquet` | 0.01 MB | 223 | - | - | NEW |
| 2012 | play_by_play | `wnba_stats_pbp` | `wnba_play_by_play_2012.parquet` | 1.59 MB | 91,399 | - | - | NEW |
| 2012 | possessions | `wnba_stats_possessions` | `wnba_possessions_2012.parquet` | 0.30 MB | 34,637 | - | - | NEW |
| 2012 | lineups | `wnba_stats_lineups` | `wnba_lineups_2012.parquet` | 0.01 MB | 4,565 | - | - | NEW |
| 2013 | schedule | `wnba_stats_schedules` | `wnba_schedule_2013.parquet` | 0.01 MB | 221 | - | - | NEW |
| 2013 | play_by_play | `wnba_stats_pbp` | `wnba_play_by_play_2013.parquet` | 1.58 MB | 89,896 | - | - | NEW |
| 2013 | possessions | `wnba_stats_possessions` | `wnba_possessions_2013.parquet` | 0.31 MB | 34,012 | - | - | NEW |
| 2013 | lineups | `wnba_stats_lineups` | `wnba_lineups_2013.parquet` | 0.02 MB | 10,521 | - | - | NEW |
| 2014 | schedule | `wnba_stats_schedules` | `wnba_schedule_2014.parquet` | 0.01 MB | 222 | - | - | NEW |
| 2014 | play_by_play | `wnba_stats_pbp` | `wnba_play_by_play_2014.parquet` | 1.60 MB | 90,134 | - | - | NEW |
| 2014 | possessions | `wnba_stats_possessions` | `wnba_possessions_2014.parquet` | 0.31 MB | 34,312 | - | - | NEW |
| 2014 | lineups | `wnba_stats_lineups` | `wnba_lineups_2014.parquet` | 0.02 MB | 9,372 | - | - | NEW |
| 2015 | schedule | `wnba_stats_schedules` | `wnba_schedule_2015.parquet` | 0.01 MB | 225 | - | - | NEW |
| 2015 | play_by_play | `wnba_stats_pbp` | `wnba_play_by_play_2015.parquet` | 1.63 MB | 90,972 | - | - | NEW |
| 2015 | possessions | `wnba_stats_possessions` | `wnba_possessions_2015.parquet` | 0.32 MB | 34,133 | - | - | NEW |
| 2015 | lineups | `wnba_stats_lineups` | `wnba_lineups_2015.parquet` | 0.03 MB | 12,724 | - | - | NEW |
| 2016 | schedule | `wnba_stats_schedules` | `wnba_schedule_2016.parquet` | 0.01 MB | 220 | - | - | NEW |
| 2016 | play_by_play | `wnba_stats_pbp` | `wnba_play_by_play_2016.parquet` | 1.68 MB | 91,724 | - | - | NEW |
| 2016 | possessions | `wnba_stats_possessions` | `wnba_possessions_2016.parquet` | 0.42 MB | 34,737 | - | - | NEW |
| 2016 | lineups | `wnba_stats_lineups` | `wnba_lineups_2016.parquet` | 0.08 MB | 62,095 | - | - | NEW |
| 2017 | schedule | `wnba_stats_schedules` | `wnba_schedule_2017.parquet` | 0.01 MB | 219 | - | - | NEW |
| 2017 | play_by_play | `wnba_stats_pbp` | `wnba_play_by_play_2017.parquet` | 1.67 MB | 90,543 | - | - | NEW |
| 2017 | possessions | `wnba_stats_possessions` | `wnba_possessions_2017.parquet` | 0.41 MB | 34,392 | - | - | NEW |
| 2017 | lineups | `wnba_stats_lineups` | `wnba_lineups_2017.parquet` | 0.08 MB | 64,280 | - | - | NEW |
| 2018 | schedule | `wnba_stats_schedules` | `wnba_schedule_2018.parquet` | 0.01 MB | 221 | - | - | NEW |
| 2018 | play_by_play | `wnba_stats_pbp` | `wnba_play_by_play_2018.parquet` | 1.68 MB | 89,269 | - | - | NEW |
| 2018 | possessions | `wnba_stats_possessions` | `wnba_possessions_2018.parquet` | 0.42 MB | 34,637 | - | - | NEW |
| 2018 | lineups | `wnba_stats_lineups` | `wnba_lineups_2018.parquet` | 0.10 MB | 70,040 | - | - | NEW |
| 2019 | schedule | `wnba_stats_schedules` | `wnba_schedule_2019.parquet` | 0.01 MB | 220 | - | - | NEW |
| 2019 | play_by_play | `wnba_stats_pbp` | `wnba_play_by_play_2019.parquet` | 1.66 MB | 89,334 | - | - | NEW |
| 2019 | possessions | `wnba_stats_possessions` | `wnba_possessions_2019.parquet` | 0.43 MB | 34,517 | - | - | NEW |
| 2019 | lineups | `wnba_stats_lineups` | `wnba_lineups_2019.parquet` | 0.12 MB | 83,172 | - | - | NEW |
| 2020 | schedule | `wnba_stats_schedules` | `wnba_schedule_2020.parquet` | 0.01 MB | 147 | - | - | NEW |
| 2020 | play_by_play | `wnba_stats_pbp` | `wnba_play_by_play_2020.parquet` | 1.13 MB | 59,512 | - | - | NEW |
| 2020 | possessions | `wnba_stats_possessions` | `wnba_possessions_2020.parquet` | 0.30 MB | 23,501 | - | - | NEW |
| 2020 | lineups | `wnba_stats_lineups` | `wnba_lineups_2020.parquet` | 0.08 MB | 52,298 | - | - | NEW |
| 2021 | schedule | `wnba_stats_schedules` | `wnba_schedule_2021.parquet` | 0.01 MB | 209 | - | - | NEW |
| 2021 | play_by_play | `wnba_stats_pbp` | `wnba_play_by_play_2021.parquet` | 1.58 MB | 83,986 | - | - | NEW |
| 2021 | possessions | `wnba_stats_possessions` | `wnba_possessions_2021.parquet` | 0.42 MB | 33,099 | - | - | NEW |
| 2021 | lineups | `wnba_stats_lineups` | `wnba_lineups_2021.parquet` | 0.11 MB | 75,795 | - | - | NEW |
| 2022 | schedule | `wnba_stats_schedules` | `wnba_schedule_2022.parquet` | 0.01 MB | 239 | - | - | NEW |
| 2022 | play_by_play | `wnba_stats_pbp` | `wnba_play_by_play_2022.parquet` | 1.83 MB | 97,050 | - | - | NEW |
| 2022 | possessions | `wnba_stats_possessions` | `wnba_possessions_2022.parquet` | 0.47 MB | 38,007 | - | - | NEW |
| 2022 | lineups | `wnba_stats_lineups` | `wnba_lineups_2022.parquet` | 0.12 MB | 83,240 | - | - | NEW |
| 2023 | schedule | `wnba_stats_schedules` | `wnba_schedule_2023.parquet` | 0.01 MB | 260 | - | - | NEW |
| 2023 | play_by_play | `wnba_stats_pbp` | `wnba_play_by_play_2023.parquet` | 1.97 MB | 106,038 | - | - | NEW |
| 2023 | possessions | `wnba_stats_possessions` | `wnba_possessions_2023.parquet` | 0.51 MB | 41,350 | - | - | NEW |
| 2023 | lineups | `wnba_stats_lineups` | `wnba_lineups_2023.parquet` | 0.13 MB | 93,827 | - | - | NEW |
| 2024 | schedule | `wnba_stats_schedules` | `wnba_schedule_2024.parquet` | 0.01 MB | 262 | - | - | NEW |
| 2024 | play_by_play | `wnba_stats_pbp` | `wnba_play_by_play_2024.parquet` | 1.99 MB | 105,797 | - | - | NEW |
| 2024 | possessions | `wnba_stats_possessions` | `wnba_possessions_2024.parquet` | 0.49 MB | 41,429 | - | - | NEW |
| 2024 | lineups | `wnba_stats_lineups` | `wnba_lineups_2024.parquet` | 0.12 MB | 88,832 | - | - | NEW |
| 2025 | schedule | `wnba_stats_schedules` | `wnba_schedule_2025.parquet` | 0.01 MB | 310 | - | - | NEW |
| 2025 | play_by_play | `wnba_stats_pbp` | `wnba_play_by_play_2025.parquet` | 2.39 MB | 126,330 | - | - | NEW |
| 2025 | possessions | `wnba_stats_possessions` | `wnba_possessions_2025.parquet` | 0.58 MB | 48,401 | - | - | NEW |
| 2025 | lineups | `wnba_stats_lineups` | `wnba_lineups_2025.parquet` | 0.14 MB | 99,114 | - | - | NEW |
| 2026 | schedule | `wnba_stats_schedules` | `wnba_schedule_2026.parquet` | 0.01 MB | 202 | - | - | NEW |
| 2026 | play_by_play | `wnba_stats_pbp` | `wnba_play_by_play_2026.parquet` | 1.70 MB | 86,784 | - | - | NEW |
| 2026 | possessions | `wnba_stats_possessions` | `wnba_possessions_2026.parquet` | 0.38 MB | 32,265 | - | - | NEW |
| 2026 | lineups | `wnba_stats_lineups` | `wnba_lineups_2026.parquet` | 0.13 MB | 83,720 | - | - | NEW |
