## ----------------------------------------------------------------------------
## wnba_stats_04_lineups.R
##
## Compile per-season WNBA Stats API league-wide 5-player lineup stats across
## all measure_types (Base/Advanced/FourFactors), bind them into one tidy
## frame per season with a measure_type column appended, and upload to
## release tag
##   - wnba_stats_lineups
##
## CLI convention (matches wnba_stats_01_pbp.R): positional args
##   Rscript R/wnba_stats_04_lineups.R <START_YEAR> <END_YEAR>
## ----------------------------------------------------------------------------

rm(list = ls())
gc()

lib_path <- Sys.getenv("R_LIBS")

if (!requireNamespace('pacman', quietly = TRUE)){
  install.packages('pacman', lib = Sys.getenv("R_LIBS"), repos = 'http://cran.us.r-project.org')
}

suppressPackageStartupMessages(suppressMessages(library(dplyr,             lib.loc = lib_path)))
suppressPackageStartupMessages(suppressMessages(library(tidyr,             lib.loc = lib_path)))
suppressPackageStartupMessages(suppressMessages(library(magrittr,          lib.loc = lib_path)))
suppressPackageStartupMessages(suppressMessages(library(janitor,           lib.loc = lib_path)))
suppressPackageStartupMessages(suppressMessages(library(jsonlite,          lib.loc = lib_path)))
suppressPackageStartupMessages(suppressMessages(library(purrr,             lib.loc = lib_path)))
suppressPackageStartupMessages(suppressMessages(library(progressr,         lib.loc = lib_path)))
suppressPackageStartupMessages(suppressMessages(library(arrow,             lib.loc = lib_path)))
suppressPackageStartupMessages(suppressMessages(library(glue,              lib.loc = lib_path)))
suppressPackageStartupMessages(suppressMessages(library(wehoop,            lib.loc = lib_path)))
suppressPackageStartupMessages(suppressMessages(library(stringr,           lib.loc = lib_path)))
suppressPackageStartupMessages(suppressMessages(library(tibble,            lib.loc = lib_path)))
suppressPackageStartupMessages(suppressMessages(library(sportsdataverse,   lib.loc = lib_path)))
suppressPackageStartupMessages(suppressMessages(library(sportsdataversedata, lib.loc = lib_path)))

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

message(glue::glue("[{Sys.time()}] WNBA Stats lineups: seasons {start_year}-{end_year}"))

measure_types <- c("Base", "Advanced", "FourFactors")
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
fetch_lineups <- function(season, measure_type, season_type) {
  proxy <- select_proxy(proxies)
  res <- tryCatch(
    if (is.null(proxy)) {
      wehoop::wnba_leaguedashlineups(
        league_id      = "10",
        season         = as.character(season),
        season_type    = season_type,
        group_quantity = 5,
        measure_type   = measure_type,
        per_mode       = "PerGame"
      )
    } else {
      wehoop::wnba_leaguedashlineups(
        league_id      = "10",
        season         = as.character(season),
        season_type    = season_type,
        group_quantity = 5,
        measure_type   = measure_type,
        per_mode       = "PerGame",
        proxy          = proxy
      )
    },
    error = function(e) {
      message(sprintf("leaguedashlineups season=%d measure=%s season_type=%s: %s",
                      season, measure_type, season_type, e$message))
      NULL
    }
  )
  if (is.null(res) || is.null(res$Lineups) || nrow(res$Lineups) == 0) {
    return(NULL)
  }
  res$Lineups %>%
    dplyr::mutate(season       = season,
                  season_type  = season_type,
                  measure_type = measure_type)
}

# --- Output dirs -------------------------------------------------------------
ifelse(!dir.exists(file.path("wnba_stats")),                  dir.create(file.path("wnba_stats")),                  FALSE)
ifelse(!dir.exists(file.path("wnba_stats/lineups")),          dir.create(file.path("wnba_stats/lineups")),          FALSE)
ifelse(!dir.exists(file.path("wnba_stats/lineups/rds")),      dir.create(file.path("wnba_stats/lineups/rds")),      FALSE)
ifelse(!dir.exists(file.path("wnba_stats/lineups/parquet")),  dir.create(file.path("wnba_stats/lineups/parquet")),  FALSE)

retry <- purrr::rate_backoff(pause_base = 1, pause_min = 60, max_times = 10)
insistent_save <- purrr::insistently(sportsdataversedata::sportsdataverse_save,
                                     rate = retry, quiet = FALSE)

# --- Manifest helper ---------------------------------------------------------
manifest_path <- "wnba_stats/wnba_stats_lineups_in_data_repo.csv"
append_manifest <- function(season, row_count) {
  row <- data.frame(
    season           = as.integer(season),
    row_count        = as.integer(row_count),
    generated_at_utc = format(Sys.time(), tz = "UTC", "%Y-%m-%dT%H:%M:%SZ"),
    source_endpoint  = "stats.wnba.com/leaguedashlineups",
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
  message(glue::glue("[{Sys.time()}] season {y}: pulling {length(measure_types)} measure_types x {length(season_types)} season_types"))

  combos <- tidyr::expand_grid(measure_type = measure_types, season_type = season_types)

  parts <- purrr::map2(combos$measure_type, combos$season_type, function(mt, st) {
    Sys.sleep(3)
    fetch_lineups(y, mt, st)
  })
  lineups <- dplyr::bind_rows(parts)

  if (nrow(lineups) == 0) {
    message(glue::glue("[{Sys.time()}] season {y}: 0 lineups rows -- skipping upload"))
    next
  }

  lineups <- lineups %>%
    janitor::clean_names() %>%
    wehoop:::make_wehoop_data("WNBA Stats League Dash Lineups from wehoop data repository", Sys.time())

  saveRDS(lineups, glue::glue("wnba_stats/lineups/rds/lineups_{y}.rds"))
  arrow::write_parquet(lineups,
                       glue::glue("wnba_stats/lineups/parquet/lineups_{y}.parquet"),
                       compression = "zstd", compression_level = 22)

  insistent_save(
    data_frame           = lineups,
    file_name            = glue::glue("lineups_{y}"),
    sportsdataverse_type = "WNBA Stats lineups",
    release_tag          = "wnba_stats_lineups",
    pkg_function         = "wehoop::load_wnba_stats_lineups()",
    file_types           = c("rds", "csv", "parquet"),
    .token               = Sys.getenv("GITHUB_PAT")
  )

  append_manifest(y, nrow(lineups))
}

# --- Manifest upload (idempotent -- overwrites release asset on each run) ----
tryCatch({
  source(file.path("R", "manifest_upload_helper.R"), local = TRUE)
  upload_wnba_stats_manifest(
    manifest_path        = manifest_path,
    release_tag          = "wnba_stats_lineups",
    file_name            = "wnba_stats_lineups_in_data_repo",
    sportsdataverse_type = "lineups manifest",
    pkg_function         = "wehoop::load_wnba_stats_lineups_manifest()"
  )
}, error = function(e) {
  cli::cli_alert_warning(
    sprintf("%s: lineups manifest upload failed (non-fatal): %s",
            Sys.time(), e$message)
  )
})

message(glue::glue("[{Sys.time()}] WNBA Stats lineups: done"))
