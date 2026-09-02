#!/usr/bin/env bash
# Commit + push, surviving a remote that moved while the build was running.
# Source it, do not execute:
#
#     source "$(dirname "${BASH_SOURCE[0]}")/_commit.sh"
#     sdv_commit_push "WNBA Stats Data Update (Start: 2026 End: 2026)" wnba_stats
#
# Extracted from daily_wnba_stats_python_processor.sh 2026-09-02 so the model
# driver reuses it instead of carrying a second copy: this function encodes two
# incidents, and a drifted duplicate would silently lose both. Matches the
# sibling convention in cfbfastR-cfb-raw/scripts/_commit.sh.
#
# The previous form pulled BEFORE staging, which can only ever abort: the build
# has just rewritten the tracked parquet/csv files, so `git pull` refuses with
# "Your local changes would be overwritten by merge". It then committed anyway,
# pushed into a non-fast-forward rejection, and swallowed all of it -- a GREEN
# job that published nothing. Observed on hoopR-nba-data run 32204419012
# (2026-08-19), and on wehoop-wnba-data runs 32192069433 + 32192069566.
#
# Order matters: stage and commit FIRST so the tree is clean, and only then
# reconcile with origin. `rebase --merge` rather than `pull --rebase` because
# git's default am backend base64-encodes every parquet blob it replays.
sdv_commit_push() {
  local msg="$1"; shift
  git add -- "$@" >/dev/null 2>&1 || true
  if git diff --cached --quiet; then
    echo "nothing to commit for: $msg"
    return 0
  fi
  git commit -m "$msg" >/dev/null || { echo "::warning ::commit failed: $msg"; return 1; }
  local attempt
  for attempt in 1 2 3; do
    if git push origin HEAD >/dev/null 2>&1; then
      echo "pushed: $msg (attempt $attempt)"
      return 0
    fi
    echo "push rejected (attempt $attempt); syncing with origin"
    git fetch --quiet origin main || true
    if ! git rebase --merge origin/main >/dev/null 2>&1; then
      git rebase --abort >/dev/null 2>&1 || true
      echo "::error ::cannot rebase onto origin/main for: $msg"
      return 1
    fi
  done
  echo "::error ::push still rejected after 3 attempts: $msg"
  return 1
}
