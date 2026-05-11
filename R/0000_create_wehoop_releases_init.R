# Create the GitHub releases on sportsdataverse/sportsdataverse-data that
# the wnba_stats_*.R parsers upload artifacts to via piggyback::pb_upload.
# Each release is created with an empty body; assets land later during the
# daily/weekly parser runs.
#
# Source-specific: this repo (wehoop-wnba-stats-data) owns the wnba_stats_*
# tags. The sister init scripts in wehoop-wnba-data and wehoop-wbb-data own
# their own source's tags.
#
# Idempotent: a release that already exists is skipped, not re-created.
# Re-run this any time a new wnba_stats_*.R script lands.

create_release <- function(tag, body) {
  tryCatch(
    piggyback::pb_release_create(
      repo = "sportsdataverse/sportsdataverse-data",
      tag  = tag,
      name = tag,
      body = body,
      .token = Sys.getenv("GITHUB_PAT")
    ),
    error = function(e) {
      # piggyback can wrap "already exists" across a newline depending on tag
      # length / cli width; collapse whitespace before matching so we don't
      # miss the line-broken variant.
      msg <- gsub("\\s+", " ", conditionMessage(e))
      if (grepl("already exists|already_exists|Validation Failed", msg, ignore.case = TRUE)) {
        message("Skipping (already exists): ", tag)
      } else {
        stop(e)
      }
    }
  )
}

#--- WNBA Stats (stats.wnba.com) ---------------------------------------------

# Original 4 (pre-Phase 1; pre-existing on sportsdataverse-data)
create_release("wnba_stats_schedules",        "WNBA Schedules Data (from stats.wnba.com)")
create_release("wnba_stats_team_boxscores",   "WNBA Team Boxscores Data (from stats.wnba.com)")
create_release("wnba_stats_player_boxscores", "WNBA Player Boxscores Data (from stats.wnba.com)")
create_release("wnba_stats_pbp",              "WNBA Play-by-Play Data (from stats.wnba.com)")

# Phase 1-6 additions (per-season + per-game + annual draft + coaches/lineups
# unique to the Stats API surface).
create_release("wnba_stats_rosters",             "WNBA Team Rosters Data (from stats.wnba.com)")
create_release("wnba_stats_player_season_stats", "WNBA Player Season Stats Data (from stats.wnba.com)")
create_release("wnba_stats_lineups",             "WNBA Lineups Data (from stats.wnba.com)")
create_release("wnba_stats_team_season_stats",   "WNBA Team Season Stats Data (from stats.wnba.com)")
create_release("wnba_stats_standings",           "WNBA Standings Data (from stats.wnba.com)")
create_release("wnba_stats_draft",               "WNBA Draft Data (from stats.wnba.com)")
create_release("wnba_stats_shots",               "WNBA Shots Data (from stats.wnba.com)")
create_release("wnba_stats_game_rosters",        "WNBA Game Rosters Data (from stats.wnba.com)")
create_release("wnba_stats_officials",           "WNBA Officials Data (from stats.wnba.com)")
create_release("wnba_stats_coaches",             "WNBA Coaches Data (from stats.wnba.com)")
