## ----------------------------------------------------------------------------
## wnba_stats_02_rosters.R
##
## Compile per-season WNBA Stats API rosters (and the Coaches sidecar) and
## upload them to the sportsdataverse-data release tags
##   - wnba_stats_rosters
##   - wnba_stats_coaches
##
## CLI convention (matches wnba_stats_01_pbp.R): positional args
##   Rscript R/wnba_stats_02_rosters.R <START_YEAR> <END_YEAR>
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

message(glue::glue("[{Sys.time()}] WNBA Stats rosters: seasons {start_year}-{end_year}"))

# --- Proxy pool --------------------------------------------------------------
# Proxy acquisition centralised in R/utils.R: load_proxies() tries
# PROXY_KEY+PROXY_PKG env vars first (live API), falls back to a local
# proxylist.csv (gitignored), then to no-proxy.
.utils_path <- Find(file.exists, c("R/utils.R", "../R/utils.R", "../../R/utils.R"))
if (is.null(.utils_path)) stop("Could not locate R/utils.R from cwd: ", getwd())
source(.utils_path)
proxies <- load_proxies()

# --- Helpers -----------------------------------------------------------------
list_team_ids <- function(season) {
  proxy <- select_proxy(proxies)
  res <- tryCatch(
    if (is.null(proxy)) {
      wehoop::wnba_commonallplayers(league_id = "10", season = as.character(season))
    } else {
      wehoop::wnba_commonallplayers(league_id = "10", season = as.character(season), proxy = proxy)
    },
    error = function(e) { message(sprintf("commonallplayers season=%d: %s", season, e$message)); NULL }
  )
  if (is.null(res) || is.null(res$CommonAllPlayers)) return(integer(0))
  ids <- suppressWarnings(as.integer(res$CommonAllPlayers$TEAM_ID))
  unique(ids[!is.na(ids) & ids > 0])
}

fetch_team_roster <- function(season, team_id) {
  proxy <- select_proxy(proxies)
  result <- tryCatch(
    if (is.null(proxy)) {
      wehoop::wnba_commonteamroster(league_id = "10",
                                    season    = as.character(season),
                                    team_id   = as.character(team_id))
    } else {
      wehoop::wnba_commonteamroster(league_id = "10",
                                    season    = as.character(season),
                                    team_id   = as.character(team_id),
                                    proxy     = proxy)
    },
    error = function(e) {
      message(sprintf("commonteamroster season=%d team=%s: %s", season, team_id, e$message))
      NULL
    }
  )
  if (is.null(result)) return(list(roster = NULL, coaches = NULL))
  list(
    roster  = if (!is.null(result$CommonTeamRoster) && nrow(result$CommonTeamRoster) > 0)
                result$CommonTeamRoster |> dplyr::mutate(season = season, team_id_lookup = team_id)
              else NULL,
    coaches = if (!is.null(result$Coaches) && nrow(result$Coaches) > 0)
                result$Coaches |> dplyr::mutate(season = season, team_id_lookup = team_id)
              else NULL
  )
}

# --- Output dirs -------------------------------------------------------------
ifelse(!dir.exists(file.path("wnba_stats")),                   dir.create(file.path("wnba_stats")),                   FALSE)
ifelse(!dir.exists(file.path("wnba_stats/rosters")),           dir.create(file.path("wnba_stats/rosters")),           FALSE)
ifelse(!dir.exists(file.path("wnba_stats/rosters/rds")),       dir.create(file.path("wnba_stats/rosters/rds")),       FALSE)
ifelse(!dir.exists(file.path("wnba_stats/rosters/parquet")),   dir.create(file.path("wnba_stats/rosters/parquet")),   FALSE)
ifelse(!dir.exists(file.path("wnba_stats/coaches")),           dir.create(file.path("wnba_stats/coaches")),           FALSE)
ifelse(!dir.exists(file.path("wnba_stats/coaches/rds")),       dir.create(file.path("wnba_stats/coaches/rds")),       FALSE)
ifelse(!dir.exists(file.path("wnba_stats/coaches/parquet")),   dir.create(file.path("wnba_stats/coaches/parquet")),   FALSE)

retry <- purrr::rate_backoff(pause_base = 1, pause_min = 60, max_times = 10)
insistent_save <- purrr::insistently(sportsdataversedata::sportsdataverse_save,
                                     rate = retry, quiet = FALSE)

