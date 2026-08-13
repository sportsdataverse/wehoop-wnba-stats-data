#!/usr/bin/env bash
# Build the historical seasons for the families published current-season-only.
#
# BUILD ONLY -- never passes --publish or --dry-run, so wnba_data_build stops
# after writing under --out. Publishing stays a separate, human-gated step.
#
# Resumable: a (dataset, season) whose parquet already exists under OUT is
# skipped, so a re-run after an interrupt picks up where it stopped.
#
#   Usage: scripts/backfill_historical_seasons.sh [dataset ...]
#   Env:   FIRST_SEASON / LAST_SEASON, RAW_ROOT, OUT, LOG
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RAW_ROOT="${RAW_ROOT:-/c/Users/saiem/Documents/GitHub-Data/sdv-dev/wehoop-dev/wehoop-wnba-stats-raw/wnba_stats/json}"
OUT="${OUT:-$HERE/build_out}"
LOG="${LOG:-$HERE/logs/backfill_$(date -u +%Y%m%dT%H%M%SZ).log}"
FIRST_SEASON="${FIRST_SEASON:-1997}"
LAST_SEASON="${LAST_SEASON:-2026}"
# Interpreter by absolute path (house style, see
# daily_wnba_stats_python_processor.sh), resolved against THIS checkout so a
# clone or a worktree does not silently drive another repo's venv.
# An explicit override is honoured strictly: if it is set and not executable we
# fail rather than quietly falling back, since silently running a DIFFERENT
# interpreter than the one asked for is how a build ends up reporting success
# against the wrong environment.
if [ -n "${WEHOOP_WNBA_STATS_PYBIN:-}" ]; then
    PY="${WEHOOP_WNBA_STATS_PYBIN}"
    if [ ! -x "$PY" ]; then
        echo "::error ::WEHOOP_WNBA_STATS_PYBIN=$PY is not executable" >&2
        exit 1
    fi
elif [ -x "$HERE/.venv/bin/python" ]; then          # unix layout
    PY="$HERE/.venv/bin/python"
elif [ -x "$HERE/.venv/Scripts/python.exe" ]; then  # windows layout
    PY="$HERE/.venv/Scripts/python.exe"
else
    echo "::error ::no venv interpreter under $HERE/.venv (checked bin/python and" \
         "Scripts/python.exe) -- run 'uv sync', or set WEHOOP_WNBA_STATS_PYBIN" >&2
    exit 1
fi

DATASETS=("$@")
[ ${#DATASETS[@]} -eq 0 ] && DATASETS=(rosters coaches player_game_logs officials game_rosters shots)

mkdir -p "$(dirname "$LOG")" "$OUT"
export PYTHONUNBUFFERED=1 PYTHONIOENCODING=utf-8 PYTHONPATH="$HERE/python"

ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }
say() { echo "[$(ts)] $*" | tee -a "$LOG"; }

overall_rc=0
failed=()

say "START backfill  datasets=${DATASETS[*]}  seasons=${FIRST_SEASON}-${LAST_SEASON}"
say "raw_root=$RAW_ROOT"
say "out=$OUT   (BUILD ONLY -- no --publish, no --dry-run)"

# stem for the resume check; mirrors datasets.py stems
stem_of() {
  case "$1" in
    rosters) echo rosters ;; coaches) echo coaches ;;
    player_game_logs) echo player_game_logs ;; officials) echo officials ;;
    game_rosters) echo game_rosters ;; shots) echo shots ;;
    *) echo "$1" ;;
  esac
}
tag_of() { echo "wnba_stats_$1"; }

for ds in "${DATASETS[@]}"; do
  stem="$(stem_of "$ds")"; tag="$(tag_of "$ds")"
  for season in $(seq "$FIRST_SEASON" "$LAST_SEASON"); do
    target="$OUT/$tag/${stem}_${season}.parquet"
    if [ -f "$target" ]; then
      say "skip  $ds $season (already built)"
      continue
    fi
    say "build $ds $season ..."
    "$PY" -m wnba_data_build \
      --datasets "$ds" --seasons "$season" \
      --root "$RAW_ROOT" --out "$OUT" 2>&1 | tee -a "$LOG"
    # tee hides python's status behind its own; recover it from PIPESTATUS[0].
    rc=${PIPESTATUS[0]}
    if [ "$rc" -ne 0 ]; then
      overall_rc=$rc
      failed+=("$ds $season (rc=$rc)")
      say "WARNING $ds $season exited $rc -- continuing"
    fi
  done
done

if [ ${#failed[@]} -gt 0 ]; then
  say "DONE backfill WITH FAILURES: ${failed[*]}"
else
  say "DONE backfill"
fi
# Aggregate status, not `$?` of the preceding echo -- a completion marker that
# always reads 0 is worse than none, since it is grepped to decide "did it work".
echo "EXIT=$overall_rc" | tee -a "$LOG"
exit "$overall_rc"
