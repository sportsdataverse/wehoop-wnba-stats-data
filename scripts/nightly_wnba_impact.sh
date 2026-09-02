#!/usr/bin/env bash
# Nightly current-season wnba_player_impact: build, publish, COMMIT.
#
# The GH workflow (wnba_models.yml) stays manual-only ON PURPOSE: its one live
# call (player-variant leaguegamelog) hangs on datacenter IPs, so a scheduled
# run from a GitHub runner stalls until timeout-minutes burns. This wrapper is
# the scheduled path instead -- it runs where the PROXY_* pool works, over the
# sibling raw checkout, current season only. Multi-season backfills stay manual.
#
# Cron (droplet, ET): 30 10 * 5-10 *  -- after the 09:00 ET stats-raw refresh.
set -uo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR" || exit 1

PY="${WNBA_MODELS_PYTHON:-}"
if [ -z "${PY}" ]; then
  for cand in .venv/Scripts/python.exe .venv/bin/python; do
    if [ -x "${cand}" ]; then PY="${cand}"; break; fi
  done
fi
[ -n "${PY}" ] || { echo "FATAL: no venv python (uv sync first, or set WNBA_MODELS_PYTHON)" >&2; exit 1; }

# Proxy credentials live in ~/.Renviron, which only R loads -- lift them here
# (same block as wehoop-wnba-stats-raw/scripts/run_pipeline.sh). Never echoed.
for f in "${HOME}/.Renviron" "${HOME}/Documents/.Renviron"; do
  [ -f "${f}" ] || continue
  for v in PROXY_ENDPOINT PROXY_KEY PROXY_PKG; do
    if [ -z "${!v:-}" ]; then
      val="$(sed -nE "s/^[[:space:]]*${v}[[:space:]]*=[[:space:]]*//p" "${f}" \
             | head -1 | tr -d "\"'" | tr -d '\r')"
      [ -n "${val}" ] && export "${v}=${val}"
    fi
  done
done

# shellcheck source=scripts/_commit.sh
source "$(dirname "${BASH_SOURCE[0]}")/_commit.sh"
git config --local user.email "action@github.com" >/dev/null 2>&1 || true
git config --local user.name "Github Action" >/dev/null 2>&1 || true

SEASON="${1:-$(date -u +%Y)}"
RAW_STORE="${WNBA_RAW_STORE:-/mnt/sdv_repos/wehoop-wnba-stats-raw/wnba_stats/json}"
# A scratch dir, never a repo path: the builder's output is an intermediate, and
# only the parquet+rds are meant to survive into the tracked tree below.
OUT_DIR="$(mktemp -d "/tmp/wnba_impact_${SEASON}.XXXXXX")"
trap 'rm -rf "${OUT_DIR}"' EXIT

"$PY" -m wnba_model_08_impact \
  --seasons "$SEASON" \
  --out "$OUT_DIR" \
  --raw-store-dir "$RAW_STORE" \
  --tag wnba_player_impact \
  --repo sportsdataverse/sportsdataverse-data \
  "${@:2}"
rc=$?
if [ "$rc" -ne 0 ]; then
  echo "EXIT=$rc"
  exit "$rc"
fi

# Sync into the committed tree, the same contract the data processor uses for
# every compiled dataset: the release is the distribution channel, but the repo
# keeps a committed copy in wnba_stats/{key}/{parquet,rds}/. csv is
# release-only (it is the largest format and adds nothing a reader of the
# parquet needs). A dry-run publishes nothing but still builds, so the commit
# is skipped too -- only a real run should move the tracked tree.
case " ${*:2} " in
  *" --dry-run "*) echo "dry run: not committing"; echo "EXIT=0"; exit 0 ;;
esac

mkdir -p "${REPO_DIR}/wnba_stats/player_impact/parquet" \
         "${REPO_DIR}/wnba_stats/player_impact/rds"
for f in "${OUT_DIR}"/*.parquet; do
  [ -e "$f" ] && cp -f "$f" "${REPO_DIR}/wnba_stats/player_impact/parquet/"
done
for f in "${OUT_DIR}"/*.rds; do
  [ -e "$f" ] && cp -f "$f" "${REPO_DIR}/wnba_stats/player_impact/rds/"
done
# The model card is the artifact that says HOW these numbers were produced;
# committing the table without it leaves the repo copy unexplained.
for f in "${OUT_DIR}"/*_card.json; do
  [ -e "$f" ] && cp -f "$f" "${REPO_DIR}/wnba_stats/player_impact/"
done

sdv_commit_push "WNBA Player Impact Update (Start: ${SEASON} End: ${SEASON})" \
  wnba_stats/player_impact || rc=1

echo "EXIT=$rc"
exit "$rc"
