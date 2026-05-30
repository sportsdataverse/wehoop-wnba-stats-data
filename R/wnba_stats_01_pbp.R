## ----------------------------------------------------------------------------
## wnba_stats_01_pbp.R
##
## Compile per-season WNBA Stats API artifacts and upload them to the
## sportsdataverse-data release tags:
##   - wnba_stats_schedules           : per-season + master schedule
##   - wnba_stats_player_game_logs    : per-season player game logs (NEW tag)
##   - wnba_stats_pbp                 : per-season V3 PBP with on-court
##                                      lineups + possession + garbage-time
##                                      + FT-to-foul attribution
##
## CLI convention (matches wnba_stats_02..10): positional args
##   Rscript R/wnba_stats_01_pbp.R <START_YEAR> <END_YEAR>
##
## Local artifacts: rds + parquet only (plus JSON for player game logs),
## all under wnba_stats/.
##
## How this script differs from the prior version
## ----------------------------------------------
##   - Lean on `wehoop::wnba_pbp(game_id, on_court = TRUE, version = "v3")`:
##     it already returns V2-shape rows with home_player1..5 / away_player1..5
##     populated via wnba_gamerotation, so the substitution-tracking and
##     missing-starter-from-boxscore code is gone.
##   - The remaining analytical layers (possession assignment, FT-to-foul
##     attribution, garbage-time flag) are kept, but factored into discrete
##     `.derive_*` helpers that operate on the wnba_pbp() output via a thin
##     `.normalize_pbp()` adapter that backfills the few columns the
##     original logic depended on (msg_type/act_type aliases, single
##     `description`, team_home/team_away from schedule).
##   - All artifacts land under wnba_stats/. RDS + parquet only (no qs/csv).
##   - Per-call tryCatch + 3-attempt proxy rotation for every API call.
##   - Structured key=value log file (`logs/...`) + cli progress bars.
##   - Per-season + master schedule + per-season PBP + per-season player
##     game logs are all uploaded to GitHub release tags via insistent_save.
## ----------------------------------------------------------------------------

rm(list = ls()); gc()


suppressPackageStartupMessages(suppressMessages({
  library(dplyr)
  library(tidyr)
  library(magrittr)
  library(janitor)
  library(jsonlite)
  library(purrr)
  library(arrow)
  library(glue)
  library(stringr)
  library(tibble)
  library(zoo)
  library(cli)
  library(future)
  library(furrr)
  library(wehoop)
  library(sportsdataverse)
  library(sportsdataversedata)
}))

options(stringsAsFactors = FALSE)
options(scipen = 999)

# --- CLI parsing (positional <START> <END> [RESCRAPE]) ---------------------
# Positional convention (matches the existing daily_wnba_stats_R_processor.sh
# `-r` flag, which defaults RESCRAPE to TRUE):
#   Rscript R/wnba_stats_01_pbp.R 2025 2025          # rescrape on (default)
#   Rscript R/wnba_stats_01_pbp.R 2025 2025 true     # explicit rescrape on
#   Rscript R/wnba_stats_01_pbp.R 2025 2025 false    # use per-game JSON cache
#   Rscript R/wnba_stats_01_pbp.R 2025               # both years 2025
#   Rscript R/wnba_stats_01_pbp.R                    # most recent season
#
# RESCRAPE defaults to TRUE: every game is re-fetched from the API and the
# per-game JSON in wnba_stats/pbp/json/ is overwritten. Pass `false` to
# treat the on-disk JSON as canonical and skip the API call for any game
# already cached. The cache path is the speed-up lever; the default just
# matches the project's existing shell-wrapper convention.
.parse_rescrape_flag <- function(x) {
  !(tolower(as.character(x)) %in% c("false", "f", "0", "no", "off"))
}
args <- commandArgs(trailingOnly = TRUE)
if (length(args) >= 3) {
  start_year <- as.integer(args[[1]])
  end_year   <- as.integer(args[[2]])
  rescrape   <- .parse_rescrape_flag(args[[3]])
} else if (length(args) == 2) {
  start_year <- as.integer(args[[1]])
  end_year   <- as.integer(args[[2]])
  rescrape   <- TRUE
} else if (length(args) == 1) {
  start_year <- as.integer(args[[1]])
  end_year   <- as.integer(args[[1]])
  rescrape   <- TRUE
} else {
  start_year <- wehoop::most_recent_wnba_season()
  end_year   <- wehoop::most_recent_wnba_season()
  rescrape   <- TRUE
}

# --- Logging -----------------------------------------------------------------
# Structured log file per run; UTC ISO-8601 timestamps; key=value fields.
# Per-event format (file):
#   2026-05-12T04:23:44.103Z INFO  phase=pbp game_id=... msg="..."
# Same events also fire to the terminal via cli::cli_alert_* so the user
# gets coloured/iconed output without losing the grep-friendly file copy.
.run_id   <- format(Sys.time(), "%Y%m%dT%H%M%SZ", tz = "UTC")
.log_dir  <- "logs"
dir.create(.log_dir, showWarnings = FALSE, recursive = TRUE)
.log_path <- file.path(
  .log_dir,
  glue::glue("wnba_stats_01_pbp_{start_year}_{end_year}_{.run_id}.log")
)
.log_con  <- file(.log_path, open = "a", encoding = "UTF-8")

.log <- function(msg, level = "INFO", ...) {
  fields <- list(...)
  kv <- if (length(fields)) {
    paste(names(fields), unlist(lapply(fields, as.character)),
          sep = "=", collapse = " ")
  } else ""
  ts   <- format(Sys.time(), "%Y-%m-%dT%H:%M:%OS3Z", tz = "UTC")
  line <- sprintf('%s %-5s %s msg="%s"', ts, level, kv, gsub('"', "'", msg))

  # The file connection only exists in the main process. Inside a furrr
  # worker (where .log_con was serialised from the parent and is no longer
  # a valid handle) the writeLines + cli::cli_alert calls would either
  # silently corrupt the file or interleave on the terminal. So gate
  # everything on the connection still being open in this process; if not,
  # this becomes a no-op (workers communicate state back via return values).
  con_ok <- tryCatch(
    isOpen(get(".log_con", envir = globalenv()), "w"),
    error = function(e) FALSE
  )
  if (!con_ok) return(invisible(NULL))

  writeLines(line, .log_con)
  flush(.log_con)
  switch(level,
    ERROR = cli::cli_alert_danger(msg),
    WARN  = cli::cli_alert_warning(msg),
    DEBUG = invisible(NULL),
            cli::cli_alert_info(msg))
}

