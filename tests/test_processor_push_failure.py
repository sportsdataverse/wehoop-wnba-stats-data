"""A season commit that cannot reach origin fails the daily processor.

Run 37207505807 (2026-10-04) published the season, then could not rebase its tree
commit onto a main that had moved -- and the processor still exited 0, because
its ``PUSH_RC`` was set inside a subshell and checked after ``exit``. The shipped
script is run here against a scratch origin, with the Python build stubbed out.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
DATA = "wnba_stats/standings/parquet/standings_2026.parquet"


ENV = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t"}
ENV |= {"GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t", "SDV_ROTATE_LOGS": "/nonexistent"}


def _git(cwd: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", *args], cwd=cwd, env=ENV, capture_output=True, text=True, check=True
    )
    return done.stdout


def _processor(tmp_path: Path, *, origin_moves: bool) -> tuple[int, str]:
    """Run the processor in a clone whose build "wrote" DATA; return (exit code, origin log)."""
    origin, repo, other = tmp_path / "origin.git", tmp_path / "repo", tmp_path / "other"
    _git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    _git(tmp_path, "clone", "-q", str(origin), str(repo))
    (repo / "scripts").mkdir()
    for name in ("daily_wnba_stats_python_processor.sh", "_commit.sh"):
        shutil.copy(SCRIPTS / name, repo / "scripts" / name)
    (repo / DATA).parent.mkdir(parents=True)
    (repo / DATA).write_text("as committed\n")
    (repo / ".gitignore").write_text("logs/\n")
    _git(repo, "checkout", "-q", "-B", "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "seed")
    _git(repo, "push", "-q", "origin", "main")
    if origin_moves:  # the run ahead of this one rewrote the same file and pushed
        _git(tmp_path, "clone", "-q", str(origin), str(other))
        (other / DATA).write_text("as the earlier run built it\n")
        _git(other, "commit", "-q", "-am", "earlier run")
        _git(other, "push", "-q", "origin", "main")
    (repo / DATA).write_text("as this run built it\n")
    python = tmp_path / "python"  # stands in for the build and for stage 99
    python.write_text("#!/bin/sh\nexit 0\n")
    python.chmod(0o755)
    env = ENV | {
        "WEHOOP_WNBA_STATS_PYBIN": str(python),
        "WEHOOP_WNBA_STATS_RAW_ROOT": "https://raw",
    }
    script = repo / "scripts" / "daily_wnba_stats_python_processor.sh"
    done = subprocess.run(["bash", str(script), "-s", "2026", "-e", "2026"], env=env, cwd=repo)
    return done.returncode, _git(tmp_path, "--git-dir", str(origin), "log", "--format=%s", "main")


def test_a_season_commit_that_cannot_rebase_fails_the_run(tmp_path: Path) -> None:
    code, log = _processor(tmp_path, origin_moves=True)
    assert "WNBA Stats Data Update" not in log  # the premise: the commit did not land
    assert code != 0


def test_a_season_commit_that_lands_is_a_green_run(tmp_path: Path) -> None:
    code, log = _processor(tmp_path, origin_moves=False)
    assert "WNBA Stats Data Update (Start: 2026 End: 2026)" in log
    assert code == 0
