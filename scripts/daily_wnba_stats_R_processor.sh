#!/bin/bash
# Daily WNBA Stats parser orchestrator. Mirrors the sibling processors
# in wehoop-wnba-data/scripts/daily_wnba_R_processor.sh and
# wehoop-wbb-data/scripts/daily_wbb_R_processor.sh, with the same
# per-season tee-to-/tmp-then-commit-tracked-log pattern used by
# wehoop-wnba-raw/scripts/daily_wnba_scraper.sh.
#
# Differences from the sibling -data processors:
#   - R scripts here use POSITIONAL args (<start_year> <end_year>) not the
#     -s/-e flag style used by the espn_{wnba,wbb}_*_creation.R parsers.
#   - Output writes under wnba_stats/, not wnba/ or wbb/.
#   - Proxy acquisition is centralised in R/utils.R load_proxies() so each
#     R script picks up PROXY_KEY+PROXY_PKG env vars without any setup
#     work here. No proxylist.csv handling needed in this script.
#   - 07_draft.R is annual cadence and lives in
#     scripts/annual_wnba_stats_draft_R_processor.sh; intentionally
#     excluded here.
#
# Logging: per-season run output is teed to a /tmp tmpfile during the
# work block, then copied to logs/wehoop_wnba_stats_logfile_<year>.log
# and committed + pushed on its own (separate commit from the data
# update). The tracked log lives under logs/ which .gitignore handles
# via `*.log` + `!logs/*.log`.
#
# Usage: bash scripts/daily_wnba_stats_R_processor.sh -s 2025 -e 2025 [-r false]

while getopts s:e:r: flag
do
    case "${flag}" in
        s) START_YEAR=${OPTARG};;
        e) END_YEAR=${OPTARG};;
        r) RESCRAPE=${OPTARG};;
    esac
done

RESCRAPE=${RESCRAPE:-true}
echo "Rescrape set to: $RESCRAPE"
mkdir -p logs

for i in $(seq "${START_YEAR}" "${END_YEAR}")
do
    LOGFILE="logs/wehoop_wnba_stats_logfile_${i}.log"
    TMPLOG=$(mktemp "/tmp/wehoop_wnba_stats_logfile_${i}.XXXXXX.log")
    echo "=== Processing season $i ==="
    # Tee inside the block writes to /tmp (untracked) so the `git pull` calls
    # don't trip over their own log output being written to a tracked file.
    {
        git pull >> /dev/null
        git config --local user.email "action@github.com"
        git config --local user.name  "Github Action"
        # 01_pbp.R takes a 3rd positional arg controlling whether to
        # re-fetch every game from the API or read the per-game JSON cache
        # at wnba_stats/pbp/json/. Default RESCRAPE for the wrapper is
        # true (full re-fetch), matching the historical behaviour.
        Rscript R/wnba_stats_01_pbp.R                 "$i" "$i" "$RESCRAPE"
        Rscript R/wnba_stats_02_rosters.R             $i $i
        Rscript R/wnba_stats_03_player_season_stats.R $i $i
        Rscript R/wnba_stats_04_lineups.R             $i $i
        Rscript R/wnba_stats_05_team_season_stats.R   $i $i
        Rscript R/wnba_stats_06_standings.R           $i $i
        # 07_draft.R is intentionally excluded -- it has annual cadence and
        # lives in scripts/annual_wnba_stats_draft_R_processor.sh. Running
        # it daily would re-upload identical artifacts to the
        # wnba_stats_draft release for no benefit.
        Rscript R/wnba_stats_08_shots.R               $i $i
        Rscript R/wnba_stats_09_game_rosters.R        $i $i
        Rscript R/wnba_stats_10_officials.R           $i $i
        git pull >> /dev/null
        git add wnba_stats/ >> /dev/null
        git pull >> /dev/null
        git add . >> /dev/null
        git commit -m "WNBA Stats Data Update (Start: $i End: $i)" || echo "No changes to commit"
        git pull >> /dev/null
        git push >> /dev/null
    } 2>&1 | tee "$TMPLOG"

    # Block is finished and pushed; tee has closed $TMPLOG. Now copy the
    # log into its tracked location and commit/push it on its own.
    cp "$TMPLOG" "$LOGFILE"
    git pull --rebase >> /dev/null || true
    git add "$LOGFILE"
    git commit -m "WNBA Stats Data log update (Start: $i End: $i)" >> /dev/null || echo "No log changes to commit"
    git push >> /dev/null
    rm -f "$TMPLOG"
done