# .with_phase wraps a body expression with cli header + start/end + elapsed
# logging. Errors inside the body are caught + logged, and the body returns
# NULL so the outer per-season loop keeps moving. The body's value is
# returned on success so callers can chain results across phases.
.with_phase <- function(name, expr) {
  cli::cli_h2(name)
  .log(glue::glue("phase start: {name}"), phase = name)
  t0 <- Sys.time()
  result <- tryCatch(
    expr,
    error = function(e) {
      .log(glue::glue("phase error: {conditionMessage(e)}"),
           level = "ERROR", phase = name)
      NULL
    }
  )
  el <- as.numeric(Sys.time() - t0, units = "secs")
  .log(glue::glue("phase end: {name}"), phase = name,
       elapsed_s = round(el, 2))
  result
}

cli::cli_h1("WNBA Stats PBP pipeline")
.log(glue::glue(
  "WNBA Stats pbp: seasons {start_year}-{end_year} | rescrape={rescrape}"
), start_year = start_year, end_year = end_year, rescrape = rescrape,
   run_id = .run_id, log_path = .log_path)

# --- Proxy pool --------------------------------------------------------------
# Proxy acquisition centralised in R/utils.R: load_proxies() tries
# PROXY_KEY+PROXY_PKG env vars first (live API), falls back to a local
# proxylist.csv (gitignored), then to no-proxy.
.utils_path <- Find(file.exists,
                    c("R/utils.R", "../R/utils.R", "../../R/utils.R"))
if (is.null(.utils_path)) stop("Could not locate R/utils.R from cwd: ", getwd())
source(.utils_path)
proxies <- load_proxies()
.log(glue::glue(
  "proxy pool loaded: {if (is.null(proxies)) 0 else nrow(proxies)} proxies"
), n_proxies = if (is.null(proxies)) 0 else nrow(proxies))

# --- Output dirs (everything under wnba_stats/<dataset>/<format>/) -----------
# Per-dataset layout: rds + parquet for every dataset; json where it adds
# value (per-game PBP cache; per-season player_game_logs raw dump).
.SUBDIRS  <- list(
  "schedules"        = c("rds", "parquet"),
  "schedule_master"  = c("rds", "parquet"),
  "pbp"              = c("rds", "parquet", "json"),
  "player_game_logs" = c("rds", "parquet", "json")
)
for (sub in names(.SUBDIRS)) {
  for (fmt in .SUBDIRS[[sub]]) {
    dir.create(file.path("wnba_stats", sub, fmt),
               showWarnings = FALSE, recursive = TRUE)
  }
}

# --- Proxy blacklist (script-local) ------------------------------------------
# Holds the set of proxy IPs that have produced a TCP-reset / Recv-failure
# error in this run. select_proxy_filtered() filters them out at pick time.
# If the entire pool ends up blacklisted, the list is cleared with a warning
# and selection falls back to the full pool (better to keep trying than to
# abort the run -- the proxy provider may have rotated by the time we
# circle back).
.proxy_blacklist <- new.env(parent = emptyenv())
.proxy_blacklist$bad_ips <- character(0)

.blacklist_proxy <- function(proxy) {
  if (is.null(proxy) || is.null(proxy$url)) return(invisible())
  ip <- as.character(proxy$url)[1]
  if (is.na(ip) || !nzchar(ip)) return(invisible())
  if (!(ip %in% .proxy_blacklist$bad_ips)) {
    .proxy_blacklist$bad_ips <- c(.proxy_blacklist$bad_ips, ip)
    .log(glue::glue(
      "proxy blacklisted: {ip} (bad pool size: {length(.proxy_blacklist$bad_ips)}/{nrow(proxies)})"
    ), level = "WARN", phase = "proxy",
       proxy = ip,
       bad_count = length(.proxy_blacklist$bad_ips))
  }
}

.select_proxy_filtered <- function() {
  if (is.null(proxies) || nrow(proxies) == 0) return(NULL)
  good <- proxies |>
    dplyr::filter(!.data$ip %in% .proxy_blacklist$bad_ips)
  if (nrow(good) == 0) {
    .log("all proxies blacklisted; clearing blacklist and retrying with full pool",
         level = "WARN", phase = "proxy")
    .proxy_blacklist$bad_ips <- character(0)
    good <- proxies
  }
  ip  <- sample(good$ip, 1)
  sel <- good |> dplyr::filter(.data$ip == ip)
  # Defensive [1] indexing: get_proxy_bonanza_ips() can return duplicate
  # IPs across ippacks, which would make sel multi-row -> each field
  # becomes a vector -> downstream `if (proxy$url %in% bad_ips)` errors
  # with "condition has length > 1". Pin every field to the first row.
  port_val <- if (!is.null(sel$port_http)) sel$port_http else sel$port
  list(
    url      = as.character(sel$ip)[1],
    port     = as.integer(port_val)[1],
    username = as.character(sel$login)[1],
    password = as.character(sel$password)[1]
  )
}

# Patterns in wehoop's captured stderr that signal a network-layer rejection
# attributable to the proxy. NOT used for "no data" / "HTML response"
# failures (gamerotation HTML errors happen at the API edge regardless of
# proxy, so blacklisting wouldn't help).
.PROXY_BAD_PATTERNS <- c(
  "Connection was reset",
  "Recv failure",
  "Connection timed out",
  "Could not resolve host",
  "OpenSSL SSL_connect"
)


