# `tests/fixtures/shots/` -- the masked three-point distance

Real captures, trimmed, in the raw-store layout `build_pbp` reads
(`playbyplayv3/{season}/{game_id}.json`). Used by
`tests/test_build.py::test_shots_*`.

stats.wnba.com `playbyplayv3` reports `shotDistance` 0 for every three whose
legacy distance `sqrt(xLegacy^2 + yLegacy^2) / 10` is under 23.5 ft. The cutoff
is a feed rule, not the three-point line: it is the same in every season. Every
other shot's `shotDistance` is exactly `floor(distance + 0.5)`. This was measured
over all 30 published `wnba_stats_shots` seasons (1997-2026, 2026-10-09):

- In every season, the largest located three at 0 is 23.48-23.50 ft.
- In every season, the smallest located three not at 0 is 23.50-23.51 ft and reads 24.

So before the 2013 line move most WNBA threes read 0 (6,931 of 7,840 in 2012). Since
the move, the 22-ft corner and much of the 22.15-ft arc read 0.

## `playbyplayv3/2025/1022500115.json`

2025 regular season. Sliced from
`wehoop-wnba-stats-raw/wnba_stats/json/playbyplayv3/2025/1022500115.json`
(request `http://nba.cloud/games/1022500115/playbyplay?Format=json`, captured
2025-07-05T22:10:29Z per its `meta.time`). `meta` and `game` are kept verbatim;
`actions` is cut to verbatim actions: all 30 threes at `shotDistance` 0 (corner
and above the break), the first 10 deeper threes, and the twos and non-shot
actions picked alongside them.

## `playbyplayv3/2000/1020000206.json`

2000 regular season, sliced from the same store (`playbyplayv3/2000/1020000206.json`,
captured 2025-02-17T17:56:41Z). It keeps all 19 threes and the first 6 twos. Of the
threes, 18 read 0: 4 are at legacy (0, 0), with no location, and 14 are located
at 21.4-23.3 ft. The remaining three reads 41 ft.

## `shotchartdetail_1022500115.json`

The ground truth for the 2025 slice: a live `stats.wnba.com/stats/shotchartdetail`
call (`GameID=1022500115`, `LeagueID=10`, `Season=2025`,
`SeasonType=Regular Season`, `ContextMeasure=FGA`, `TeamID=0`, `PlayerID=0`;
curl_cffi `impersonate="chrome"`, 2026-10-09), with `rowSet` cut to the field
goals in the pbp slice.

- `LOC_X`/`LOC_Y` equal `xLegacy`/`yLegacy` on all 129 of the game's field goals.
- `SHOT_DISTANCE` is `floor(distance)`.
- It reads 22-23 ft on the threes the play-by-play reports as 0.
