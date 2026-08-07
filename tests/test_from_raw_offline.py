"""`readonly_store` must make a raw-store miss terminal, never a live fetch."""

from __future__ import annotations

from sportsdataverse.wnba import wnba_engine
from wnba_data_build.from_raw import readonly_store

_FETCHERS = ("_fetch_pbp", "_fetch_rotation", "_fetch_box")


def test_readonly_store_makes_a_miss_terminal_not_a_live_fetch() -> None:
    """A store miss returns {} without touching stats.wnba.com.

    Regression: ``SDV_PY_WNBA_RAW_JSON_READONLY`` suppresses only the *persist*
    half of sdv-py's ``_through_raw_store`` -- a miss still called the live
    fetcher, costing a 30s curl timeout per uncaptured ``gamerotation`` (sparse
    in the raw store: 27 of 220 games in 2010). ``readonly_store`` now swaps the
    engine's module-level ``_fetch_*`` helpers for store-only readers.
    """
    originals = {name: getattr(wnba_engine, name) for name in _FETCHERS}

    with readonly_store("nonexistent-store-root"):
        for name in _FETCHERS:
            patched = getattr(wnba_engine, name)
            assert patched is not originals[name], f"{name} was not swapped"
            # Empty dict on a miss -- and crucially no network call, no exception.
            assert patched("1021000001") == {}

    for name, original in originals.items():
        assert getattr(wnba_engine, name) is original, f"{name} was not restored"


def test_readonly_store_reads_a_present_capture(tmp_path) -> None:
    """A capture that IS on disk still resolves through the swapped helper."""
    import json

    root = tmp_path / "json"
    d = root / "playbyplayv3" / "2010"
    d.mkdir(parents=True)
    (d / "1021000001.json").write_text(json.dumps({"game": {"actions": [1, 2]}}), encoding="utf-8")

    with readonly_store(root):
        payload = wnba_engine._fetch_pbp("1021000001")
    assert payload["game"]["actions"] == [1, 2]