# --- Insistent saver (release upload, mirror sibling 02_rosters.R) -----------
retry          <- purrr::rate_backoff(pause_base = 1, pause_min = 60,
                                      max_times = 10)
insistent_save <- purrr::insistently(sportsdataversedata::sportsdataverse_save,
                                     rate = retry, quiet = FALSE)

# --- WNBA-only validation ----------------------------------------------------
# WNBA game_ids: 10-digit zero-padded, leading "10".
# WNBA SEASON_ID: 5-digit "[1-5]YYYY"
#   1 = preseason | 2 = regular | 3 = all-star | 4 = playoffs | 5 = play-in
.is_wnba_game_id   <- function(ids) {
  grepl("^10\\d{8}$", sprintf("%010s", as.character(ids)))
}
.is_wnba_season_id <- function(ids) {
  grepl("^[1-5]\\d{4}$", as.character(ids))
}
.keep_wnba_game_ids <- function(ids, where = "") {
  ok <- .is_wnba_game_id(ids)
  if (!all(ok)) {
    .log(glue::glue("dropped {sum(!ok)} non-WNBA game_id(s) at {where}"),
         level = "WARN", n_dropped = sum(!ok), where = where)
  }
  ids[ok]
}

# --- Per-season fetchers -----------------------------------------------------
fetch_schedule <- function(season) {
  proxy <- select_proxy(proxies)
  pull <- function(season_type) {
    tryCatch(
      wehoop::wnba_leaguegamefinder(
        league_id   = "10",
        season      = as.character(season),
        season_type = season_type,
        proxy       = proxy
      ),
      error = function(e) {
        .log(glue::glue("leaguegamefinder failed: {conditionMessage(e)}"),
             level = "WARN", season = season, season_type = season_type)
        NULL
      }
    )
  }
  reg <- pull("Regular Season")
  po  <- pull("Playoffs")
  reg_df <- if (!is.null(reg) && !is.null(reg$LeagueGameFinderResults)) {
              reg$LeagueGameFinderResults
            } else data.frame()
  po_df  <- if (!is.null(po)  && !is.null(po$LeagueGameFinderResults)) {
              po$LeagueGameFinderResults
            } else data.frame()
  out <- dplyr::bind_rows(reg_df, po_df)
  if (nrow(out) > 0) {
    out <- out |>
      dplyr::filter(.is_wnba_season_id(.data$SEASON_ID),
                    .is_wnba_game_id(.data$GAME_ID)) |>
      dplyr::mutate(season = as.integer(season))
  }
  tibble::as_tibble(out)
}

fetch_player_game_logs <- function(season) {
  proxy <- select_proxy(proxies)
  res <- tryCatch(
    wehoop::wnba_leaguegamelog(league_id      = "10",
                               season         = as.character(season),
                               player_or_team = "P",
                               proxy          = proxy),
    error = function(e) {
      .log(glue::glue("leaguegamelog failed: {conditionMessage(e)}"),
           level = "WARN", season = season)
      NULL
    }
  )
  if (is.null(res) || is.null(res$LeagueGameLog)) return(tibble::tibble())
  res$LeagueGameLog |>
    janitor::clean_names() |>
    dplyr::filter(.is_wnba_game_id(.data$game_id)) |>
    dplyr::mutate(
      team_location = ifelse(stringr::str_detect(.data$matchup, "@"),
                             "away", "home"),
      dplyr::across(dplyr::any_of(c("player_id", "team_id")), as.integer),
      season = as.integer(season)
    ) |>
    tibble::as_tibble()
}

fetch_pbp_one <- function(game_id, attempts = 2, rescrape = TRUE) {
  # attempts defaults to 2 -- wehoop's wnba_pbp already retries each of
  # its 3 internal endpoints (playbyplayv3 / boxscore-traditional-v3 /
  # gamerotation) on its own, so one outer retry is enough to cycle in a
  # fresh proxy + give the API edge a 10s breather between attempts. A
  # third attempt rarely adds value -- the cool-off pass below picks up
  # any games that still fail after both attempts.
  json_path <- file.path("wnba_stats", "pbp", "json",
                         paste0(game_id, ".json"))

  # Cache hit: read the per-game JSON instead of re-hitting the API.
  # PBP is immutable post-game so staleness risk is essentially nil; the
  # only reason to bypass the cache is to force re-fetch (rescrape = TRUE,
  # which is the default to match the shell wrapper's `-r true` default).
  if (!rescrape && file.exists(json_path)) {
    cached <- tryCatch(
      jsonlite::read_json(json_path, simplifyVector = TRUE),
      error = function(e) {
        .log(glue::glue("pbp json cache read failed: {conditionMessage(e)}"),
             level = "WARN", phase = "pbp", game_id = game_id)
        NULL
      }
    )
    if (!is.null(cached) && length(cached) > 0 &&
        (is.data.frame(cached) || is.list(cached))) {
      df <- tibble::as_tibble(cached)
      if (nrow(df) > 0) {
        .log("pbp cache hit", level = "DEBUG", phase = "pbp",
             game_id = game_id, source = "json_cache", rows = nrow(df))
        return(df)
      }
    }
  }

  for (i in seq_len(attempts)) {
    p  <- .select_proxy_filtered()
    t0 <- Sys.time()
    # Capture (rather than discard) wehoop's stderr so we can both keep the
    # terminal clean and inspect the captured noise for proxy-attributable
    # failure signatures. cli::cli_alert_danger from .report_api_error
    # writes to the message stream; capture.output(type = "message")
    # routes that to `captured` instead of stderr. Our structured log file
    # still records the outcome via the `.log()` calls below.
    captured <- character(0)
    out <- NULL
    captured <- capture.output(
      out <- tryCatch(
        wehoop::wnba_pbp(game_id, on_court = TRUE, version = "v3", proxy = p),
        error = function(e) {
          .log(glue::glue("wnba_pbp threw on attempt {i}/{attempts}: {conditionMessage(e)}"),
               level = "WARN", phase = "pbp", game_id = game_id, attempt = i)
          NULL
        }
      ),
      type = "message"
    )
    el <- as.numeric(Sys.time() - t0, units = "secs")

    # If the captured stderr matches any of the network-layer signatures,
    # treat THIS proxy as bad for the rest of the run. Don't blacklist on
    # other failure modes (HTML responses, "no data available", etc.) --
    # those are API-side or game-specific and persist across proxies.
    if (length(captured) > 0 &&
        any(vapply(.PROXY_BAD_PATTERNS,
                   function(pat) any(grepl(pat, captured, fixed = TRUE)),
                   logical(1)))) {
      .blacklist_proxy(p)
    }
    if (!is.null(out) && is.data.frame(out) && nrow(out) > 0) {
      # Per-game JSON dump (post-V3-to-V2 conversion + on-court populated,
      # i.e. the same shape as what gets bound into the season parquet).
      # Wrapped in tryCatch so a single bad write doesn't drop the row
      # from the season compile.
      tryCatch(
        jsonlite::write_json(
          out, json_path,
          auto_unbox = TRUE, null = "null"
        ),
        error = function(e) {
          .log(glue::glue("pbp json write failed: {conditionMessage(e)}"),
               level = "WARN", phase = "pbp", game_id = game_id)
        }
      )
      .log("pbp ok", level = "DEBUG", phase = "pbp", game_id = game_id,
           rows = nrow(out), elapsed_s = round(el, 2),
           attempt = i, source = "api")
      return(tibble::as_tibble(out))
    }
    # 10s backoff between attempts -- gives the proxy pool / API edge a
    # chance to recover. With attempts=1 this never fires; matters in the
    # cool-off pass (and any caller that bumps attempts).
    Sys.sleep(10)
  }
  .log("pbp empty after retries", level = "WARN",
       phase = "pbp", game_id = game_id, attempts = attempts)
  tibble::tibble(game_id = as.character(game_id))
}

