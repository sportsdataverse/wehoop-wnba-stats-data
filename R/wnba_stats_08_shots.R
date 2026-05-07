#!/usr/bin/env Rscript
## ----------------------------------------------------------------------------
## wnba_stats_08_shots.R
##
## Compile per-season WNBA Stats API shots (extracted from V3 PBP) and upload
## to release tag
##   - wnba_stats_shots
##
## Sources shot rows by calling wehoop::wnba_pbp() per game (V3 path retains
## shot columns: is_field_goal, x_legacy, y_legacy, shot_distance, shot_value,
## shot_result, points_total). Falls back to a locally cached season parquet
## under wnba_stats/pbp/parquet/play_by_play_{y}.parquet if it carries the
## V3 shot columns.
##
## CLI convention (matches wnba_stats_01_pbp.R): positional args
##   Rscript R/wnba_stats_08_shots.R <START_YEAR> <END_YEAR>
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

cli::cli_alert_info("[{Sys.time()}] WNBA Stats shots: seasons {start_year}-{end_year}")

# --- Proxy pool --------------------------------------------------------------
proxies <- tryCatch(
  data.table::fread("../../proxylist.csv"),
  error = function(e) {
    cli::cli_alert_warning("Could not read ../../proxylist.csv -- proceeding without proxy pool: {e$message}")
    NULL
  }
)

select_proxy <- function(proxies) {
  if (is.null(proxies) || nrow(proxies) == 0) return(NULL)
  proxy <- sample(proxies$ip, 1)
  proxy_selected <- proxies %>% dplyr::filter(.data$ip == proxy)
  httr::use_proxy(url      = proxy_selected$ip,
                  port     = proxy_selected$port,
                  username = proxy_selected$login,
                  password = proxy_selected$password)
}

# --- Shot column set ---------------------------------------------------------
shot_cols <- c(
  "game_id", "season", "period", "clock",
  "team_id", "person_id",
  "action_type", "sub_type", "description",
  "x_legacy", "y_legacy", "shot_distance",
  "shot_value", "shot_result", "points_total"
)

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

fetch_pbp_with_shots <- function(game_id) {
  proxy <- select_proxy(proxies)
  tryCatch(
    if (is.null(proxy)) {
      wehoop::wnba_pbp(game_id)
    } else {
      wehoop::wnba_pbp(game_id, proxy = proxy)
    },
    error = function(e) {
      cli::cli_alert_warning("wnba_pbp game_id={game_id}: {e$message}")
      NULL
    }
  )
}

extract_shots <- function(pbp_df, season) {
  if (is.null(pbp_df) || !is.data.frame(pbp_df) || nrow(pbp_df) == 0) {
    return(NULL)
  }
  pbp_df <- pbp_df %>% janitor::clean_names()

  if (!"is_field_goal" %in% names(pbp_df)) {
    # No V3 shot columns present (legacy V2 path) -- nothing to extract.
    return(NULL)
  }

  shots <- pbp_df %>%
    dplyr::filter(!is.na(.data$is_field_goal) & as.integer(.data$is_field_goal) == 1L)

  if (nrow(shots) == 0) return(NULL)

  shots <- shots %>%
    dplyr::mutate(season = as.integer(season))

  # Add any missing requested columns as NA so the per-season frame is uniform.
  for (col in shot_cols) {
    if (!col %in% names(shots)) {
      shots[[col]] <- NA
    }
  }

  shots %>% dplyr::select(dplyr::all_of(shot_cols))
}

# --- Output dirs -------------------------------------------------------------
ifelse(!dir.exists(file.path("wnba_stats")),                dir.create(file.path("wnba_stats")),                FALSE)
ifelse(!dir.exists(file.path("wnba_stats/shots")),          dir.create(file.path("wnba_stats/shots")),          FALSE)
ifelse(!dir.exists(file.path("wnba_stats/shots/rds")),      dir.create(file.path("wnba_stats/shots/rds")),      FALSE)
ifelse(!dir.exists(file.path("wnba_stats/shots/parquet")),  dir.create(file.path("wnba_stats/shots/parquet")),  FALSE)

