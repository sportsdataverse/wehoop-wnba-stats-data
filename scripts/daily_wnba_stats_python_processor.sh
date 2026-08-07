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
# Artifacts ship to the release tags AND land in the committed wnba_stats/
# tree (parquet+rds+csv), mirroring the R processor's run_and_commit paradigm:
# every -data repo keeps at least one committed version of each compiled
# dataset alongside the release. Each season commits with the load-bearing
# "WNBA Stats Data Update (Start: YYYY End: YYYY)" message.

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
# Packaging moved to the repo root (2026-08-02); the venv lives at .venv now.
PYBIN="${WEHOOP_WNBA_STATS_PYBIN:-${REPO_DIR}/.venv/bin/python}"

# Fail before doing anything if the raw checkout isn't where we expect. A missing
# root would build zero rows and "succeed", quietly publishing nothing. A URL
# root is passed straight through (the builders are dual-mode Path|str).
if [[ "${RAW_ROOT}" != http*://* && ! -d "${RAW_ROOT}/playbyplayv3" ]]; then
    echo "::error ::raw store not found at ${RAW_ROOT} (no playbyplayv3/ under it)"
    exit 1
fi

if [ ! -x "${PYBIN}" ]; then
    echo "::error ::python venv not found at ${PYBIN} -- run 'uv sync' in ${REPO_DIR}"
    exit 1
fi

cd "${REPO_DIR}" || exit 1
mkdir -p "${REPO_DIR}/logs"

# Commit identity for CI/droplet runs (no-op when already configured).
git -C "${REPO_DIR}" config --local user.email "action@github.com" >> /dev/null 2>&1 || true
git -C "${REPO_DIR}" config --local user.name "Github Action" >> /dev/null 2>&1 || true

ANY_FAILED=0
for i in $(seq "${START_YEAR}" "${END_YEAR}"); do
    LOGFILE="${REPO_DIR}/logs/wehoop_wnba_stats_python_logfile_${i}.log"
    OUT_DIR="$(mktemp -d "/tmp/wnba_stats_build_${i}.XXXXXX")"
    echo "=== Building WNBA stats (python) for season ${i} ==="
    # A SUBSHELL, not a brace group: a group's status is its LAST command, so
    # the trailing echo masked a failing build -- PIPESTATUS[0] was always 0 and
    # every season reported success (same bug fixed in the NBA sibling).
    (
        echo "=== season ${i} started $(date -u +'%F %T')Z ==="
        "${PYBIN}" -m wnba_data_build \
            --root "${RAW_ROOT}" \
            --seasons "${i}" \
            --out "${OUT_DIR}" \
            --publish
        py_rc=$?
        echo "EXIT=${py_rc}"
        echo "=== season ${i} finished $(date -u +'%F %T')Z ==="
        exit "${py_rc}"
    ) 2>&1 | tee -a "${LOGFILE}"
    # tee hides python's exit status behind its own; recover it from PIPESTATUS[0].
    rc=${PIPESTATUS[0]}
    if [ "${rc}" -ne 0 ]; then
        rm -rf "${OUT_DIR}"
        echo "season ${i} FAILED (rc=${rc})"
        ANY_FAILED=1
        continue
    fi
    # Sync the built artifacts into the committed R-shaped tree
    # (wnba_stats/{key}/{parquet,rds}/): the release stays the distribution
    # channel, but the repo keeps a committed version of every compiled
    # dataset -- exactly the R tree's rds+parquet shape (csv is release-only).
    # The builder's own layout ({out}/wnba_stats_{key}/file) is left untouched;
    # this maps tag dirs onto the short tree keys.
    for d in "${OUT_DIR}"/wnba_stats_*/; do
        [ -d "${d}" ] || continue
        key="$(basename "${d}")"
        key="${key#wnba_stats_}"
        for f in "${d}"*.parquet; do
            [ -e "${f}" ] || continue
            mkdir -p "${REPO_DIR}/wnba_stats/${key}/parquet"
            cp -f "${f}" "${REPO_DIR}/wnba_stats/${key}/parquet/"
        done
        for f in "${d}"*.rds; do
            [ -e "${f}" ] || continue
            mkdir -p "${REPO_DIR}/wnba_stats/${key}/rds"
            cp -f "${f}" "${REPO_DIR}/wnba_stats/${key}/rds/"
        done
    done
    # Stage 99 (spec D34), in-loop half: restamp this season's committed
    # schedule file's in_* flags from the artifacts just built, BEFORE the
    # scratch dir goes away (and before the season commit below picks the
    # stamped file up). Non-fatal: a stamp failure must not fail the publish
    # that already happened.
    "${PYBIN}" python/wnba_stats_99_schedule_master_creation.py \
        --built-dir "${OUT_DIR}" --season "${i}" --stamp-only \
        2>&1 | tee -a "${LOGFILE}" \
        || echo "schedule-master stamp failed for season ${i}" | tee -a "${LOGFILE}"
    rm -rf "${OUT_DIR}"
    # Mirror the R processor's run_and_commit: pull, add the tree, commit with
    # the load-bearing message format, rebase, push. Best-effort like R.
    (
        cd "${REPO_DIR}" || exit 0
        git pull >> /dev/null 2>&1 || true
        git add wnba_stats/ >> /dev/null 2>&1 || true
        git commit -m "WNBA Stats Data Update (Start: ${i} End: ${i})" >> /dev/null 2>&1 \
            || echo "season ${i}: nothing new to commit"
        git pull --rebase >> /dev/null 2>&1 || true
        git push >> /dev/null 2>&1 || true
    )
done

# Stage 99, union half: rebuild the master + games_in_data_repo manifest +
# coverage index from ALL committed season schedules (the whole archive, not
# just this run's window). Non-fatal for the same reason as above; the
# workflow's schedule-family commit step (or the next season commit) picks
# the artifacts up.
"${PYBIN}" python/wnba_stats_99_schedule_master_creation.py \
    || echo "schedule-master union failed"

exit "${ANY_FAILED}"
