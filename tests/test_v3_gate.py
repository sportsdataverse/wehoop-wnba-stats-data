"""Offline unit tests for the section-9.3 gate diff logic (WNBA)."""

from __future__ import annotations

import polars as pl
from wnba_data_build import v3_gate as vg


def _sched(rows: list[tuple[str, int, int]]) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": [r[0] for r in rows],
            "home_pts": [r[1] for r in rows],
            "away_pts": [r[2] for r in rows],
        }
    )


def _legacy_sched(rows: list[tuple[str, str, int]]) -> pl.DataFrame:
    """rows: (game_id, matchup, pts) team-level rows -- player_id null."""
    return pl.DataFrame(
        {
            "game_id": [r[0] for r in rows],
            "matchup": [r[1] for r in rows],
            "pts": [r[2] for r in rows],
            "player_id": [None] * len(rows),
        }
    )


def test_core_ids_excludes_noncore_types() -> None:
    ids = {"1021000001", "1041000001", "1011000001", "1031000001", "1051000001"}
    assert vg.core_ids(ids) == {"1021000001", "1041000001"}


def test_gate_schedule_ok_with_explained_preseason() -> None:
    staged = _sched([("1021000001", 80, 75)])
    legacy = _legacy_sched(
        [
            ("1021000001", "AAA vs. BBB", 80),
            ("1021000001", "BBB @ AAA", 75),
            ("1011000001", "AAA vs. BBB", 60),
            ("1011000001", "BBB @ AAA", 55),
        ]
    )
    f = vg.gate_schedule(2010, staged, legacy, raw_game_count=None)
    assert f["verdict"] == "OK"
    assert "legacy_excluded_noncore=1" in f["detail"]


def test_gate_schedule_flags_missing_and_score_mismatch() -> None:
    staged = _sched([("1021000001", 80, 75)])
    legacy = _legacy_sched(
        [
            ("1021000001", "AAA vs. BBB", 79),
            ("1021000001", "BBB @ AAA", 75),
            ("1021000002", "AAA vs. BBB", 60),
            ("1021000002", "BBB @ AAA", 55),
        ]
    )
    f = vg.gate_schedule(2010, staged, legacy, raw_game_count=None)
    assert f["verdict"] == "DIFF"
    assert "missing_in_v3=1" in f["detail"]
    assert "score_mismatch=1" in f["detail"]


def test_legacy_team_rows_filters_player_rows() -> None:
    df = pl.DataFrame({"game_id": ["a", "b"], "player_id": [None, 123]})
    out = vg.legacy_team_rows(df)
    assert out["game_id"].to_list() == ["a"]


def _pbp(games: dict[str, tuple[int, int, int]]) -> pl.DataFrame:
    rows = []
    for gid, (n_events, home, away) in games.items():
        for i in range(n_events):
            last = i == n_events - 1
            rows.append(
                {
                    "game_id": gid,
                    "score_home": home if last else 0,
                    "score_away": away if last else 0,
                }
            )
    return pl.DataFrame(rows)


def test_gate_pbp_legacy_ok() -> None:
    staged = _pbp({"1021000001": (10, 80, 75)})
    sched = _sched([("1021000001", 80, 75)])
    legacy = pl.DataFrame({"game_id": ["1021000001"]})
    f = vg.gate_pbp(2010, staged, sched, legacy, raw_ids=None)
    assert f["verdict"] == "OK"


def test_gate_pbp_score_vs_schedule_mismatch_is_diff() -> None:
    staged = _pbp({"1021000001": (10, 79, 75)})
    sched = _sched([("1021000001", 80, 75)])
    legacy = pl.DataFrame({"game_id": ["1021000001"]})
    f = vg.gate_pbp(2010, staged, sched, legacy, raw_ids=None)
    assert f["verdict"] == "DIFF"
    assert "score_mismatch=1" in f["detail"]


def test_gate_pbp_no_legacy_validates_against_raw_store() -> None:
    staged = _pbp({"1022400001": (10, 90, 85)})
    sched = _sched([("1022400001", 90, 85)])
    ok = vg.gate_pbp(2024, staged, sched, None, raw_ids={"1022400001"})
    assert ok["verdict"] == "NO_LEGACY_OK"
    short = vg.gate_pbp(2024, staged, sched, None, raw_ids={"1022400001", "1022400002"})
    assert short["verdict"] == "DIFF"
    assert "uncompiled=1" in short["detail"]


def test_gate_missing_staged_is_fatal() -> None:
    assert vg.gate_schedule(2010, None, None, None)["verdict"] == "MISSING_STAGED"
    assert vg.gate_pbp(2010, None, None, None, None)["verdict"] == "MISSING_STAGED"


def test_run_gate_exit_code(tmp_path) -> None:
    findings, code = vg.run_gate([2010], tmp_path, tmp_path, tmp_path)
    assert code == 1
    assert {f["verdict"] for f in findings} == {"MISSING_STAGED"}