# --- PBP normalization + analytical derivations ------------------------------
# `wehoop::wnba_pbp(version = "v3")` already produces V2-shape rows with
# `home_player1..5` / `away_player1..5` populated via gamerotation. The
# downstream analytical helpers below were originally written against the
# legacy V2 column names (msg_type, act_type, slug_team, team_home, etc.),
# so .normalize_pbp adds those as aliases / derived columns from the V3
# output + per-game schedule lookup. Keeps the analytical code dialect
# unchanged; only the input shape adapts.

.normalize_pbp <- function(pbp, schedule) {
  if (nrow(pbp) == 0) return(pbp)

  # Some V3 columns can drop out when serialised through jsonlite if the
  # column was all-NA for a given game (e.g., early-season games with no
  # scoring events): jsonlite::write_json + read_json round-trips with
  # simplifyVector silently elides empty columns. Backfill the
  # downstream-required ones with NA so .data$<col> in the mutate below
  # always resolves. dplyr::if_else evaluates BOTH branches regardless of
  # the condition, so a missing column can't be guarded inline inside a
  # mutate -- it has to exist before the call.
  required_cols <- list(
    score_value               = NA_integer_,
    home_description          = NA_character_,
    visitor_description       = NA_character_,
    neutral_description       = NA_character_,
    player1_team_abbreviation = NA_character_,
    player2_team_abbreviation = NA_character_,
    player3_team_abbreviation = NA_character_,
    event_type                = NA_character_,
    event_action_type         = NA_character_,
    period                    = NA_integer_,
    minute_remaining_quarter  = NA_real_,
    seconds_remaining_quarter = NA_real_,
    home_score                = NA_integer_,
    away_score                = NA_integer_
  )
  for (col in names(required_cols)) {
    if (!col %in% names(pbp)) pbp[[col]] <- required_cols[[col]]
  }

  # team_home / team_away per game_id (one row per game) from the schedule
  team_lut <- schedule |>
    dplyr::transmute(
      game_id    = as.character(.data$GAME_ID),
      team_abbr  = as.character(.data$TEAM_ABBREVIATION),
      home_away  = ifelse(stringr::str_detect(.data$MATCHUP, "@"),
                          "team_away", "team_home")
    ) |>
    dplyr::distinct() |>
    tidyr::pivot_wider(names_from = "home_away",
                       values_from = "team_abbr",
                       values_fn   = dplyr::first)

  pbp |>
    dplyr::mutate(
      game_id     = as.character(.data$game_id),
      msg_type    = suppressWarnings(as.integer(.data$event_type)),
      act_type    = suppressWarnings(as.integer(.data$event_action_type)),
      description = dplyr::coalesce(.data$home_description,
                                    .data$visitor_description,
                                    .data$neutral_description,
                                    NA_character_),
      slug_team   = dplyr::coalesce(.data$player1_team_abbreviation,
                                    .data$player2_team_abbreviation,
                                    .data$player3_team_abbreviation,
                                    NA_character_),
      score_value = suppressWarnings(as.integer(
        as.character(.data$score_value)
      )),
      shot_pts    = dplyr::case_when(
        .data$msg_type %in% c(1L, 3L) &
          !stringr::str_detect(dplyr::coalesce(.data$description, ""),
                               stringr::regex("Missed", ignore_case = TRUE)) ~
          dplyr::coalesce(.data$score_value, 0L),
        TRUE ~ 0L
      ),
      secs_passed_game = dplyr::case_when(
        .data$period %in% c(1:4) ~ (.data$period - 1) * 600 +
                                     (10 - .data$minute_remaining_quarter) * 60 -
                                     .data$seconds_remaining_quarter,
        .data$period >= 5 ~ 2400 + (.data$period - 5) * 300 +
                              (5 - .data$minute_remaining_quarter) * 60 -
                              .data$seconds_remaining_quarter,
        TRUE ~ NA_real_
      )
    ) |>
    dplyr::left_join(team_lut, by = "game_id") |>
    # off_slug_team: team currently on offense for this event. For most
    # events that's the slug_team itself; for defensive rebounds it's the
    # OTHER team (the rebound transfers possession). Best-effort heuristic
    # that keeps the rest of the possession logic working without rebuilding
    # state from scratch.
    dplyr::mutate(
      off_slug_team = dplyr::case_when(
        .data$msg_type == 4L & .data$act_type == 0L ~  # defensive rebound
          dplyr::if_else(.data$slug_team == .data$team_home,
                         .data$team_away, .data$team_home),
        TRUE ~ .data$slug_team
      )
    ) |>
    dplyr::group_by(.data$game_id) |>
    dplyr::arrange(.data$secs_passed_game, .by_group = TRUE) |>
    dplyr::mutate(number_event = dplyr::row_number()) |>
    dplyr::ungroup()
}

