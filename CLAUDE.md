# CLAUDE.md -- wehoop-wnba-stats-data Development Guide

## Repo Overview

`wehoop-wnba-stats-data` is the R-side parser and uploader for **WNBA
Stats API** datasets (source: <https://stats.wnba.com/>). It compiles
per-season artifacts -- play-by-play, rosters, lineups, player and team
season stats, standings, draft, shots, per-game rosters, officials --
and pushes them as release assets to the
`sportsdataverse/sportsdataverse-data` GitHub releases via `piggyback`.
Downstream, the `wehoop` R package's `load_wnba_stats_*()` loaders read
from those release tags.

Package metadata (per `DESCRIPTION`):
- **Package**: `wehoop.wnbastats` (not the same name as the repo)
- **Version**: 0.0.1
- **License**: CC BY 4.0
- **R Requirement**: >= 4.0.0
- **URL**: <https://github.com/sportsdataverse/wehoop-wnba-stats-data>
- **Authors**: Saiem Gilani (cre), Geoffery Hutchinson (aut)

Sister repos in the women's basketball pipeline -- distinct sources:

| Repo                          | Source         | Role                              |
|-------------------------------|----------------|-----------------------------------|
| `wehoop-wnba-raw`             | ESPN WNBA      | Python scraper -> raw JSON cache  |
| `wehoop-wnba-data`            | ESPN WNBA      | R parser -> release uploader      |
| `wehoop-wnba-stats-data` [HERE] | WNBA Stats API | R parser + uploader (no raw cache) |
| `wehoop-wbb-raw`              | ESPN WBB       | Python scraper -> raw JSON cache  |
| `wehoop-wbb-data`             | ESPN WBB       | R parser -> release uploader      |

There is no `wehoop-wnba-stats-raw` -- the WNBA Stats API IS the raw
layer; this repo calls it directly via the `wehoop` R package and
caches per-game JSON locally under `wnba_stats/pbp/json/`.

## Pipeline Position

```
stats.wnba.com --[wehoop::wnba_*()] --> wehoop-wnba-stats-data [HERE]
                                              | piggyback upload
                                              v
                                        sportsdataverse-data releases
                                              | load_wnba_stats_*()
                                              v
                                          wehoop R package
```

Upload target: `sportsdataverse/sportsdataverse-data` release tags
created by `R/0000_create_wehoop_releases_init.R`:

- `wnba_stats_schedules`
- `wnba_stats_pbp`
- `wnba_stats_player_game_logs`
- `wnba_stats_rosters`
- `wnba_stats_player_season_stats`
- `wnba_stats_lineups`
- `wnba_stats_team_season_stats`
- `wnba_stats_standings`
- `wnba_stats_draft`
- `wnba_stats_shots`
- `wnba_stats_game_rosters`
- `wnba_stats_officials`
- `wnba_stats_coaches`
- `wnba_stats_team_boxscores`
- `wnba_stats_player_boxscores`

## Build & Development Commands

The daily entry point is `scripts/daily_wnba_stats_R_processor.sh`,
which loops over seasons and runs each per-dataset parser in order.
**Note**: `R/wnba_stats_*.R` scripts take POSITIONAL args
(`<start_year> <end_year>`), not the `-s`/`-e` flag style used by the
sister ESPN parsers in `wehoop-wnba-data`.

```sh
# Full daily flow for one or more seasons (CI entry point)
bash scripts/daily_wnba_stats_R_processor.sh -s 2025 -e 2025 -r false

# Annual draft (intentionally split out of the daily flow)
bash scripts/annual_wnba_stats_draft_R_processor.sh -s 2025 -e 2025

# Or call individual parsers directly when iterating
Rscript R/wnba_stats_01_pbp.R                 2025 2025 false  # 3rd arg = RESCRAPE
Rscript R/wnba_stats_02_rosters.R             2025 2025
Rscript R/wnba_stats_03_player_season_stats.R 2025 2025
Rscript R/wnba_stats_04_lineups.R             2025 2025
Rscript R/wnba_stats_05_team_season_stats.R   2025 2025
Rscript R/wnba_stats_06_standings.R           2025 2025
Rscript R/wnba_stats_07_draft.R               2025 2025  # ANNUAL cadence only
Rscript R/wnba_stats_08_shots.R               2025 2025
Rscript R/wnba_stats_09_game_rosters.R        2025 2025
Rscript R/wnba_stats_10_officials.R           2025 2025

# One-off: create / refresh the release tags on sportsdataverse-data
Rscript R/0000_create_wehoop_releases_init.R

# One-off: re-push every artifact already on disk to the release tags
Rscript R/0001_push_existing_release_data.R
```

`scripts/daily_wnba_stats_R_processor.sh -r` controls whether
`wnba_stats_01_pbp.R` re-fetches every game from the API (`true`,
default) or reads the per-game JSON cache under `wnba_stats/pbp/json/`
(`false`). The other scripts ignore `-r`.

## Project Structure

```
R/
  0000_create_wehoop_releases_init.R   # Idempotent release-tag creation on sportsdataverse-data
  0001_push_existing_release_data.R    # Re-uploads every artifact already on disk
  utils.R                              # load_proxies(), select_proxy(), rejoin_schedules()
  manifest_upload_helper.R             # Manifest helpers for piggyback uploads
  minify_json_folders.R                # JSON cache compaction helper
  wnba_stats_01_pbp.R                  # PBP + schedules + player game logs (V3 PBP)
  wnba_stats_02_rosters.R              # Team rosters (per season + per team)
  wnba_stats_03_player_season_stats.R  # Per-athlete season aggregates
  wnba_stats_04_lineups.R              # 5-man lineup stats
  wnba_stats_05_team_season_stats.R    # Per-team season aggregates
  wnba_stats_06_standings.R            # Per-season standings
  wnba_stats_07_draft.R                # Per-season draft results (annual cadence)
  wnba_stats_08_shots.R                # Shot-chart detail
  wnba_stats_09_game_rosters.R        # Per-game rosters (per-game iteration)
  wnba_stats_10_officials.R            # Per-game officials (per-game iteration)
scripts/
  daily_wnba_stats_R_processor.sh      # Daily orchestrator (loops seasons -> all parsers)
  annual_wnba_stats_draft_R_processor.sh  # Annual draft parser wrapper
wnba_stats/                            # Local artifact cache (committed; some subdirs piggyback-uploaded)
  coaches/, lineups/, player_season_stats/, rosters/, team_season_stats/
  pbp/json/                            # Per-game JSON cache, gated by RESCRAPE flag
logs/                                  # Tracked run logs (one per (script, season))
themes/                                # cli theme files used by scripts
.github/workflows/
  daily_wnba_stats.yml                 # In-repo cron entry point
DESCRIPTION                            # Package: wehoop.wnbastats
.Rbuildignore                          # Minimal -- this repo is not built as an R package
requirements.txt                       # Python deps (currently unused; kept for symmetry)
```

The R scripts here are not assembled into an installable R package
(despite the `DESCRIPTION`). They are runnable Rscripts that call
`wehoop::wnba_*()` and persist + upload the result. Treat
`DESCRIPTION` as a dependency manifest for `devtools::install_deps()`,
not as a CRAN-bound package definition.

## Conventions

- **Positional CLI args** for every `R/wnba_stats_*.R` script:
  `Rscript R/wnba_stats_NN_*.R <START> <END>` (and `<RESCRAPE>` for
  `01_pbp.R`). The sibling ESPN repos use `-s`/`-e` flags; do not port
  that style here without also updating the shell processors.
- **Library loading** uses plain `library(pkg)` inside
  `suppressPackageStartupMessages(suppressMessages(...))`, resolving
  against the full `.libPaths()`. (Earlier scripts pinned
  `lib.loc = Sys.getenv("R_LIBS")`, but the workflow installs deps via
  `setup-r-dependencies` into the default user library and never exports
  `R_LIBS`, so the pinned `lib.loc` resolved to `""` and every script
  halted -- matching the sibling `wehoop-wnba-data` espn parsers, which
  load plainly.)
- **Proxy acquisition** is centralised in `R/utils.R::load_proxies()`.
  Order of precedence:
  1. `PROXY_KEY` + `PROXY_PKG` env vars (CI default) -> fresh
     proxybonanza.com pull.
  2. Local `../../proxylist.csv` (gitignored; refresh weekly via
     `data.table::fwrite(get_proxy_bonanza_ips(), "proxylist.csv")`).
  3. `NULL` -> unproxied, rate-limited but functional.
  Each script calls `select_proxy(proxies)` per request so rotation is
  per-call.
- **Output paths** all land under `wnba_stats/`. Local artifacts are
  rds + parquet (plus per-game JSON for PBP and player game logs).
  Anything destined for `sportsdataverse-data` is also uploaded via
  `piggyback::pb_upload()` inside an `insistent_save()` retry wrapper.
- **Logging**: every parser tees its run output to
  `logs/wehoop_wnba_stats_*_logfile_<year>.log`. `.gitignore` ignores
  `*.log` globally and re-includes `logs/*.log` so tracked logs commit
  cleanly. The shell processors commit the data update and the log
  update as **separate commits** -- the tee writes to `/tmp` during
  the work block so the in-flight `git pull` calls don't collide with
  their own log output.
- **Cli messaging**: scripts use `cli::cli_alert_*` for status,
  `cli::cli_progress_*` for per-season loops. Theme files in `themes/`
  customise default cli styles.

## Daily Umbrella Workflow

`.github/workflows/daily_wnba_stats.yml` is the in-repo cron entry
point. It shells out to `scripts/daily_wnba_stats_R_processor.sh` and
captures one season per job invocation. Output is two commits per
season: the data update (`WNBA Stats Data Update (Start: YYYY End:
YYYY)`) and the log update (`WNBA Stats Data log update (...)`).

- **Cadence**: in-season cron at the WNBA window (April-October).
- **Draft is excluded** from the daily flow. `wnba_stats_07_draft.R`
  runs once a year via `scripts/annual_wnba_stats_draft_R_processor.sh`;
  including it daily would re-upload identical artifacts to the
  `wnba_stats_draft` release for no benefit.
- **Commit message format is load-bearing**. The downstream `wehoop`
  loader and any sportsdataverse triggers parse the
  `(Start: YYYY End: YYYY)` substring. Don't change the wording.

## Cross-Repo References

- Upstream R wrapper (the SDK this repo calls): <https://github.com/sportsdataverse/wehoop>
- ESPN-side WNBA parser (sister): <https://github.com/sportsdataverse/wehoop-wnba-data>
- Upload destination: <https://github.com/sportsdataverse/sportsdataverse-data>

## Project-Specific Gotchas

- The package name in `DESCRIPTION` is `wehoop.wnbastats`, not
  `wehoop-wnba-stats-data`. The repo name and package name diverge on
  purpose -- `wehoop.wnbastats` is the namespace string used inside R
  scripts and logs. Don't rename one without the other.
- `wnba_stats_01_pbp.R` leans on `wehoop::wnba_pbp(game_id, on_court =
  TRUE, version = "v3")` -- which already returns V2-shape rows with
  `home_player1..5` / `away_player1..5` populated via
  `wnba_gamerotation`. Don't reintroduce the old substitution-tracking
  logic this script used to carry; fix bugs in `wehoop` instead.
- `RESCRAPE` defaults to `true` for `wnba_stats_01_pbp.R`. Set it to
  `false` only when the local JSON cache at `wnba_stats/pbp/json/` is
  known-good and you're iterating on the parsing layer.
- WNBA Stats API rate-limits aggressively. Always run through
  `select_proxy(load_proxies())`; un-proxied calls work but choke on
  any sustained per-second volume.
- Per-call `tryCatch` and 3-attempt proxy rotation are mandatory for
  every API call. The retry block is the difference between a flake
  causing a one-game miss vs aborting a whole-season run.
- The downstream `wehoop` package's `load_wnba_stats_*()` loaders read
  release assets by `(release_tag, file_prefix, season)`. If you add
  a new dataset, both: (a) add a `create_release(...)` call in
  `R/0000_create_wehoop_releases_init.R`, and (b) coordinate a
  matching `load_wnba_stats_<name>()` row in `wehoop`'s release
  catalog.

## Commit Convention

Daily and annual processor commits follow a load-bearing format:

```
WNBA Stats Data Update (Start: 2025 End: 2025)
WNBA Stats Data log update (Start: 2025 End: 2025)
WNBA Stats Draft Update (Start: 2025 End: 2025)
WNBA Stats Draft log update (Start: 2025 End: 2025)
```

The `(Start: YYYY End: YYYY)` substring is parsed by downstream
tooling -- do not reword.

For code changes (parser tweaks, helper edits, workflow updates), use
[Conventional Commits](https://www.conventionalcommits.org/):

```
feat(pbp): add FT-to-foul attribution to wnba_stats_01_pbp.R
fix(proxy): handle empty port_http column in select_proxy()
chore(deps): bump wehoop pin in DESCRIPTION
ci: align cron window with WNBA in-season dates
```

Prefer scoped subjects. Split unrelated work into separate commits.

**Important**: Never include AI agents or assistants (Claude, Copilot,
Cursor, GPT, Gemini, etc.) as co-authors on commits. Omit all
`Co-Authored-By` trailers referencing AI tools. This applies whether
the change was generated, refactored, or reviewed with AI assistance --
the human author is the sole attributable contributor.
