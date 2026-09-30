#!/usr/bin/env bash
# Nightly current-season refresh of the release assets the daily compile
# (daily_wnba_stats.yml) does NOT build:
#
#   1. Program V v3 families -> wnba_stats_{schedules,pbp,possessions,game_lineups}
#      (the wnba_*_{season}.* assets -- the ones sdv-py's load_wnba_stats_* read
#      and each tag's README calls AUTHORITATIVE)
#   2. the league-dash cube  -> wnba_stats_leaguedash
#
# Both were operator-only runs, so the 2026 assets sat frozen at 2026-08-12/13
# while the season and the playoffs went on. Nothing failed; nothing ran.
#
# Droplet cron, not CI: leaguedash scrapes stats.wnba.com live (hangs on
# datacenter IPs without the PROXY_* pool), and the v3 build reads the sibling
# raw checkout.
#
# Cron (droplet, ET): 0 10 * 5-10 *
# Ordering matters: the cutover's section-9.3 gate diffs the staged v3 season
# against the LEGACY tree the daily compile commits here, so this must run after
# the 09:00 stats-raw refresh AND the compile that refresh dispatches -- hence
# the pull first. A gate failure refuses the v3 publish and exits 1 (alerted);
# leaguedash still runs.
#
#   bash scripts/nightly_wnba_season_refresh.sh            # current season
#   bash scripts/nightly_wnba_season_refresh.sh 2026 -n    # build + gate + plan, upload nothing
set -uo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR" || exit 1

PY="${WEHOOP_WNBA_STATS_PYBIN:-}"
if [ -z "${PY}" ]; then
  for cand in .venv/bin/python .venv/Scripts/python.exe; do
    if [ -x "${cand}" ]; then PY="${cand}"; break; fi
  done
fi
[ -n "${PY}" ] || { echo "FATAL: no venv python (uv sync first, or set WEHOOP_WNBA_STATS_PYBIN)" >&2; echo "EXIT=1"; exit 1; }

# Proxy credentials live in ~/.Renviron, which only R loads -- lift them here
# (same block as scripts/nightly_wnba_impact.sh). Never echoed.
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

export PYTHONUNBUFFERED=1
export PYTHONIOENCODING=utf-8
export PYTHONPATH="${REPO_DIR}/python${PYTHONPATH:+:${PYTHONPATH}}"

SEASON="${1:-$(date -u +%Y)}"
EXECUTE="--execute"; LD_MODE="--publish"
if [ "${2:-}" = "-n" ]; then EXECUTE=""; LD_MODE="--dry-run"; fi
RAW_ROOT="${WNBA_RAW_STORE:-/mnt/sdv_repos/wehoop-wnba-stats-raw/wnba_stats/json}"
# A fresh per-game cache every run: the cache is keyed by game id only, so a
# sdv-py bump (daily lock commits) would otherwise keep serving frames the old
# engine built. A cold season rebuild measured 65 s (334 games, 2026-09-30).
CACHE_DIR="$(mktemp -d "/tmp/wnba_v3_cache_${SEASON}.XXXXXX")"
trap 'rm -rf "${CACHE_DIR}"' EXIT

echo "=== nightly season refresh ${SEASON} started $(date -u +'%F %T')Z ==="
git pull -q --ff-only || echo "WARN: git pull failed -- gating against the checked-out legacy tree"

rc=0
if "$PY" -m wnba_data_build.v3_backfill -s "$SEASON" -e "$SEASON" \
     --raw-root "$RAW_ROOT" --cache-dir "$CACHE_DIR" --rebuild; then
  # --no-readme: each tag's README states the full published season range; a
  # one-season run would rewrite it as "${SEASON}-${SEASON}".
  "$PY" -m wnba_data_build.v3_cutover -s "$SEASON" -e "$SEASON" \
    --raw-root "$RAW_ROOT" --no-readme \
    --manifest "${REPO_DIR}/build_out/v3_cutover_manifest_nightly.md" \
    ${EXECUTE} || rc=1
else
  rc=1
fi

# Persistent out dir, not scratch: the megas assemble from on-disk tables, so a
# variant that fails today keeps yesterday's file instead of narrowing the mega.
"$PY" -m wnba_data_build.leaguedash_cli --seasons "$SEASON" \
  --out build_out/leaguedash "${LD_MODE}" || rc=1

echo "=== nightly season refresh ${SEASON} finished $(date -u +'%F %T')Z ==="
echo "EXIT=${rc}"
exit "${rc}"
