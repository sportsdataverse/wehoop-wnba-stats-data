# wehoop-wnba-stats-data Copilot Instructions

## Project Context

This R repo is the production pipeline for the WNBA Stats API
(`stats.wnba.com`). It calls `wehoop::wnba_*()` functions directly (with
proxy rotation), compiles per-season tidy tables, and uploads them as
releases on `sportsdataverse-data` via
`sportsdataversedata::sportsdataverse_save()`. The `wehoop` R package
loads from those releases. There is no raw cache repo
(`wehoop-wnba-stats-raw` is a placeholder) — the API is the raw layer.

Pipeline: `stats.wnba.com -> wehoop-wnba-stats-data [HERE] -> sportsdataverse-data -> wehoop`.

## Repository Workflow

- Branch from `main`; `main` is the default and release branch.
- CI entry point: `.github/workflows/daily_wnba_stats.yml` calls `scripts/daily_wnba_stats_R_processor.sh`. CI runs once a day at **08:00 UTC**, intentionally offset from the ESPN repo's 07:00 to avoid proxy-pool contention.
- Triggers: cron (four entries spanning the WNBA calendar), `repository_dispatch: daily_wnba_stats_data`, manual `workflow_dispatch` with `start_year`/`end_year` inputs.
- Defaults to `wehoop::most_recent_wnba_season()` when inputs are empty.
- Future scripts follow the `wnba_stats_NN_*.R` numeric-prefix convention.

## Build & Development Commands

```sh
bash scripts/daily_wnba_stats_R_processor.sh -s 2025 -e 2025
Rscript R/wnba_stats_01_pbp.R 2025 2025   # positional args, NOT -s/-e flags
```

## Code Style

- Follow the parent package's R style guide (tidyverse, snake_case, 2-space indent, `cli::cli_*` for messaging) — see `wehoop/CLAUDE.md`.
- Don't add per-endpoint parsing here — call into `wehoop::wnba_*()`.
- Keep `DESCRIPTION` Imports minimal.
- `sportsdataversedata::sportsdataverse_save()` is the only upload boundary — never call `piggyback` directly.
- Proxy list lives at `../../proxylist.csv` relative to the script CWD; the CI workflow writes it from the `WNBA_STATS_PROXY_LIST` secret.

## Cross-Repo References

- Conventions, WNBA Stats wrapper pattern, proxy plumbing, V3-vs-V2 notes: <https://github.com/sportsdataverse/wehoop/blob/main/CLAUDE.md>
- Placeholder raw repo: <https://github.com/sportsdataverse/wehoop-wnba-stats-raw>

## Conventional Commits

Use: `type(scope): description`. Common types: `feat`, `fix`, `docs`, `chore`, `ci`, `refactor`. Use `type!:` or a `BREAKING CHANGE:` footer for breaking changes.

**Important: Never include AI agents or assistants (e.g., Claude, Copilot, Cursor, GPT, Gemini) as co-authors on commits.** Omit all `Co-Authored-By` trailers referencing AI tools. This applies whether the change was generated, refactored, or reviewed with AI assistance — the human author is the sole attributable contributor.