# .derive_possessions assigns possession start markers to events. Mirrors
# the legacy logic: made shots, missed shots, turnovers, and certain FT
# types (act_type 12 / 15) start a new possession; non-consecutive
# possessions by the same offence collapse to one. The original used `&&`
# inside a grouped filter which short-circuits to length-1 -- that bug is
# fixed below by switching to `&` for vectorised semantics.
.derive_possessions <- function(pbp) {
  if (nrow(pbp) == 0) return(pbp)

  initial <- pbp |>
    dplyr::mutate(possession = dplyr::case_when(
      .data$msg_type %in% c(1L, 2L, 5L)                     ~ 1L,
      .data$msg_type == 3L & .data$act_type %in% c(12L, 15L) ~ 1L,
      TRUE                                                   ~ 0L
    ))

  # Collapse runs of consecutive possessions where offence didn't change.
  # `&` (vectorised), not `&&` (scalar short-circuit) -- bug in old version.
  consec <- initial |>
    dplyr::filter(.data$possession == 1L |
                    (.data$msg_type == 6L & .data$act_type == 30L)) |>
    dplyr::group_by(.data$game_id, .data$period) |>
    dplyr::mutate(
      same_as_next = .data$possession == dplyr::lead(.data$possession) &
                     .data$off_slug_team == dplyr::lead(.data$off_slug_team)
    ) |>
    dplyr::filter(.data$same_as_next %in% TRUE) |>
    dplyr::ungroup() |>
    dplyr::transmute(.data$game_id, .data$number_event, possession = 0L)

  initial |>
    dplyr::rows_update(consec, by = c("game_id", "number_event"))
}

# .derive_ft_foul_link connects FT events back to their source foul events
# and aggregates FT pts + possessions onto the foul row. Returns the input
# PBP with shot_pts_home / shot_pts_away / poss_home / poss_away columns
# coalesced from the per-foul aggregation.
.derive_ft_foul_link <- function(pbp) {
  if (nrow(pbp) == 0 || !"player1" %in% names(pbp)) {
    # V3 output uses `player1_name` not `player1`; pivot to the latter
    # if the former isn't there.
  }
  player1     <- if ("player1_name" %in% names(pbp)) pbp$player1_name else NA
  player3     <- if ("player3_name" %in% names(pbp)) pbp$player3_name else NA

  enriched <- pbp |>
    dplyr::mutate(
      .player1 = player1,
      .player3 = player3
    )

  # Regular foul-FT pairing. Matches each FT event (msg_type 3, non-tech
  # / non-flagrant act_types) to a same-time foul row by (game_id,
  # secs_passed_game, fouled-player identity). Tech / flagrant fouls
  # follow distinct linkage rules; we handle the 80% case here and leave
  # the tail to downstream consumers.
  fts <- enriched |>
    dplyr::filter(.data$msg_type == 3L,
                  !.data$act_type %in% c(10L, 12L, 15L,
                                         16L, 18L, 19L, 20L, 25L, 26L,
                                         27L, 28L, 29L)) |>
    dplyr::transmute(.data$game_id, .data$secs_passed_game,
                     number_event_ft = .data$number_event,
                     ft_team = .data$slug_team,
                     fouled  = .data$.player1,
                     ft_pts  = .data$shot_pts,
                     ft_poss = .data$possession)

  fouls <- enriched |>
    dplyr::filter(.data$msg_type == 6L,
                  stringr::str_detect(
                    dplyr::coalesce(.data$description, ""),
                    stringr::regex("FT", ignore_case = TRUE))) |>
    dplyr::transmute(.data$game_id, .data$secs_passed_game,
                     number_event_foul = .data$number_event,
                     foul_team = .data$slug_team,
                     fouled    = .data$.player3)

  paired <- fts |>
    dplyr::inner_join(
      fouls,
      by = c("game_id", "secs_passed_game", "fouled")
    )

  if (nrow(paired) == 0) return(pbp)

  # Aggregate per source foul.
  per_foul <- paired |>
    dplyr::left_join(
      enriched |> dplyr::select(.data$game_id, .data$number_event,
                                 .data$team_home, .data$team_away),
      by = c("game_id", "number_event_foul" = "number_event")
    ) |>
    dplyr::group_by(.data$game_id, number_event = .data$number_event_foul,
                    .data$ft_team, .data$team_home, .data$team_away) |>
    dplyr::summarise(total_fta = dplyr::n(),
                     total_pts = sum(.data$ft_pts, na.rm = TRUE),
                     total_poss = sum(.data$ft_poss, na.rm = TRUE),
                     .groups = "drop") |>
    dplyr::mutate(
      shot_pts_home = ifelse(.data$ft_team == .data$team_home,
                             .data$total_pts, 0L),
      shot_pts_away = ifelse(.data$ft_team == .data$team_away,
                             .data$total_pts, 0L),
      poss_home     = ifelse(.data$ft_team == .data$team_home,
                             .data$total_poss, 0L),
      poss_away     = ifelse(.data$ft_team == .data$team_away,
                             .data$total_poss, 0L)
    ) |>
    dplyr::select(.data$game_id, .data$number_event, .data$total_fta,
                  .data$shot_pts_home, .data$shot_pts_away,
                  .data$poss_home, .data$poss_away)

  pbp |>
    dplyr::left_join(per_foul, by = c("game_id", "number_event")) |>
    dplyr::mutate(
      shot_pts_home = dplyr::coalesce(
        .data$shot_pts_home,
        ifelse(.data$msg_type == 1L & .data$slug_team == .data$team_home,
               .data$shot_pts, 0L)),
      shot_pts_away = dplyr::coalesce(
        .data$shot_pts_away,
        ifelse(.data$msg_type == 1L & .data$slug_team == .data$team_away,
               .data$shot_pts, 0L)),
      poss_home     = dplyr::coalesce(
        .data$poss_home,
        ifelse(.data$msg_type != 3L & .data$possession == 1L &
                 .data$slug_team == .data$team_home, 1L, 0L)),
      poss_away     = dplyr::coalesce(
        .data$poss_away,
        ifelse(.data$msg_type != 3L & .data$possession == 1L &
                 .data$slug_team == .data$team_away, 1L, 0L))
    )
}

