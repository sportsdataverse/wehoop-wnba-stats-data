# wehoop-wnba-stats-data Copilot Instructions

## Project Context

This repo is the R-side parser + uploader for the **WNBA Stats API**
(source: <https://stats.wnba.com/>). Per-season artifacts (PBP,
rosters, lineups, player and team season stats, standings, draft,
shots, per-game rosters, officials) are compiled by
`R/wnba_stats_*.R` and pushed to release tags on
`sportsdataverse/sportsdataverse-data` via `piggyback::pb_upload()`.

Package metadata (per `DESCRIPTION`):
- **Package**: `wehoop.wnbastats`
- **Version**: 0.0.1
- **License**: CC BY 4.0
- **R**: >= 4.0.0

Pipeline: `stats.wnba.com -> wehoop-wnba-stats-data [HERE] -> sportsdataverse-data releases -> wehoop`.

There is no `wehoop-wnba-stats-raw` -- the WNBA Stats API IS the raw
layer. The per-game JSON cache lives in this repo under
`wnba_stats/pbp/json/`, gated by the `RESCRAPE` flag.

## Repository Workflow

- Branch from `main`; `main` is the default and release branch.
- The CI entry point is `scripts/daily_wnba_stats_R_processor.sh -s <START> -e <END> -r <true|false>`.
- Annual draft runs separately via `scripts/annual_wnba_stats_draft_R_processor.sh`.
- The R scripts here are runnable Rscripts, **not** an installable R
  package, despite the `DESCRIPTION`. Treat `DESCRIPTION` as a
  dependency manifest for `devtools::install_deps()`.

## Build & Development Commands

`R/wnba_stats_*.R` scripts take **positional args**
(`<start_year> <end_year>`), not the `-s`/`-e` flag style used by the
sister ESPN parsers in `wehoop-wnba-data`.

```sh
# Daily orchestrator (CI entry point)
bash scripts/daily_wnba_stats_R_processor.sh -s 2025 -e 2025 -r false

# Annual draft (excluded from daily)
bash scripts/annual_wnba_stats_draft_R_processor.sh -s 2025 -e 2025

# Individual parsers (positional args)
Rscript R/wnba_stats_01_pbp.R                 2025 2025 false  # 3rd arg = RESCRAPE
Rscript R/wnba_stats_02_rosters.R             2025 2025
Rscript R/wnba_stats_03_player_season_stats.R 2025 2025
Rscript R/wnba_stats_04_lineups.R             2025 2025
Rscript R/wnba_stats_05_team_season_stats.R   2025 2025
Rscript R/wnba_stats_06_standings.R           2025 2025
Rscript R/wnba_stats_07_draft.R               2025 2025  # ANNUAL only
Rscript R/wnba_stats_08_shots.R               2025 2025
Rscript R/wnba_stats_09_game_rosters.R        2025 2025
Rscript R/wnba_stats_10_officials.R           2025 2025

# One-off helpers
Rscript R/0000_create_wehoop_releases_init.R    # Idempotent release creation
Rscript R/0001_push_existing_release_data.R     # Re-push everything on disk
```

`RESCRAPE=true` (default for `01_pbp.R`) re-fetches every game from
the API and overwrites `wnba_stats/pbp/json/`. `RESCRAPE=false` reads
the on-disk JSON when present and skips the API call for cached games.
The other parsers ignore `RESCRAPE`.

## Code Style

- **Library loading** uses `lib.loc = Sys.getenv("R_LIBS")` inside
  `suppressPackageStartupMessages(suppressMessages(...))`. CI exports
  `R_LIBS` to a project-local path; every script must respect it so
  it doesn't pick up a stale system library.
- **Proxy acquisition** is centralised in `R/utils.R::load_proxies()`
  (env vars first, then `../../proxylist.csv`, then unproxied). Every
  API call goes through `select_proxy(load_proxies())`.
- **Per-call `tryCatch`** with 3-attempt proxy rotation is mandatory
  for every WNBA Stats API request. A flake should cause a one-game
  miss, not a whole-season abort.
- **Output paths** all land under `wnba_stats/`. Local artifacts are
  rds + parquet (plus per-game JSON for PBP and player game logs).
  Release uploads go via `piggyback::pb_upload()` inside
  `insistent_save()` retry wrappers.
- **cli messaging**: `cli::cli_alert_*` for status, `cli::cli_progress_*`
  for per-season loops. Theme files in `themes/` set defaults.
- **Logging**: every parser tees output to
  `logs/wehoop_wnba_stats_*_logfile_<year>.log`. `.gitignore` ignores
  `*.log` globally and re-includes `logs/*.log`. The shell processors
  commit data and log as **separate commits** -- tee writes to `/tmp`
  during the work block so in-flight `git pull` calls don't collide.

## HTTP / Messaging Conventions

- Calls go through the upstream `wehoop` R package
  (`wehoop::wnba_pbp()`, `wehoop::wnba_commonteamroster()`, etc.) --
  never hand-roll a WNBA Stats API request in this repo.
- Fix WNBA Stats parsing bugs in `wehoop`, not here.
- `wnba_stats_01_pbp.R` relies on
  `wehoop::wnba_pbp(game_id, on_court = TRUE, version = "v3")` which
  already returns V2-shape rows with on-court lineups populated via
  `wnba_gamerotation`. Don't reintroduce the old
  substitution-tracking code path.

## Daily Umbrella Workflow

`.github/workflows/daily_wnba_stats.yml` invokes
`scripts/daily_wnba_stats_R_processor.sh` on a cron, looping seasons
through every per-dataset parser **except** `07_draft.R`. The draft
has annual cadence -- it runs separately on
`annual_wnba_stats_draft_R_processor.sh`.

- Two commits per season: the data update and the log update.
- Commit message format `WNBA Stats Data Update (Start: YYYY End: YYYY)`
  is **load-bearing** -- downstream tooling parses the year range. Do
  not reword.

## Cross-Repo References

- Upstream R SDK: <https://github.com/sportsdataverse/wehoop>
- Sister parser (ESPN side): <https://github.com/sportsdataverse/wehoop-wnba-data>
- Upload destination: <https://github.com/sportsdataverse/sportsdataverse-data>

## Conventional Commits

For code/CI changes, use `type(scope): description`. Common types:
`feat`, `fix`, `chore`, `ci`, `docs`, `refactor`. Use `type!:` or a
`BREAKING CHANGE:` footer for breaking changes. The processor commits
themselves use the load-bearing `WNBA Stats Data Update (Start: YYYY
End: YYYY)` format -- do not change it.

**Important**: Never include AI agents or assistants (Claude, Copilot,
Cursor, GPT, Gemini, etc.) as co-authors on commits. Omit all
`Co-Authored-By` trailers referencing AI tools.
