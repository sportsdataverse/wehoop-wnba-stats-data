#!/bin/bash
# Annual WNBA Stats draft parser.
#
# The WNBA Draft happens once per year (typically April). Running its
# parser inside the daily processor would re-upload the same artifact
# to the wnba_stats_draft release every day with no semantic change.
# Mirrors the split done on the scraper side in
# wehoop-wnba-raw/scripts/annual_wnba_draft_scraper.sh.
#
# Run once shortly after the draft, or any time a season's draft rds /
# parquet on sportsdataverse-data needs a refresh. The CLI shape is
# identical to the daily processor so workflow inputs can be reused.
#
# Usage: bash scripts/annual_wnba_stats_draft_R_processor.sh -s 2025 -e 2025 [-r false]

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
    Rscript R/wnba_stats_07_draft.R $i $i
    git pull >> /dev/null
    git add wnba_stats/draft >> /dev/null
    git pull >> /dev/null
    git commit -m "WNBA Stats Draft Update (Start: $i End: $i)" >> /dev/null || echo "No changes to commit"
    git pull --rebase >> /dev/null
    git push >> /dev/null
done
