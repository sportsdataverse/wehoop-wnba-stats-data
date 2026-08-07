"""Enriched play-by-play, on-court lineups and possessions, from saved raw only.

Follows hoopR-nba-stats-data's ``process/from_raw.py``: rather than reimplementing
the derivations the R scripts carried (possessions, free-throw/foul linking,
garbage time), drive sdv-py's engine over the verbatim captures. The algorithm
then lives in one place for both leagues and improves for both at once, instead of
drifting between an R implementation here and a Python one there.

The WNBA engine (``sportsdataverse.wnba.wnba_engine``) already routes its fetches
through the raw store, so the job here is to **pin that store and make a miss
terminal** for the duration.

``SDV_PY_WNBA_RAW_JSON_READONLY=1`` alone does NOT do that. In sdv-py's shared
chokepoint (``nba_possessions._through_raw_store``) ``readonly`` suppresses only
the *persist* half -- a store miss still calls the live fetcher and merely
declines to write the result::

    payload = fetch()                 # runs on every miss, readonly or not
    if ro:
        return payload                # readonly == "don't write", not "don't fetch"

That matters here because ``gamerotation`` is sparse in the raw store (193 of
220 games in 2010 were never captured), so a compile that trusts the env var
alone fires one live stats.wnba.com request per missing capture -- each hanging
until the 30s curl timeout on a host that is already IP-sensitive. Observed
cost: ~10s/game for WNBA versus ~0.12s/game for the NBA path, plus sporadic
``Timeout`` exceptions surfacing as bogus "engine returned no pbp" failures.

:func:`readonly_store` therefore also swaps the engine's three module-level
fetch helpers for store-only readers that return ``{}`` on a miss. That is the
seam sdv-py itself documents as monkeypatchable ("module-level so tests can
monkeypatch them"), and it makes the compile genuinely offline: a gap surfaces
as a skipped game, which is what this module always claimed to guarantee.

Environment and the patched helpers are restored afterwards so importing this
module never leaves the process pointed at a different store -- or a different
fetch path -- than the caller configured.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import NamedTuple

import polars as pl


class ProcessedGame(NamedTuple):
    """One game's derived surfaces."""

    game_id: str
    enhanced_pbp: pl.DataFrame
    on_court: pl.DataFrame
    possessions: pl.DataFrame


#: Engine fetch helper -> raw-store endpoint directory it reads.
_FETCH_ENDPOINTS = {
    "_fetch_pbp": "playbyplayv3",
    "_fetch_rotation": "gamerotation",
    "_fetch_box": "boxscoretraditionalv3",
}


def _store_only_reader(root: str | Path, endpoint: str):
    """A ``_fetch_*`` replacement that reads the store and never hits the network."""

    def read(game_id: str) -> dict:
        from wnba_data_build import raw

        payload = raw.read_game(root, endpoint, game_id)
        return payload if isinstance(payload, dict) else {}

    return read


@contextmanager
def readonly_store(root: str | Path) -> Iterator[None]:
    """Point sdv-py's WNBA store at ``root`` and make a miss terminal, then restore.

    Sets the store env vars *and* swaps the engine's module-level ``_fetch_*``
    helpers for store-only readers. The env vars alone are not enough --
    ``SDV_PY_WNBA_RAW_JSON_READONLY`` suppresses the persist, not the fetch, so a
    missing capture would still cost a live stats.wnba.com round trip (see the
    module docstring). With the helpers swapped, a capture that was never taken
    surfaces as a gap rather than a live request.
    """
    from sportsdataverse.wnba import wnba_engine

    keys = ("SDV_PY_WNBA_RAW_JSON_DIR", "SDV_PY_WNBA_RAW_JSON_READONLY")
    previous = {k: os.environ.get(k) for k in keys}
    os.environ["SDV_PY_WNBA_RAW_JSON_DIR"] = str(root)
    os.environ["SDV_PY_WNBA_RAW_JSON_READONLY"] = "1"

    patched = {name: getattr(wnba_engine, name, None) for name in _FETCH_ENDPOINTS}
    for name, endpoint in _FETCH_ENDPOINTS.items():
        if patched[name] is not None:
            setattr(wnba_engine, name, _store_only_reader(root, endpoint))
    try:
        yield
    finally:
        for name, original in patched.items():
            if original is not None:
                setattr(wnba_engine, name, original)
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def process_game(root: str | Path, game_id: str) -> ProcessedGame | None:
    """Derive one game's enhanced pbp, on-court lineups and possessions.

    Returns ``None`` when the engine cannot build the game from what was captured
    — a season is always partially swept, and one ungrounded game should cost that
    game rather than the season.
    """
    from sportsdataverse.wnba.wnba_engine import (
        wnba_enhanced_pbp,
        wnba_on_court,
        wnba_possessions,
    )

    gid = str(game_id).zfill(10)
    with readonly_store(root):
        try:
            pbp = wnba_enhanced_pbp(gid)
            # The engine returns an empty frame for an uncaptured game rather than
            # raising, so an all-empty result is indistinguishable from a real gap
            # unless it is checked for. Report it as the gap it is.
            if not isinstance(pbp, pl.DataFrame) or pbp.is_empty():
                return None
            return ProcessedGame(gid, pbp, wnba_on_court(gid), wnba_possessions(gid))
        except Exception:  # noqa: BLE001 - a game-local gap must not kill the season
            return None


def process_season(
    root: str | Path, season: int, game_ids: list[str] | None = None
) -> dict[str, pl.DataFrame]:
    """Bind a season's derived surfaces into one frame each.

    Returns only the non-empty surfaces, keyed ``enhanced_pbp`` / ``on_court`` /
    ``possessions``.
    """
    from wnba_data_build import raw

    if game_ids is None:
        game_ids = raw.season_game_ids(root, season) or raw.available_games(
            root, "playbyplayv3", season
        )

    acc: dict[str, list[pl.DataFrame]] = {
        "enhanced_pbp": [],
        "on_court": [],
        "possessions": [],
    }
    for gid in game_ids:
        got = process_game(root, gid)
        if got is None:
            continue
        for name, df in (
            ("enhanced_pbp", got.enhanced_pbp),
            ("on_court", got.on_court),
            ("possessions", got.possessions),
        ):
            if isinstance(df, pl.DataFrame) and not df.is_empty():
                acc[name].append(
                    df.with_columns(game_id=pl.lit(got.game_id), season=pl.lit(season))
                )

    out: dict[str, pl.DataFrame] = {}
    for name, frames in acc.items():
        if frames:
            out[name] = pl.concat(frames, how="diagonal_relaxed")
    return out


def engine_available() -> bool:
    """Whether sdv-py exposes the WNBA engine this module drives."""
    try:
        from sportsdataverse.wnba import wnba_engine  # noqa: F401
    except ImportError:
        return False
    return True
