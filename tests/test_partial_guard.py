"""Staging leftovers must never reach a release; era floors must be refused.

Both guards exist because of failures observed during the 1997-2026 backfill:
the rds writer's atomic rename intermittently lost to a Windows file lock and
stranded ``.partial`` files in the directory publish globs, and ``officials``
built a well-formed 3-row frame for 1999 that looks like a season and is not.
"""

from __future__ import annotations

import polars as pl
import pytest
from wnba_data_build import cli
from wnba_data_build.datasets import BY_KEY
from wnba_data_build.io import _sweep_partials, write_release_formats
from wnba_data_build.publish import plan_uploads


def test_plan_uploads_refuses_partial_and_dotfiles(tmp_path):
    """A stranded .partial is not publishable even though it holds a real ext."""
    (tmp_path / "officials_2024.parquet").write_bytes(b"real")
    (tmp_path / "officials_2024.rds").write_bytes(b"real")
    # what a failed atomic rename leaves behind
    (tmp_path / ".officials_2024.rds.deadbeef.partial").write_bytes(b"truncated")
    (tmp_path / ".officials_2024.parquet").write_bytes(b"truncated")

    names = [p.name for p in plan_uploads(tmp_path)]

    assert names == ["officials_2024.parquet", "officials_2024.rds"]
    assert not any(".partial" in n or n.startswith(".") for n in names)


def test_plan_uploads_custom_pattern_also_refuses_partial(tmp_path):
    """The custom-pattern branch is guarded too, not just the extension globs."""
    (tmp_path / "model_card.json").write_bytes(b"real")
    (tmp_path / ".model_card.json.abc123.partial").write_bytes(b"truncated")

    names = [p.name for p in plan_uploads(tmp_path, pattern="*.json")]

    assert names == ["model_card.json"]


def test_write_release_formats_sweeps_its_own_partials(tmp_path):
    """A leftover from an earlier failed write is gone after the next success."""
    stale = tmp_path / ".officials_2024.rds.deadbeef.partial"
    tmp_path.mkdir(exist_ok=True)
    stale.write_bytes(b"truncated")
    other = tmp_path / ".officials_2023.rds.cafe.partial"
    other.write_bytes(b"another season, must survive")

    write_release_formats(
        pl.DataFrame({"official_id": [1], "game_id": ["1022400001"]}),
        tmp_path,
        "officials_2024",
    )

    assert not stale.exists(), "stale .partial for this stem should be swept"
    assert other.exists(), "sweep must be scoped to its own stem"
    assert (tmp_path / "officials_2024.parquet").exists()


def test_sweep_partials_tolerates_a_locked_file(tmp_path, monkeypatch):
    """A still-locked leftover must not crash the build (publish refuses it anyway)."""
    (tmp_path / ".officials_2024.rds.deadbeef.partial").write_bytes(b"x")

    def boom(self):
        raise PermissionError("locked by antivirus")

    monkeypatch.setattr("pathlib.Path.unlink", boom)
    assert _sweep_partials(tmp_path, "officials_2024") == []


def test_officials_declares_the_2004_era_floor():
    assert BY_KEY["officials"].first_season == 2004
    # datasets with genuine full history must not have picked one up
    assert BY_KEY["rosters"].first_season is None
    assert BY_KEY["shots"].first_season is None


@pytest.mark.parametrize("season", [1997, 1999, 2002, 2003])
def test_cli_refuses_officials_before_the_floor(tmp_path, capsys, season):
    """A pre-2004 officials build is skipped, and nothing is written."""
    rc = cli.main(
        [
            "--datasets",
            "officials",
            "--seasons",
            str(season),
            "--root",
            str(tmp_path / "raw"),
            "--out",
            str(tmp_path / "out"),
        ]
    )

    assert rc == 0
    assert f"skip officials {season}" in capsys.readouterr().out
    assert not (tmp_path / "out" / "wnba_stats_officials").exists()