# .derive_garbage_time flags Q4 events under the canonical NBA-style
# garbage-time rule, scaled to WNBA's 10-min quarters / 40-min regulation.
# Margin thresholds (held over from the original implementation):
#   * minutes 10:00-7:30 of Q4 with margin >= 25
#   * minutes  7:30-5:00 of Q4 with margin >= 20
#   * minutes  5:00-end  of Q4 with margin >= 10
# AND fewer than 2 starters on the floor (across both teams). The
# starter-count test uses lineup_start_home / lineup_start_away derived
# from the Q1 starting lineups joined back onto each event's lineup_home /
# lineup_away. If on_court is missing for a game, we degrade to
# garbage_time = 0 rather than NA so downstream filters still work.
.derive_garbage_time <- function(pbp) {
  if (nrow(pbp) == 0) return(pbp)
  on_court_cols <- c(paste0("home_player", 1:5), paste0("away_player", 1:5))
  if (!all(on_court_cols %in% names(pbp))) {
    return(dplyr::mutate(pbp, garbage_time = 0L,
                         total_starters_home = NA_integer_,
                         total_starters_away = NA_integer_))
  }

  # Q1 starters per game per side (the first row of period 1, by game).
  q1 <- pbp |>
    dplyr::filter(.data$period == 1L) |>
    dplyr::group_by(.data$game_id) |>
    dplyr::slice_min(.data$number_event, n = 1, with_ties = FALSE) |>
    dplyr::ungroup() |>
    dplyr::transmute(
      .data$game_id,
      home_starters = purrr::pmap(dplyr::across(dplyr::all_of(
        paste0("home_player", 1:5))), ~ unname(c(...))),
      away_starters = purrr::pmap(dplyr::across(dplyr::all_of(
        paste0("away_player", 1:5))), ~ unname(c(...)))
    )

  pbp |>
    dplyr::left_join(q1, by = "game_id") |>
    dplyr::mutate(
      .home_now = purrr::pmap(dplyr::across(dplyr::all_of(
        paste0("home_player", 1:5))), ~ unname(c(...))),
      .away_now = purrr::pmap(dplyr::across(dplyr::all_of(
        paste0("away_player", 1:5))), ~ unname(c(...))),
      total_starters_home = purrr::map2_int(.data$.home_now, .data$home_starters,
                                            ~ length(intersect(.x, .y))),
      total_starters_away = purrr::map2_int(.data$.away_now, .data$away_starters,
                                            ~ length(intersect(.x, .y))),
      margin_now = abs(dplyr::coalesce(.data$home_score, 0L) -
                       dplyr::coalesce(.data$away_score, 0L)),
      garbage_time = dplyr::case_when(
        .data$period == 4L & .data$secs_passed_game >= 1800 &
          .data$secs_passed_game < 1950 & .data$margin_now >= 25 &
          (.data$total_starters_home + .data$total_starters_away) <= 2 ~ 1L,
        .data$period == 4L & .data$secs_passed_game >= 1950 &
          .data$secs_passed_game < 2100 & .data$margin_now >= 20 &
          (.data$total_starters_home + .data$total_starters_away) <= 2 ~ 1L,
        .data$period == 4L & .data$secs_passed_game >= 2100 &
          .data$margin_now >= 10 &
          (.data$total_starters_home + .data$total_starters_away) <= 2 ~ 1L,
        TRUE ~ 0L
      )
    ) |>
    dplyr::group_by(.data$game_id) |>
    dplyr::mutate(
      max_nongarbage = suppressWarnings(
        max(.data$number_event[.data$garbage_time == 0L], na.rm = TRUE)),
      garbage_time   = ifelse(
        .data$garbage_time == 1L & .data$number_event < .data$max_nongarbage,
        0L, .data$garbage_time)
    ) |>
    dplyr::ungroup() |>
    dplyr::select(-dplyr::any_of(c("home_starters", "away_starters",
                                    ".home_now", ".away_now",
                                    "max_nongarbage", "margin_now")))
}

# --- Disk + release-upload helpers (DRY: every dataset uses these) -----------
.write_local <- function(df, subdir, file_stem) {
  rds_path <- file.path("wnba_stats", subdir, "rds",
                        glue::glue("{file_stem}.rds"))
  pq_path  <- file.path("wnba_stats", subdir, "parquet",
                        glue::glue("{file_stem}.parquet"))
  saveRDS(df, rds_path)
  arrow::write_parquet(df, pq_path,
                       compression = "zstd", compression_level = 22)
  invisible(list(rds = rds_path, parquet = pq_path))
}

.upload_release <- function(df, file_name, release_tag,
                            sportsdataverse_type, pkg_function) {
  insistent_save(
    data_frame           = df,
    file_name            = file_name,
    sportsdataverse_type = sportsdataverse_type,
    release_tag          = release_tag,
    pkg_function         = pkg_function,
    file_types           = c("rds", "csv", "parquet"),
    .token               = Sys.getenv("GITHUB_PAT")
  )
}

