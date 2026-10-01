"""Stage 16 ``rolling_windows`` (F3b-T3): rolling shooting form over the committed tree.

sdv-py's ``shot_events`` + ``rolling_windows`` over every committed shots season up
to the one built, dated by the committed schedule master plus this season's
``schedules`` frame. WNBA seasons are calendar years, so ``season`` goes in and out
unchanged. The WNBA shots carry no ``season_type_id``: it is the game id's type
digit (``game_id[2]``), the same derivation stage 17 ``metric_curves`` uses.
The archive tests run on two real committed seasons copied to a tmp tree; their
oracle is a plain-Python hand count of A'ja Wilson's 2024 + 2025 attempts.
"""

from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path

import polars as pl
import pytest
from polars.testing import assert_frame_equal
from sportsdataverse.rolling_windows import OUTPUT_SCHEMA, rolling_windows, shot_events
from wnba_data_build import build, cli, datasets, docs
from wnba_data_build.manifest import _NEW_TAG_ENDPOINTS
from wnba_data_build.models import MODELS, polars_schema

REPO = Path(__file__).resolve().parents[1]
TREE = REPO / "wnba_stats"
MASTER = "wnba_stats_schedule_master.parquet"
WILSON = "1628932"
SCHEMA = {**OUTPUT_SCHEMA, "id_source": pl.Utf8}

#: Reads the committed wnba_stats/ tree, which PR CI does not check out.
real = pytest.mark.archive


def _shots(game_id: str, clocks: list[str], results: list[str], values: list[int]) -> pl.DataFrame:
    k = len(clocks)
    return pl.DataFrame(
        {
            "game_id": [game_id] * k,
            "season": pl.Series([2025] * k, dtype=pl.Int32),
            "period": [1] * k,
            "clock": clocks,
            "team_id": [1611661319] * k,
            "person_id": [1628932] * k,
            "player_name": ["Wilson"] * k,
            "shot_result": results,
            "shot_value": values,
        }
    )


# A'ja Wilson's first four attempts of 1022500005 (2025-05-17, regular season) and
# her first two of 1042500111 (2025-09-14, playoffs), verbatim from the committed
# wnba_stats/shots/parquet/shots_2025.parquet.
REGULAR = _shots(
    "1022500005",
    ["PT09M25.00S", "PT08M25.00S", "PT08M09.00S", "PT06M19.00S"],
    ["Made", "Missed", "Made", "Missed"],
    [2, 2, 2, 3],
)
PLAYOFF = _shots("1042500111", ["PT09M30.00S", "PT06M59.00S"], ["Made", "Missed"], [2, 2])
#: The same real regular-season rows re-keyed to a type-5 game id: never counted.
#: It binds the digit's POSITION -- game_id[3] is the season's "2" on every
#: 2020s id, so a slice(3, 1) read would count these as regular season.
TYPE5 = REGULAR.with_columns(game_id=pl.lit("1052500005"))
SHOTS = pl.concat([REGULAR, PLAYOFF, TYPE5])
DATES = pl.DataFrame(
    {
        "game_id": ["1022500005", "1042500111", "1052500005"],
        "game_date": [date(2025, 5, 17), date(2025, 9, 14), date(2025, 5, 18)],
    }
)


def _row(df: pl.DataFrame, **kw) -> dict:
    out = df.filter(pl.all_horizontal([pl.col(k) == v for k, v in kw.items()]))
    assert out.height == 1, out
    return out.row(0, named=True)


@pytest.fixture
def small_tree(tmp_path: Path) -> Path:
    base = tmp_path / "wnba_stats"
    (base / "shots" / "parquet").mkdir(parents=True)
    SHOTS.write_parquet(base / "shots" / "parquet" / "shots_2025.parquet")
    DATES.write_parquet(base / MASTER)
    return base


def test_regular_season_and_playoffs_count_type_5_does_not(small_tree):
    df = build.build_rolling_windows(small_tree, 2025)
    assert dict(df.schema) == SCHEMA
    assert set(df["season"]) == {2025}, "calendar year in, calendar year out: no +1"
    assert set(df["id_source"]) == {"wnba_stats"}
    fga = _row(df, window_unit="fga", window_n=50)
    assert fga["n"] == 6, "4 regular + 2 playoff attempts; the 4 type-5 rows are not events"
    assert fga["cur"] == 0.5 and fga["prev"] is None and fga["qualified"] is False
    assert fga["entity_id"] == WILSON and fga["team_id"] == "1611661319"
    assert fga["last_event_date"] == date(2025, 9, 14)
    fg3a = _row(df, window_unit="fg3a", window_n=50)
    assert (fg3a["n"], fg3a["cur"]) == (1, 0.0)


def test_this_seasons_schedule_dates_a_game_the_master_lacks(small_tree):
    """The master is unioned at the END of a run, so tonight's games are only in stage 08."""
    DATES.filter(pl.col("game_id") != "1042500111").write_parquet(small_tree / MASTER)
    with pytest.raises(ValueError, match="game_date"):
        build.build_rolling_windows(small_tree, 2025)
    # stage 08's frame as the reshaper builds it: game_date text, a row per team
    schedule = pl.DataFrame({"game_id": ["1042500111"] * 2, "game_date": ["2025-09-14"] * 2})
    df = build.build_rolling_windows(small_tree, 2025, schedule=schedule)
    assert _row(df, window_unit="fga", window_n=50)["n"] == 6
    # ...and the committed file stands in when stage 08 is not in the run
    (small_tree / "schedules" / "parquet").mkdir(parents=True)
    schedule.write_parquet(
        small_tree / "schedules" / "parquet" / "wnba_stats_schedule_2025.parquet"
    )
    assert (
        _row(build.build_rolling_windows(small_tree, 2025), window_unit="fga", window_n=50)["n"]
        == 6
    )


