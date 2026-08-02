"""Builder tests. Synthetic payloads everywhere except the real-store cases."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from wnba_data_build import build
from wnba_data_build.datasets import BY_KEY, DATASETS, RELEASE_TAGS

REAL = Path("/mnt/sdv_repos/wehoop-wnba-stats-raw/wnba_stats/json")
needs_real = pytest.mark.skipif(not REAL.is_dir(), reason="no sibling raw checkout")


def _write(root: Path, rel: str, payload: object) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload), encoding="utf-8")


def _rs(headers, rows, name="X"):
    return {"resultSets": [{"name": name, "headers": headers, "rowSet": rows}]}


# -- column naming -------------------------------------------------------------


@pytest.mark.parametrize(
    "raw_name,expected",
    [
        ("TEAM_ID", "team_id"),
        ("PLAYER_NAME", "player_name"),
        ("W_PCT", "w_pct"),
        ("GP", "gp"),
        ("teamId", "team_id"),
        ("actionNumber", "action_number"),
        ("isFieldGoal", "is_field_goal"),
        # trailing acronyms: a naive split-before-capital yields league_i_d, and
        # these are join keys -- a mangled name breaks joins silently downstream
        ("LeagueID", "league_id"),
        ("SeasonID", "season_id"),
        ("TeamID", "team_id"),
    ],
)
def test_snake(raw_name: str, expected: str) -> None:
    assert build.snake(raw_name) == expected


# -- frames --------------------------------------------------------------------


def test_frame_from_result_set_adds_extras() -> None:
    df = build.frame_from_result_set(
        ["TEAM_ID", "W"], [[1, 2], [3, 4]], {"season": 2025}
    )
    assert df.columns == ["team_id", "w", "season"]
    assert df.height == 2 and df["season"].to_list() == [2025, 2025]


def test_frame_tolerates_short_rows() -> None:
    """A truncated row should cost that cell, not the season."""
    df = build.frame_from_result_set(["A", "B"], [[1, 2], [3]])
    assert df["b"].to_list() == [2, None]


def test_frame_tolerates_mixed_types() -> None:
    """stats.com flips an id between int and str across rows more often than you'd like."""
    df = build.frame_from_result_set(["ID"], [[1], ["2"]])
    assert df.height == 2


def test_empty_result_set_is_an_empty_frame() -> None:
    assert build.frame_from_result_set([], []).height == 0


def test_variant_columns_carry_the_parameters() -> None:
    """Binding variants without these silently stacks Base rows next to Advanced."""
    assert build._variant_columns("regular-season_base_totals") == {
        "season_type": "regular-season",
        "measure_type": "base",
        "per_mode": "totals",
    }
    assert build._variant_columns(None) == {}


# -- season datasets -----------------------------------------------------------


def test_season_dataset_binds_variants_and_tags_them(tmp_path: Path) -> None:
    for variant, rows in (
        ("regular-season_base_totals", [[1]]),
        ("playoffs_base_totals", [[2]]),
    ):
        _write(
            tmp_path, f"leaguedashteamstats/2025/{variant}.json", _rs(["TEAM_ID"], rows)
        )
    df = build.build_season_dataset(tmp_path, BY_KEY["team_season_stats"], 2025)
    assert df.height == 2
    assert set(df["season_type"].to_list()) == {"regular-season", "playoffs"}
    assert df["season"].to_list() == [2025, 2025]


def test_season_dataset_reads_the_unparameterized_form(tmp_path: Path) -> None:
    _write(tmp_path, "leaguestandingsv3/2025.json", _rs(["TEAM_ID"], [[1]]))
    assert build.build_season_dataset(tmp_path, BY_KEY["standings"], 2025).height == 1


def test_named_result_set_is_selected(tmp_path: Path) -> None:
    """rosters and coaches come from the same payload, different sets."""
    payload = {
        "resultSets": [
            {
                "name": "CommonTeamRoster",
                "headers": ["PLAYER"],
                "rowSet": [["a"], ["b"]],
            },
            {"name": "Coaches", "headers": ["COACH_NAME"], "rowSet": [["c"]]},
        ]
    }
    _write(tmp_path, "commonteamroster/2025/1611661313.json", payload)
    assert build.build_season_dataset(tmp_path, BY_KEY["rosters"], 2025).height == 2
    assert build.build_season_dataset(tmp_path, BY_KEY["coaches"], 2025).height == 1


def test_missing_season_is_empty_not_an_error(tmp_path: Path) -> None:
    assert build.build_season_dataset(tmp_path, BY_KEY["standings"], 1998).height == 0


def test_derived_dataset_refuses_the_generic_builder() -> None:
    with pytest.raises(ValueError, match="derived"):
        build.build_season_dataset("/tmp", BY_KEY["shots"], 2025)


# -- game datasets -------------------------------------------------------------


def test_game_dataset_binds_and_skips_misses(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "boxscoresummaryv2/2025/1022500001.json",
        _rs(["OFFICIAL_ID"], [[1], [2]], name="Officials"),
    )
    df = build.build_game_dataset(
        tmp_path, BY_KEY["officials"], 2025, ["1022500001", "1022500002"]
    )
    assert df.height == 2
    assert df["game_id"].unique().to_list() == ["1022500001"]


# -- registry ------------------------------------------------------------------


def test_registry_is_internally_consistent() -> None:
    assert len({d.key for d in DATASETS}) == len(DATASETS)
    assert all(d.release_tag.startswith("wnba_stats_") for d in DATASETS)
    assert all(d.level in ("season", "game", "derived") for d in DATASETS)
    # a derived dataset has no endpoint; everything else must name one
    for d in DATASETS:
        assert (d.endpoint is None) == (d.level == "derived"), d.key
    assert len(RELEASE_TAGS) == len(set(RELEASE_TAGS))


# -- against the real store ----------------------------------------------------


@needs_real
@pytest.mark.parametrize(
    "key",
    [
        "standings",
        "player_season_stats",
        "team_season_stats",
        "lineups",
        "rosters",
        "coaches",
        "draft",
        "schedules",
    ],
)
def test_builds_from_real_captures(key: str) -> None:
    df = build.build(REAL, BY_KEY[key], 1997)
    assert df.height > 0, f"{key} built empty from the real store"
    assert "season" in df.columns
    # id columns must survive naming intact -- these are join keys
    assert not [c for c in df.columns if "_i_d" in c], df.columns
