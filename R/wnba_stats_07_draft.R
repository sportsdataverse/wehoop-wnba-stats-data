## ----------------------------------------------------------------------------
## wnba_stats_07_draft.R
##
## Compile per-season WNBA Stats API draft history and upload to release tag
##   - wnba_stats_draft
##
## Standalone-runnable: this script is not invoked by the daily processor.
## It is called separately (e.g. from wehoop-wnba-data's annual draft
## workflow) against arbitrary seasons.
##
## CLI convention (matches wnba_stats_01_pbp.R): positional args
##   Rscript R/wnba_stats_07_draft.R <START_YEAR> <END_YEAR>
## ----------------------------------------------------------------------------

rm(list = ls())
gc()


suppressPackageStartupMessages(suppressMessages(library(dplyr)))
suppressPackageStartupMessages(suppressMessages(library(tidyr)))
suppressPackageStartupMessages(suppressMessages(library(magrittr)))
suppressPackageStartupMessages(suppressMessages(library(janitor)))
suppressPackageStartupMessages(suppressMessages(library(jsonlite)))
suppressPackageStartupMessages(suppressMessages(library(purrr)))
suppressPackageStartupMessages(suppressMessages(library(progressr)))
suppressPackageStartupMessages(suppressMessages(library(arrow)))
suppressPackageStartupMessages(suppressMessages(library(glue)))
suppressPackageStartupMessages(suppressMessages(library(wehoop)))
suppressPackageStartupMessages(suppressMessages(library(stringr)))
suppressPackageStartupMessages(suppressMessages(library(tibble)))
suppressPackageStartupMessages(suppressMessages(library(sportsdataversedata)))

options(stringsAsFactors = FALSE)
options(scipen = 999)

# --- CLI parsing (positional <START> <END>) ----------------------------------
args <- commandArgs(trailingOnly = TRUE)
if (length(args) >= 2) {
  start_year <- as.integer(args[[1]])
  end_year   <- as.integer(args[[2]])
} else if (length(args) == 1) {
  start_year <- as.integer(args[[1]])
  end_year   <- as.integer(args[[1]])
} else {
  start_year <- wehoop::most_recent_wnba_season() - 1
  end_year   <- wehoop::most_recent_wnba_season() - 1
}

cli::cli_alert_info("[{Sys.time()}] WNBA Stats draft: seasons {start_year}-{end_year}")

# --- Proxy pool --------------------------------------------------------------
# Proxy acquisition centralised in R/utils.R: load_proxies() tries
# PROXY_KEY+PROXY_PKG env vars first (live API), falls back to a local
# proxylist.csv (gitignored), then to no-proxy.
.utils_path <- Find(file.exists, c("R/utils.R", "../R/utils.R", "../../R/utils.R"))
if (is.null(.utils_path)) stop("Could not locate R/utils.R from cwd: ", getwd())
source(.utils_path)
proxies <- load_proxies()

# --- Helpers -----------------------------------------------------------------
# Map a wnba_draftboard() `picks` tibble onto the drafthistory clean-name
# schema so a current-season fill is shape-compatible with prior, drafthistory-
# sourced seasons. The live board lacks team_city / team_abbreviation and the
# player_profile_flag, so those are NA; round_pick / overall_pick are derived
# from draft order (the board lists picks in order).
.map_board_to_history <- function(picks, season) {
  picks %>%
    dplyr::mutate(overall_pick_tmp = dplyr::row_number()) %>%
    dplyr::group_by(.data$round) %>%
    dplyr::mutate(round_pick_tmp = dplyr::row_number()) %>%
    dplyr::ungroup() %>%
    dplyr::transmute(
      person_id           = as.character(.data$prospect_id),
      player_name         = stringr::str_squish(paste(
        dplyr::coalesce(.data$first_name, ""),
        dplyr::coalesce(.data$last_name, "")
      )),
      season              = as.integer(season),
      round_number        = as.character(.data$round),
      round_pick          = as.character(.data$round_pick_tmp),
      overall_pick        = as.character(.data$overall_pick_tmp),
      draft_type          = "Draft",
      team_id             = as.character(.data$team_external_id),
      team_city           = NA_character_,
      team_name           = as.character(.data$team_name),
      team_abbreviation   = NA_character_,
      organization        = as.character(.data$college),
      organization_type   = dplyr::if_else(
        !is.na(.data$college) & nzchar(.data$college), "College", NA_character_
      ),
      player_profile_flag = NA_character_,
      season_2            = as.integer(season)
    )
}

# Current-season fallback: stats.wnba.com/drafthistory only serves prior
# *completed* drafts, so for the current (or a future) season pull the live
# content-api draft board instead and reshape it to the history schema.
fetch_draft_board <- function(season) {
  # wnba_draftboard() does not accept a per-call proxy (it calls
  # .retry_request() without ...), so route proxy rotation through the
  # getOption("wehoop.proxy") path it honours.
  proxy <- select_proxy(proxies)
  if (!is.null(proxy)) {
    old <- options(wehoop.proxy = proxy)
    on.exit(options(old), add = TRUE)
  }
  res <- tryCatch(
    wehoop::wnba_draftboard(season = as.character(season)),
    error = function(e) {
      cli::cli_alert_warning("draftboard season={season}: {e$message}")
      NULL
    }
  )
  picks <- res$picks
  if (is.null(picks) || nrow(picks) == 0) return(NULL)
  out <- .map_board_to_history(picks, season)
  attr(out, "draft_source") <- "content-api-prod.nba.com/draft/board"
  out
}