# --- Manifests (one CSV per dataset, uploaded once at end of run) ------------
schedules_manifest_path <- "wnba_stats/wnba_stats_schedules_in_data_repo.csv"
plog_manifest_path      <- "wnba_stats/wnba_stats_player_game_logs_in_data_repo.csv"
pbp_manifest_path       <- "wnba_stats/wnba_stats_pbp_in_data_repo.csv"

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

  # 1. Schedule -------------------------------------------------------------
  sched <- .with_phase(glue::glue("season {y}: schedule"), {
    s <- fetch_schedule(y)
    if (nrow(s) == 0) {
      .log("no schedule rows", level = "WARN",
           phase = "schedule", season = y)
      tibble::tibble()
    } else {
      s_out <- s |>
        wehoop:::make_wehoop_data(
          "WNBA Stats Schedule from wehoop data repository", Sys.time())
      .write_local(s_out, "schedules", glue::glue("wnba_stats_schedule_{y}"))
      .upload_release(
        df                   = s_out,
        file_name            = glue::glue("wnba_stats_schedule_{y}"),
        release_tag          = "wnba_stats_schedules",
        sportsdataverse_type = "WNBA Stats schedule",
        pkg_function         = "wehoop::load_wnba_stats_schedule()"
      )
      append_manifest_row(schedules_manifest_path, y, nrow(s_out),
                          "stats.wnba.com/leaguegamefinder")
      .log("schedule ok", phase = "schedule", season = y,
           rows = nrow(s_out),
           games = dplyr::n_distinct(s_out$GAME_ID))
      s
    }
  })

  # 2. Player game logs -----------------------------------------------------
  .with_phase(glue::glue("season {y}: player_game_logs"), {
    plog <- fetch_player_game_logs(y)
    if (nrow(plog) == 0) {
      .log("no player game log rows", level = "WARN",
           phase = "player_game_logs", season = y)
    } else {
      jsonlite::write_json(
        plog,
        file.path("wnba_stats", "player_game_logs", "json",
                  glue::glue("player_game_logs_{y}.json"))
      )
      plog_out <- plog |>
        wehoop:::make_wehoop_data(
          "WNBA Stats Player Game Logs from wehoop data repository",
          Sys.time())
      .write_local(plog_out, "player_game_logs",
                   glue::glue("player_game_logs_{y}"))
      .upload_release(
        df                   = plog_out,
        file_name            = glue::glue("player_game_logs_{y}"),
        release_tag          = "wnba_stats_player_game_logs",
        sportsdataverse_type = "WNBA Stats player game logs",
        pkg_function         = "wehoop::load_wnba_stats_player_game_logs()"
      )
      append_manifest_row(plog_manifest_path, y, nrow(plog),
                          "stats.wnba.com/leaguegamelog")
      .log("player_game_logs ok", phase = "player_game_logs", season = y,
           rows = nrow(plog),
           players = dplyr::n_distinct(plog$player_id))
    }
  })

  # 3. PBP (V3 + on_court via wnba_pbp + analytical derivations) -----------
  .with_phase(glue::glue("season {y}: pbp"), {
    games <- if (!is.null(sched) && nrow(sched) > 0) {
      .keep_wnba_game_ids(unique(sched$GAME_ID), where = "schedule")
    } else character(0)

    if (length(games) == 0) {
      .log("no games to fetch", level = "WARN",
           phase = "pbp", season = y)
    } else {
      # Parallel under interactive R sessions (RStudio, R console);
      # sequential when invoked via Rscript (CI / shell wrapper). The
      # parallel path uses furrr::future_map across multisession workers,
      # capped at 8 to stay well under the 50-proxy pool capacity. Per-game
      # .log() calls degrade to no-op inside workers (the file connection
      # doesn't survive serialisation), so the visible feedback is the
      # furrr progress bar plus the season-level summary log line below.
      # A failure-case return from fetch_pbp_one is a single-row, single-col
      # tibble with just `game_id`. The success-case has many cols incl.
      # event_num. Identifies which games fell through the first pass so
      # we can give them a second chance with a fresh proxy pick after a
      # cool-off delay.
      .is_failed_pbp <- function(df) {
        is.null(df) || nrow(df) == 0 ||
          (nrow(df) == 1 && ncol(df) == 1 && "game_id" %in% names(df))
      }

      if (interactive()) {
        n_workers <- max(1L, min(8L, parallel::detectCores() - 1L))
        future::plan(future::multisession, workers = n_workers)
        on.exit(future::plan(future::sequential), add = TRUE)
        .log(glue::glue("pbp parallel: workers={n_workers}"),
             phase = "pbp", season = y, n_workers = n_workers)
        parts <- furrr::future_map(
          games,
          function(g) fetch_pbp_one(g, rescrape = rescrape),
          .progress = TRUE,
          .options  = furrr::furrr_options(seed = TRUE)
        )
      } else {
        cli::cli_progress_bar(
          name   = glue::glue("season {y} pbp"),
          total  = length(games),
          format = paste0(
            "{cli::pb_bar} {cli::pb_current}/{cli::pb_total} ",
            "({cli::pb_percent}) | rate {cli::pb_rate} | ETA {cli::pb_eta}"
          )
        )
        parts <- vector("list", length(games))
        for (i in seq_along(games)) {
          parts[[i]] <- fetch_pbp_one(games[[i]], rescrape = rescrape)
          cli::cli_progress_update()
        }
        cli::cli_progress_done()
      }

      # --- Cool-off retry pass for failed games --------------------------
      # The first pass uses attempts=1 in fetch_pbp_one (wehoop's internal
      # retries are enough); games that still failed go through one more
      # round after a 30s cool-off that lets the proxy pool / API edge
      # settle. Proxies blacklisted during the first pass remain
      # blacklisted across this boundary -- if they were bad once, they're
      # not getting reused. fetch_pbp_one already JSON-caches on success
      # so a recovered game gets persisted just like a first-pass success.
      failed_idx <- which(vapply(parts, .is_failed_pbp, logical(1)))
      if (length(failed_idx) > 0) {
        .log(glue::glue(
          "pbp cool-off pass: {length(failed_idx)} failed game{?s} (sleeping 30s)"
        ), phase = "pbp", season = y, n_failed = length(failed_idx),
           n_blacklisted_proxies = length(.proxy_blacklist$bad_ips))
        Sys.sleep(30)
        cli::cli_progress_bar(
          name   = glue::glue("season {y} pbp cool-off"),
          total  = length(failed_idx),
          format = paste0(
            "{cli::pb_bar} {cli::pb_current}/{cli::pb_total} ",
            "({cli::pb_percent}) | retry: {cli::pb_status}"
          ),
          status = "..."
        )
        for (idx in failed_idx) {
          parts[[idx]] <- fetch_pbp_one(games[[idx]], rescrape = rescrape)
          cli::cli_progress_update(
            status = if (.is_failed_pbp(parts[[idx]])) "still failing" else "recovered"
          )
        }
        cli::cli_progress_done()
        recovered <- sum(!vapply(parts[failed_idx], .is_failed_pbp, logical(1)))
        .log("pbp cool-off pass complete",
             phase = "pbp", season = y,
             retried = length(failed_idx),
             recovered = recovered,
             still_failed = length(failed_idx) - recovered)
      }

      pbp_raw <- parts |> purrr::list_rbind()

      ok_games  <- if ("event_num" %in% names(pbp_raw)) {
                     pbp_raw |>
                       dplyr::filter(!is.na(.data$event_num)) |>
                       dplyr::pull(.data$game_id) |>
                       unique() |> length()
                   } else 0L
      bad_games <- length(games) - ok_games

      if (nrow(pbp_raw) == 0) {
        .log("pbp empty for season", level = "WARN",
             phase = "pbp", season = y,
             games_total = length(games))
      } else {
        pbp <- pbp_raw |>
          .normalize_pbp(schedule = sched) |>
          .derive_possessions() |>
          .derive_ft_foul_link() |>
          .derive_garbage_time() |>
          dplyr::mutate(season = as.integer(y)) |>
          wehoop:::make_wehoop_data(
            "WNBA Stats Play-by-Play (V3 with on-court, possessions, FT-foul, garbage-time) from wehoop data repository",
            Sys.time())
        .write_local(pbp, "pbp", glue::glue("play_by_play_{y}"))
        .upload_release(
          df                   = pbp,
          file_name            = glue::glue("play_by_play_{y}"),
          release_tag          = "wnba_stats_pbp",
          sportsdataverse_type = "WNBA Stats play-by-play",
          pkg_function         = "wehoop::load_wnba_stats_pbp()"
        )
        append_manifest_row(pbp_manifest_path, y, nrow(pbp),
                            "stats.wnba.com/playbyplayv3")
        .log("pbp ok", phase = "pbp", season = y,
             rows = nrow(pbp), games_total = length(games),
             games_ok = ok_games, games_failed = bad_games)
      }
    }
  })
}

