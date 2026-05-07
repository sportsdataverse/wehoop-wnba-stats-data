# CLAUDE.md — wehoop-wnba-stats-data Development Guide

## Repo Overview

`wehoop-wnba-stats-data` is the R-side production pipeline for the WNBA
Stats API (`stats.wnba.com`). Unlike the ESPN-side data repos which read
from a per-sport `*-raw` JSON cache, this repo calls
`wehoop::wnba_*()` functions directly against `stats.wnba.com` (with
proxy rotation), compiles per-season tidy tables, and uploads them as
releases on `sportsdataverse/sportsdataverse-data` via
`piggyback` / `sportsdataversedata::sportsdataverse_save()`. The
`wehoop` R package then loads from those releases.

The CI workflow (`.github/workflows/daily_wnba_stats.yml`) was bootstrapped
recently — the orchestration here is newer than its ESPN siblings, and
the script roster is still expanding (PBP first; team box, player box,
rosters slated to follow).

## Pipeline Position

```
WNBA Stats API (stats.wnba.com)
    | direct call with proxy rotation (no intermediate raw cache)
    v
wehoop-wnba-stats-data [HERE] --[release upload]--> sportsdataverse-data
                                                          | piggyback
                                                          v
                                                    wehoop R package
```

## Build & Development Commands

```sh
# Full daily flow for one or more seasons (CI entry point)
bash scripts/daily_wnba_stats_R_processor.sh -s 2025 -e 2025

# Individual creation script
Rscript R/wnba_stats_01_pbp.R 2025 2025
```

The CI workflow runs once a day at **08:00 UTC**, intentionally offset one
hour from the ESPN-side `daily_wnba.yml` (07:00 UTC) so the two jobs do
not contend for the same proxy pool.

Triggers:

- Cron — four entries cover the WNBA calendar (Oct 18-31, Nov-Dec, Jan-Jun, Jul 1-12).
- `repository_dispatch` event-type **`daily_wnba_stats_data`**.
- Manual `workflow_dispatch` with `start_year` / `end_year` inputs:
  `gh workflow run daily_wnba_stats.yml -f start_year=2024 -f end_year=2024`.

When inputs are omitted, both default to `wehoop::most_recent_wnba_season()`.

## Project Structure

```
R/
  0000_create_wehoop_releases_init.R   # One-shot release-tag bootstrapper
  0001_push_existing_release_data.R    # Backfill helper
  utils.R                              # Shared helpers
  wnba_stats_00_proxy.R                # Proxy-list loader / rotation helper
  wnba_stats_01_pbp.R                  # Per-season PBP compile + upload (positional CLI args: <START> <END>)
  minify_json_folders.R                # JSON minifier (carried from sibling repos)
scripts/
  daily_wnba_stats_R_processor.sh      # CI entry point — loops seasons, commits, pushes
.github/workflows/
  daily_wnba_stats.yml                 # Scheduled + dispatch + manual triggers
DESCRIPTION                            # R deps (uses wehoop, sportsdataversedata, piggyback)
requirements.txt                       # Python deps (helpers if used)
wnba_stats/                            # Committed local artifacts (output staging)
```

Future R generation scripts are intended to follow the existing numeric
prefix scheme: `wnba_stats_02_rosters.R`, `wnba_stats_03_team_box.R`,
`wnba_stats_04_player_box.R`, etc. (See the commented-out lines in
`scripts/daily_wnba_stats_R_processor.sh`.)

## Cross-Repo References

- Shared coding conventions, WNBA Stats wrapper pattern, proxy plumbing, V3-vs-V2 notes, error reporting: <https://github.com/sportsdataverse/wehoop/blob/main/CLAUDE.md>
- Placeholder sibling raw repo: <https://github.com/sportsdataverse/wehoop-wnba-stats-raw>
- ESPN-side production sibling: <https://github.com/sportsdataverse/wehoop-wnba-data>

The actual WNBA Stats API wrappers live in `wehoop` (`R/wnba_stats_*.R`).
The R scripts here are thin compile-and-upload wrappers; bug fixes to per-
endpoint parsing belong in `wehoop`.

## Project-Specific Gotchas

- The R generation scripts read a proxy list from **`../../proxylist.csv`** (relative to the script's CWD). The CI workflow writes that file at job start from the `WNBA_STATS_PROXY_LIST` GitHub Actions secret (CSV body with columns `ip,port,login,password`). For local runs, you must seed the same path or stub the proxy step.
- `wnba_stats_01_pbp.R` takes positional CLI arguments (`<START> <END>`) — it does NOT use the `optparse` `-s`/`-e` flags that the ESPN-side scripts use. The wrapping shell script calls it as `Rscript R/wnba_stats_01_pbp.R "$YEAR" "$YEAR"`.
- The 08:00-UTC cron is intentionally offset from the ESPN repo's 07:00-UTC schedule to avoid proxy-pool contention. Don't realign them without coordination.
- `WNBA_STATS_PROXY_LIST` is the only secret that strictly needs to exist on the repo for live runs to succeed — without it, the R scripts will read an empty / missing file and the WNBA Stats API will throttle / block.
- This repo runs on `ubuntu-latest` (the ESPN-side data repos run on `windows-latest`).

## Commit Convention

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(stats): add wnba_stats_02_rosters.R generation script
fix(proxy): handle empty proxylist.csv without aborting the run
ci(daily): widen cron window to cover preseason
chore: bump piggyback retry budget
```

Prefer scoped subjects. Use `type!:` or a `BREAKING CHANGE:` footer for
breaking changes. Split unrelated work into separate commits.

**Important: Never include AI agents or assistants (e.g., Claude, Copilot, Cursor, GPT, Gemini) as co-authors on commits.** Omit all `Co-Authored-By` trailers referencing AI tools. This applies whether the change was generated, refactored, or reviewed with AI assistance — the human author is the sole attributable contributor.
