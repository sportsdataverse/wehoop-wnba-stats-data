#!/usr/bin/env Rscript
## ----------------------------------------------------------------------------
## wnba_stats_09_game_rosters.R
##
## Compile per-season WNBA Stats API per-game inactive-player rosters from
## the boxscoresummaryv2 InactivePlayers table and upload to release tag
##   - wnba_stats_game_rosters
##
## CLI convention (matches wnba_stats_01_pbp.R): positional args
##   Rscript R/wnba_stats_09_game_rosters.R <START_YEAR> <END_YEAR>
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
  start_year <- wehoop::most_recent_wnba_season()
  end_year   <- wehoop::most_recent_wnba_season()
}

cli::cli_alert_info("[{Sys.time()}] WNBA Stats game rosters (inactive players): seasons {start_year}-{end_year}")

# --- Proxy pool --------------------------------------------------------------
# Proxy acquisition centralised in R/utils.R: load_proxies() tries
# PROXY_KEY+PROXY_PKG env vars first (live API), falls back to a local
# proxylist.csv (gitignored), then to no-proxy.
.utils_path <- Find(file.exists, c("R/utils.R", "../R/utils.R", "../../R/utils.R"))
if (is.null(.utils_path)) stop("Could not locate R/utils.R from cwd: ", getwd())
source(.utils_path)
proxies <- load_proxies()

# --- Helpers -----------------------------------------------------------------
list_season_games <- function(season) {
  proxy <- select_proxy(proxies)
  res <- tryCatch(
    if (is.null(proxy)) {
      wehoop::wnba_leaguegamelog(season = season, player_or_team = "T")
    } else {
      wehoop::wnba_leaguegamelog(season = season, player_or_team = "T", proxy = proxy)
    },
    error = function(e) {
      cli::cli_alert_warning("leaguegamelog season={season}: {e$message}")
      NULL
    }
  )
  if (is.null(res) || is.null(res$LeagueGameLog) || nrow(res$LeagueGameLog) == 0) {
    return(character(0))
  }
  res$LeagueGameLog %>%
    janitor::clean_names() %>%
    dplyr::pull("game_id") %>%
    unique() %>%
    as.character()
}

fetch_inactives_one_game <- function(game_id, season) {
  proxy <- select_proxy(proxies)
  res <- tryCatch(
    if (is.null(proxy)) {
      wehoop::wnba_boxscoresummaryv2(game_id = game_id)
    } else {
      wehoop::wnba_boxscoresummaryv2(game_id = game_id, proxy = proxy)
    },
    error = function(e) {
      cli::cli_alert_warning("boxscoresummaryv2 game_id={game_id}: {e$message}")
      NULL
    }
  )
  if (is.null(res) || is.null(res$InactivePlayers)) return(NULL)
  ip <- res$InactivePlayers
  if (!is.data.frame(ip) || nrow(ip) == 0) return(NULL)

  ip <- ip %>% janitor::clean_names()
  if (!"game_id" %in% names(ip)) {
    ip$game_id <- as.character(game_id)
  } else {
    ip$game_id <- as.character(ip$game_id)
  }
  ip$season <- as.integer(season)
  ip
}

# --- Output dirs -------------------------------------------------------------
ifelse(!dir.exists(file.path("wnba_stats")),                       dir.create(file.path("wnba_stats")),                       FALSE)
ifelse(!dir.exists(file.path("wnba_stats/game_rosters")),          dir.create(file.path("wnba_stats/game_rosters")),          FALSE)
ifelse(!dir.exists(file.path("wnba_stats/game_rosters/rds")),      dir.create(file.path("wnba_stats/game_rosters/rds")),      FALSE)
ifelse(!dir.exists(file.path("wnba_stats/game_rosters/parquet")),  dir.create(file.path("wnba_stats/game_rosters/parquet")),  FALSE)

retry <- purrr::rate_backoff(pause_base = 1, pause_min = 1, max_times = 5)
insistent_save <- purrr::insistently(sportsdataversedata::sportsdataverse_save,
                                     rate = retry, quiet = FALSE)

# --- Manifest helper ---------------------------------------------------------
manifest_path <- "wnba_stats/wnba_stats_game_rosters_in_data_repo.csv"
append_manifest <- function(season, row_count) {
  row <- data.frame(
    season           = as.integer(season),
    row_count        = as.integer(row_count),
    generated_at_utc = format(Sys.time(), tz = "UTC", "%Y-%m-%dT%H:%M:%SZ"),
    source_endpoint  = "stats.wnba.com/boxscoresummaryv2 (InactivePlayers)",
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
    cli::cli_alert_info("[{Sys.time()}] season {y}: discovering games")
    Sys.sleep(3)
    games <- list_season_games(y)
    if (length(games) == 0) {
      cli::cli_alert_warning("[{Sys.time()}] season {y}: 0 games -- skipping")
      next
    }
    cli::cli_alert_info("[{Sys.time()}] season {y}: {length(games)} games")

    parts <- vector("list", length(games))
    for (gi in seq_along(games)) {
      g <- games[[gi]]
      Sys.sleep(3)
      parts[[gi]] <- tryCatch(
        fetch_inactives_one_game(g, y),
        error = function(e) {
          cli::cli_alert_warning("game_id={g}: {e$message}")
          NULL
        }
      )
    }

    season_df <- dplyr::bind_rows(parts)

    if (is.null(season_df) || nrow(season_df) == 0) {
      cli::cli_alert_warning("[{Sys.time()}] season {y}: 0 inactive-player rows -- skipping upload")
      next
    }

    season_df <- season_df %>%
      janitor::clean_names() %>%
      wehoop:::make_wehoop_data("WNBA Stats Game Rosters (Inactive Players) from wehoop data repository", Sys.time())

    saveRDS(season_df, glue::glue("wnba_stats/game_rosters/rds/game_rosters_{y}.rds"))
    arrow::write_parquet(season_df,
                         glue::glue("wnba_stats/game_rosters/parquet/game_rosters_{y}.parquet"),
                         compression = "zstd", compression_level = 22)

    insistent_save(
      data_frame           = season_df,
      file_name            = glue::glue("game_rosters_{y}"),
      sportsdataverse_type = "WNBA Stats game rosters",
      release_tag          = "wnba_stats_game_rosters",
      pkg_function         = "wehoop::load_wnba_stats_game_rosters()",
      file_types           = c("rds", "csv", "parquet"),
      .token               = Sys.getenv("GITHUB_PAT")
    )

    append_manifest(y, nrow(season_df))
    cli::cli_alert_success("[{Sys.time()}] season {y}: uploaded {nrow(season_df)} rows")
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
    release_tag          = "wnba_stats_game_rosters",
    file_name            = "wnba_stats_game_rosters_in_data_repo",
    sportsdataverse_type = "game rosters manifest",
    pkg_function         = "wehoop::load_wnba_stats_game_rosters_manifest()"
  )
}, error = function(e) {
  cli::cli_alert_warning(
    sprintf("%s: game_rosters manifest upload failed (non-fatal): %s",
            Sys.time(), e$message)
  )
})

cli::cli_alert_success("[{Sys.time()}] WNBA Stats game rosters: done")
