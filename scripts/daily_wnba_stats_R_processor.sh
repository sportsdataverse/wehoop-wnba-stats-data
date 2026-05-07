#!/bin/bash
set -e

while getopts s:e: flag
do
    case "${flag}" in
        s) START_YEAR=${OPTARG};;
        e) END_YEAR=${OPTARG};;
    esac
done

echo "==============================================="
echo " WNBA Stats Data refresh: ${START_YEAR}-${END_YEAR}"
echo "==============================================="

for YEAR in $(seq "${START_YEAR}" "${END_YEAR}")
do
    echo "--- Processing season ${YEAR} ---"
    git pull >> /dev/null
    git config --local user.email "action@github.com"
    git config --local user.name "Github Action"

    Rscript R/wnba_stats_01_pbp.R                  "$YEAR" "$YEAR"
    Rscript R/wnba_stats_02_rosters.R              "$YEAR" "$YEAR"
    Rscript R/wnba_stats_03_player_season_stats.R  "$YEAR" "$YEAR"
    Rscript R/wnba_stats_04_lineups.R              "$YEAR" "$YEAR"
    Rscript R/wnba_stats_05_team_season_stats.R    "$YEAR" "$YEAR"
    Rscript R/wnba_stats_06_standings.R            "$YEAR" "$YEAR"
    Rscript R/wnba_stats_08_shots.R                "$YEAR" "$YEAR"
    Rscript R/wnba_stats_09_game_rosters.R         "$YEAR" "$YEAR"
    Rscript R/wnba_stats_10_officials.R            "$YEAR" "$YEAR"

    git pull >> /dev/null
    git add wnba_stats/* >> /dev/null || echo "No wnba_stats artifacts to stage"
    git pull >> /dev/null
    git commit -m "WNBA Stats Data Update (Start: $YEAR End: $YEAR)" >> /dev/null || echo "No changes to commit"
    git pull --rebase >> /dev/null
    git push >> /dev/null
done
