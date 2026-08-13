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
from wnba_data_build.docs import dataset_page
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


# -- generated-page consistency ------------------------------------------------
#
# `Seasons built` is one of the _VOLATILE fields the docs drift gate excludes
# from its comparison, so `--check` passes whether or not these are right. These
# assertions are the only thing standing between a page documenting a 2004 floor
# and the same page advertising 1997 coverage two sections later.


@pytest.mark.parametrize("with_manifest", [True, False])
def test_officials_page_does_not_advertise_pre_floor_seasons(monkeypatch, with_manifest):
    """Holds on both coverage branches.

    ``coverage_table`` renders per-season counts when the committed manifest is
    present and a release-link sentence when it is not. CI has no manifest, so
    the second branch is the one that actually ships there -- a floor stated on
    only one of them is a page that omits it exactly where nobody looks.
    """
    if not with_manifest:
        monkeypatch.setattr("wnba_data_build.docs._games_in_repo", lambda: None)

    page = dataset_page("officials", live=False)

    assert "Officials coverage begins in 2004" in page, "caveat missing"
    assert "not built or published" in page, "coverage should name the floor on both branches"
    for season in ("1997", "1999", "2001", "2003"):
        assert f"| {season} |" not in page, (
            f"{season} is listed as built coverage but the floor is 2004"
        )
    if with_manifest:
        assert "| 2004 |" in page, "2004 must still be listed when counts render"


def test_player_game_logs_page_matches_builder_output():
    """Column descriptions must agree with what build_season_dataset emits."""
    page = dataset_page("player_game_logs", live=False)

    # the builder emits lower-case hyphenated values, and NULL (not "t") on team rows
    assert '"regular-season"' in page, "the emitted season_type value must be documented"
    assert 'not "Regular Season"' in page, (
        "the page should explicitly correct the upstream-cased form, since that is "
        "what a reader coming from stats.wnba.com will otherwise assume"
    )
    assert 'not "t"' in page, "measure_type must not claim a 't' value it never emits"
    assert "player_id.is_not_null()" in page, "the working filter should be named"


def test_team_partitioned_pages_flag_the_mislabelled_season_type():
    for dataset in ("rosters", "coaches"):
        page = dataset_page(dataset, live=False)
        assert "mislabelled copy of `team_id`" in page, f"{dataset} missing the warning"
