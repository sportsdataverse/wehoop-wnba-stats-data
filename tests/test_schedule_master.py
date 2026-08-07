"""Schedule master (D34): registry-derived in_* flags, manifest, coverage.

Offline, fixture-backed. The load-bearing invariant: the ``in_*`` column set
exactly mirrors the ``DATASETS`` registry's game-level keys — a dataset added
to the registry gets its flag with no edit here, and a hand-listed flag with
no registry entry cannot exist.

WNBA divergences locked here: yearly schedule files are mixed-grain
leaguegamelog frames (two TEAM rows per game plus player game-log rows)
pivoted to game level by the master build, and seasons are bare calendar
years derived from ``season_id`` ("22023" -> "2023"), never a span.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest
from wnba_data_build.datasets import DATASETS
from wnba_data_build.master import (
    GAME_LEVEL,
    build_coverage,
    build_master,
    flag_columns,
    game_level,
    games_in_data_repo,
    stamp_from_built,
    stamp_from_raw,
)

GIDS = ["1022300001", "1022300002", "1042300101"]

GAME_LEVEL_COLUMNS = (
    "game_id",
    "season",
    "season_type_id",
    "game_date",
    "home_team_id",
    "home_team_abbreviation",
    "home_team_name",
    "home_team_score",
    "away_team_id",
    "away_team_abbreviation",
    "away_team_name",
    "away_team_score",
)

_TEAMS = {
    "1022300001": ((1611661319, "LVA", "Las Vegas Aces"), (1611661328, "SEA", "Seattle Storm")),
    "1022300002": (
        (1611661313, "NYL", "New York Liberty"),
        (1611661322, "WAS", "Washington Mystics"),
    ),
    "1042300101": (
        (1611661319, "LVA", "Las Vegas Aces"),
        (1611661313, "NYL", "New York Liberty"),
    ),
    "1022400001": ((1611661319, "LVA", "Las Vegas Aces"), (1611661328, "SEA", "Seattle Storm")),
}


def _yearly(year: str, gids: list[str]) -> pl.DataFrame:
    """Mixed-grain leaguegamelog rows, the committed-file shape: two TEAM rows
    per game plus a player game-log row (``player_id`` set) that the game-level
    pivot must drop."""
    rows = []
    for i, gid in enumerate(gids):
        sid = ("2" if i < len(gids) - 1 else "4") + year
        (home_id, home_abbr, home_name), (away_id, away_abbr, away_name) = _TEAMS[gid]
        date = f"{year}-05-19"
        home_vs = f"{home_abbr} vs. {away_abbr}"
        rows.append([sid, home_id, home_abbr, home_name, gid, date, home_vs, 88, None, None])
        rows.append(
            [
                sid,
                away_id,
                away_abbr,
                away_name,
                gid,
                date,
                f"{away_abbr} @ {home_abbr}",
                84,
                None,
                None,
            ]
        )
        # Player game-log row: same game id, must not double the pivot.
        rows.append([sid, home_id, home_abbr, home_name, gid, date, home_vs, 21, 203400, "p"])
    return pl.DataFrame(
        rows,
        schema={
            "season_id": pl.Utf8,
            "team_id": pl.Int64,
            "team_abbreviation": pl.Utf8,
            "team_name": pl.Utf8,
            "game_id": pl.Utf8,
            "game_date": pl.Utf8,
            "matchup": pl.Utf8,
            "pts": pl.Int64,
            "player_id": pl.Int64,
            "measure_type": pl.Utf8,
        },
        orient="row",
    )


def _flagged(frame: pl.DataFrame, flag: str, gids: list[str]) -> pl.DataFrame:
    return frame.with_columns(pl.col("game_id").is_in(gids).alias(flag))


def test_flag_columns_exactly_mirror_the_registry():
    assert flag_columns() == tuple(f"in_{d.key}" for d in DATASETS if d.level == "game")
    assert len(flag_columns()) > 0


def test_game_level_pivots_two_team_rows_into_one_game_row():
    frame = game_level(_yearly("2023", GIDS))
    assert frame.height == len(GIDS)
    row = frame.filter(pl.col("game_id") == GIDS[0]).to_dicts()[0]
    assert row["home_team_abbreviation"] == "LVA"
    assert row["away_team_abbreviation"] == "SEA"
    assert row["home_team_score"] == 88
    assert row["away_team_score"] == 84


def test_season_is_a_bare_calendar_year_from_season_id():
    """WNBA season format: SEASON_ID "22023" -> "2023", never a "2023-24" span."""
    frame = game_level(_yearly("2023", GIDS))
    assert frame["season"].unique().to_list() == ["2023"]
    assert frame.schema["season"] == pl.Utf8
    assert frame.filter(pl.col("game_id") == GIDS[-1])["season_type_id"].item() == "4"
    assert str(frame["game_date"].min()) == "2023-05-19"


def test_master_schema_is_game_level_schema_plus_registry_flags():
    master = build_master([_yearly("2023", GIDS), _yearly("2024", ["1022400001"])])
    assert set(master.columns) == set(GAME_LEVEL_COLUMNS) | set(flag_columns())
    assert master.columns == sorted(master.columns)  # pinned order
    assert master.schema["game_id"] == pl.Utf8
    assert master["season"].unique().sort().to_list() == ["2023", "2024"]
    for flag in flag_columns():
        assert master.schema[flag] == pl.Boolean


def test_stamp_from_built_reads_the_run_artifacts(tmp_path: Path):
    dataset = GAME_LEVEL[0]  # pbp
    built = tmp_path / dataset.release_tag
    built.mkdir(parents=True)
    pl.DataFrame({"game_id": GIDS[:2]}).write_parquet(built / f"{dataset.stem}_2023.parquet")

    stamped = game_level(stamp_from_built(_yearly("2023", GIDS), tmp_path, 2023))
    assert stamped[f"in_{dataset.key}"].to_list() == [True, True, False]
    # Datasets with no built file this run stay False, not absent.
    for other in GAME_LEVEL[1:]:
        assert stamped[f"in_{other.key}"].to_list() == [False, False, False]


def test_stamp_from_built_restores_int_origin_ids(tmp_path: Path):
    """An Int64 built game_id must still match the Utf8 "1022300001"."""
    dataset = GAME_LEVEL[0]
    built = tmp_path / dataset.release_tag
    built.mkdir(parents=True)
    pl.DataFrame({"game_id": [int(g) for g in GIDS[:1]]}).write_parquet(
        built / f"{dataset.stem}_2023.parquet"
    )
    stamped = game_level(stamp_from_built(_yearly("2023", GIDS), tmp_path, 2023))
    assert stamped[f"in_{dataset.key}"].to_list() == [True, False, False]


def test_stamp_from_raw_uses_the_dataset_source_endpoint():
    endpoint_gids = {d.endpoint: {GIDS[0]} for d in GAME_LEVEL if d.endpoint}
    stamped = game_level(stamp_from_raw(_yearly("2023", GIDS), endpoint_gids))
    for dataset in GAME_LEVEL:
        assert stamped[f"in_{dataset.key}"].to_list() == [True, False, False]


def test_manifest_keeps_only_games_with_a_flag():
    frame = _flagged(_yearly("2023", GIDS), flag_columns()[0], [GIDS[0]])
    master = build_master([frame])
    manifest = games_in_data_repo(master)
    assert manifest["game_id"].to_list() == [GIDS[0]]
    assert manifest.columns == master.columns  # same schema, filtered rows


def test_coverage_grain_and_rates():
    frame = _flagged(_yearly("2023", GIDS), flag_columns()[0], GIDS[:2])
    coverage = build_coverage(build_master([frame]))
    assert coverage.height == 2  # (2023, "2") + (2023, "4")
    regular = coverage.filter(pl.col("season_type_id") == "2").to_dicts()[0]
    assert regular["n_games"] == 2
    assert regular[f"pct_{flag_columns()[0]}"] == 1.0
    assert str(regular["first_date"]) == "2023-05-19"


def test_build_master_requires_frames():
    with pytest.raises(ValueError, match="at least one season frame"):
        build_master([])
