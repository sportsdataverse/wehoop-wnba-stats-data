#!/bin/bash
# Annual WNBA Stats draft parser.
#
# The WNBA Draft happens once per year (typically April). Running its
# parser inside the daily processor would re-upload the same artifact
# to the wnba_stats_draft release every day with no semantic change.
# Mirrors the split done on the scraper side in
# wehoop-wnba-raw/scripts/annual_wnba_draft_scraper.sh.
#
# Logging: per-season run output is teed to a /tmp tmpfile during the
# work block, then copied to
# logs/wehoop_wnba_stats_draft_logfile_<year>.log and committed +
# pushed on its own (separate commit from the draft update). The
# tracked log lives under logs/ which .gitignore handles via
# `*.log` + `!logs/*.log`.
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

RESCRAPE=${RESCRAPE:-true}
echo "Rescrape set to: $RESCRAPE"
mkdir -p logs

for i in $(seq "${START_YEAR}" "${END_YEAR}")
do
    LOGFILE="logs/wehoop_wnba_stats_draft_logfile_${i}.log"
    TMPLOG=$(mktemp "/tmp/wehoop_wnba_stats_draft_logfile_${i}.XXXXXX.log")
    echo "=== Processing draft $i ==="
    # Tee inside the block writes to /tmp (untracked) so the `git pull` calls
    # don't trip over their own log output being written to a tracked file.
    {
        git pull >> /dev/null
        git config --local user.email "action@github.com"
        git config --local user.name  "Github Action"
        Rscript R/wnba_stats_07_draft.R $i $i
        git pull >> /dev/null
        git add wnba_stats/draft >> /dev/null
        git pull >> /dev/null
        git add . >> /dev/null
        git commit -m "WNBA Stats Draft Update (Start: $i End: $i)" || echo "No changes to commit"
        git pull >> /dev/null
        git push >> /dev/null
    } 2>&1 | tee "$TMPLOG"

    # Block is finished and pushed; tee has closed $TMPLOG. Now copy the
    # log into its tracked location and commit/push it on its own.
    cp "$TMPLOG" "$LOGFILE"
    git pull --rebase >> /dev/null || true
    git add "$LOGFILE"
    git commit -m "WNBA Stats Draft log update (Start: $i End: $i)" >> /dev/null || echo "No log changes to commit"
    git push >> /dev/null
    rm -f "$TMPLOG"
done
