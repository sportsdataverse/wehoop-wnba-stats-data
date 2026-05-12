#!/bin/bash
# Daily WNBA Stats parser orchestrator. Mirrors the sibling processors
# in wehoop-wnba-data/scripts/daily_wnba_R_processor.sh and
# wehoop-wbb-data/scripts/daily_wbb_R_processor.sh.
#
# Differences from the sibling repos:
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
# Usage: bash scripts/daily_wnba_stats_R_processor.sh -s 2025 -e 2025 [-r false]

while getopts s:e:r: flag
do
    case "${flag}" in
        s) START_YEAR=${OPTARG};;
        e) END_YEAR=${OPTARG};;
        r) RESCRAPE=${OPTARG};;
    esac
done

for i in $(seq "${START_YEAR}" "${END_YEAR}")
do
    echo "$i"
    git pull >> /dev/null
    git config --local user.email "action@github.com"
    git config --local user.name  "Github Action"
    Rscript R/wnba_stats_01_pbp.R                 $i $i
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
    git commit -m "WNBA Stats Data Update (Start: $i End: $i)" >> /dev/null || echo "No changes to commit"
    git pull --rebase >> /dev/null
    git push >> /dev/null
done