fetch_draft <- function(season) {
  proxy <- select_proxy(proxies)
  res <- tryCatch(
    if (is.null(proxy)) {
      wehoop::wnba_drafthistory(
        league_id = "10",
        season    = as.character(season)
      )
    } else {
      wehoop::wnba_drafthistory(
        league_id = "10",
        season    = as.character(season),
        proxy     = proxy
      )
    },
    error = function(e) {
      cli::cli_alert_warning("drafthistory season={season}: {e$message}")
      NULL
    }
  )
  if (!is.null(res) && !is.null(res$DraftHistory) && nrow(res$DraftHistory) > 0) {
    out <- res$DraftHistory %>%
      dplyr::mutate(season = season)
    attr(out, "draft_source") <- "stats.wnba.com/drafthistory"
    return(out)
  }
  # Only fall back to the live board for the current/future season -- never for
  # a historical season, where an empty drafthistory result is a transient API
  # blip and the board (NA team_city/abbrev) would degrade good data.
  if (season >= wehoop::most_recent_wnba_season()) {
    cli::cli_alert_info(
      "[{Sys.time()}] season {season}: drafthistory empty -- falling back to wnba_draftboard()"
    )
    return(fetch_draft_board(season))
  }
  cli::cli_alert_warning(
    "[{Sys.time()}] season {season}: drafthistory empty and not current season -- no board fallback"
  )
  NULL
}

# --- Output dirs -------------------------------------------------------------
ifelse(!dir.exists(file.path("wnba_stats")),                dir.create(file.path("wnba_stats")),                FALSE)
ifelse(!dir.exists(file.path("wnba_stats/draft")),          dir.create(file.path("wnba_stats/draft")),          FALSE)
ifelse(!dir.exists(file.path("wnba_stats/draft/rds")),      dir.create(file.path("wnba_stats/draft/rds")),      FALSE)
ifelse(!dir.exists(file.path("wnba_stats/draft/parquet")),  dir.create(file.path("wnba_stats/draft/parquet")),  FALSE)

retry <- purrr::rate_backoff(pause_base = 1, pause_min = 1, max_times = 5)
insistent_save <- purrr::insistently(sportsdataversedata::sportsdataverse_save,
                                     rate = retry, quiet = FALSE)

# --- Manifest helper ---------------------------------------------------------
manifest_path <- "wnba_stats/wnba_stats_draft_in_data_repo.csv"
append_manifest <- function(season, row_count,
                             source_endpoint = "stats.wnba.com/drafthistory") {
  row <- data.frame(
    season           = as.integer(season),
    row_count        = as.integer(row_count),
    generated_at_utc = format(Sys.time(), tz = "UTC", "%Y-%m-%dT%H:%M:%SZ"),
    source_endpoint  = source_endpoint,
    stringsAsFactors = FALSE
  )
  if (file.exists(manifest_path)) {
    utils::write.table(row, manifest_path, sep = ",", row.names = FALSE,
                       col.names = FALSE, append = TRUE, qmethod = "double")
  } else {
    utils::write.csv(row, manifest_path, row.names = FALSE)
  }
}

# --- Main loop ---------------------------------------------------------------
for (y in start_year:end_year) {
  tryCatch({
    cli::cli_alert_info("[{Sys.time()}] season {y}: pulling draft history")
    Sys.sleep(3)
    draft <- fetch_draft(y)

    if (is.null(draft) || nrow(draft) == 0) {
      cli::cli_alert_warning("[{Sys.time()}] season {y}: 0 draft rows -- skipping upload")
      next
    }

    # Capture provenance before the clean_names/make_wehoop_data pipeline,
    # which does not preserve the custom attribute.
    draft_source <- attr(draft, "draft_source")
    if (is.null(draft_source)) draft_source <- "stats.wnba.com/drafthistory"

    draft <- draft %>%
      janitor::clean_names() %>%
      wehoop:::make_wehoop_data("WNBA Stats Draft History from wehoop data repository", Sys.time())

    saveRDS(draft, glue::glue("wnba_stats/draft/rds/draft_{y}.rds"))
    arrow::write_parquet(draft,
                         glue::glue("wnba_stats/draft/parquet/draft_{y}.parquet"),
                         compression = "zstd", compression_level = 22)

    insistent_save(
      data_frame           = draft,
      file_name            = glue::glue("draft_{y}"),
      sportsdataverse_type = "WNBA Stats draft",
      release_tag          = "wnba_stats_draft",
      pkg_function         = "wehoop::load_wnba_stats_draft()",
      file_types           = c("rds", "csv", "parquet"),
      .token               = Sys.getenv("GITHUB_PAT")
    )

    append_manifest(y, nrow(draft), draft_source)
    cli::cli_alert_success("[{Sys.time()}] season {y}: uploaded {nrow(draft)} rows (source: {draft_source})")
  },
  error = function(e) {
    cli::cli_alert_danger("[{Sys.time()}] season {y}: aborted ({e$message}) -- continuing")
  })
}

# --- Manifest upload (idempotent -- overwrites release asset on each run) ----
tryCatch({
  source(file.path("R", "manifest_upload_helper.R"), local = TRUE)
  upload_wnba_stats_manifest(
    manifest_path        = manifest_path,
    release_tag          = "wnba_stats_draft",
    file_name            = "wnba_stats_draft_in_data_repo",
    sportsdataverse_type = "draft manifest",
    pkg_function         = "wehoop::load_wnba_stats_draft_manifest()"
  )
}, error = function(e) {
  cli::cli_alert_warning(
    sprintf("%s: draft manifest upload failed (non-fatal): %s",
            Sys.time(), e$message)
  )
})

cli::cli_alert_success("[{Sys.time()}] WNBA Stats draft: done")