def test_missing_season_returns_the_contract_schema(small_tree):
    empty = build.build_rolling_windows(small_tree, 2026)
    assert empty.height == 0 and dict(empty.schema) == SCHEMA


def test_cli_reuses_this_runs_frames_and_falls_back_to_the_tree(small_tree):
    """The daily run builds schedules and shots first; both reach the stage."""
    (small_tree / "shots" / "parquet" / "shots_2025.parquet").unlink()
    DATES.head(1).write_parquet(small_tree / MASTER)
    ds = datasets.BY_KEY["rolling_windows"]
    sched = DATES.with_columns(pl.col("game_date").cast(pl.Utf8))
    out = cli.build_dataset("root", ds, 2025, _shots=SHOTS, _schedule=sched, base=small_tree)
    assert out.height > 0
    assert cli.build_dataset("root", ds, 2025, base=small_tree).height == 0


def test_stage_16_is_registered_everywhere():
    ds = datasets.BY_KEY["rolling_windows"]
    assert (ds.stem, ds.release_tag, ds.level, ds.endpoint) == (
        "rolling_windows",
        "wnba_stats_rolling_windows",
        "derived",
        None,
    )
    keys = [d.key for d in datasets.DATASETS]
    assert keys.index("rolling_windows") == keys.index("metric_curves") - 1, "16 builds before 17"
    assert keys.index("schedules") < keys.index("shots") < keys.index("rolling_windows")
    notes = datasets.RELEASE_NOTES["wnba_stats_rolling_windows"]
    for phrase in ("season_type_id", "id_source", "calendar", "career_baseline", "1997"):
        assert phrase in notes
    assert docs.BUILDER["rolling_windows"] == "python/wnba_stats_16_rolling_windows_creation.py"
    assert polars_schema("rolling_windows") == pl.Schema(SCHEMA)
    assert "rolling_windows" in MODELS
    assert "wnba_stats_rolling_windows" in _NEW_TAG_ENDPOINTS


@pytest.fixture(scope="module")
def two_seasons(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The committed 2024 + 2025 shots and the schedule master, copied to a tmp tree."""
    src = [TREE / "shots" / "parquet" / f"shots_{y}.parquet" for y in (2024, 2025)]
    if not all(p.is_file() for p in src) or not (TREE / MASTER).is_file():
        pytest.skip("no committed shots / schedule master")
    base = tmp_path_factory.mktemp("tree") / "wnba_stats"
    (base / "shots" / "parquet").mkdir(parents=True)
    for p in src:
        shutil.copy(p, base / "shots" / "parquet" / p.name)
    shutil.copy(TREE / MASTER, base / MASTER)
    return base


@pytest.fixture(scope="module")
def rw2025(two_seasons: Path) -> pl.DataFrame:
    return build.build_rolling_windows(two_seasons, 2025)


# hand count (plain Python): Wilson's type-2/4 attempts ordered by (date, game,
# period, clock down, row), 2024 then 2025 -- 1,747 attempts (842 before 2025),
# 142 threes (68 before 2025)
@real
@pytest.mark.parametrize(
    ("unit", "metric", "window", "n", "cur", "prev", "start", "career"),
    [
        ("fga", "fg_pct", 50, 50, 0.44, 0.52, 0.58, 0.510312),
        ("fga", "fg_pct", 200, 200, 0.46, 0.565, 0.5, 0.514544),
        ("fg3a", "fg3_pct", 50, 50, 0.5, 0.26, 0.32, 0.315217),
        ("fg3a", "fg3_pct", 200, 142, 0.380282, None, None, None),
    ],
)
def test_wilson_windows_match_a_hand_count(
    rw2025, unit, metric, window, n, cur, prev, start, career
):
    r = _row(rw2025, entity_id=WILSON, window_unit=unit, metric=metric, window_n=window)
    assert r["n"] == n and r["season"] == 2025 and r["id_source"] == "wnba_stats"
    assert r["cur"] == pytest.approx(cur, abs=1e-6)
    for col, want in (("prev", prev), ("season_start", start), ("career_baseline", career)):
        assert r[col] == (None if want is None else pytest.approx(want, abs=1e-6)), col
    assert r["last_event_date"] == date(2025, 10, 10)


@real
def test_reading_only_this_seasons_shooters_changes_nothing(two_seasons, rw2025):
    """The stage reads history for the season's shooters only; the full league is the oracle."""
    shots = pl.concat(
        pl.read_parquet(p) for p in sorted((two_seasons / "shots" / "parquet").glob("*.parquet"))
    ).with_columns(season_type_id=pl.col("game_id").str.slice(2, 1))
    dates = pl.read_parquet(two_seasons / MASTER, columns=["game_id", "game_date"])
    full = rolling_windows(shot_events(shots, dates), 2025).with_columns(
        id_source=pl.lit("wnba_stats")
    )
    assert_frame_equal(rw2025, full)
    assert rw2025["entity_id"].n_unique() > 100, "every 2025 shooter, not just Wilson"