# --- Manifest helpers --------------------------------------------------------
rosters_manifest_path <- "wnba_stats/wnba_stats_rosters_in_data_repo.csv"
coaches_manifest_path <- "wnba_stats/wnba_stats_coaches_in_data_repo.csv"
append_manifest_row <- function(path, season, row_count, source_endpoint) {
  row <- data.frame(
    season           = as.integer(season),
    row_count        = as.integer(row_count),
    generated_at_utc = format(Sys.time(), tz = "UTC", "%Y-%m-%dT%H:%M:%SZ"),
    source_endpoint  = source_endpoint,
    stringsAsFactors = FALSE
  )
  if (file.exists(path)) {
    utils::write.table(row, path, sep = ",", row.names = FALSE,
                       col.names = FALSE, append = TRUE, qmethod = "double")
  } else {
    utils::write.csv(row, path, row.names = FALSE)
  }
}

# --- Main loop ---------------------------------------------------------------
for (y in start_year:end_year) {
  message(glue::glue("[{Sys.time()}] season {y}: discovering team_ids"))
  team_ids <- list_team_ids(y)
  if (length(team_ids) == 0) {
    message(glue::glue("[{Sys.time()}] season {y}: no team_ids -- skipping"))
    next
  }
  message(glue::glue("[{Sys.time()}] season {y}: {length(team_ids)} teams"))

  parts <- purrr::map(team_ids, function(tid) {
    Sys.sleep(3)
    fetch_team_roster(y, tid)
  })

  rosters <- purrr::map_dfr(parts, "roster")
  coaches <- purrr::map_dfr(parts, "coaches")

  if (nrow(rosters) > 0) {
    rosters <- rosters %>%
      janitor::clean_names() %>%
      wehoop:::make_wehoop_data("WNBA Stats Common Team Roster from wehoop data repository", Sys.time())

    saveRDS(rosters,           glue::glue("wnba_stats/rosters/rds/rosters_{y}.rds"))
    arrow::write_parquet(rosters,
                         glue::glue("wnba_stats/rosters/parquet/rosters_{y}.parquet"),
                         compression = "zstd", compression_level = 22)

    insistent_save(
      data_frame           = rosters,
      file_name            = glue::glue("rosters_{y}"),
      sportsdataverse_type = "WNBA Stats rosters",
      release_tag          = "wnba_stats_rosters",
      pkg_function         = "wehoop::load_wnba_stats_rosters()",
      file_types           = c("rds", "csv", "parquet"),
      .token               = Sys.getenv("GITHUB_PAT")
    )

    append_manifest_row(rosters_manifest_path, y, nrow(rosters),
                        "stats.wnba.com/commonteamroster")
  } else {
    message(glue::glue("[{Sys.time()}] season {y}: 0 roster rows"))
  }

  if (nrow(coaches) > 0) {
    coaches <- coaches %>%
      janitor::clean_names() %>%
      wehoop:::make_wehoop_data("WNBA Stats Coaches from wehoop data repository", Sys.time())

    saveRDS(coaches,           glue::glue("wnba_stats/coaches/rds/coaches_{y}.rds"))
    arrow::write_parquet(coaches,
                         glue::glue("wnba_stats/coaches/parquet/coaches_{y}.parquet"),
                         compression = "zstd", compression_level = 22)

    insistent_save(
      data_frame           = coaches,
      file_name            = glue::glue("coaches_{y}"),
      sportsdataverse_type = "WNBA Stats coaches",
      release_tag          = "wnba_stats_coaches",
      pkg_function         = "wehoop::load_wnba_stats_coaches()",
      file_types           = c("rds", "csv", "parquet"),
      .token               = Sys.getenv("GITHUB_PAT")
    )

    append_manifest_row(coaches_manifest_path, y, nrow(coaches),
                        "stats.wnba.com/commonteamroster")
  } else {
    message(glue::glue("[{Sys.time()}] season {y}: 0 coaches rows"))
  }
}

# --- Manifest upload (idempotent -- overwrites release asset on each run) ----
tryCatch({
  source(file.path("R", "manifest_upload_helper.R"), local = TRUE)
  upload_wnba_stats_manifest(
    manifest_path        = rosters_manifest_path,
    release_tag          = "wnba_stats_rosters",
    file_name            = "wnba_stats_rosters_in_data_repo",
    sportsdataverse_type = "rosters manifest",
    pkg_function         = "wehoop::load_wnba_stats_rosters_manifest()"
  )
  upload_wnba_stats_manifest(
    manifest_path        = coaches_manifest_path,
    release_tag          = "wnba_stats_coaches",
    file_name            = "wnba_stats_coaches_in_data_repo",
    sportsdataverse_type = "coaches manifest",
    pkg_function         = "wehoop::load_wnba_stats_coaches_manifest()"
  )
}, error = function(e) {
  cli::cli_alert_warning(
    sprintf("%s: rosters/coaches manifest upload failed (non-fatal): %s",
            Sys.time(), e$message)
  )
})

message(glue::glue("[{Sys.time()}] WNBA Stats rosters: done"))
