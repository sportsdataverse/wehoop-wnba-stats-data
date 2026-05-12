lib_path <- Sys.getenv("R_LIBS")

suppressPackageStartupMessages(suppressMessages(library(dplyr, lib.loc = lib_path)))
suppressPackageStartupMessages(suppressMessages(library(httr, lib.loc = lib_path)))
suppressPackageStartupMessages(suppressMessages(library(jsonlite, lib.loc = lib_path)))
suppressPackageStartupMessages(suppressMessages(library(glue, lib.loc = lib_path)))
suppressPackageStartupMessages(suppressMessages(library(purrr, lib.loc = lib_path)))
get_proxy_bonanza_ips <- function(api_key = Sys.getenv("PROXY_KEY"),
                                  user_package = Sys.getenv("PROXY_PKG")) {
  res <- httr::RETRY(
    "GET",
    glue::glue("https://proxybonanza.com/api/v1/userpackages/{user_package}.json"),
    httr::add_headers(Authorization = paste(api_key))
  ) %>%
    httr::content(as = "text", encoding = "UTF-8")

  resp <- res %>%
    jsonlite::fromJSON() %>%
    purrr::pluck("data")

  login <- resp$login
  password <- resp$password
  ips <- resp$ippacks

  ips$login <- login
  ips$password <- password
  proxies <- ips %>%
    dplyr::select("ip", "port_http", "login", "password")
  return(proxies)
}

# load_proxies() centralises proxy acquisition for every wnba_stats_*.R
# script. Priority:
#   1. API:  PROXY_KEY + PROXY_PKG env vars set -> hit proxybonanza.com
#            for fresh proxies (CI default; nothing to commit).
#   2. CSV:  fall back to a local file at csv_path (default
#            "../../proxylist.csv", matching the existing script cwd).
#            The file is gitignored; refresh weekly via
#              data.table::fwrite(get_proxy_bonanza_ips(), "proxylist.csv")
#   3. NULL: return NULL so select_proxy() yields an un-proxied httr call
#            (rate-limited but functional). Loud message either way.
load_proxies <- function(csv_path = "../../proxylist.csv") {
  api_key <- Sys.getenv("PROXY_KEY")
  api_pkg <- Sys.getenv("PROXY_PKG")
  if (nzchar(api_key) && nzchar(api_pkg)) {
    proxies <- tryCatch(
      get_proxy_bonanza_ips(api_key = api_key, user_package = api_pkg),
      error = function(e) {
        message(
          "get_proxy_bonanza_ips() failed: ", e$message,
          " -- falling back to CSV/none"
        )
        NULL
      }
    )
    if (!is.null(proxies) && nrow(proxies) > 0) return(proxies)
  }
  if (file.exists(csv_path)) {
    proxies <- tryCatch(
      data.table::fread(csv_path),
      error = function(e) {
        message(
          "fread('", csv_path, "') failed: ", e$message,
          " -- proceeding without proxies"
        )
        NULL
      }
    )
    if (!is.null(proxies) && nrow(proxies) > 0) return(proxies)
  }
  message(
    "No proxies available (no PROXY_KEY/PROXY_PKG env, no readable ",
    csv_path, "); running un-proxied"
  )
  NULL
}

# Accepts NULL or empty proxies and returns NULL (wehoop's request_with_proxy
# treats NULL as no proxy). All wnba_stats_*.R scripts call select_proxy(proxies)
# per request so a per-call NULL just disables rotation for that one call.
#
# Returns a plain list keyed for httr2::req_proxy(url, port, username, password)
# -- NOT an httr::use_proxy() request object. wehoop 3.0.0's internal
# .retry_request does `do.call(httr2::req_proxy, c(list(req=req), proxy))`,
# splatting the proxy list as named args. An httr::request object's internal
# slots (method/headers/fields/options/auth_token/output) would be rejected
# by req_proxy as "unused arguments". This shape side-steps that mismatch.
select_proxy <- function(proxies = load_proxies()) {
  if (is.null(proxies) || nrow(proxies) == 0) return(NULL)
  proxy <- sample(proxies$ip, 1) # pick a random proxy from the list above
  proxy_selected <- proxies %>%
    dplyr::filter(.data$ip == proxy)
  # CSV format from get_proxy_bonanza_ips() ships the port column as
  # `port_http`. Earlier code read `port` and silently produced NA, which
  # made every WNBA Stats request fall through to direct (rate-limited)
  # access. Prefer `port_http`, fall back to `port` for legacy CSVs.
  port_val <- if (!is.null(proxy_selected$port_http)) {
    proxy_selected$port_http
  } else {
    proxy_selected$port
  }
  list(
    url      = as.character(proxy_selected$ip),
    port     = as.integer(port_val),
    username = as.character(proxy_selected$login),
    password = as.character(proxy_selected$password)
  )
}


rejoin_schedules <- function(df) {
  df <- df %>%
    dplyr::mutate(
      HOME_AWAY = ifelse(stringr::str_detect(.data$MATCHUP, "@"), "AWAY", "HOME")
    ) %>%
    dplyr::select(-.data$WL, .data$MATCHUP)
  away_df <- df %>%
    dplyr::filter(.data$HOME_AWAY == "AWAY") %>%
    dplyr::select(-.data$HOME_AWAY) %>%
    dplyr::select(.data$SEASON_ID, .data$GAME_ID, .data$GAME_DATE, .data$MATCHUP, tidyr::everything())
  colnames(away_df)[5:ncol(away_df)] <- paste0("AWAY_", colnames(away_df)[5:ncol(away_df)])
  home_df <- df %>%
    dplyr::filter(.data$HOME_AWAY == "HOME") %>%
    dplyr::select(-.data$HOME_AWAY, -.data$MATCHUP) %>%
    dplyr::select(.data$SEASON_ID, .data$GAME_ID, .data$GAME_DATE, tidyr::everything())
  colnames(home_df)[4:ncol(home_df)] <- paste0("HOME_", colnames(home_df)[4:ncol(home_df)])
  sched_df <- away_df %>%
    dplyr::left_join(home_df, by = c("GAME_ID", "SEASON_ID", "GAME_DATE"))
  return(sched_df)
}
