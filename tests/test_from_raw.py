"""Tests for the derived surfaces (enhanced pbp / on-court / possessions)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from wnba_data_build import from_raw

REAL = Path("/mnt/sdv_repos/wehoop-wnba-stats-raw/wnba_stats/json")
needs_real = pytest.mark.skipif(not REAL.is_dir(), reason="no sibling raw checkout")


def test_readonly_store_sets_and_restores(tmp_path: Path) -> None:
    before = dict(os.environ)
    with from_raw.readonly_store(tmp_path):
        assert os.environ["SDV_PY_WNBA_RAW_JSON_DIR"] == str(tmp_path)
        assert os.environ["SDV_PY_WNBA_RAW_JSON_READONLY"] == "1"
    assert os.environ.get("SDV_PY_WNBA_RAW_JSON_DIR") == before.get("SDV_PY_WNBA_RAW_JSON_DIR")
    assert os.environ.get("SDV_PY_WNBA_RAW_JSON_READONLY") == before.get("SDV_PY_WNBA_RAW_JSON_READONLY")


def test_readonly_store_restores_on_exception(tmp_path: Path) -> None:
    """A failed game must not leave the process pointed at another store."""
    before = os.environ.get("SDV_PY_WNBA_RAW_JSON_DIR")
    with pytest.raises(RuntimeError):
        with from_raw.readonly_store(tmp_path):
            raise RuntimeError("boom")
    assert os.environ.get("SDV_PY_WNBA_RAW_JSON_DIR") == before


def test_readonly_store_preserves_a_preexisting_value(tmp_path: Path) -> None:
    os.environ["SDV_PY_WNBA_RAW_JSON_DIR"] = "/prior"
    try:
        with from_raw.readonly_store(tmp_path):
            assert os.environ["SDV_PY_WNBA_RAW_JSON_DIR"] == str(tmp_path)
        assert os.environ["SDV_PY_WNBA_RAW_JSON_DIR"] == "/prior"
    finally:
        os.environ.pop("SDV_PY_WNBA_RAW_JSON_DIR", None)


def _no_live_fallback(monkeypatch) -> None:
    """Sever the engine's live fallback: a store miss must MISS, not fetch.

    The read-through store falls back to stats.wnba.com on a miss, so these
    empty-store tests only passed while the host was unreachable (they went
    red the moment a residential IP's throttle lifted). Offline-pin them.
    """
    from sportsdataverse.wnba import wnba_engine

    def _die(*args, **kwargs):
        raise RuntimeError("live fetch attempted in an offline test")

    monkeypatch.setattr(wnba_engine, "_fetch_pbp", _die)
    monkeypatch.setattr(wnba_engine, "_fetch_rotation", _die)
    monkeypatch.setattr(wnba_engine, "_fetch_box", _die)


def test_missing_game_returns_none_not_an_error(tmp_path: Path, monkeypatch) -> None:
    """An uncaptured game costs that game, never the season."""
    _no_live_fallback(monkeypatch)
    assert from_raw.process_game(tmp_path, "1022400001") is None


def test_process_season_of_nothing_is_empty(tmp_path: Path, monkeypatch) -> None:
    _no_live_fallback(monkeypatch)
    assert from_raw.process_season(tmp_path, 2024, ["1022400001"]) == {}


@needs_real
def test_engine_is_available() -> None:
    assert from_raw.engine_available()


@needs_real
def test_derives_a_real_game_from_captures_only() -> None:
    from wnba_data_build import raw

    gids = raw.available_games(REAL, "playbyplayv3", 2024)[:1]
    assert gids, "no 2024 play-by-play captured"
    pg = from_raw.process_game(REAL, gids[0])
    assert pg is not None
    assert pg.enhanced_pbp.height > 0
    assert pg.possessions.height > 0
    # possessions are a coarser grain than plays -- if they ever match, the
    # possession grouping has collapsed to one row per play
    assert pg.possessions.height < pg.enhanced_pbp.height
