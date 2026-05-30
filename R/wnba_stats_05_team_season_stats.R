## ----------------------------------------------------------------------------
## wnba_stats_05_team_season_stats.R
##
## Compile per-season WNBA Stats API league-wide team season stats across all
## measure_types (Base/Advanced/Misc/Scoring/Usage/Defense/Opponent), bind them
## into one tidy frame per season with a measure_type column appended, and
## upload to release tag
##   - wnba_stats_team_season_stats
##
## CLI convention (matches wnba_stats_01_pbp.R): positional args
##   Rscript R/wnba_stats_05_team_season_stats.R <START_YEAR> <END_YEAR>
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
suppressPackageStartupMessages(suppressMessages(library(sportsdataverse)))
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
  start_year <- wehoop::most_recent_wnba_season()
  end_year   <- wehoop::most_recent_wnba_season()
}

cli::cli_alert_info("[{Sys.time()}] WNBA Stats team season stats: seasons {start_year}-{end_year}")

measure_types <- c("Base", "Advanced", "Misc", "Scoring", "Usage", "Defense", "Opponent")
season_types  <- c("Regular Season", "Playoffs")

# --- Proxy pool --------------------------------------------------------------
# Proxy acquisition centralised in R/utils.R: load_proxies() tries
# PROXY_KEY+PROXY_PKG env vars first (live API), falls back to a local
# proxylist.csv (gitignored), then to no-proxy.
.utils_path <- Find(file.exists, c("R/utils.R", "../R/utils.R", "../../R/utils.R"))
if (is.null(.utils_path)) stop("Could not locate R/utils.R from cwd: ", getwd())
source(.utils_path)
proxies <- load_proxies()

# --- Helpers -----------------------------------------------------------------
fetch_team_stats <- function(season, measure_type, season_type) {
  proxy <- select_proxy(proxies)
  res <- tryCatch(
    if (is.null(proxy)) {
      wehoop::wnba_leaguedashteamstats(
        league_id    = "10",
        season       = as.character(season),
        season_type  = season_type,
        measure_type = measure_type,
        per_mode     = "PerGame"
      )
    } else {
      wehoop::wnba_leaguedashteamstats(
        league_id    = "10",
        season       = as.character(season),
        season_type  = season_type,
        measure_type = measure_type,
        per_mode     = "PerGame",
        proxy        = proxy
      )
    },
    error = function(e) {
      cli::cli_alert_warning("leaguedashteamstats season={season} measure={measure_type} season_type={season_type}: {e$message}")
      NULL
    }
  )
  if (is.null(res) || is.null(res$LeagueDashTeamStats) || nrow(res$LeagueDashTeamStats) == 0) {
    return(NULL)
  }
  res$LeagueDashTeamStats %>%
    dplyr::mutate(season       = season,
                  season_type  = season_type,
                  measure_type = measure_type)
}

# --- Output dirs -------------------------------------------------------------
ifelse(!dir.exists(file.path("wnba_stats")),                            dir.create(file.path("wnba_stats")),                            FALSE)
ifelse(!dir.exists(file.path("wnba_stats/team_season_stats")),          dir.create(file.path("wnba_stats/team_season_stats")),          FALSE)
ifelse(!dir.exists(file.path("wnba_stats/team_season_stats/rds")),      dir.create(file.path("wnba_stats/team_season_stats/rds")),      FALSE)
ifelse(!dir.exists(file.path("wnba_stats/team_season_stats/parquet")),  dir.create(file.path("wnba_stats/team_season_stats/parquet")),  FALSE)

retry <- purrr::rate_backoff(pause_base = 1, pause_min = 1, max_times = 5)
insistent_save <- purrr::insistently(sportsdataversedata::sportsdataverse_save,
                                     rate = retry, quiet = FALSE)

# --- Manifest helper ---------------------------------------------------------
manifest_path <- "wnba_stats/wnba_stats_team_season_stats_in_data_repo.csv"
append_manifest <- function(season, row_count) {
  row <- data.frame(
    season           = as.integer(season),
    row_count        = as.integer(row_count),
    generated_at_utc = format(Sys.time(), tz = "UTC", "%Y-%m-%dT%H:%M:%SZ"),
    source_endpoint  = "stats.wnba.com/leaguedashteamstats",
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
  season_ok <- tryCatch({
    cli::cli_alert_info("[{Sys.time()}] season {y}: pulling {length(measure_types)} measure_types x {length(season_types)} season_types")

    combos <- tidyr::expand_grid(measure_type = measure_types, season_type = season_types)

    parts <- purrr::map2(combos$measure_type, combos$season_type, function(mt, st) {
      Sys.sleep(3)
      fetch_team_stats(y, mt, st)
    })
    team_stats <- dplyr::bind_rows(parts)

    if (nrow(team_stats) == 0) {
      cli::cli_alert_warning("[{Sys.time()}] season {y}: 0 team_stats rows -- skipping upload")
      next
    }

    team_stats <- team_stats %>%
      janitor::clean_names() %>%
      wehoop:::make_wehoop_data("WNBA Stats League Dash Team Stats from wehoop data repository", Sys.time())

    saveRDS(team_stats, glue::glue("wnba_stats/team_season_stats/rds/team_season_stats_{y}.rds"))
    arrow::write_parquet(team_stats,
                         glue::glue("wnba_stats/team_season_stats/parquet/team_season_stats_{y}.parquet"),
                         compression = "zstd", compression_level = 22)

    insistent_save(
      data_frame           = team_stats,
      file_name            = glue::glue("team_season_stats_{y}"),
      sportsdataverse_type = "WNBA Stats team season stats",
      release_tag          = "wnba_stats_team_season_stats",
      pkg_function         = "wehoop::load_wnba_stats_team_stats()",
      file_types           = c("rds", "csv", "parquet"),
      .token               = Sys.getenv("GITHUB_PAT")
    )

    append_manifest(y, nrow(team_stats))
    cli::cli_alert_success("[{Sys.time()}] season {y}: uploaded {nrow(team_stats)} rows")
    TRUE
  },
  error = function(e) {
    cli::cli_alert_danger("[{Sys.time()}] season {y}: aborted ({e$message}) -- continuing")
    FALSE
  })
}

# --- Manifest upload (idempotent -- overwrites release asset on each run) ----
tryCatch({
  source(file.path("R", "manifest_upload_helper.R"), local = TRUE)
  upload_wnba_stats_manifest(
    manifest_path        = manifest_path,
    release_tag          = "wnba_stats_team_season_stats",
    file_name            = "wnba_stats_team_season_stats_in_data_repo",
    sportsdataverse_type = "team season stats manifest",
    pkg_function         = "wehoop::load_wnba_stats_team_stats_manifest()"
  )
}, error = function(e) {
  cli::cli_alert_warning(
    sprintf("%s: team_season_stats manifest upload failed (non-fatal): %s",
            Sys.time(), e$message)
  )
})

cli::cli_alert_success("[{Sys.time()}] WNBA Stats team season stats: done")
