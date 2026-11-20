"""``matchups_cli`` -- leagueseasonmatchups compile + playoffs derived from boxscorematchupsv3.

Offline: a temporary raw tree built from envelopes and one trimmed real game.
"""

from __future__ import annotations

import json
from pathlib import Path

import polars as pl
import pytest
from wnba_data_build import matchups_cli

_GAME = Path(__file__).resolve().parent / "fixtures/boxscorematchupsv3/1042500101.json"
_HEADERS = ["SEASON_ID", "OFF_PLAYER_ID", "DEF_PLAYER_ID", "GP"]
_TAG = "wnba_stats_matchups"


def _payload(raw: Path, season: int, stem: str, rows: list[list]) -> None:
    d = raw / "leagueseasonmatchups" / str(season)
    d.mkdir(parents=True, exist_ok=True)
    body = {"resultSets": [{"name": "SeasonMatchups", "headers": _HEADERS, "rowSet": rows}]}
    (d / f"{stem}.json").write_text(json.dumps(body), encoding="utf-8")


def _games(raw: Path, game_ids: list[str]) -> None:
    d = raw / "boxscorematchupsv3" / "2025"
    d.mkdir(parents=True, exist_ok=True)
    for gid in game_ids:
        (d / f"{gid}.json").write_text(_GAME.read_text(encoding="utf-8"), encoding="utf-8")


def _files(out: Path, name: str) -> list[str]:
    return sorted(p.name for p in (out / _TAG).glob(f"{name}.*"))


def test_empty_playoffs_payload_is_derived_from_playoff_boxscores(tmp_path: Path) -> None:
    """stats.wnba.com serves no playoff leagueseasonmatchups rows; the games carry them."""
    raw, out = tmp_path / "raw", tmp_path / "out"
    _payload(raw, 2025, "playoffs_totals", [])
    _payload(raw, 2025, "playoffs_pergame", [])
    # the same game twice as two playoff ids, plus a regular-season id that must be ignored
    _games(raw, ["1042500101", "1042500102", "1022500001"])
    one = matchups_cli.game_matchups(raw, 2025, "regular-season")

    written = matchups_cli.build([2025], out, root=raw)

    tot = pl.read_parquet(out / _TAG / "leagueseasonmatchups_playoffs_totals_2025.parquet")
    pg = pl.read_parquet(out / _TAG / "leagueseasonmatchups_playoffs_pergame_2025.parquet")
    pairs = one.select("off_player_id", "def_player_id").unique().height
    assert written[f"{_TAG}/leagueseasonmatchups_playoffs_totals"] == pairs == tot.height
    assert tot["gp"].unique().to_list() == [2]
    assert tot["player_pts"].sum() == 2 * one["player_pts"].sum()
    assert pg["player_pts"].sum() == pytest.approx(one["player_pts"].sum(), abs=0.05 * pairs)
    assert tot["season_id"].unique().to_list() == ["42025"]
    assert tot["season_type"].unique().to_list() == ["playoffs"]
    assert pg["per_mode"].unique().to_list() == ["pergame"]
    # all three released formats, as for every other tag
    assert _files(out, "leagueseasonmatchups_playoffs_totals_2025") == [
        "leagueseasonmatchups_playoffs_totals_2025.csv",
        "leagueseasonmatchups_playoffs_totals_2025.parquet",
        "leagueseasonmatchups_playoffs_totals_2025.rds",
    ]


def test_regular_season_derivation_reads_only_regular_season_games(tmp_path: Path) -> None:
    """The parity check derives regular season through the same path; ids pick the type."""
    raw = tmp_path / "raw"
    _games(raw, ["1042500101", "1022500001", "1022500002"])
    tot = matchups_cli.derived_matchups(raw, 2025, "regular-season")["regular-season_totals"]
    assert tot["season_id"].unique().to_list() == ["22025"]
    assert tot["gp"].unique().to_list() == [2]


def test_a_real_playoffs_payload_is_never_replaced(tmp_path: Path) -> None:
    raw, out = tmp_path / "raw", tmp_path / "out"
    _payload(raw, 2025, "playoffs_totals", [["42025", 1, 2, 3]])
    _games(raw, ["1042500101"])

    written = matchups_cli.build([2025], out, root=raw)

    assert written[f"{_TAG}/leagueseasonmatchups_playoffs_totals"] == 1
    # pergame had no payload at all, so it is derived
    assert f"{_TAG}/leagueseasonmatchups_playoffs_pergame" in written


