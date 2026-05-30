## ----------------------------------------------------------------------------
## wnba_stats_06_standings.R
##
## Compile per-season WNBA Stats API league standings (V3) and upload to
## release tag
##   - wnba_stats_standings
##
## CLI convention (matches wnba_stats_01_pbp.R): positional args
##   Rscript R/wnba_stats_06_standings.R <START_YEAR> <END_YEAR>
## ----------------------------------------------------------------------------

rm(list = ls())
gc()

lib_path <- Sys.getenv("R_LIBS")
if (lib_path == "") lib_path <- .libPaths()[1]

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

cli::cli_alert_info("[{Sys.time()}] WNBA Stats standings: seasons {start_year}-{end_year}")

# --- Proxy pool --------------------------------------------------------------
# Proxy acquisition centralised in R/utils.R: load_proxies() tries
# PROXY_KEY+PROXY_PKG env vars first (live API), falls back to a local
# proxylist.csv (gitignored), then to no-proxy.
.utils_path <- Find(file.exists, c("R/utils.R", "../R/utils.R", "../../R/utils.R"))
if (is.null(.utils_path)) stop("Could not locate R/utils.R from cwd: ", getwd())
source(.utils_path)
proxies <- load_proxies()

# --- Helpers -----------------------------------------------------------------
fetch_standings <- function(season) {
  proxy <- select_proxy(proxies)
  res <- tryCatch(
    if (is.null(proxy)) {
      wehoop::wnba_leaguestandingsv3(
        league_id   = "10",
        season      = as.character(season),
        season_type = "Regular Season"
      )
    } else {
      wehoop::wnba_leaguestandingsv3(
        league_id   = "10",
        season      = as.character(season),
        season_type = "Regular Season",
        proxy       = proxy
      )
    },
    error = function(e) {
      cli::cli_alert_warning("leaguestandingsv3 season={season}: {e$message}")
      NULL
    }
  )
  if (is.null(res) || is.null(res$Standings) || nrow(res$Standings) == 0) {
    return(NULL)
  }
  res$Standings %>%
    dplyr::mutate(season = season)
}

# --- Output dirs -------------------------------------------------------------
ifelse(!dir.exists(file.path("wnba_stats")),                    dir.create(file.path("wnba_stats")),                    FALSE)
ifelse(!dir.exists(file.path("wnba_stats/standings")),          dir.create(file.path("wnba_stats/standings")),          FALSE)
ifelse(!dir.exists(file.path("wnba_stats/standings/rds")),      dir.create(file.path("wnba_stats/standings/rds")),      FALSE)
ifelse(!dir.exists(file.path("wnba_stats/standings/parquet")),  dir.create(file.path("wnba_stats/standings/parquet")),  FALSE)

retry <- purrr::rate_backoff(pause_base = 1, pause_min = 1, max_times = 5)
insistent_save <- purrr::insistently(sportsdataversedata::sportsdataverse_save,
                                     rate = retry, quiet = FALSE)

# --- Manifest helper ---------------------------------------------------------
manifest_path <- "wnba_stats/wnba_stats_standings_in_data_repo.csv"
append_manifest <- function(season, row_count) {
  row <- data.frame(
    season           = as.integer(season),
    row_count        = as.integer(row_count),
    generated_at_utc = format(Sys.time(), tz = "UTC", "%Y-%m-%dT%H:%M:%SZ"),
    source_endpoint  = "stats.wnba.com/leaguestandingsv3",
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
    cli::cli_alert_info("[{Sys.time()}] season {y}: pulling standings")
    Sys.sleep(3)
    standings <- fetch_standings(y)

    if (is.null(standings) || nrow(standings) == 0) {
      cli::cli_alert_warning("[{Sys.time()}] season {y}: 0 standings rows -- skipping upload")
      next
    }

    standings <- standings %>%
      janitor::clean_names() %>%
      wehoop:::make_wehoop_data("WNBA Stats League Standings V3 from wehoop data repository", Sys.time())

    saveRDS(standings, glue::glue("wnba_stats/standings/rds/standings_{y}.rds"))
    arrow::write_parquet(standings,
                         glue::glue("wnba_stats/standings/parquet/standings_{y}.parquet"),
                         compression = "zstd", compression_level = 22)

    insistent_save(
      data_frame           = standings,
      file_name            = glue::glue("standings_{y}"),
      sportsdataverse_type = "WNBA Stats standings",
      release_tag          = "wnba_stats_standings",
      pkg_function         = "wehoop::load_wnba_stats_standings()",
      file_types           = c("rds", "csv", "parquet"),
      .token               = Sys.getenv("GITHUB_PAT")
    )

    append_manifest(y, nrow(standings))
    cli::cli_alert_success("[{Sys.time()}] season {y}: uploaded {nrow(standings)} rows")
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
    release_tag          = "wnba_stats_standings",
    file_name            = "wnba_stats_standings_in_data_repo",
    sportsdataverse_type = "standings manifest",
    pkg_function         = "wehoop::load_wnba_stats_standings_manifest()"
  )
}, error = function(e) {
  cli::cli_alert_warning(
    sprintf("%s: standings manifest upload failed (non-fatal): %s",
            Sys.time(), e$message)
  )
})

cli::cli_alert_success("[{Sys.time()}] WNBA Stats standings: done")
