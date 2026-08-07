"""Offline unit tests for the Program V backfill (WNBA): gamelog pivot + checkpoint/resume."""

from __future__ import annotations

import json
from pathlib import Path

import polars as pl
import pytest
from wnba_data_build import v3_backfill as vb


def _write_gamelog(raw_root: Path, season: int, variant: str, rows: list[list]) -> None:
    headers = [
        "SEASON_ID",
        "TEAM_ID",
        "TEAM_ABBREVIATION",
        "TEAM_NAME",
        "GAME_ID",
        "GAME_DATE",
        "MATCHUP",
        "WL",
        "PTS",
    ]
    d = raw_root / "leaguegamelog" / str(season)
    d.mkdir(parents=True, exist_ok=True)
    payload = {"resultSets": [{"name": "LeagueGameLog", "headers": headers, "rowSet": rows}]}
    (d / f"{variant}.json").write_text(json.dumps(payload), encoding="utf-8")


@pytest.fixture()
def raw_root(tmp_path: Path) -> Path:
    root = tmp_path / "raw"
    _write_gamelog(
        root,
        2010,
        "regular-season",
        [
            ["12010", 1, "AAA", "Alphas", "1021000001", "2010-06-01", "AAA vs. BBB", "W", 80],
            ["12010", 2, "BBB", "Betas", "1021000001", "2010-06-01", "BBB @ AAA", "L", 75],
        ],
    )
    _write_gamelog(
        root,
        2010,
        "playoffs",
        [
            ["42010", 1, "AAA", "Alphas", "1041000001", "2010-09-01", "AAA vs. BBB", "L", 70],
            ["42010", 2, "BBB", "Betas", "1041000001", "2010-09-01", "BBB @ AAA", "W", 72],
        ],
    )
    return root


def test_schedule_from_gamelog_pivots_home_away(raw_root: Path) -> None:
    df = vb.schedule_from_gamelog(raw_root, 2010)
    assert df.height == 2
    assert df.schema["game_id"] == pl.Utf8
    reg = df.filter(pl.col("game_id") == "1021000001").row(0, named=True)
    assert reg["home_team_abbreviation"] == "AAA"
    assert reg["home_pts"] == 80 and reg["away_pts"] == 75
    assert reg["season"] == 2010 and reg["season_type"] == "regular-season"
    po = df.filter(pl.col("game_id") == "1041000001").row(0, named=True)
    assert po["season_type"] == "playoffs" and po["home_wl"] == "L"


def test_schedule_from_gamelog_empty_when_uncaptured(tmp_path: Path) -> None:
    df = vb.schedule_from_gamelog(tmp_path, 2010)
    assert df.height == 0
    assert set(vb._SCHEDULE_SCHEMA) == set(df.columns)


def test_season_done_checkpoint(tmp_path: Path) -> None:
    staging = tmp_path / "v3_staging"
    assert not vb.season_done(staging, 2010)
    staging.mkdir()
    paths = vb.season_paths(staging, 2010)
    assert paths["schedule"].name == "wnba_schedule_2010.parquet"
    assert paths["play_by_play"].name == "wnba_play_by_play_2010.parquet"
    for p in paths.values():
        p.touch()
    assert vb.season_done(staging, 2010)


def test_build_season_skips_when_done(tmp_path: Path, raw_root: Path) -> None:
    staging = tmp_path / "v3_staging"
    staging.mkdir()
    for p in vb.season_paths(staging, 2010).values():
        p.touch()
    out = vb.build_season(raw_root, 2010, staging, tmp_path / "cache")
    assert out == {"season": 2010, "status": "skipped"}


def test_build_season_uncaptured_games_dont_fail(tmp_path: Path, raw_root: Path) -> None:
    # No per-game pbp captures exist in the fixture store: build still writes the
    # schedule + empty frames and reports the games as uncaptured.
    staging = tmp_path / "v3_staging"
    out = vb.build_season(raw_root, 2010, staging, tmp_path / "cache")
    assert out["status"] == "built"
    assert out["games_indexed"] == 2
    assert out["games_uncaptured"] == 2
    assert out["games_processed"] == 0
    assert out["rows"]["schedule"] == 2
    sched = pl.read_parquet(vb.season_paths(staging, 2010)["schedule"])
    assert sched["game_id"].to_list() == ["1021000001", "1041000001"]
    # Checkpoint now holds: a rerun skips.
    assert vb.build_season(raw_root, 2010, staging, tmp_path / "cache")["status"] == "skipped"


def test_coerce_id_dtypes_pins_game_id_utf8_and_id_cols_int() -> None:
    # game_id always -> Utf8; a non-Utf8 *_id / player-slot column (e.g. the all-null
    # Null-dtype column diagonal_relaxed produces when a source frame lacked it) -> Int64.
    df = pl.DataFrame(
        {
            "game_id": [1021000001],
            "player_id": [12345],
            "off_player_1": [None],
        }
    )
    out = vb._coerce_id_dtypes(df)
    assert out.schema["game_id"] == pl.Utf8
    assert out.schema["player_id"] == pl.Int64
    assert out.schema["off_player_1"] == pl.Int64