retry <- purrr::rate_backoff(pause_base = 1, pause_min = 1, max_times = 5)
insistent_save <- purrr::insistently(sportsdataversedata::sportsdataverse_save,
                                     rate = retry, quiet = FALSE)

# --- Manifest helper ---------------------------------------------------------
manifest_path <- "wnba_stats/wnba_stats_shots_in_data_repo.csv"
append_manifest <- function(season, row_count) {
  row <- data.frame(
    season           = as.integer(season),
    row_count        = as.integer(row_count),
    generated_at_utc = format(Sys.time(), tz = "UTC", "%Y-%m-%dT%H:%M:%SZ"),
    source_endpoint  = "stats.wnba.com/playbyplayv3 (via wehoop::wnba_pbp)",
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

    # Try local cache first if it carries the V3 shot columns.
    season_shots <- NULL
    cached_pbp_path <- glue::glue("wnba_stats/pbp/parquet/play_by_play_{y}.parquet")
    if (file.exists(cached_pbp_path)) {
      cached <- tryCatch(arrow::read_parquet(cached_pbp_path),
                         error = function(e) {
                           cli::cli_alert_warning("read cache {cached_pbp_path}: {e$message}")
                           NULL
                         })
      if (!is.null(cached) && "is_field_goal" %in% janitor::make_clean_names(names(cached))) {
        season_shots <- extract_shots(cached, y)
        if (!is.null(season_shots) && nrow(season_shots) > 0) {
          cli::cli_alert_info("[{Sys.time()}] season {y}: using local PBP cache ({nrow(season_shots)} shot rows)")
        } else {
          season_shots <- NULL
        }
      }
    }

    if (is.null(season_shots)) {
      Sys.sleep(3)
      games <- list_season_games(y)
      if (length(games) == 0) {
        cli::cli_alert_warning("[{Sys.time()}] season {y}: 0 games -- skipping")
        next
      }
      cli::cli_alert_info("[{Sys.time()}] season {y}: {length(games)} games")

      shots_list <- vector("list", length(games))
      for (gi in seq_along(games)) {
        g <- games[[gi]]
        Sys.sleep(3)
        pbp_df <- fetch_pbp_with_shots(g)
        shots_list[[gi]] <- tryCatch(
          extract_shots(pbp_df, y),
          error = function(e) {
            cli::cli_alert_warning("extract_shots game_id={g}: {e$message}")
            NULL
          }
        )
      }
      season_shots <- dplyr::bind_rows(shots_list)
    }

    if (is.null(season_shots) || nrow(season_shots) == 0) {
      cli::cli_alert_warning("[{Sys.time()}] season {y}: 0 shot rows -- skipping upload")
      next
    }

    season_shots <- season_shots %>%
      janitor::clean_names() %>%
      wehoop:::make_wehoop_data("WNBA Stats Shots (V3 PBP) from wehoop data repository", Sys.time())

    saveRDS(season_shots, glue::glue("wnba_stats/shots/rds/shots_{y}.rds"))
    arrow::write_parquet(season_shots,
                         glue::glue("wnba_stats/shots/parquet/shots_{y}.parquet"),
                         compression = "zstd", compression_level = 22)

    insistent_save(
      data_frame           = season_shots,
      file_name            = glue::glue("shots_{y}"),
      sportsdataverse_type = "WNBA Stats shots",
      release_tag          = "wnba_stats_shots",
      pkg_function         = "wehoop::load_wnba_stats_shots()",
      file_types           = c("rds", "csv", "parquet"),
      .token               = Sys.getenv("GITHUB_PAT")
    )

    append_manifest(y, nrow(season_shots))
    cli::cli_alert_success("[{Sys.time()}] season {y}: uploaded {nrow(season_shots)} shot rows")
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
    release_tag          = "wnba_stats_shots",
    file_name            = "wnba_stats_shots_in_data_repo",
    sportsdataverse_type = "shots manifest",
    pkg_function         = "wehoop::load_wnba_stats_shots_manifest()"
  )
}, error = function(e) {
  cli::cli_alert_warning(
    sprintf("%s: shots manifest upload failed (non-fatal): %s",
            Sys.time(), e$message)
  )
})

cli::cli_alert_success("[{Sys.time()}] WNBA Stats shots: done")
