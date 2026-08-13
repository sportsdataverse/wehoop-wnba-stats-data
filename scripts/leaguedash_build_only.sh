#!/usr/bin/env bash
# Build (NOT publish) the league-dash cube for one or more seasons.
#
# Why this exists alongside scripts/leaguedash_backfill.sh: that script hardcodes
# --publish and uploads after every season. This one never passes --publish or
# --dry-run, so the cube lands under --out and nothing is uploaded -- the shape
# you want when the release step is human-gated.
#
# Proxy credentials are read from ~/.Renviron AT CALL TIME (python cannot read
# .Renviron itself) and are never echoed. Rate limits stay env-tunable:
#   export STATS_RATE_HITS=3 STATS_RATE_MAX=250 STATS_RATE_WINDOW=600
#
#   Usage: scripts/leaguedash_build_only.sh 2026 [more seasons ...]
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${OUT:-$HERE/build_out/leaguedash}"
LOG="${LOG:-$HERE/logs/leaguedash_build_$(date -u +%Y%m%dT%H%M%SZ).log}"
PY="/c/Users/saiem/Documents/GitHub-Data/sdv-dev/wehoop-dev/wehoop-wnba-stats-data/.venv/Scripts/python.exe"

[ $# -gt 0 ] || { echo "usage: $0 <season> [season ...]" >&2; exit 2; }

# -- credentials from .Renviron, at call time, never printed -------------------
for f in "$HOME/.Renviron" "$HOME/Documents/.Renviron"; do
  [ -f "$f" ] || continue
  for v in PROXY_ENDPOINT PROXY_KEY PROXY_PKG; do
    if [ -z "${!v:-}" ]; then
      val="$(sed -nE "s/^[[:space:]]*${v}[[:space:]]*=[[:space:]]*//p" "$f" | head -1 | tr -d "\"'" | tr -d '\r')"
      [ -n "$val" ] && export "$v=$val"
    fi
  done
done
for v in PROXY_ENDPOINT PROXY_KEY PROXY_PKG; do
  [ -n "${!v:-}" ] || { echo "$v not set and not found in .Renviron" >&2; exit 1; }
done

mkdir -p "$(dirname "$LOG")" "$OUT"
export PYTHONUNBUFFERED=1 PYTHONIOENCODING=utf-8 PYTHONPATH="$HERE/python"

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] START leaguedash build-only seasons=$*" | tee -a "$LOG"
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] proxy creds loaded (values not shown); out=$OUT" | tee -a "$LOG"
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] NO --publish / NO --dry-run: nothing is uploaded" | tee -a "$LOG"

"$PY" -m wnba_data_build.leaguedash_cli --seasons "$@" --out "$OUT" 2>&1 | tee -a "$LOG"
rc=${PIPESTATUS[0]}

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] DONE leaguedash build-only" | tee -a "$LOG"
echo "EXIT=$rc" | tee -a "$LOG"
exit "$rc"
