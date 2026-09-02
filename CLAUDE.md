# CLAUDE.md — wehoop-wnba-stats-data

Parser + release uploader for the **WNBA Stats API** (`stats.wnba.com`, the
official NBA-Stats-style tracking/advanced endpoints — distinct upstream from
the ESPN-sourced `wehoop-wnba-data`). Compiles per-season artifacts and
uploads them to `sportsdataverse-data` release tags that `wehoop`'s
`load_wnba_stats_*()` loaders read.

> **Producer is Python (`python/wnba_data_build/`); this repo does not scrape.**
> Capture lives in the sibling **`wehoop-wnba-stats-raw`**, which holds a full
> 1997–2026 raw store (`wnba_stats/json/{endpoint}/{season}/`). Two claims that
> were true once and are now false: that this is "the R-side parser", and that
> the raw sibling "ships no scraper".
>
> **The R stage scripts and both R processors were deleted** when the Python
> producer took over — `R/wnba_stats_01_pbp.R` … `10_officials.R`,
> `scripts/daily_wnba_stats_R_processor.sh`,
> `scripts/annual_wnba_stats_draft_R_processor.sh`. `R/` retains three helpers
> (`utils.R`, `manifest_upload_helper.R`, `minify_json_folders.R`).

`DESCRIPTION`: package `wehoop.wnbastats` (≠ repo name; namespace string used in
logs — don't rename one without the other), CC BY 4.0. Vestigial: not a CRAN
package and no longer an R pipeline; treat it as a dependency manifest for the
remaining helpers.

## Commands
```sh
bash scripts/daily_wnba_stats_python_processor.sh -s 2025 -e 2025   # daily entry
python -m wnba_data_build --root <wehoop-wnba-stats-raw> \
    --seasons 2025 --out wnba_stats --publish                       # direct
python -m wnba_data_build --root <...> --seasons 2025 --out wnba_stats
                                                     # omit --publish = dry run
bash scripts/leaguedash_backfill.sh                  # league-dash cube, BUILD-ONLY
bash scripts/leaguedash_backfill.sh -s 2026 -e 2026 -n   # ...plan uploads, upload nothing
python -m wnba_data_build.leaguedash_cli --seasons 2026 --publish   # publish (deliberate)
bash scripts/backfill_historical_seasons.sh          # raw-backed families, all seasons
bash scripts/run_v3_backfill.sh -s 1997 -e 2026      # Program V v3 backfill (resumable)
bash scripts/run_v3_cutover.sh -s 1997 -e 2026       # D26d cutover -- DRY RUN by default
python -m wnba_data_build.manifest check              # do the tags' manifests match their assets?
python -m wnba_data_build.manifest build --tags wnba_stats_shots --publish  # refresh one
Rscript ops/init/0000_create_wehoop_releases_init.R  # one-off: create release tags
Rscript ops/init/0001_push_existing_release_data.R   # one-off: re-push on-disk artifacts
```
Seasons are **calendar years** here (no October rollover — the NBA sibling's
end-year span convention does not apply).

**Backfill scripts build; they do not publish.** `leaguedash_backfill.sh` and
`backfill_historical_seasons.sh` both write under `build_out/` and have **no
upload path at all** -- `leaguedash_backfill.sh` rejects `-p` with exit 2, and
`-n` plans a publish without uploading. Publishing is a deliberate, separate
invocation of the builder module with `--publish`. `leaguedash_backfill.sh` previously passed `--publish`
unconditionally, leaving a live release one stray invocation away from a
rewrite — the same hazard as the R creation stages that overwrote three WNBA
2025 tags.

**Uploading season assets does NOT refresh the tag's manifest.** Each tag carries
a `<tag>_in_data_repo.csv` (`season`, `row_count`, `generated_at_utc`,
`source_endpoint`) that `wehoop::load_wnba_stats_*_manifest()` reads to discover
which seasons are published. It was written by the R chain
(`R/manifest_upload_helper.R`); `publish.upload_artifacts` — what every Python
build and backfill goes through — never carried that step over. On 2026-08-13
that gap was found holding seven tags' full history behind a **one-row** manifest
dated 2026-05-30, understating coverage by up to 29 seasons.

Publishing stays upload-only, so the manifest is a **separate deliberate
invocation** of `wnba_data_build.manifest build --publish`. What is automatic is
the *detection*: both CLIs run the read-only `check_tags()` after uploading and
**exit 1** when a tag's asset seasons and its manifest disagree. Rows are derived
from what is actually on the tag (asset list + each parquet's footer + GitHub's
`updatedAt`), never from a local build dir, and `source_endpoint` is inherited
verbatim from the published manifest so a rebuild never invents provenance.

**Era floors live in the registry, not in a runbook.** A dataset whose upstream
coverage starts late carries `first_season` in `datasets.py` (today: `officials`
= 2004), and the CLI refuses earlier seasons. This exists because those seasons
build a *valid* 3-6 row frame that looks like a season and is not one — the
failure mode a "just don't build it" note in a doc does not prevent.

`scripts/run_v3_cutover.sh` (`python -m wnba_data_build.v3_cutover`) is the
Program V (design §9, D26d) cutover publisher: it moves the staged `v3_staging/`
parquets onto the **production** release tags. **It is a dry run by default** —
it re-runs the §9.3 gate, writes a REPLACE MANIFEST into `logs/`, and uploads
nothing. Publishing needs an explicit `-x` (`--execute`), which is the least
reversible action in the program: overwriting a release asset destroys the
previous bytes and `wehoop::load_wnba_*()` reads them.

```sh
bash scripts/run_v3_cutover.sh -s 1997 -e 2026            # dry run; prints its own tail -f
bash scripts/run_v3_cutover.sh -s 1997 -e 2026 -- --allow-diff 1999:play_by_play
bash scripts/run_v3_cutover.sh -s 1997 -e 2026 -x         # PUBLISH (after reading the manifest)
bash scripts/run_v3_cutover.sh -R -x                      # SEPARATE step: retire the _v3 tags
bash scripts/run_v3_cutover.sh -L -x                      # SEPARATE step: retire the LEGACY assets
```

**Three formats, always.** Every artifact publishes as `parquet` + `rds` +
`csv.gz` (`wnba_data_build/v3_formats.py`). `wehoop::load_wnba_*()` reads the
`.rds`, so a parquet-only publish ships data wehoop cannot open; the rds comes
from `sportsdataverse._rds.write_rds` (byte-parity, no R / no `Rscript`) and is
**verified by reading it back** — shape, column names, and per-column R vector
type against the source parquet — before it can be uploaded. The csv is gzipped
per the `ncaa-wbb-hoops-data` convention (GitHub's 2 GiB per-asset limit).

**The publish is ADDITIVE (decision B).** The `wnba_`-prefixed assets land *next
to* the legacy ones rather than replacing them, so an all-`NEW` / 0-`REPLACE`
manifest is the intended outcome, not a defect. The manifest's **SEASON-LABEL
COLLISION** section enumerates, per tag, each new asset and the legacy asset
covering the same season (here both carry the same number — `legacy_offset=0` —
so the hazard is "which is authoritative", not "which year"; the NBA sibling's
legacy names are START-year and really do disagree). A generated per-tag
`README.md` is uploaded on `-x` to say so. `-L` (`--retire-legacy-assets`)
removes the legacy names once consumers have migrated; it refuses any season
whose replacement is not present and byte-verified on the tag **in every
format**, and is never bundled with an upload or with `-R`.

**The v3 per-game lineups publish to `wnba_stats_game_lineups`** (decision 3),
not `wnba_stats_lineups` — the latter carries the season-level
`leaguedashlineups` dataset from stage 04, a different dataset rather than an
older version, and is left untouched.

Read the manifest's **WOULD BE DESTROYED** and **SURVIVES UN-REPLACED** sections
before ever passing `-x`. The gate hard-aborts on any unexplained `DIFF`; each
explained case needs its own `--allow-diff SEASON:FAMILY`, which is echoed into
the manifest — there is no blanket ignore switch. Uploads run one asset at a time
with a size re-check after each and stop on the first mismatch (`gh release
upload` with many files has silently dropped large assets). Verified uploads land
in `v3_staging/.cutover_receipts.json`, so a re-run skips them: resumable and
idempotent. Operator-run, not workflow-wired.

## Inputs / Outputs
- Artifacts land under `wnba_stats/` as rds + parquet (plus per-game JSON for PBP /
  player game logs). Anything destined for releases is uploaded via
  `piggyback::pb_upload()` wrapped in `insistent_save()` (`purrr::insistently`).
- 17 release tags on `sportsdataverse/sportsdataverse-data` (created by
  `ops/init/0000_create_wehoop_releases_init.R`): `wnba_stats_{schedules,pbp,player_game_logs,rosters,player_season_stats,lineups,team_season_stats,standings,draft,shots,game_rosters,officials,coaches,team_boxscores,player_boxscores,possessions,game_lineups}`.
  The last two are the Program V (D26d) cutover targets. **`run_v3_cutover.sh -x`
  uploads but never creates a tag** — `gh release upload` fails on a missing
  release, so run the init script first whenever the cutover gains a new target.

## Gotchas — stats.wnba.com handling (the non-obvious part)
- **Headers are load-bearing** and live in `wehoop` (`R/utils_wnba_stats.R`,
  `request_with_proxy`): `Host: stats.wnba.com`, a desktop-Chrome `User-Agent`,
  `x-nba-stats-origin: stats`, `x-nba-stats-token: true`, `Origin: https://stats.wnba.com`,
  `Referer: https://www.wnba.com/`. Un-proxied/header-less calls time out. `pad_id()`
  (zero-pad game IDs to 10) + `LeagueID="10"` are mandatory before any call.
- **Proxies** via `R/utils.R::load_proxies()`, precedence: (1) `PROXY_KEY`+`PROXY_PKG`
  env → fresh proxybonanza.com pull (CI default); (2) gitignored `../../proxylist.csv`;
  (3) `NULL` → un-proxied, rate-limited but functional. `select_proxy(proxies)` is called
  **per request** and returns a plain list keyed for `httr2::req_proxy()` (NOT an
  `httr::use_proxy()` object — wehoop 3.0.0 splats it as named args). Per-call `tryCatch`
  + 3-attempt rotation is mandatory.
- **Rate limiting** is a trailing-window token bucket in `R/utils.R::rate_limit()`,
  tuned by env (defaults): `STATS_RATE_MAX=250` reqs / `STATS_RATE_WINDOW=600` s, each
  PBP game budgeted as `STATS_RATE_HITS=3` hits (set in the workflow). The limiter state
  is single-process — **keep the PBP fetch loop sequential; never wrap it in furrr/future_map**
  (parallel workers blow the shared budget).
- `wnba_stats_01_pbp.R` relies on `wehoop::wnba_pbp(game_id, on_court=TRUE, version="v3")`
  already populating `home_player1..5`/`away_player1..5` via `wnba_gamerotation` — fix PBP
  bugs in `wehoop`, don't reintroduce old substitution-tracking here. WNBA time math:
  10-min quarters, 2400s regulation (do not copy NBA constants).
- Library loads are plain `library(pkg)` inside `suppressPackageStartupMessages(suppressMessages(...))`
  — do NOT pin `lib.loc = Sys.getenv("R_LIBS")` (CI never exports `R_LIBS`, so it halts every script).

## Model publish — `python/wnba_model_publish`

Builds + uploads the per-season **`wnba_player_impact`** tables (RAPM /
adj-RAPM / SPM / BPM / DARKO / WAR; one row per player-season-season_type,
Regular Season + Playoffs) from WNBA possessions compiled off the committed
`wehoop-wnba-stats-raw` store, via the league-agnostic `sportsdataverse.nba`
model zoo. Runs from the repo root (the root uv project installs
`wnba_model_publish` from `python/`):

```sh
# Plan only -- builds locally, uploads nothing:
uv run python -m wnba_model_publish impact \
  --seasons 2026 --out out/wnba_player_impact \
  --raw-store-dir "$SDV_PY_WNBA_RAW_JSON_DIR" --dry-run

# Re-upload an already-built directory (no recompute):
uv run python -m wnba_model_publish upload \
  --dir out/wnba_player_impact --tag wnba_player_impact --dry-run

# The SCHEDULED path (droplet cron `30 10 * 5-10 *` ET, after the 09:00 stats-raw
# refresh): current season only, local raw store, PROXY_* lifted from ~/.Renviron.
bash scripts/nightly_wnba_impact.sh            # defaults to the current season
bash scripts/nightly_wnba_impact.sh 2026 --dry-run
```

**Dry-run discipline:** there is no `--publish` flag — publishing is the
*default*; `--dry-run` is the opt-out that plans the uploads without touching
the release. Always run `--dry-run` first and inspect the plan, then rerun
the identical command without it. Seasons build earliest-to-latest so
multi-season priors (adj-RAPM / DARKO) flow forward — for a single-season
refresh pass a few trailing seasons (e.g. `2021:2026`).

Scheduled runs live on the DROPLET, not in CI: `scripts/nightly_wnba_impact.sh`
(cron `30 10 * 5-10 *` ET) builds the current season off the local raw store,
lifting `PROXY_*` from `~/.Renviron` — which cron does not load and only R reads.
That placement is forced by the same caveat that keeps CI dispatch-only: the
player-variant leaguegamelog call still goes live, and stats.wnba.com HANGS
(never errors) on datacenter IPs. `.github/workflows/wnba_models.yml` stays
workflow_dispatch-only with `dry_run` defaulting **true**, for backfills run
from a residential IP.

| Model | Artifact | Release tag | Training data | Fitting script | Cadence |
|---|---|---|---|---|---|
| `wnba_player_impact` (RAPM/adj-RAPM/SPM/BPM/DARKO/WAR) | `wnba_player_impact_{season}.parquet` + `*_card.json` | `wnba_player_impact` on `sportsdataverse-data` | 1997–2026 possessions + box logs (stats.wnba.com via the raw store) | `python/wnba_model_publish/builders.py` (`build_wnba_player_impact`) | nightly (droplet cron, current season); `wnba_models.yml` dispatch for backfills |

## Workflows & commits
- `.github/workflows/daily_wnba_stats.yml` — cron over the WNBA window (`0 14 * 5-9 *`
  + `0 14 1-20 10 *`), one season per run, shells to the daily processor. It has **no
  checkout of the raw store** and reads each JSON file over HTTP from
  `WEHOOP_WNBA_STATS_RAW_ROOT`; 14:00 UTC = 10:00 ET puts it after the droplet's
  09:00 ET stats-raw refresh (the old 07:00 UTC slot compiled yesterday's capture). Draft is **excluded**
  (annual `0 8 15 4 *` / `16` in `annual_wnba_stats_draft.yml`; draft endpoint defaults to
  `most_recent_wnba_season() - 1` since `Season=current` returns 0 rows). Auth via `SDV_GH_TOKEN`.
- Each parser tees output to `logs/wehoop_wnba_stats_*_logfile_<year>.log`; the processor emits
  **two separate commits per season** (data update, then log update). The
  `(Start: YYYY End: YYYY)` subject substring is **load-bearing** for downstream year parsing — do not reword.
- Code-change commits use Conventional Commits (`feat(pbp):`, `fix(proxy):`, `ci:`).
- **Never add AI co-author / `Co-Authored-By` trailers to commits.**

Upstream SDK: <https://github.com/sportsdataverse/wehoop> · ESPN sister: `wehoop-wnba-data` · upload target: `sportsdataverse-data`.

## Datasets

<!-- BEGIN GENERATED: datasets -->
| Script | Dataset | Release tag | Last published |
|---|---|---|---|
| [`python/wnba_stats_01_standings_creation.py`](python/wnba_stats_01_standings_creation.py) | [`standings`](docs/datasets/standings.md) | [`wnba_stats_standings`](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/wnba_stats_standings) | 2026-07-29 |
| [`python/wnba_stats_02_player_season_stats_creation.py`](python/wnba_stats_02_player_season_stats_creation.py) | [`player_season_stats`](docs/datasets/player_season_stats.md) | [`wnba_stats_player_season_stats`](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/wnba_stats_player_season_stats) | 2026-07-29 |
| [`python/wnba_stats_03_team_season_stats_creation.py`](python/wnba_stats_03_team_season_stats_creation.py) | [`team_season_stats`](docs/datasets/team_season_stats.md) | [`wnba_stats_team_season_stats`](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/wnba_stats_team_season_stats) | 2026-07-29 |
| [`python/wnba_stats_04_lineups_creation.py`](python/wnba_stats_04_lineups_creation.py) | [`lineups`](docs/datasets/lineups.md) | [`wnba_stats_lineups`](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/wnba_stats_lineups) | 2026-07-29 |
| [`python/wnba_stats_05_rosters_creation.py`](python/wnba_stats_05_rosters_creation.py) | [`rosters`](docs/datasets/rosters.md) | [`wnba_stats_rosters`](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/wnba_stats_rosters) | 2026-07-29 |
| [`python/wnba_stats_06_coaches_creation.py`](python/wnba_stats_06_coaches_creation.py) | [`coaches`](docs/datasets/coaches.md) | [`wnba_stats_coaches`](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/wnba_stats_coaches) | 2026-07-29 |
| [`python/wnba_stats_07_draft_creation.py`](python/wnba_stats_07_draft_creation.py) | [`draft`](docs/datasets/draft.md) | [`wnba_stats_draft`](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/wnba_stats_draft) | 2026-08-12 |
| [`python/wnba_stats_08_schedules_creation.py`](python/wnba_stats_08_schedules_creation.py) | [`schedules`](docs/datasets/schedules.md) | [`wnba_stats_schedules`](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/wnba_stats_schedules) | 2026-08-12 |
| [`python/wnba_stats_09_player_game_logs_creation.py`](python/wnba_stats_09_player_game_logs_creation.py) | [`player_game_logs`](docs/datasets/player_game_logs.md) | [`wnba_stats_player_game_logs`](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/wnba_stats_player_game_logs) | 2026-07-29 |
| [`python/wnba_stats_10_pbp_creation.py`](python/wnba_stats_10_pbp_creation.py) | [`pbp`](docs/datasets/pbp.md) | [`wnba_stats_pbp`](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/wnba_stats_pbp) | 2026-08-12 |
| [`python/wnba_stats_11_game_rosters_creation.py`](python/wnba_stats_11_game_rosters_creation.py) | [`game_rosters`](docs/datasets/game_rosters.md) | [`wnba_stats_game_rosters`](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/wnba_stats_game_rosters) | 2026-07-29 |
| [`python/wnba_stats_12_officials_creation.py`](python/wnba_stats_12_officials_creation.py) | [`officials`](docs/datasets/officials.md) | [`wnba_stats_officials`](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/wnba_stats_officials) | 2026-07-29 |
| [`python/wnba_stats_13_player_boxscores_creation.py`](python/wnba_stats_13_player_boxscores_creation.py) | [`player_boxscores`](docs/datasets/player_boxscores.md) | [`wnba_stats_player_boxscores`](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/wnba_stats_player_boxscores) | 2026-07-29 |
| [`python/wnba_stats_14_team_boxscores_creation.py`](python/wnba_stats_14_team_boxscores_creation.py) | [`team_boxscores`](docs/datasets/team_boxscores.md) | [`wnba_stats_team_boxscores`](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/wnba_stats_team_boxscores) | 2026-07-29 |
| [`python/wnba_stats_15_shots_creation.py`](python/wnba_stats_15_shots_creation.py) | [`shots`](docs/datasets/shots.md) | [`wnba_stats_shots`](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/wnba_stats_shots) | 2026-07-29 |
| [`python/wnba_stats_99_schedule_master_creation.py`](python/wnba_stats_99_schedule_master_creation.py) | [`schedule_master`](docs/datasets/schedule_master.md) | `wnba_stats/wnba_stats_schedule_master.parquet` (committed) | — |
| [`python/wnba_stats_99_schedule_master_creation.py`](python/wnba_stats_99_schedule_master_creation.py) | [`games_in_data_repo`](docs/datasets/games_in_data_repo.md) | `wnba_stats/wnba_stats_games_in_data_repo.parquet` (committed) | — |
<!-- END GENERATED: datasets -->
