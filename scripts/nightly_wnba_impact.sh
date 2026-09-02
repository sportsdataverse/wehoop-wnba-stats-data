#!/usr/bin/env bash
# Nightly current-season wnba_player_impact publish (droplet cron).
#
# The GH workflow (wnba_models.yml) stays manual-only ON PURPOSE: its one live
# call (player-variant leaguegamelog) hangs on datacenter IPs, so a scheduled
# run from a GitHub runner stalls until timeout-minutes burns. This wrapper is
# the scheduled path instead -- it runs where the PROXY_* pool works, over the
# sibling raw checkout (no URL round-trips), current season only. Multi-season
# backfills stay manual (scripts/leaguedash_backfill.sh-style).
#
# Cron (droplet, ET): 30 10 * 5-10 *  -- after the 09:00 ET stats-raw refresh.
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

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

SEASON="${1:-$(date -u +%Y)}"
RAW_STORE="${WNBA_RAW_STORE:-/mnt/sdv_repos/wehoop-wnba-stats-raw/wnba_stats/json}"

"$PY" -m wnba_model_08_impact \
  --seasons "$SEASON" \
  --out out/wnba_player_impact \
  --raw-store-dir "$RAW_STORE" \
  --tag wnba_player_impact \
  --repo sportsdataverse/sportsdataverse-data \
  "${@:2}"
rc=$?
echo "EXIT=$rc"
exit "$rc"
