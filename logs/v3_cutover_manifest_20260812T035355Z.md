# Program V D26d cutover -- REPLACE MANIFEST

- generated: `2026-08-12T03:53:55Z`
- mode: **DRY RUN (nothing uploaded)**
- gate (section 10.3): **PASS**
- release repo: `sportsdataverse/sportsdataverse-data`
- seasons: 1997-2026 (30) calendar-year

## Target map

| family | tag | asset | shadowed legacy asset | collision |
|---|---|---|---|---|
| `schedule` | `wnba_stats_schedules` | `wnba_schedule_{season}.parquet` | `wnba_stats_schedule_{season+0}.parquet` | no |
| `play_by_play` | `wnba_stats_pbp` | `wnba_play_by_play_{season}.parquet` | `play_by_play_{season+0}.parquet` | no |
| `possessions` | `wnba_stats_possessions` | `wnba_possessions_{season}.parquet` | `-` | no |
| `lineups` | `wnba_stats_game_lineups` | `wnba_lineups_{season}.parquet` | `-` | no |

## Summary per tag

| tag | NEW | REPLACE | UNCHANGED | upload bytes |
|---|---:|---:|---:|---:|
| `wnba_stats_game_lineups` | 90 | 0 | 0 | 6.50 MB |
| `wnba_stats_pbp` | 90 | 0 | 0 | 181.79 MB |
| `wnba_stats_possessions` | 90 | 0 | 0 | 39.03 MB |
| `wnba_stats_schedules` | 90 | 0 | 0 | 0.52 MB |
| **total** | 360 | 0 | 0 | 227.84 MB |

## Summary per format

| format | assets | bytes |
|---|---:|---:|
| `.csv.gz` | 120 | 96.86 MB |
| `.parquet` | 120 | 61.24 MB |
| `.rds` | 120 | 69.74 MB |
| **all formats** | 360 | 227.84 MB |

## WOULD BE DESTROYED (existing remote assets overwritten)

_none -- every planned asset name is new on its tag._

## SEASON-LABEL COLLISION (two names, one real season)

This publish is **additive** (decision B): the END-year assets land next to
the existing START-year ones. For every row below, both files describe the
**same real season** -- a consumer asking for one number gets different data
depending on which pattern it reads. The END-year name is authoritative; the
legacy name is scheduled for `--retire-legacy-assets`.

| tag | real season | NEW (END-year, authoritative) | LEGACY (START-year, to be retired) | legacy bytes |
|---|---|---|---|---:|
| `wnba_stats_schedules` | 2025 | `wnba_schedule_2025.*` | `wnba_stats_schedule_2025.csv`, `wnba_stats_schedule_2025.parquet`, `wnba_stats_schedule_2025.rds` | 0.14 MB |
| `wnba_stats_schedules` | 2026 | `wnba_schedule_2026.*` | `wnba_stats_schedule_2026.csv`, `wnba_stats_schedule_2026.parquet`, `wnba_stats_schedule_2026.rds` | 0.97 MB |
| `wnba_stats_pbp` | 2026 | `wnba_play_by_play_2026.*` | `play_by_play_2026.csv`, `play_by_play_2026.parquet`, `play_by_play_2026.rds` | 16.77 MB |

**3 overlapping season(s) across 2 tag(s): `wnba_stats_pbp`, `wnba_stats_schedules`** -- of which **0** carry a DIFFERENT season number for the same games (the real hazard); the rest are same-number duplicates. On `--execute` each of those tags receives a generated `README.md` naming both patterns and which one wins.


## SURVIVES UN-REPLACED (still served to load_wnba_*() after this cutover)

22 remote asset(s) on the target tags are not touched by this plan.

| tag | asset | bytes | updated |
|---|---|---:|---|
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

**PASS** -- no unexplained finding over the season range.

### Allowlisted (explained) diffs

| season:family | verdict | detail |
|---|---|---|
| `1997:play_by_play` | DIFF | staged_games=115 raw_captured=115 uncompiled=0 phantom=0 min_events=295 scores_vs_sched=115 score_mismatch=5 |
| `1998:play_by_play` | DIFF | staged_games=157 raw_captured=158 uncompiled=1 phantom=0 min_events=335 scores_vs_sched=157 score_mismatch=2 uncompiled_sample=['1029800096'] |
| `1999:play_by_play` | DIFF | staged_games=203 raw_captured=203 uncompiled=0 phantom=0 min_events=40 scores_vs_sched=203 score_mismatch=1 |
| `2000:play_by_play` | DIFF | staged_games=272 raw_captured=272 uncompiled=0 phantom=0 min_events=44 scores_vs_sched=272 score_mismatch=2 |
| `2006:play_by_play` | DIFF | staged_games=256 raw_captured=257 uncompiled=1 phantom=0 min_events=333 scores_vs_sched=256 score_mismatch=1 uncompiled_sample=['1020600130'] |
| `2018:play_by_play` | DIFF | staged_games=220 raw_captured=221 uncompiled=1 phantom=0 min_events=334 scores_vs_sched=220 score_mismatch=0 uncompiled_sample=['1021800162'] |

## Full plan