def test_an_empty_payload_writes_nothing_and_a_stale_asset_is_cleared(tmp_path: Path) -> None:
    """A schema-only asset would advertise coverage the tag does not have."""
    raw, out = tmp_path / "raw", tmp_path / "out"
    _payload(raw, 2025, "regular-season_totals", [["22025", 1, 2, 3]])
    matchups_cli.build([2025], out, root=raw)
    assert _files(out, "leagueseasonmatchups_regular-season_totals_2025")

    # the capture is re-swept and now comes back empty, with no games to derive from
    _payload(raw, 2025, "regular-season_totals", [])
    _payload(raw, 2025, "playoffs_totals", [])
    assert matchups_cli.build([2025], out, root=raw) == {}
    assert list((out / _TAG).glob("*_2025.*")) == []


def test_derived_frames_take_the_regular_season_columns_and_dtypes(tmp_path: Path) -> None:
    """Derived playoffs must concatenate with the season's regular-season assets."""
    raw, out = tmp_path / "raw", tmp_path / "out"
    # real headers, so the cast path runs against the published schema
    headers = [
        "SEASON_ID", "OFF_PLAYER_ID", "OFF_PLAYER_NAME", "DEF_PLAYER_ID", "DEF_PLAYER_NAME",
        "GP", "MATCHUP_MIN", "PARTIAL_POSS", "PLAYER_PTS", "TEAM_PTS", "MATCHUP_AST",
        "MATCHUP_TOV", "MATCHUP_BLK", "MATCHUP_FGM", "MATCHUP_FGA", "MATCHUP_FG_PCT",
        "MATCHUP_FG3M", "MATCHUP_FG3A", "MATCHUP_FG3_PCT", "HELP_BLK", "HELP_FGM", "HELP_FGA",
        "HELP_FG_PERC", "MATCHUP_FTM", "MATCHUP_FTA", "SFL", "MATCHUP_TIME_SEC",
    ]  # fmt: skip
    totals = ["22025", 1, "A B", 2, "C D", 6, "37:36", 180.6, 31, 181, 12, 6, 1, 11, 34]
    totals += [0.324, 1, 4, 0.25, 0, 0, 0, 0, 8, 10, 5, 2255.6]
    pergame = ["22025", 1, "A B", 2, "C D", 1, 13.2, 53.9, 3.0, 50.0, 1.0, 1.0, 0.0, 1.0]
    pergame += [9.0, 0.111, 1.0, 7.0, 0.143, 0, 0, 0, 0, 0.0, 0.0, 0.0]
    d = raw / "leagueseasonmatchups" / "2025"
    d.mkdir(parents=True)
    for stem, row, h in (
        ("regular-season_totals", totals, headers),
        ("regular-season_pergame", pergame, headers[:-1]),
    ):
        body = {"resultSets": [{"name": "SeasonMatchups", "headers": h, "rowSet": [row]}]}
        (d / f"{stem}.json").write_text(json.dumps(body), encoding="utf-8")
    _games(raw, ["1042500101"])

    matchups_cli.build([2025], out, root=raw)

    for pm in ("totals", "pergame"):
        reg = pl.read_parquet(out / _TAG / f"leagueseasonmatchups_regular-season_{pm}_2025.parquet")
        po = pl.read_parquet(out / _TAG / f"leagueseasonmatchups_playoffs_{pm}_2025.parquet")
        assert po.schema == reg.schema
        assert po.height > 0


def test_dry_run_prints_the_upload_plan(tmp_path: Path, capsys) -> None:
    raw = tmp_path / "raw"
    _payload(raw, 2025, "regular-season_totals", [["22025", 1, 2, 3]])
    argv = ["--seasons", "2025", "--root", str(raw), "--out", str(tmp_path / "out"), "--dry-run"]
    assert matchups_cli.main(argv) == 0
    assert (
        f"would upload {_TAG}/leagueseasonmatchups_regular-season_totals_2025.parquet"
        in capsys.readouterr().out
    )


def test_main_does_not_publish_an_empty_build(tmp_path: Path, capsys) -> None:
    raw = tmp_path / "raw"
    _payload(raw, 2025, "regular-season_totals", [])
    argv = ["--seasons", "2025", "--root", str(raw), "--out", str(tmp_path / "out"), "--publish"]
    assert matchups_cli.main(argv) == 0
    assert "not publishing" in capsys.readouterr().out
