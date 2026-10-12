#!/usr/bin/env bash
# Nightly current-season wnba_player_impact: build, publish, COMMIT.
#
# The GH workflow (wnba_models.yml) stays manual-only ON PURPOSE: its one live
# call (player-variant leaguegamelog) hangs on datacenter IPs, so a scheduled
# run from a GitHub runner stalls until timeout-minutes burns. This wrapper is
# the scheduled path instead -- it runs where the PROXY_* pool works, over the
# sibling raw checkout. Multi-season backfills stay manual.
#
# Trailing window: the build covers the last WNBA_IMPACT_WINDOW seasons (default
# 6, e.g. 2021:2026) because adj-RAPM takes the previous season's SPM as its
# prior and DARKO needs a >= 2-season panel -- a one-season build ships an empty
# prior and all-null darko_* columns. Only the CURRENT season is published and
# committed; the trailing seasons are warm-up inputs. Republishing them would
# move numbers already on the release (the raw store has been re-scraped since
# the July backfill). They cost no stats.wnba.com calls: every trailing season
# is served by the committed raw store (incl. the player-variant leaguegamelog
# *_p.json captures) and the per-game possession cache -- local compute only.
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
WINDOW="${WNBA_IMPACT_WINDOW:-6}"
case "${WINDOW}" in
  ''|*[!0-9]*) echo "FATAL: WNBA_IMPACT_WINDOW must be an integer >= 2 (got '${WINDOW}')" >&2; exit 1 ;;
esac
[ "${WINDOW}" -ge 2 ] || { echo "FATAL: WNBA_IMPACT_WINDOW must be >= 2: DARKO needs a 2-season panel" >&2; exit 1; }
START=$(( SEASON - WINDOW + 1 ))
[ "${START}" -ge 1997 ] || START=1997
RAW_STORE="${WNBA_RAW_STORE:-/mnt/sdv_repos/wehoop-wnba-stats-raw/wnba_stats/json}"
# A scratch dir, never a repo path: the builder's output is an intermediate, and
# only the parquet (+ card) is meant to survive into the tracked tree below.
OUT_DIR="$(mktemp -d "/tmp/wnba_impact_${SEASON}.XXXXXX")"
trap 'rm -rf "${OUT_DIR}"' EXIT

TAG=wnba_player_impact
REPO=sportsdataverse/sportsdataverse-data
echo "impact window: ${START}:${SEASON} (publishing ${SEASON} only)"
# Build (+ publish-floor gates) the whole window, uploading nothing: the CLI
# would otherwise publish every season it built.
"$PY" -m wnba_model_08_impact \
  --seasons "${START}:${SEASON}" \
  --out "$OUT_DIR" \
  --raw-store-dir "$RAW_STORE" \
  --tag "$TAG" \
  --repo "$REPO" \
  "${@:2}" --dry-run
rc=$?
if [ "$rc" -ne 0 ]; then
  echo "EXIT=$rc"
  exit "$rc"
fi

# Sync into the committed tree, the same contract the data processor uses for
# every compiled dataset: the release is the distribution channel, but the repo
# keeps a committed copy in wnba_stats/{key}/parquet/. csv and rds are
# release-only (csv is the largest format and adds nothing a reader of the
# parquet needs). A dry-run publishes nothing but still builds, so the commit
# is skipped too -- only a real run should move the tracked tree.
case " ${*:2} " in
  *" --dry-run "*) echo "dry run: not publishing or committing"; echo "EXIT=0"; exit 0 ;;
esac

# The SPM coefficient sidecar on the release is canonical: one record per
# PUBLISHED season (1997-...). The build's own sidecar holds the whole trailing
# window, so uploading it as-is replaced the full history with warm-up fits that
# match nothing published. Overlay the current season onto the published sidecar
# first -- before any upload, so a failed read blocks the publish instead of
# half-completing it.
"$PY" -m wnba_model_publish spm-merge --dir "$OUT_DIR" --seasons "$SEASON" \
  --tag "$TAG" --repo "$REPO" || { echo "EXIT=1"; exit 1; }

# Publish the current season only (parquet + csv + rds), then the json sidecars
# (model card + the merged SPM coefficients). `upload` never recomputes.
for pat in "${TAG}_${SEASON}.*" "*.json"; do
  "$PY" -m wnba_model_publish upload --dir "$OUT_DIR" --tag "$TAG" --repo "$REPO" \
    --pattern "$pat" || { echo "EXIT=1"; exit 1; }
done

# Parquet only in the tree (owner rule 2026-09-30); the release carries rds + csv too.
mkdir -p "${REPO_DIR}/wnba_stats/player_impact/parquet"
cp -f "${OUT_DIR}/${TAG}_${SEASON}.parquet" "${REPO_DIR}/wnba_stats/player_impact/parquet/" || rc=1
# The model card is the artifact that says HOW these numbers were produced;
# committing the table without it leaves the repo copy unexplained.
for f in "${OUT_DIR}"/*_card.json; do
  [ -e "$f" ] && cp -f "$f" "${REPO_DIR}/wnba_stats/player_impact/"
done

sdv_commit_push "WNBA Player Impact Update (Start: ${SEASON} End: ${SEASON})" \
  wnba_stats/player_impact || rc=1

echo "EXIT=$rc"
exit "$rc"