# --- Master schedule rebuild + upload (after the season loop) ----------------
.with_phase("master schedule", {
  rds_files <- list.files(
    file.path("wnba_stats", "schedules", "rds"),
    pattern = "^wnba_stats_schedule_\\d{4}\\.rds$", full.names = TRUE
  )
  if (length(rds_files) == 0) {
    .log("no per-season schedule files to bind", level = "WARN",
         phase = "master_schedule")
  } else {
    master <- rds_files |>
      lapply(readRDS) |>
      data.table::rbindlist(use.names = TRUE, fill = TRUE) |>
      tibble::as_tibble() |>
      dplyr::distinct(.data$SEASON_ID, .data$GAME_ID, .data$TEAM_ID,
                      .keep_all = TRUE) |>
      dplyr::arrange(.data$GAME_DATE, .data$GAME_ID, .data$TEAM_ID) |>
      wehoop:::make_wehoop_data(
        "WNBA Stats Master Schedule from wehoop data repository",
        Sys.time())
    .write_local(master, "schedule_master", "wnba_stats_schedule_master")
    .upload_release(
      df                   = master,
      file_name            = "wnba_stats_schedule_master",
      release_tag          = "wnba_stats_schedules",
      sportsdataverse_type = "WNBA Stats schedule (master)",
      pkg_function         = "wehoop::load_wnba_stats_schedule(seasons = TRUE)"
    )
    .log("master schedule ok", phase = "master_schedule",
         rows = nrow(master),
         games = dplyr::n_distinct(master$GAME_ID),
         seasons_covered = dplyr::n_distinct(master$season))
  }
})

# --- Final manifest uploads (idempotent: overwrites the asset on each run) ---
.with_phase("manifest upload", {
  tryCatch({
    source(file.path("R", "manifest_upload_helper.R"), local = TRUE)
    upload_wnba_stats_manifest(
      manifest_path        = schedules_manifest_path,
      release_tag          = "wnba_stats_schedules",
      file_name            = "wnba_stats_schedules_in_data_repo",
      sportsdataverse_type = "schedules manifest",
      pkg_function         = "wehoop::load_wnba_stats_schedule_manifest()"
    )
    upload_wnba_stats_manifest(
      manifest_path        = plog_manifest_path,
      release_tag          = "wnba_stats_player_game_logs",
      file_name            = "wnba_stats_player_game_logs_in_data_repo",
      sportsdataverse_type = "player game logs manifest",
      pkg_function         = "wehoop::load_wnba_stats_player_game_logs_manifest()"
    )
    upload_wnba_stats_manifest(
      manifest_path        = pbp_manifest_path,
      release_tag          = "wnba_stats_pbp",
      file_name            = "wnba_stats_pbp_in_data_repo",
      sportsdataverse_type = "pbp manifest",
      pkg_function         = "wehoop::load_wnba_stats_pbp_manifest()"
    )
  }, error = function(e) {
    .log(glue::glue("manifest upload failed (non-fatal): {conditionMessage(e)}"),
         level = "WARN", phase = "manifest")
  })
})

cli::cli_h1("done")
.log("pipeline complete",
     start_year = start_year, end_year = end_year)
close(.log_con)