| season | family | format | tag | asset | local bytes | rows | remote bytes | remote updated | verdict |
|---:|---|---|---|---|---:|---:|---:|---|---|
| 1997 | schedule | `parquet` | `wnba_stats_schedules` | `wnba_schedule_1997.parquet` | 0.01 MB | 115 | - | - | NEW |
| 1997 | schedule | `rds` | `wnba_stats_schedules` | `wnba_schedule_1997.rds` | 0.00 MB | 115 | - | - | NEW |
| 1997 | schedule | `csv.gz` | `wnba_stats_schedules` | `wnba_schedule_1997.csv.gz` | 0.00 MB | 115 | - | - | NEW |
| 1997 | play_by_play | `parquet` | `wnba_stats_pbp` | `wnba_play_by_play_1997.parquet` | 0.77 MB | 47,583 | - | - | NEW |
| 1997 | play_by_play | `rds` | `wnba_stats_pbp` | `wnba_play_by_play_1997.rds` | 0.94 MB | 47,583 | - | - | NEW |
| 1997 | play_by_play | `csv.gz` | `wnba_stats_pbp` | `wnba_play_by_play_1997.csv.gz` | 1.22 MB | 47,583 | - | - | NEW |
| 1997 | possessions | `parquet` | `wnba_stats_possessions` | `wnba_possessions_1997.parquet` | 0.16 MB | 17,451 | - | - | NEW |
| 1997 | possessions | `rds` | `wnba_stats_possessions` | `wnba_possessions_1997.rds` | 0.15 MB | 17,451 | - | - | NEW |
| 1997 | possessions | `csv.gz` | `wnba_stats_possessions` | `wnba_possessions_1997.csv.gz` | 0.30 MB | 17,451 | - | - | NEW |
| 1997 | lineups | `parquet` | `wnba_stats_game_lineups` | `wnba_lineups_1997.parquet` | 0.01 MB | 11,556 | - | - | NEW |
| 1997 | lineups | `rds` | `wnba_stats_game_lineups` | `wnba_lineups_1997.rds` | 0.01 MB | 11,556 | - | - | NEW |
| 1997 | lineups | `csv.gz` | `wnba_stats_game_lineups` | `wnba_lineups_1997.csv.gz` | 0.03 MB | 11,556 | - | - | NEW |
| 1998 | schedule | `parquet` | `wnba_stats_schedules` | `wnba_schedule_1998.parquet` | 0.01 MB | 158 | - | - | NEW |
| 1998 | schedule | `rds` | `wnba_stats_schedules` | `wnba_schedule_1998.rds` | 0.00 MB | 158 | - | - | NEW |
| 1998 | schedule | `csv.gz` | `wnba_stats_schedules` | `wnba_schedule_1998.csv.gz` | 0.00 MB | 158 | - | - | NEW |
| 1998 | play_by_play | `parquet` | `wnba_stats_pbp` | `wnba_play_by_play_1998.parquet` | 1.04 MB | 63,658 | - | - | NEW |
| 1998 | play_by_play | `rds` | `wnba_stats_pbp` | `wnba_play_by_play_1998.rds` | 1.28 MB | 63,658 | - | - | NEW |
| 1998 | play_by_play | `csv.gz` | `wnba_stats_pbp` | `wnba_play_by_play_1998.csv.gz` | 1.66 MB | 63,658 | - | - | NEW |
| 1998 | possessions | `parquet` | `wnba_stats_possessions` | `wnba_possessions_1998.parquet` | 0.21 MB | 23,533 | - | - | NEW |
| 1998 | possessions | `rds` | `wnba_stats_possessions` | `wnba_possessions_1998.rds` | 0.20 MB | 23,533 | - | - | NEW |
| 1998 | possessions | `csv.gz` | `wnba_stats_possessions` | `wnba_possessions_1998.csv.gz` | 0.40 MB | 23,533 | - | - | NEW |
| 1998 | lineups | `parquet` | `wnba_stats_game_lineups` | `wnba_lineups_1998.parquet` | 0.01 MB | 10,948 | - | - | NEW |
| 1998 | lineups | `rds` | `wnba_stats_game_lineups` | `wnba_lineups_1998.rds` | 0.01 MB | 10,948 | - | - | NEW |
| 1998 | lineups | `csv.gz` | `wnba_stats_game_lineups` | `wnba_lineups_1998.csv.gz` | 0.03 MB | 10,948 | - | - | NEW |
| 1999 | schedule | `parquet` | `wnba_stats_schedules` | `wnba_schedule_1999.parquet` | 0.01 MB | 203 | - | - | NEW |
| 1999 | schedule | `rds` | `wnba_stats_schedules` | `wnba_schedule_1999.rds` | 0.00 MB | 203 | - | - | NEW |
| 1999 | schedule | `csv.gz` | `wnba_stats_schedules` | `wnba_schedule_1999.csv.gz` | 0.00 MB | 203 | - | - | NEW |
| 1999 | play_by_play | `parquet` | `wnba_stats_pbp` | `wnba_play_by_play_1999.parquet` | 1.30 MB | 79,679 | - | - | NEW |
| 1999 | play_by_play | `rds` | `wnba_stats_pbp` | `wnba_play_by_play_1999.rds` | 1.61 MB | 79,679 | - | - | NEW |
| 1999 | play_by_play | `csv.gz` | `wnba_stats_pbp` | `wnba_play_by_play_1999.csv.gz` | 2.08 MB | 79,679 | - | - | NEW |
| 1999 | possessions | `parquet` | `wnba_stats_possessions` | `wnba_possessions_1999.parquet` | 0.25 MB | 29,027 | - | - | NEW |
| 1999 | possessions | `rds` | `wnba_stats_possessions` | `wnba_possessions_1999.rds` | 0.25 MB | 29,027 | - | - | NEW |
| 1999 | possessions | `csv.gz` | `wnba_stats_possessions` | `wnba_possessions_1999.csv.gz` | 0.50 MB | 29,027 | - | - | NEW |
| 1999 | lineups | `parquet` | `wnba_stats_game_lineups` | `wnba_lineups_1999.parquet` | 0.02 MB | 16,909 | - | - | NEW |
| 1999 | lineups | `rds` | `wnba_stats_game_lineups` | `wnba_lineups_1999.rds` | 0.01 MB | 16,909 | - | - | NEW |
| 1999 | lineups | `csv.gz` | `wnba_stats_game_lineups` | `wnba_lineups_1999.csv.gz` | 0.04 MB | 16,909 | - | - | NEW |
| 2000 | schedule | `parquet` | `wnba_stats_schedules` | `wnba_schedule_2000.parquet` | 0.01 MB | 272 | - | - | NEW |
| 2000 | schedule | `rds` | `wnba_stats_schedules` | `wnba_schedule_2000.rds` | 0.01 MB | 272 | - | - | NEW |
| 2000 | schedule | `csv.gz` | `wnba_stats_schedules` | `wnba_schedule_2000.csv.gz` | 0.00 MB | 272 | - | - | NEW |
| 2000 | play_by_play | `parquet` | `wnba_stats_pbp` | `wnba_play_by_play_2000.parquet` | 1.73 MB | 105,417 | - | - | NEW |
| 2000 | play_by_play | `rds` | `wnba_stats_pbp` | `wnba_play_by_play_2000.rds` | 2.13 MB | 105,417 | - | - | NEW |
| 2000 | play_by_play | `csv.gz` | `wnba_stats_pbp` | `wnba_play_by_play_2000.csv.gz` | 2.75 MB | 105,417 | - | - | NEW |
| 2000 | possessions | `parquet` | `wnba_stats_possessions` | `wnba_possessions_2000.parquet` | 0.32 MB | 38,139 | - | - | NEW |
| 2000 | possessions | `rds` | `wnba_stats_possessions` | `wnba_possessions_2000.rds` | 0.32 MB | 38,139 | - | - | NEW |
| 2000 | possessions | `csv.gz` | `wnba_stats_possessions` | `wnba_possessions_2000.csv.gz` | 0.66 MB | 38,139 | - | - | NEW |
| 2000 | lineups | `parquet` | `wnba_stats_game_lineups` | `wnba_lineups_2000.parquet` | 0.03 MB | 34,265 | - | - | NEW |
| 2000 | lineups | `rds` | `wnba_stats_game_lineups` | `wnba_lineups_2000.rds` | 0.02 MB | 34,265 | - | - | NEW |
| 2000 | lineups | `csv.gz` | `wnba_stats_game_lineups` | `wnba_lineups_2000.csv.gz` | 0.09 MB | 34,265 | - | - | NEW |
| 2001 | schedule | `parquet` | `wnba_stats_schedules` | `wnba_schedule_2001.parquet` | 0.01 MB | 274 | - | - | NEW |
| 2001 | schedule | `rds` | `wnba_stats_schedules` | `wnba_schedule_2001.rds` | 0.01 MB | 274 | - | - | NEW |
| 2001 | schedule | `csv.gz` | `wnba_stats_schedules` | `wnba_schedule_2001.csv.gz` | 0.00 MB | 274 | - | - | NEW |
| 2001 | play_by_play | `parquet` | `wnba_stats_pbp` | `wnba_play_by_play_2001.parquet` | 1.74 MB | 105,957 | - | - | NEW |
| 2001 | play_by_play | `rds` | `wnba_stats_pbp` | `wnba_play_by_play_2001.rds` | 2.16 MB | 105,957 | - | - | NEW |
| 2001 | play_by_play | `csv.gz` | `wnba_stats_pbp` | `wnba_play_by_play_2001.csv.gz` | 2.77 MB | 105,957 | - | - | NEW |
| 2001 | possessions | `parquet` | `wnba_stats_possessions` | `wnba_possessions_2001.parquet` | 0.32 MB | 38,039 | - | - | NEW |
| 2001 | possessions | `rds` | `wnba_stats_possessions` | `wnba_possessions_2001.rds` | 0.32 MB | 38,039 | - | - | NEW |
| 2001 | possessions | `csv.gz` | `wnba_stats_possessions` | `wnba_possessions_2001.csv.gz` | 0.65 MB | 38,039 | - | - | NEW |
| 2001 | lineups | `parquet` | `wnba_stats_game_lineups` | `wnba_lineups_2001.parquet` | 0.02 MB | 22,667 | - | - | NEW |
| 2001 | lineups | `rds` | `wnba_stats_game_lineups` | `wnba_lineups_2001.rds` | 0.01 MB | 22,667 | - | - | NEW |
| 2001 | lineups | `csv.gz` | `wnba_stats_game_lineups` | `wnba_lineups_2001.csv.gz` | 0.06 MB | 22,667 | - | - | NEW |
| 2002 | schedule | `parquet` | `wnba_stats_schedules` | `wnba_schedule_2002.parquet` | 0.01 MB | 273 | - | - | NEW |
| 2002 | schedule | `rds` | `wnba_stats_schedules` | `wnba_schedule_2002.rds` | 0.01 MB | 273 | - | - | NEW |
| 2002 | schedule | `csv.gz` | `wnba_stats_schedules` | `wnba_schedule_2002.csv.gz` | 0.00 MB | 273 | - | - | NEW |
| 2002 | play_by_play | `parquet` | `wnba_stats_pbp` | `wnba_play_by_play_2002.parquet` | 1.73 MB | 105,276 | - | - | NEW |
| 2002 | play_by_play | `rds` | `wnba_stats_pbp` | `wnba_play_by_play_2002.rds` | 2.14 MB | 105,276 | - | - | NEW |
| 2002 | play_by_play | `csv.gz` | `wnba_stats_pbp` | `wnba_play_by_play_2002.csv.gz` | 2.76 MB | 105,276 | - | - | NEW |
| 2002 | possessions | `parquet` | `wnba_stats_possessions` | `wnba_possessions_2002.parquet` | 0.33 MB | 38,256 | - | - | NEW |
| 2002 | possessions | `rds` | `wnba_stats_possessions` | `wnba_possessions_2002.rds` | 0.32 MB | 38,256 | - | - | NEW |
| 2002 | possessions | `csv.gz` | `wnba_stats_possessions` | `wnba_possessions_2002.csv.gz` | 0.66 MB | 38,256 | - | - | NEW |
| 2002 | lineups | `parquet` | `wnba_stats_game_lineups` | `wnba_lineups_2002.parquet` | 0.02 MB | 21,300 | - | - | NEW |
| 2002 | lineups | `rds` | `wnba_stats_game_lineups` | `wnba_lineups_2002.rds` | 0.01 MB | 21,300 | - | - | NEW |
| 2002 | lineups | `csv.gz` | `wnba_stats_game_lineups` | `wnba_lineups_2002.csv.gz` | 0.05 MB | 21,300 | - | - | NEW |
| 2003 | schedule | `parquet` | `wnba_stats_schedules` | `wnba_schedule_2003.parquet` | 0.01 MB | 257 | - | - | NEW |
| 2003 | schedule | `rds` | `wnba_stats_schedules` | `wnba_schedule_2003.rds` | 0.01 MB | 257 | - | - | NEW |
| 2003 | schedule | `csv.gz` | `wnba_stats_schedules` | `wnba_schedule_2003.csv.gz` | 0.00 MB | 257 | - | - | NEW |
| 2003 | play_by_play | `parquet` | `wnba_stats_pbp` | `wnba_play_by_play_2003.parquet` | 1.62 MB | 99,349 | - | - | NEW |
| 2003 | play_by_play | `rds` | `wnba_stats_pbp` | `wnba_play_by_play_2003.rds` | 2.02 MB | 99,349 | - | - | NEW |
| 2003 | play_by_play | `csv.gz` | `wnba_stats_pbp` | `wnba_play_by_play_2003.csv.gz` | 2.61 MB | 99,349 | - | - | NEW |
| 2003 | possessions | `parquet` | `wnba_stats_possessions` | `wnba_possessions_2003.parquet` | 0.31 MB | 36,082 | - | - | NEW |
| 2003 | possessions | `rds` | `wnba_stats_possessions` | `wnba_possessions_2003.rds` | 0.30 MB | 36,082 | - | - | NEW |
| 2003 | possessions | `csv.gz` | `wnba_stats_possessions` | `wnba_possessions_2003.csv.gz` | 0.62 MB | 36,082 | - | - | NEW |
| 2003 | lineups | `parquet` | `wnba_stats_game_lineups` | `wnba_lineups_2003.parquet` | 0.02 MB | 17,955 | - | - | NEW |
| 2003 | lineups | `rds` | `wnba_stats_game_lineups` | `wnba_lineups_2003.rds` | 0.01 MB | 17,955 | - | - | NEW |
| 2003 | lineups | `csv.gz` | `wnba_stats_game_lineups` | `wnba_lineups_2003.csv.gz` | 0.05 MB | 17,955 | - | - | NEW |
| 2004 | schedule | `parquet` | `wnba_stats_schedules` | `wnba_schedule_2004.parquet` | 0.01 MB | 240 | - | - | NEW |
| 2004 | schedule | `rds` | `wnba_stats_schedules` | `wnba_schedule_2004.rds` | 0.01 MB | 240 | - | - | NEW |
| 2004 | schedule | `csv.gz` | `wnba_stats_schedules` | `wnba_schedule_2004.csv.gz` | 0.00 MB | 240 | - | - | NEW |
| 2004 | play_by_play | `parquet` | `wnba_stats_pbp` | `wnba_play_by_play_2004.parquet` | 1.51 MB | 92,441 | - | - | NEW |
| 2004 | play_by_play | `rds` | `wnba_stats_pbp` | `wnba_play_by_play_2004.rds` | 1.87 MB | 92,441 | - | - | NEW |
| 2004 | play_by_play | `csv.gz` | `wnba_stats_pbp` | `wnba_play_by_play_2004.csv.gz` | 2.43 MB | 92,441 | - | - | NEW |
| 2004 | possessions | `parquet` | `wnba_stats_possessions` | `wnba_possessions_2004.parquet` | 0.31 MB | 33,451 | - | - | NEW |
| 2004 | possessions | `rds` | `wnba_stats_possessions` | `wnba_possessions_2004.rds` | 0.29 MB | 33,451 | - | - | NEW |
| 2004 | possessions | `csv.gz` | `wnba_stats_possessions` | `wnba_possessions_2004.csv.gz` | 0.58 MB | 33,451 | - | - | NEW |
| 2004 | lineups | `parquet` | `wnba_stats_game_lineups` | `wnba_lineups_2004.parquet` | 0.03 MB | 12,375 | - | - | NEW |
| 2004 | lineups | `rds` | `wnba_stats_game_lineups` | `wnba_lineups_2004.rds` | 0.02 MB | 12,375 | - | - | NEW |
| 2004 | lineups | `csv.gz` | `wnba_stats_game_lineups` | `wnba_lineups_2004.csv.gz` | 0.04 MB | 12,375 | - | - | NEW |
| 2005 | schedule | `parquet` | `wnba_stats_schedules` | `wnba_schedule_2005.parquet` | 0.01 MB | 238 | - | - | NEW |
| 2005 | schedule | `rds` | `wnba_stats_schedules` | `wnba_schedule_2005.rds` | 0.01 MB | 238 | - | - | NEW |
| 2005 | schedule | `csv.gz` | `wnba_stats_schedules` | `wnba_schedule_2005.csv.gz` | 0.00 MB | 238 | - | - | NEW |
| 2005 | play_by_play | `parquet` | `wnba_stats_pbp` | `wnba_play_by_play_2005.parquet` | 1.49 MB | 91,502 | - | - | NEW |
| 2005 | play_by_play | `rds` | `wnba_stats_pbp` | `wnba_play_by_play_2005.rds` | 1.85 MB | 91,502 | - | - | NEW |
| 2005 | play_by_play | `csv.gz` | `wnba_stats_pbp` | `wnba_play_by_play_2005.csv.gz` | 2.41 MB | 91,502 | - | - | NEW |
| 2005 | possessions | `parquet` | `wnba_stats_possessions` | `wnba_possessions_2005.parquet` | 0.31 MB | 33,290 | - | - | NEW |
| 2005 | possessions | `rds` | `wnba_stats_possessions` | `wnba_possessions_2005.rds` | 0.30 MB | 33,290 | - | - | NEW |
| 2005 | possessions | `csv.gz` | `wnba_stats_possessions` | `wnba_possessions_2005.csv.gz` | 0.58 MB | 33,290 | - | - | NEW |
| 2005 | lineups | `parquet` | `wnba_stats_game_lineups` | `wnba_lineups_2005.parquet` | 0.03 MB | 15,656 | - | - | NEW |
| 2005 | lineups | `rds` | `wnba_stats_game_lineups` | `wnba_lineups_2005.rds` | 0.02 MB | 15,656 | - | - | NEW |
| 2005 | lineups | `csv.gz` | `wnba_stats_game_lineups` | `wnba_lineups_2005.csv.gz` | 0.05 MB | 15,656 | - | - | NEW |
| 2006 | schedule | `parquet` | `wnba_stats_schedules` | `wnba_schedule_2006.parquet` | 0.01 MB | 257 | - | - | NEW |
| 2006 | schedule | `rds` | `wnba_stats_schedules` | `wnba_schedule_2006.rds` | 0.01 MB | 257 | - | - | NEW |
| 2006 | schedule | `csv.gz` | `wnba_stats_schedules` | `wnba_schedule_2006.csv.gz` | 0.00 MB | 257 | - | - | NEW |
| 2006 | play_by_play | `parquet` | `wnba_stats_pbp` | `wnba_play_by_play_2006.parquet` | 1.74 MB | 104,864 | - | - | NEW |
| 2006 | play_by_play | `rds` | `wnba_stats_pbp` | `wnba_play_by_play_2006.rds` | 2.14 MB | 104,864 | - | - | NEW |
| 2006 | play_by_play | `csv.gz` | `wnba_stats_pbp` | `wnba_play_by_play_2006.csv.gz` | 2.73 MB | 104,864 | - | - | NEW |
| 2006 | possessions | `parquet` | `wnba_stats_possessions` | `wnba_possessions_2006.parquet` | 0.36 MB | 39,384 | - | - | NEW |
| 2006 | possessions | `rds` | `wnba_stats_possessions` | `wnba_possessions_2006.rds` | 0.34 MB | 39,384 | - | - | NEW |
| 2006 | possessions | `csv.gz` | `wnba_stats_possessions` | `wnba_possessions_2006.csv.gz` | 0.67 MB | 39,384 | - | - | NEW |
| 2006 | lineups | `parquet` | `wnba_stats_game_lineups` | `wnba_lineups_2006.parquet` | 0.03 MB | 16,832 | - | - | NEW |
| 2006 | lineups | `rds` | `wnba_stats_game_lineups` | `wnba_lineups_2006.rds` | 0.02 MB | 16,832 | - | - | NEW |
| 2006 | lineups | `csv.gz` | `wnba_stats_game_lineups` | `wnba_lineups_2006.csv.gz` | 0.05 MB | 16,832 | - | - | NEW |
| 2007 | schedule | `parquet` | `wnba_stats_schedules` | `wnba_schedule_2007.parquet` | 0.01 MB | 241 | - | - | NEW |
| 2007 | schedule | `rds` | `wnba_stats_schedules` | `wnba_schedule_2007.rds` | 0.01 MB | 241 | - | - | NEW |
| 2007 | schedule | `csv.gz` | `wnba_stats_schedules` | `wnba_schedule_2007.csv.gz` | 0.00 MB | 241 | - | - | NEW |
| 2007 | play_by_play | `parquet` | `wnba_stats_pbp` | `wnba_play_by_play_2007.parquet` | 1.67 MB | 101,161 | - | - | NEW |
| 2007 | play_by_play | `rds` | `wnba_stats_pbp` | `wnba_play_by_play_2007.rds` | 2.05 MB | 101,161 | - | - | NEW |
| 2007 | play_by_play | `csv.gz` | `wnba_stats_pbp` | `wnba_play_by_play_2007.csv.gz` | 2.63 MB | 101,161 | - | - | NEW |
| 2007 | possessions | `parquet` | `wnba_stats_possessions` | `wnba_possessions_2007.parquet` | 0.35 MB | 38,191 | - | - | NEW |
| 2007 | possessions | `rds` | `wnba_stats_possessions` | `wnba_possessions_2007.rds` | 0.32 MB | 38,191 | - | - | NEW |
| 2007 | possessions | `csv.gz` | `wnba_stats_possessions` | `wnba_possessions_2007.csv.gz` | 0.64 MB | 38,191 | - | - | NEW |
| 2007 | lineups | `parquet` | `wnba_stats_game_lineups` | `wnba_lineups_2007.parquet` | 0.02 MB | 12,039 | - | - | NEW |
| 2007 | lineups | `rds` | `wnba_stats_game_lineups` | `wnba_lineups_2007.rds` | 0.02 MB | 12,039 | - | - | NEW |
| 2007 | lineups | `csv.gz` | `wnba_stats_game_lineups` | `wnba_lineups_2007.csv.gz` | 0.03 MB | 12,039 | - | - | NEW |
| 2008 | schedule | `parquet` | `wnba_stats_schedules` | `wnba_schedule_2008.parquet` | 0.01 MB | 259 | - | - | NEW |
| 2008 | schedule | `rds` | `wnba_stats_schedules` | `wnba_schedule_2008.rds` | 0.01 MB | 259 | - | - | NEW |
| 2008 | schedule | `csv.gz` | `wnba_stats_schedules` | `wnba_schedule_2008.csv.gz` | 0.00 MB | 259 | - | - | NEW |
| 2008 | play_by_play | `parquet` | `wnba_stats_pbp` | `wnba_play_by_play_2008.parquet` | 1.82 MB | 109,761 | - | - | NEW |
| 2008 | play_by_play | `rds` | `wnba_stats_pbp` | `wnba_play_by_play_2008.rds` | 2.23 MB | 109,761 | - | - | NEW |
| 2008 | play_by_play | `csv.gz` | `wnba_stats_pbp` | `wnba_play_by_play_2008.csv.gz` | 2.86 MB | 109,761 | - | - | NEW |
| 2008 | possessions | `parquet` | `wnba_stats_possessions` | `wnba_possessions_2008.parquet` | 0.38 MB | 40,514 | - | - | NEW |
| 2008 | possessions | `rds` | `wnba_stats_possessions` | `wnba_possessions_2008.rds` | 0.35 MB | 40,514 | - | - | NEW |
| 2008 | possessions | `csv.gz` | `wnba_stats_possessions` | `wnba_possessions_2008.csv.gz` | 0.69 MB | 40,514 | - | - | NEW |
| 2008 | lineups | `parquet` | `wnba_stats_game_lineups` | `wnba_lineups_2008.parquet` | 0.03 MB | 16,643 | - | - | NEW |
| 2008 | lineups | `rds` | `wnba_stats_game_lineups` | `wnba_lineups_2008.rds` | 0.02 MB | 16,643 | - | - | NEW |
| 2008 | lineups | `csv.gz` | `wnba_stats_game_lineups` | `wnba_lineups_2008.csv.gz` | 0.05 MB | 16,643 | - | - | NEW |
| 2009 | schedule | `parquet` | `wnba_stats_schedules` | `wnba_schedule_2009.parquet` | 0.01 MB | 241 | - | - | NEW |
| 2009 | schedule | `rds` | `wnba_stats_schedules` | `wnba_schedule_2009.rds` | 0.01 MB | 241 | - | - | NEW |
| 2009 | schedule | `csv.gz` | `wnba_stats_schedules` | `wnba_schedule_2009.csv.gz` | 0.00 MB | 241 | - | - | NEW |
| 2009 | play_by_play | `parquet` | `wnba_stats_pbp` | `wnba_play_by_play_2009.parquet` | 1.71 MB | 101,779 | - | - | NEW |
| 2009 | play_by_play | `rds` | `wnba_stats_pbp` | `wnba_play_by_play_2009.rds` | 2.10 MB | 101,779 | - | - | NEW |
| 2009 | play_by_play | `csv.gz` | `wnba_stats_pbp` | `wnba_play_by_play_2009.csv.gz` | 2.67 MB | 101,779 | - | - | NEW |
| 2009 | possessions | `parquet` | `wnba_stats_possessions` | `wnba_possessions_2009.parquet` | 0.35 MB | 38,097 | - | - | NEW |
| 2009 | possessions | `rds` | `wnba_stats_possessions` | `wnba_possessions_2009.rds` | 0.33 MB | 38,097 | - | - | NEW |
| 2009 | possessions | `csv.gz` | `wnba_stats_possessions` | `wnba_possessions_2009.csv.gz` | 0.65 MB | 38,097 | - | - | NEW |
| 2009 | lineups | `parquet` | `wnba_stats_game_lineups` | `wnba_lineups_2009.parquet` | 0.03 MB | 14,521 | - | - | NEW |
| 2009 | lineups | `rds` | `wnba_stats_game_lineups` | `wnba_lineups_2009.rds` | 0.02 MB | 14,521 | - | - | NEW |
| 2009 | lineups | `csv.gz` | `wnba_stats_game_lineups` | `wnba_lineups_2009.csv.gz` | 0.04 MB | 14,521 | - | - | NEW |
| 2010 | schedule | `parquet` | `wnba_stats_schedules` | `wnba_schedule_2010.parquet` | 0.01 MB | 220 | - | - | NEW |
| 2010 | schedule | `rds` | `wnba_stats_schedules` | `wnba_schedule_2010.rds` | 0.00 MB | 220 | - | - | NEW |
| 2010 | schedule | `csv.gz` | `wnba_stats_schedules` | `wnba_schedule_2010.csv.gz` | 0.00 MB | 220 | - | - | NEW |
| 2010 | play_by_play | `parquet` | `wnba_stats_pbp` | `wnba_play_by_play_2010.parquet` | 1.56 MB | 91,581 | - | - | NEW |
| 2010 | play_by_play | `rds` | `wnba_stats_pbp` | `wnba_play_by_play_2010.rds` | 1.90 MB | 91,581 | - | - | NEW |
| 2010 | play_by_play | `csv.gz` | `wnba_stats_pbp` | `wnba_play_by_play_2010.csv.gz` | 2.42 MB | 91,581 | - | - | NEW |
| 2010 | possessions | `parquet` | `wnba_stats_possessions` | `wnba_possessions_2010.parquet` | 0.32 MB | 34,797 | - | - | NEW |
| 2010 | possessions | `rds` | `wnba_stats_possessions` | `wnba_possessions_2010.rds` | 0.29 MB | 34,797 | - | - | NEW |
| 2010 | possessions | `csv.gz` | `wnba_stats_possessions` | `wnba_possessions_2010.csv.gz` | 0.59 MB | 34,797 | - | - | NEW |
| 2010 | lineups | `parquet` | `wnba_stats_game_lineups` | `wnba_lineups_2010.parquet` | 0.02 MB | 11,444 | - | - | NEW |
| 2010 | lineups | `rds` | `wnba_stats_game_lineups` | `wnba_lineups_2010.rds` | 0.02 MB | 11,444 | - | - | NEW |
| 2010 | lineups | `csv.gz` | `wnba_stats_game_lineups` | `wnba_lineups_2010.csv.gz` | 0.03 MB | 11,444 | - | - | NEW |
| 2011 | schedule | `parquet` | `wnba_stats_schedules` | `wnba_schedule_2011.parquet` | 0.01 MB | 223 | - | - | NEW |
| 2011 | schedule | `rds` | `wnba_stats_schedules` | `wnba_schedule_2011.rds` | 0.00 MB | 223 | - | - | NEW |
| 2011 | schedule | `csv.gz` | `wnba_stats_schedules` | `wnba_schedule_2011.csv.gz` | 0.00 MB | 223 | - | - | NEW |
| 2011 | play_by_play | `parquet` | `wnba_stats_pbp` | `wnba_play_by_play_2011.parquet` | 1.57 MB | 90,663 | - | - | NEW |
| 2011 | play_by_play | `rds` | `wnba_stats_pbp` | `wnba_play_by_play_2011.rds` | 1.90 MB | 90,663 | - | - | NEW |
| 2011 | play_by_play | `csv.gz` | `wnba_stats_pbp` | `wnba_play_by_play_2011.csv.gz` | 2.43 MB | 90,663 | - | - | NEW |
| 2011 | possessions | `parquet` | `wnba_stats_possessions` | `wnba_possessions_2011.parquet` | 0.31 MB | 34,652 | - | - | NEW |
| 2011 | possessions | `rds` | `wnba_stats_possessions` | `wnba_possessions_2011.rds` | 0.29 MB | 34,652 | - | - | NEW |
| 2011 | possessions | `csv.gz` | `wnba_stats_possessions` | `wnba_possessions_2011.csv.gz` | 0.58 MB | 34,652 | - | - | NEW |
| 2011 | lineups | `parquet` | `wnba_stats_game_lineups` | `wnba_lineups_2011.parquet` | 0.02 MB | 8,314 | - | - | NEW |
| 2011 | lineups | `rds` | `wnba_stats_game_lineups` | `wnba_lineups_2011.rds` | 0.01 MB | 8,314 | - | - | NEW |
| 2011 | lineups | `csv.gz` | `wnba_stats_game_lineups` | `wnba_lineups_2011.csv.gz` | 0.02 MB | 8,314 | - | - | NEW |
| 2012 | schedule | `parquet` | `wnba_stats_schedules` | `wnba_schedule_2012.parquet` | 0.01 MB | 223 | - | - | NEW |
| 2012 | schedule | `rds` | `wnba_stats_schedules` | `wnba_schedule_2012.rds` | 0.00 MB | 223 | - | - | NEW |
| 2012 | schedule | `csv.gz` | `wnba_stats_schedules` | `wnba_schedule_2012.csv.gz` | 0.00 MB | 223 | - | - | NEW |
| 2012 | play_by_play | `parquet` | `wnba_stats_pbp` | `wnba_play_by_play_2012.parquet` | 1.59 MB | 91,399 | - | - | NEW |
| 2012 | play_by_play | `rds` | `wnba_stats_pbp` | `wnba_play_by_play_2012.rds` | 1.92 MB | 91,399 | - | - | NEW |
| 2012 | play_by_play | `csv.gz` | `wnba_stats_pbp` | `wnba_play_by_play_2012.csv.gz` | 2.45 MB | 91,399 | - | - | NEW |
| 2012 | possessions | `parquet` | `wnba_stats_possessions` | `wnba_possessions_2012.parquet` | 0.30 MB | 34,637 | - | - | NEW |
| 2012 | possessions | `rds` | `wnba_stats_possessions` | `wnba_possessions_2012.rds` | 0.28 MB | 34,637 | - | - | NEW |
| 2012 | possessions | `csv.gz` | `wnba_stats_possessions` | `wnba_possessions_2012.csv.gz` | 0.58 MB | 34,637 | - | - | NEW |
| 2012 | lineups | `parquet` | `wnba_stats_game_lineups` | `wnba_lineups_2012.parquet` | 0.01 MB | 4,565 | - | - | NEW |
| 2012 | lineups | `rds` | `wnba_stats_game_lineups` | `wnba_lineups_2012.rds` | 0.01 MB | 4,565 | - | - | NEW |
| 2012 | lineups | `csv.gz` | `wnba_stats_game_lineups` | `wnba_lineups_2012.csv.gz` | 0.01 MB | 4,565 | - | - | NEW |
| 2013 | schedule | `parquet` | `wnba_stats_schedules` | `wnba_schedule_2013.parquet` | 0.01 MB | 221 | - | - | NEW |
| 2013 | schedule | `rds` | `wnba_stats_schedules` | `wnba_schedule_2013.rds` | 0.00 MB | 221 | - | - | NEW |
| 2013 | schedule | `csv.gz` | `wnba_stats_schedules` | `wnba_schedule_2013.csv.gz` | 0.00 MB | 221 | - | - | NEW |
| 2013 | play_by_play | `parquet` | `wnba_stats_pbp` | `wnba_play_by_play_2013.parquet` | 1.58 MB | 89,896 | - | - | NEW |
| 2013 | play_by_play | `rds` | `wnba_stats_pbp` | `wnba_play_by_play_2013.rds` | 1.89 MB | 89,896 | - | - | NEW |
| 2013 | play_by_play | `csv.gz` | `wnba_stats_pbp` | `wnba_play_by_play_2013.csv.gz` | 2.41 MB | 89,896 | - | - | NEW |
| 2013 | possessions | `parquet` | `wnba_stats_possessions` | `wnba_possessions_2013.parquet` | 0.31 MB | 34,012 | - | - | NEW |
| 2013 | possessions | `rds` | `wnba_stats_possessions` | `wnba_possessions_2013.rds` | 0.29 MB | 34,012 | - | - | NEW |
| 2013 | possessions | `csv.gz` | `wnba_stats_possessions` | `wnba_possessions_2013.csv.gz` | 0.57 MB | 34,012 | - | - | NEW |
| 2013 | lineups | `parquet` | `wnba_stats_game_lineups` | `wnba_lineups_2013.parquet` | 0.02 MB | 10,521 | - | - | NEW |
| 2013 | lineups | `rds` | `wnba_stats_game_lineups` | `wnba_lineups_2013.rds` | 0.02 MB | 10,521 | - | - | NEW |
| 2013 | lineups | `csv.gz` | `wnba_stats_game_lineups` | `wnba_lineups_2013.csv.gz` | 0.03 MB | 10,521 | - | - | NEW |
| 2014 | schedule | `parquet` | `wnba_stats_schedules` | `wnba_schedule_2014.parquet` | 0.01 MB | 222 | - | - | NEW |
| 2014 | schedule | `rds` | `wnba_stats_schedules` | `wnba_schedule_2014.rds` | 0.00 MB | 222 | - | - | NEW |
| 2014 | schedule | `csv.gz` | `wnba_stats_schedules` | `wnba_schedule_2014.csv.gz` | 0.00 MB | 222 | - | - | NEW |
| 2014 | play_by_play | `parquet` | `wnba_stats_pbp` | `wnba_play_by_play_2014.parquet` | 1.60 MB | 90,134 | - | - | NEW |
| 2014 | play_by_play | `rds` | `wnba_stats_pbp` | `wnba_play_by_play_2014.rds` | 1.91 MB | 90,134 | - | - | NEW |
| 2014 | play_by_play | `csv.gz` | `wnba_stats_pbp` | `wnba_play_by_play_2014.csv.gz` | 2.44 MB | 90,134 | - | - | NEW |
| 2014 | possessions | `parquet` | `wnba_stats_possessions` | `wnba_possessions_2014.parquet` | 0.31 MB | 34,312 | - | - | NEW |
| 2014 | possessions | `rds` | `wnba_stats_possessions` | `wnba_possessions_2014.rds` | 0.29 MB | 34,312 | - | - | NEW |
| 2014 | possessions | `csv.gz` | `wnba_stats_possessions` | `wnba_possessions_2014.csv.gz` | 0.58 MB | 34,312 | - | - | NEW |
| 2014 | lineups | `parquet` | `wnba_stats_game_lineups` | `wnba_lineups_2014.parquet` | 0.02 MB | 9,372 | - | - | NEW |
| 2014 | lineups | `rds` | `wnba_stats_game_lineups` | `wnba_lineups_2014.rds` | 0.01 MB | 9,372 | - | - | NEW |
| 2014 | lineups | `csv.gz` | `wnba_stats_game_lineups` | `wnba_lineups_2014.csv.gz` | 0.03 MB | 9,372 | - | - | NEW |
| 2015 | schedule | `parquet` | `wnba_stats_schedules` | `wnba_schedule_2015.parquet` | 0.01 MB | 225 | - | - | NEW |
| 2015 | schedule | `rds` | `wnba_stats_schedules` | `wnba_schedule_2015.rds` | 0.00 MB | 225 | - | - | NEW |
| 2015 | schedule | `csv.gz` | `wnba_stats_schedules` | `wnba_schedule_2015.csv.gz` | 0.00 MB | 225 | - | - | NEW |
| 2015 | play_by_play | `parquet` | `wnba_stats_pbp` | `wnba_play_by_play_2015.parquet` | 1.63 MB | 90,972 | - | - | NEW |
| 2015 | play_by_play | `rds` | `wnba_stats_pbp` | `wnba_play_by_play_2015.rds` | 1.93 MB | 90,972 | - | - | NEW |
| 2015 | play_by_play | `csv.gz` | `wnba_stats_pbp` | `wnba_play_by_play_2015.csv.gz` | 2.46 MB | 90,972 | - | - | NEW |
| 2015 | possessions | `parquet` | `wnba_stats_possessions` | `wnba_possessions_2015.parquet` | 0.32 MB | 34,133 | - | - | NEW |
| 2015 | possessions | `rds` | `wnba_stats_possessions` | `wnba_possessions_2015.rds` | 0.29 MB | 34,133 | - | - | NEW |
| 2015 | possessions | `csv.gz` | `wnba_stats_possessions` | `wnba_possessions_2015.csv.gz` | 0.58 MB | 34,133 | - | - | NEW |
| 2015 | lineups | `parquet` | `wnba_stats_game_lineups` | `wnba_lineups_2015.parquet` | 0.03 MB | 12,724 | - | - | NEW |
| 2015 | lineups | `rds` | `wnba_stats_game_lineups` | `wnba_lineups_2015.rds` | 0.02 MB | 12,724 | - | - | NEW |
| 2015 | lineups | `csv.gz` | `wnba_stats_game_lineups` | `wnba_lineups_2015.csv.gz` | 0.04 MB | 12,724 | - | - | NEW |
| 2016 | schedule | `parquet` | `wnba_stats_schedules` | `wnba_schedule_2016.parquet` | 0.01 MB | 220 | - | - | NEW |
| 2016 | schedule | `rds` | `wnba_stats_schedules` | `wnba_schedule_2016.rds` | 0.00 MB | 220 | - | - | NEW |
| 2016 | schedule | `csv.gz` | `wnba_stats_schedules` | `wnba_schedule_2016.csv.gz` | 0.00 MB | 220 | - | - | NEW |
| 2016 | play_by_play | `parquet` | `wnba_stats_pbp` | `wnba_play_by_play_2016.parquet` | 1.68 MB | 91,724 | - | - | NEW |
| 2016 | play_by_play | `rds` | `wnba_stats_pbp` | `wnba_play_by_play_2016.rds` | 1.98 MB | 91,724 | - | - | NEW |
| 2016 | play_by_play | `csv.gz` | `wnba_stats_pbp` | `wnba_play_by_play_2016.csv.gz` | 2.51 MB | 91,724 | - | - | NEW |
| 2016 | possessions | `parquet` | `wnba_stats_possessions` | `wnba_possessions_2016.parquet` | 0.42 MB | 34,737 | - | - | NEW |
| 2016 | possessions | `rds` | `wnba_stats_possessions` | `wnba_possessions_2016.rds` | 0.36 MB | 34,737 | - | - | NEW |
| 2016 | possessions | `csv.gz` | `wnba_stats_possessions` | `wnba_possessions_2016.csv.gz` | 0.65 MB | 34,737 | - | - | NEW |
| 2016 | lineups | `parquet` | `wnba_stats_game_lineups` | `wnba_lineups_2016.parquet` | 0.08 MB | 62,095 | - | - | NEW |
| 2016 | lineups | `rds` | `wnba_stats_game_lineups` | `wnba_lineups_2016.rds` | 0.08 MB | 62,095 | - | - | NEW |
| 2016 | lineups | `csv.gz` | `wnba_stats_game_lineups` | `wnba_lineups_2016.csv.gz` | 0.18 MB | 62,095 | - | - | NEW |
| 2017 | schedule | `parquet` | `wnba_stats_schedules` | `wnba_schedule_2017.parquet` | 0.01 MB | 219 | - | - | NEW |
| 2017 | schedule | `rds` | `wnba_stats_schedules` | `wnba_schedule_2017.rds` | 0.00 MB | 219 | - | - | NEW |
| 2017 | schedule | `csv.gz` | `wnba_stats_schedules` | `wnba_schedule_2017.csv.gz` | 0.00 MB | 219 | - | - | NEW |
| 2017 | play_by_play | `parquet` | `wnba_stats_pbp` | `wnba_play_by_play_2017.parquet` | 1.67 MB | 90,543 | - | - | NEW |
| 2017 | play_by_play | `rds` | `wnba_stats_pbp` | `wnba_play_by_play_2017.rds` | 1.95 MB | 90,543 | - | - | NEW |
| 2017 | play_by_play | `csv.gz` | `wnba_stats_pbp` | `wnba_play_by_play_2017.csv.gz` | 2.49 MB | 90,543 | - | - | NEW |
| 2017 | possessions | `parquet` | `wnba_stats_possessions` | `wnba_possessions_2017.parquet` | 0.41 MB | 34,392 | - | - | NEW |
| 2017 | possessions | `rds` | `wnba_stats_possessions` | `wnba_possessions_2017.rds` | 0.35 MB | 34,392 | - | - | NEW |
| 2017 | possessions | `csv.gz` | `wnba_stats_possessions` | `wnba_possessions_2017.csv.gz` | 0.65 MB | 34,392 | - | - | NEW |
| 2017 | lineups | `parquet` | `wnba_stats_game_lineups` | `wnba_lineups_2017.parquet` | 0.08 MB | 64,280 | - | - | NEW |
| 2017 | lineups | `rds` | `wnba_stats_game_lineups` | `wnba_lineups_2017.rds` | 0.08 MB | 64,280 | - | - | NEW |
| 2017 | lineups | `csv.gz` | `wnba_stats_game_lineups` | `wnba_lineups_2017.csv.gz` | 0.19 MB | 64,280 | - | - | NEW |
| 2018 | schedule | `parquet` | `wnba_stats_schedules` | `wnba_schedule_2018.parquet` | 0.01 MB | 221 | - | - | NEW |
| 2018 | schedule | `rds` | `wnba_stats_schedules` | `wnba_schedule_2018.rds` | 0.00 MB | 221 | - | - | NEW |
| 2018 | schedule | `csv.gz` | `wnba_stats_schedules` | `wnba_schedule_2018.csv.gz` | 0.00 MB | 221 | - | - | NEW |
| 2018 | play_by_play | `parquet` | `wnba_stats_pbp` | `wnba_play_by_play_2018.parquet` | 1.68 MB | 89,269 | - | - | NEW |
| 2018 | play_by_play | `rds` | `wnba_stats_pbp` | `wnba_play_by_play_2018.rds` | 1.96 MB | 89,269 | - | - | NEW |
| 2018 | play_by_play | `csv.gz` | `wnba_stats_pbp` | `wnba_play_by_play_2018.csv.gz` | 2.49 MB | 89,269 | - | - | NEW |
| 2018 | possessions | `parquet` | `wnba_stats_possessions` | `wnba_possessions_2018.parquet` | 0.42 MB | 34,637 | - | - | NEW |
| 2018 | possessions | `rds` | `wnba_stats_possessions` | `wnba_possessions_2018.rds` | 0.36 MB | 34,637 | - | - | NEW |
| 2018 | possessions | `csv.gz` | `wnba_stats_possessions` | `wnba_possessions_2018.csv.gz` | 0.66 MB | 34,637 | - | - | NEW |
| 2018 | lineups | `parquet` | `wnba_stats_game_lineups` | `wnba_lineups_2018.parquet` | 0.10 MB | 70,040 | - | - | NEW |
| 2018 | lineups | `rds` | `wnba_stats_game_lineups` | `wnba_lineups_2018.rds` | 0.10 MB | 70,040 | - | - | NEW |
| 2018 | lineups | `csv.gz` | `wnba_stats_game_lineups` | `wnba_lineups_2018.csv.gz` | 0.21 MB | 70,040 | - | - | NEW |
| 2019 | schedule | `parquet` | `wnba_stats_schedules` | `wnba_schedule_2019.parquet` | 0.01 MB | 220 | - | - | NEW |
| 2019 | schedule | `rds` | `wnba_stats_schedules` | `wnba_schedule_2019.rds` | 0.00 MB | 220 | - | - | NEW |
| 2019 | schedule | `csv.gz` | `wnba_stats_schedules` | `wnba_schedule_2019.csv.gz` | 0.00 MB | 220 | - | - | NEW |
| 2019 | play_by_play | `parquet` | `wnba_stats_pbp` | `wnba_play_by_play_2019.parquet` | 1.66 MB | 89,334 | - | - | NEW |
| 2019 | play_by_play | `rds` | `wnba_stats_pbp` | `wnba_play_by_play_2019.rds` | 1.96 MB | 89,334 | - | - | NEW |
| 2019 | play_by_play | `csv.gz` | `wnba_stats_pbp` | `wnba_play_by_play_2019.csv.gz` | 2.48 MB | 89,334 | - | - | NEW |
| 2019 | possessions | `parquet` | `wnba_stats_possessions` | `wnba_possessions_2019.parquet` | 0.43 MB | 34,517 | - | - | NEW |
| 2019 | possessions | `rds` | `wnba_stats_possessions` | `wnba_possessions_2019.rds` | 0.37 MB | 34,517 | - | - | NEW |
| 2019 | possessions | `csv.gz` | `wnba_stats_possessions` | `wnba_possessions_2019.csv.gz` | 0.67 MB | 34,517 | - | - | NEW |
| 2019 | lineups | `parquet` | `wnba_stats_game_lineups` | `wnba_lineups_2019.parquet` | 0.12 MB | 83,172 | - | - | NEW |
| 2019 | lineups | `rds` | `wnba_stats_game_lineups` | `wnba_lineups_2019.rds` | 0.12 MB | 83,172 | - | - | NEW |
| 2019 | lineups | `csv.gz` | `wnba_stats_game_lineups` | `wnba_lineups_2019.csv.gz` | 0.25 MB | 83,172 | - | - | NEW |
| 2020 | schedule | `parquet` | `wnba_stats_schedules` | `wnba_schedule_2020.parquet` | 0.01 MB | 147 | - | - | NEW |
| 2020 | schedule | `rds` | `wnba_stats_schedules` | `wnba_schedule_2020.rds` | 0.00 MB | 147 | - | - | NEW |
| 2020 | schedule | `csv.gz` | `wnba_stats_schedules` | `wnba_schedule_2020.csv.gz` | 0.00 MB | 147 | - | - | NEW |
| 2020 | play_by_play | `parquet` | `wnba_stats_pbp` | `wnba_play_by_play_2020.parquet` | 1.13 MB | 59,512 | - | - | NEW |
| 2020 | play_by_play | `rds` | `wnba_stats_pbp` | `wnba_play_by_play_2020.rds` | 1.31 MB | 59,512 | - | - | NEW |
| 2020 | play_by_play | `csv.gz` | `wnba_stats_pbp` | `wnba_play_by_play_2020.csv.gz` | 1.64 MB | 59,512 | - | - | NEW |
| 2020 | possessions | `parquet` | `wnba_stats_possessions` | `wnba_possessions_2020.parquet` | 0.30 MB | 23,501 | - | - | NEW |
| 2020 | possessions | `rds` | `wnba_stats_possessions` | `wnba_possessions_2020.rds` | 0.25 MB | 23,501 | - | - | NEW |
| 2020 | possessions | `csv.gz` | `wnba_stats_possessions` | `wnba_possessions_2020.csv.gz` | 0.45 MB | 23,501 | - | - | NEW |
| 2020 | lineups | `parquet` | `wnba_stats_game_lineups` | `wnba_lineups_2020.parquet` | 0.08 MB | 52,298 | - | - | NEW |
| 2020 | lineups | `rds` | `wnba_stats_game_lineups` | `wnba_lineups_2020.rds` | 0.08 MB | 52,298 | - | - | NEW |
| 2020 | lineups | `csv.gz` | `wnba_stats_game_lineups` | `wnba_lineups_2020.csv.gz` | 0.16 MB | 52,298 | - | - | NEW |
| 2021 | schedule | `parquet` | `wnba_stats_schedules` | `wnba_schedule_2021.parquet` | 0.01 MB | 209 | - | - | NEW |
| 2021 | schedule | `rds` | `wnba_stats_schedules` | `wnba_schedule_2021.rds` | 0.00 MB | 209 | - | - | NEW |
| 2021 | schedule | `csv.gz` | `wnba_stats_schedules` | `wnba_schedule_2021.csv.gz` | 0.00 MB | 209 | - | - | NEW |
| 2021 | play_by_play | `parquet` | `wnba_stats_pbp` | `wnba_play_by_play_2021.parquet` | 1.58 MB | 83,986 | - | - | NEW |
| 2021 | play_by_play | `rds` | `wnba_stats_pbp` | `wnba_play_by_play_2021.rds` | 1.84 MB | 83,986 | - | - | NEW |
| 2021 | play_by_play | `csv.gz` | `wnba_stats_pbp` | `wnba_play_by_play_2021.csv.gz` | 2.33 MB | 83,986 | - | - | NEW |
| 2021 | possessions | `parquet` | `wnba_stats_possessions` | `wnba_possessions_2021.parquet` | 0.42 MB | 33,099 | - | - | NEW |
| 2021 | possessions | `rds` | `wnba_stats_possessions` | `wnba_possessions_2021.rds` | 0.35 MB | 33,099 | - | - | NEW |
| 2021 | possessions | `csv.gz` | `wnba_stats_possessions` | `wnba_possessions_2021.csv.gz` | 0.64 MB | 33,099 | - | - | NEW |
| 2021 | lineups | `parquet` | `wnba_stats_game_lineups` | `wnba_lineups_2021.parquet` | 0.11 MB | 75,795 | - | - | NEW |
| 2021 | lineups | `rds` | `wnba_stats_game_lineups` | `wnba_lineups_2021.rds` | 0.11 MB | 75,795 | - | - | NEW |
| 2021 | lineups | `csv.gz` | `wnba_stats_game_lineups` | `wnba_lineups_2021.csv.gz` | 0.23 MB | 75,795 | - | - | NEW |
| 2022 | schedule | `parquet` | `wnba_stats_schedules` | `wnba_schedule_2022.parquet` | 0.01 MB | 239 | - | - | NEW |
| 2022 | schedule | `rds` | `wnba_stats_schedules` | `wnba_schedule_2022.rds` | 0.00 MB | 239 | - | - | NEW |
| 2022 | schedule | `csv.gz` | `wnba_stats_schedules` | `wnba_schedule_2022.csv.gz` | 0.00 MB | 239 | - | - | NEW |
| 2022 | play_by_play | `parquet` | `wnba_stats_pbp` | `wnba_play_by_play_2022.parquet` | 1.83 MB | 97,050 | - | - | NEW |
| 2022 | play_by_play | `rds` | `wnba_stats_pbp` | `wnba_play_by_play_2022.rds` | 2.13 MB | 97,050 | - | - | NEW |
| 2022 | play_by_play | `csv.gz` | `wnba_stats_pbp` | `wnba_play_by_play_2022.csv.gz` | 2.70 MB | 97,050 | - | - | NEW |
| 2022 | possessions | `parquet` | `wnba_stats_possessions` | `wnba_possessions_2022.parquet` | 0.47 MB | 38,007 | - | - | NEW |
| 2022 | possessions | `rds` | `wnba_stats_possessions` | `wnba_possessions_2022.rds` | 0.40 MB | 38,007 | - | - | NEW |
| 2022 | possessions | `csv.gz` | `wnba_stats_possessions` | `wnba_possessions_2022.csv.gz` | 0.73 MB | 38,007 | - | - | NEW |
| 2022 | lineups | `parquet` | `wnba_stats_game_lineups` | `wnba_lineups_2022.parquet` | 0.12 MB | 83,240 | - | - | NEW |
| 2022 | lineups | `rds` | `wnba_stats_game_lineups` | `wnba_lineups_2022.rds` | 0.12 MB | 83,240 | - | - | NEW |
| 2022 | lineups | `csv.gz` | `wnba_stats_game_lineups` | `wnba_lineups_2022.csv.gz` | 0.25 MB | 83,240 | - | - | NEW |
| 2023 | schedule | `parquet` | `wnba_stats_schedules` | `wnba_schedule_2023.parquet` | 0.01 MB | 260 | - | - | NEW |
| 2023 | schedule | `rds` | `wnba_stats_schedules` | `wnba_schedule_2023.rds` | 0.01 MB | 260 | - | - | NEW |
| 2023 | schedule | `csv.gz` | `wnba_stats_schedules` | `wnba_schedule_2023.csv.gz` | 0.00 MB | 260 | - | - | NEW |
| 2023 | play_by_play | `parquet` | `wnba_stats_pbp` | `wnba_play_by_play_2023.parquet` | 1.97 MB | 106,038 | - | - | NEW |
| 2023 | play_by_play | `rds` | `wnba_stats_pbp` | `wnba_play_by_play_2023.rds` | 2.33 MB | 106,038 | - | - | NEW |
| 2023 | play_by_play | `csv.gz` | `wnba_stats_pbp` | `wnba_play_by_play_2023.csv.gz` | 2.96 MB | 106,038 | - | - | NEW |
| 2023 | possessions | `parquet` | `wnba_stats_possessions` | `wnba_possessions_2023.parquet` | 0.51 MB | 41,350 | - | - | NEW |
| 2023 | possessions | `rds` | `wnba_stats_possessions` | `wnba_possessions_2023.rds` | 0.43 MB | 41,350 | - | - | NEW |
| 2023 | possessions | `csv.gz` | `wnba_stats_possessions` | `wnba_possessions_2023.csv.gz` | 0.80 MB | 41,350 | - | - | NEW |
| 2023 | lineups | `parquet` | `wnba_stats_game_lineups` | `wnba_lineups_2023.parquet` | 0.13 MB | 93,827 | - | - | NEW |
| 2023 | lineups | `rds` | `wnba_stats_game_lineups` | `wnba_lineups_2023.rds` | 0.13 MB | 93,827 | - | - | NEW |
| 2023 | lineups | `csv.gz` | `wnba_stats_game_lineups` | `wnba_lineups_2023.csv.gz` | 0.29 MB | 93,827 | - | - | NEW |
| 2024 | schedule | `parquet` | `wnba_stats_schedules` | `wnba_schedule_2024.parquet` | 0.01 MB | 262 | - | - | NEW |
| 2024 | schedule | `rds` | `wnba_stats_schedules` | `wnba_schedule_2024.rds` | 0.01 MB | 262 | - | - | NEW |
| 2024 | schedule | `csv.gz` | `wnba_stats_schedules` | `wnba_schedule_2024.csv.gz` | 0.00 MB | 262 | - | - | NEW |
| 2024 | play_by_play | `parquet` | `wnba_stats_pbp` | `wnba_play_by_play_2024.parquet` | 1.99 MB | 105,797 | - | - | NEW |
| 2024 | play_by_play | `rds` | `wnba_stats_pbp` | `wnba_play_by_play_2024.rds` | 2.32 MB | 105,797 | - | - | NEW |
| 2024 | play_by_play | `csv.gz` | `wnba_stats_pbp` | `wnba_play_by_play_2024.csv.gz` | 2.95 MB | 105,797 | - | - | NEW |
| 2024 | possessions | `parquet` | `wnba_stats_possessions` | `wnba_possessions_2024.parquet` | 0.49 MB | 41,429 | - | - | NEW |
| 2024 | possessions | `rds` | `wnba_stats_possessions` | `wnba_possessions_2024.rds` | 0.43 MB | 41,429 | - | - | NEW |
| 2024 | possessions | `csv.gz` | `wnba_stats_possessions` | `wnba_possessions_2024.csv.gz` | 0.79 MB | 41,429 | - | - | NEW |
| 2024 | lineups | `parquet` | `wnba_stats_game_lineups` | `wnba_lineups_2024.parquet` | 0.12 MB | 88,832 | - | - | NEW |
| 2024 | lineups | `rds` | `wnba_stats_game_lineups` | `wnba_lineups_2024.rds` | 0.12 MB | 88,832 | - | - | NEW |
| 2024 | lineups | `csv.gz` | `wnba_stats_game_lineups` | `wnba_lineups_2024.csv.gz` | 0.27 MB | 88,832 | - | - | NEW |
| 2025 | schedule | `parquet` | `wnba_stats_schedules` | `wnba_schedule_2025.parquet` | 0.01 MB | 310 | - | - | NEW |
| 2025 | schedule | `rds` | `wnba_stats_schedules` | `wnba_schedule_2025.rds` | 0.01 MB | 310 | - | - | NEW |
| 2025 | schedule | `csv.gz` | `wnba_stats_schedules` | `wnba_schedule_2025.csv.gz` | 0.00 MB | 310 | - | - | NEW |
| 2025 | play_by_play | `parquet` | `wnba_stats_pbp` | `wnba_play_by_play_2025.parquet` | 2.39 MB | 126,330 | - | - | NEW |
| 2025 | play_by_play | `rds` | `wnba_stats_pbp` | `wnba_play_by_play_2025.rds` | 2.77 MB | 126,330 | - | - | NEW |
| 2025 | play_by_play | `csv.gz` | `wnba_stats_pbp` | `wnba_play_by_play_2025.csv.gz` | 3.52 MB | 126,330 | - | - | NEW |
| 2025 | possessions | `parquet` | `wnba_stats_possessions` | `wnba_possessions_2025.parquet` | 0.58 MB | 48,401 | - | - | NEW |
| 2025 | possessions | `rds` | `wnba_stats_possessions` | `wnba_possessions_2025.rds` | 0.50 MB | 48,401 | - | - | NEW |
| 2025 | possessions | `csv.gz` | `wnba_stats_possessions` | `wnba_possessions_2025.csv.gz` | 0.93 MB | 48,401 | - | - | NEW |
| 2025 | lineups | `parquet` | `wnba_stats_game_lineups` | `wnba_lineups_2025.parquet` | 0.14 MB | 99,114 | - | - | NEW |
| 2025 | lineups | `rds` | `wnba_stats_game_lineups` | `wnba_lineups_2025.rds` | 0.14 MB | 99,114 | - | - | NEW |
| 2025 | lineups | `csv.gz` | `wnba_stats_game_lineups` | `wnba_lineups_2025.csv.gz` | 0.30 MB | 99,114 | - | - | NEW |
| 2026 | schedule | `parquet` | `wnba_stats_schedules` | `wnba_schedule_2026.parquet` | 0.01 MB | 202 | - | - | NEW |
| 2026 | schedule | `rds` | `wnba_stats_schedules` | `wnba_schedule_2026.rds` | 0.00 MB | 202 | - | - | NEW |
| 2026 | schedule | `csv.gz` | `wnba_stats_schedules` | `wnba_schedule_2026.csv.gz` | 0.00 MB | 202 | - | - | NEW |
| 2026 | play_by_play | `parquet` | `wnba_stats_pbp` | `wnba_play_by_play_2026.parquet` | 1.70 MB | 86,784 | - | - | NEW |
| 2026 | play_by_play | `rds` | `wnba_stats_pbp` | `wnba_play_by_play_2026.rds` | 1.93 MB | 86,784 | - | - | NEW |
| 2026 | play_by_play | `csv.gz` | `wnba_stats_pbp` | `wnba_play_by_play_2026.csv.gz` | 2.42 MB | 86,784 | - | - | NEW |
| 2026 | possessions | `parquet` | `wnba_stats_possessions` | `wnba_possessions_2026.parquet` | 0.38 MB | 32,265 | - | - | NEW |
| 2026 | possessions | `rds` | `wnba_stats_possessions` | `wnba_possessions_2026.rds` | 0.37 MB | 32,265 | - | - | NEW |
| 2026 | possessions | `csv.gz` | `wnba_stats_possessions` | `wnba_possessions_2026.csv.gz` | 0.64 MB | 32,265 | - | - | NEW |
| 2026 | lineups | `parquet` | `wnba_stats_game_lineups` | `wnba_lineups_2026.parquet` | 0.13 MB | 83,720 | - | - | NEW |
| 2026 | lineups | `rds` | `wnba_stats_game_lineups` | `wnba_lineups_2026.rds` | 0.12 MB | 83,720 | - | - | NEW |
| 2026 | lineups | `csv.gz` | `wnba_stats_game_lineups` | `wnba_lineups_2026.csv.gz` | 0.26 MB | 83,720 | - | - | NEW |
