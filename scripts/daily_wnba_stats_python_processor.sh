#!/bin/bash
# Build + publish the WNBA stats datasets with the Python builder
# (python/wnba_data_build) instead of the R creation scripts.
#
# Drop-in for daily_wnba_stats_R_processor.sh's build half: same -s/-e contract,
# so sdv-orch's data.build_py stage can call it. Reads the already-committed raw
# store from the sibling wehoop-wnba-stats-raw checkout, builds parquet+rds+csv,
# and uploads them to the wnba_stats_* releases (creating any missing tag).
#
#   bash scripts/daily_wnba_stats_python_processor.sh -s 2025 -e 2025
#
# DROPLET-SAFE: unlike the R scrape, this makes NO stats.wnba.com calls -- it
# only reads local JSON and talks to `gh`. That is why it can run on the droplet
# where data.scrape cannot (datacenter IP hangs on stats.wnba.com).
#
# Artifacts are release-only (io.py: parquet+rds+csv all ship to tags, none are
# committed here), so this writes to a scratch dir and uploads -- no git commit.

set -uo pipefail

while getopts s:e:r: flag; do
    case "${flag}" in
        s) START_YEAR=${OPTARG};;
        e) END_YEAR=${OPTARG};;
        r) : ;;  # accepted for -s/-e/-r parity with the R processor; unused (no scrape)
        *) echo "Usage: $0 -s <start_year> -e <end_year>"; exit 1;;
    esac
done

if [ -z "${START_YEAR:-}" ] || [ -z "${END_YEAR:-}" ]; then
    echo "Usage: $0 -s <start_year> -e <end_year>"
    exit 1
fi

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPOS_ROOT="${SDV_REPOS:-/mnt/sdv_repos}"
# The raw store lives in the -raw sibling; the CLI's --root is its json base.
# Override with WEHOOP_WNBA_STATS_RAW_ROOT (e.g. a raw.githubusercontent URL in CI).
RAW_ROOT="${WEHOOP_WNBA_STATS_RAW_ROOT:-${REPOS_ROOT}/wehoop-wnba-stats-raw/wnba_stats/json}"

# Venv interpreter by absolute path, not `uv run`: sdv-orch invokes this from a
# systemd unit whose PATH excludes /root/.local/bin, so `uv` exits 127 there.
PYBIN="${WEHOOP_WNBA_STATS_PYBIN:-${REPO_DIR}/python/.venv/bin/python}"

# Fail before doing anything if the raw checkout isn't where we expect. A missing
# root would build zero rows and "succeed", quietly publishing nothing. A URL
# root is passed straight through (the builders are dual-mode Path|str).
if [[ "${RAW_ROOT}" != http*://* && ! -d "${RAW_ROOT}/playbyplayv3" ]]; then
    echo "::error ::raw store not found at ${RAW_ROOT} (no playbyplayv3/ under it)"
    exit 1
fi

if [ ! -x "${PYBIN}" ]; then
    echo "::error ::python venv not found at ${PYBIN} -- run 'uv sync' in ${REPO_DIR}/python"
    exit 1
fi

cd "${REPO_DIR}/python" || exit 1
mkdir -p "${REPO_DIR}/logs"

ANY_FAILED=0
for i in $(seq "${START_YEAR}" "${END_YEAR}"); do
    LOGFILE="${REPO_DIR}/logs/wehoop_wnba_stats_python_logfile_${i}.log"
    OUT_DIR="$(mktemp -d "/tmp/wnba_stats_build_${i}.XXXXXX")"
    echo "=== Building WNBA stats (python) for season ${i} ==="
    {
        echo "=== season ${i} started $(date -u +'%F %T')Z ==="
        "${PYBIN}" -m wnba_data_build \
            --root "${RAW_ROOT}" \
            --seasons "${i}" \
            --out "${OUT_DIR}" \
            --publish
        echo "EXIT=$?"
        echo "=== season ${i} finished $(date -u +'%F %T')Z ==="
    } 2>&1 | tee -a "${LOGFILE}"
    # tee hides python's exit status behind its own; recover it from PIPESTATUS[0].
    rc=${PIPESTATUS[0]}
    rm -rf "${OUT_DIR}"
    [ "${rc}" -ne 0 ] && { echo "season ${i} FAILED (rc=${rc})"; ANY_FAILED=1; }
done

exit "${ANY_FAILED}"
