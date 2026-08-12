# wehoop-wnba-stats-data Copilot Instructions

## Project Context

This repo is the parser + uploader for the **WNBA Stats API**
(source: <https://stats.wnba.com/>). Per-season artifacts (PBP,
rosters, lineups, player and team season stats, standings, draft,
shots, per-game rosters, officials) are compiled and pushed to release
tags on `sportsdataverse/sportsdataverse-data`.

Pipeline: `stats.wnba.com -> wehoop-wnba-stats-raw -> wehoop-wnba-stats-data [HERE] -> sportsdataverse-data releases -> wehoop`.

> **The producer is Python: `python/wnba_data_build/`.** It reads the unified
> raw store in the sibling **`wehoop-wnba-stats-raw`** repo
> (`wnba_stats/json/{endpoint}/{season}/`, a full 1997–2026 capture) and
> publishes with `python -m wnba_data_build --publish`.
>
> **The R stage scripts no longer exist.** `R/wnba_stats_01_pbp.R` …
> `R/wnba_stats_10_officials.R`, `scripts/daily_wnba_stats_R_processor.sh` and
> `scripts/annual_wnba_stats_draft_R_processor.sh` were all removed when the
> Python producer took over; this file described them long after. `R/` now
> holds three helpers only (`utils.R`, `manifest_upload_helper.R`,
> `minify_json_folders.R`) and `DESCRIPTION` is a vestigial dependency
> manifest. Do not reintroduce an R scrape path here.

`python/wnba_model_publish/` is the separate model-publish CLI
(`wnba_models.yml`, dispatch-only, `dry_run` default true) — see the model
registry in the README.

## Repository Workflow

- Branch from `main`; `main` is the default and release branch.
- The CI entry point is `.github/workflows/daily_wnba_stats.yml`, which calls
  `scripts/daily_wnba_stats_python_processor.sh -s <START> -e <END>`.
- Annual draft runs separately on `.github/workflows/annual_wnba_stats_draft.yml`.
- **Seasons are calendar years** (no October rollover — the WNBA convention,
  unlike the NBA sibling's end-year span). The daily workflow derives the
  default window from `date -u +%Y`.
- This repo does not scrape. Capture belongs to `wehoop-wnba-stats-raw`; if a
  season is missing here, check the raw store first.

## Build & Development Commands

```sh
# Daily flow (droplet / local entry point; the workflow calls this same script)
bash scripts/daily_wnba_stats_python_processor.sh -s 2025 -e 2025

# Direct invocation
python -m wnba_data_build --root <path-to-wehoop-wnba-stats-raw> \
    --seasons 2025 --out wnba_stats --publish

# Backfill a leaguedash season range (checkpointed; .done_<season> on rc 0 only)
bash scripts/leaguedash_backfill.sh

# Program V v3 backfill -> v3_staging/ (resumable; verify with the section-9.3 gate)
bash scripts/run_v3_backfill.sh -s 1997 -e 2026
python -m wnba_data_build.v3_gate -s 1997 -e 2026

# D26d cutover: staged v3 -> production release tags. DRY RUN unless -x is passed.
bash scripts/run_v3_cutover.sh -s 1997 -e 2026        # writes logs/v3_cutover_manifest_*.md
bash scripts/run_v3_cutover.sh -s 1997 -e 2026 -x     # PUBLISH (destructive; read the manifest)
bash scripts/run_v3_cutover.sh -R -x                  # SEPARATE step: retire the _v3 tags
bash scripts/run_v3_cutover.sh -L -x                  # SEPARATE step: retire the LEGACY assets

# One-off helpers (already run; kept for reference)
Rscript ops/init/0000_create_wehoop_releases_init.R    # Idempotent release creation
Rscript ops/init/0001_push_existing_release_data.R     # Re-push everything on disk
```

Omit `--publish` for a local build with no release upload — that is the
dry-run equivalent, and the right default while iterating.

`scripts/run_v3_cutover.sh` (`python -m wnba_data_build.v3_cutover`) publishes the
staged `v3_staging/` parquets onto the production release tags. It re-runs the
§9.3 gate and hard-aborts on any unexplained `DIFF` (explained cases are
allowlisted one at a time with `--allow-diff SEASON:FAMILY` and echoed into the
manifest — there is no blanket ignore switch). It writes a REPLACE MANIFEST
naming every asset it would overwrite, with the current remote size and
updated-at, before touching anything. Uploads are per-file with a post-upload
size verification and stop on the first mismatch; verified uploads are recorded
in `v3_staging/.cutover_receipts.json` so a re-run is idempotent. Operator-run,
not workflow-wired.

Every artifact publishes in **three formats** — `parquet` + `rds` + `csv.gz`,
derived from the staged parquet by `wnba_data_build/v3_formats.py`.
`wehoop::load_wnba_*()` reads the `.rds`, which is written by
`sportsdataverse._rds.write_rds` (no R) and verified by reading it back before
upload. The publish is **additive**: the `wnba_`-prefixed assets land beside the
legacy ones, so an all-`NEW` manifest is expected, the manifest carries a
**SEASON-LABEL COLLISION** section pairing the two names covering each season,
and each touched tag gets a generated `README.md`. The v3 per-game lineups go to
`wnba_stats_game_lineups`, leaving the season-level `wnba_stats_lineups` dataset
untouched. Retiring the `_v3` tags (`-R`) and retiring the legacy assets (`-L`,
which refuses any season whose replacement is not verified in every format) are
separate invocations, never bundled with the data upload or with each other.

## Code Style

- **polars 1.x modern API only**; snake_case; typed new modules. Read the
  raw store, reshape, write — no HTTP in this repo.
- **Output paths** all land under `wnba_stats/`. Local artifacts are
  parquet + rds + csv; the rds is written natively by the sdv-py writer
  (there is no `serialize_rds.R` shim — that pattern is retired
  ecosystem-wide).
- **Exit codes must survive `tee`.** The driver pipes each season through
  `tee` and recovers the real status from `PIPESTATUS[0]`; a trailing `echo`
  inside the pipeline masked a failing build and reported every season green
  (the same bug was fixed in the NBA sibling). Don't reintroduce a trailing
  command after the build inside a teed subshell.
- **Logging**: the driver tees to
  `logs/wehoop_wnba_stats_python_logfile_<year>.log`. `.gitignore` ignores
  `*.log` globally but re-includes `logs/*.log`, so that path is trackable —
  the committed logs there are R-era leftovers; the Python driver writes them
  and commits only `wnba_stats/`.

## HTTP / Messaging Conventions

- **This repo makes no WNBA Stats API calls.** Capture lives in
  `wehoop-wnba-stats-raw`, whose scrape layer is the shared
  `sportsdataverse.scrape.stats` engine (TLS-impersonating `curl_cffi`
  transport — `stats.wnba.com` silently stalls on plain `requests`).
- Fix WNBA Stats *parsing* bugs in `sportsdataverse-py`, and *capture* bugs
  in the shared engine, not here.

## Daily Umbrella Workflow

`.github/workflows/daily_wnba_stats.yml` invokes
`scripts/daily_wnba_stats_python_processor.sh` on a cron, looping seasons
through `python -m wnba_data_build --publish`. The draft has annual cadence
and runs separately on `.github/workflows/annual_wnba_stats_draft.yml`.

- One commit per season (`git add wnba_stats/`). The R processors made a
  second log commit; the Python driver does not.
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
