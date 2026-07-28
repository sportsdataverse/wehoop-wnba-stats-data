"""Offline tests for wnba_model_publish CLI parsing + store-layout mapping."""

import argparse

import pytest

from wnba_model_publish.builders import (
    _season_store_year,
    _season_str,
    _slug,
    _store_variant,
)
from wnba_model_publish.cli import _parse_season_types, _parse_seasons, build_parser


def test_parse_seasons_range_and_single():
    assert _parse_seasons("1997:2000") == [1997, 1998, 1999, 2000]
    assert _parse_seasons("2024") == [2024]


def test_parse_seasons_rejects_inverted():
    with pytest.raises(argparse.ArgumentTypeError):
        _parse_seasons("2024:2020")


def test_parse_season_types_canonical_order():
    assert _parse_season_types("Playoffs,Regular Season") == [
        "Regular Season",
        "Playoffs",
    ]


def test_parse_season_types_rejects_playoffs_alone():
    with pytest.raises(argparse.ArgumentTypeError):
        _parse_season_types("Playoffs")


def test_season_str_is_calendar_year():
    # WNBA seasons are single calendar years — no "2023-24" form.
    assert _season_str(2024) == "2024"
    assert _season_str(1997) == "1997"


def test_season_store_year_verbatim():
    # Both store halves are keyed by the same calendar year for the WNBA.
    assert _season_store_year(2024) == 2024
    assert _season_store_year("2024") == 2024
    assert _season_store_year(None) is None
    assert _season_store_year("bad") is None


def test_store_variant_layout():
    assert _store_variant("playerindex", {}) == ""
    assert _store_variant("leaguegamelog", {"season_type_all_star": "Regular Season"}) == "regular-season"
    assert (
        _store_variant(
            "leaguegamelog",
            {"season_type_all_star": "Playoffs", "player_or_team_abbreviation": "P"},
        )
        == "playoffs_p"
    )
    assert _store_variant("leaguedashplayerbiostats", {"season_type_all_star": "Playoffs"}) == "playoffs_totals"
    assert _store_variant("unknown_endpoint", {}) is None
    assert _slug("Regular Season") == "regular-season"


def test_cli_defaults():
    args = build_parser().parse_args(["impact", "--seasons", "1997:2026", "--out", "out/impact"])
    assert args.tag == "wnba_player_impact"
    assert args.seasons[0] == 1997 and args.seasons[-1] == 2026
    assert args.season_types == ["Regular Season", "Playoffs"]
