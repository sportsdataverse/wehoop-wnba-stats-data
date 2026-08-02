"""CLI dispatch tests. The routing table is the only non-trivial logic here; the
builders and IO are covered elsewhere, so these stub them and assert the wiring."""

from __future__ import annotations

import polars as pl
import pytest
from wnba_data_build import cli
from wnba_data_build.datasets import DATASETS


def test_resolve_datasets_defaults_to_all_in_registry_order() -> None:
    assert cli._resolve_datasets(None) == list(DATASETS)


def test_resolve_datasets_subset_keeps_registry_order_and_dedupes() -> None:
    # request out of order + a duplicate; expect registry order, once each.
    got = [d.key for d in cli._resolve_datasets(["shots", "standings", "shots"])]
    order = [d.key for d in DATASETS]
    assert got == sorted({"shots", "standings"}, key=order.index)


def test_resolve_datasets_rejects_unknown_key() -> None:
    with pytest.raises(SystemExit):
        cli._resolve_datasets(["not_a_dataset"])


def test_shots_derives_from_the_passed_pbp_frame_without_rebuilding(
    monkeypatch,
) -> None:
    """shots must reuse the caller's pbp frame, not trigger a second build_pbp."""
    calls = {"build_pbp": 0, "build_shots": 0}

    def fake_build_pbp(root, season):
        calls["build_pbp"] += 1
        return pl.DataFrame({"x": [1]})

    def fake_build_shots(pbp):
        calls["build_shots"] += 1
        assert pbp.equals(pl.DataFrame({"x": [1]}))
        return pl.DataFrame({"shot": [1]})

    monkeypatch.setattr(cli._build, "build_pbp", fake_build_pbp)
    monkeypatch.setattr(cli._build, "build_shots", fake_build_shots)

    shots = next(d for d in DATASETS if d.key == "shots")
    pbp_frame = pl.DataFrame({"x": [1]})
    out = cli.build_dataset("root", shots, 2024, _pbp=pbp_frame)

    assert out.equals(pl.DataFrame({"shot": [1]}))
    assert calls == {"build_pbp": 0, "build_shots": 1}, "reused pbp, no rebuild"


def test_boxscores_route_to_team_and_player_levels(monkeypatch) -> None:
    seen = []
    monkeypatch.setattr(
        cli._build,
        "build_boxscores",
        lambda root, season, *, team_level: seen.append(team_level) or pl.DataFrame(),
    )
    for key in ("player_boxscores", "team_boxscores"):
        ds = next(d for d in DATASETS if d.key == key)
        cli.build_dataset("root", ds, 2024)
    assert seen == [False, True]
