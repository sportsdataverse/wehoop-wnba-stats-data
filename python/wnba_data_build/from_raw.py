"""Enriched play-by-play, on-court lineups and possessions, from saved raw only.

Follows hoopR-nba-stats-data's ``process/from_raw.py``: rather than reimplementing
the derivations the R scripts carried (possessions, free-throw/foul linking,
garbage time), drive sdv-py's engine over the verbatim captures. The algorithm
then lives in one place for both leagues and improves for both at once, instead of
drifting between an R implementation here and a Python one there.

The WNBA engine (``sportsdataverse.wnba.wnba_engine``) already routes its fetches
through the raw store, so the whole job here is to **pin that store and force
read-only** for the duration. Read-only is the load-bearing part: without it a
missing capture is silently fetched from stats.wnba.com, which turns a
reproducible offline compile into a slow, partially-live one that can differ
between runs. With it, a gap surfaces as a skipped game.

Environment is restored afterwards so importing this module never leaves the
process pointed at a different store than the caller configured.
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


@contextmanager
def readonly_store(root: str | Path) -> Iterator[None]:
    """Point sdv-py's WNBA store at ``root`` in read-only mode, then restore.

    Read-only is what guarantees this is a compile and not a scrape: a capture
    that was never taken must surface as a gap, not as a live request.
    """
    keys = ("SDV_PY_WNBA_RAW_JSON_DIR", "SDV_PY_WNBA_RAW_JSON_READONLY")
    previous = {k: os.environ.get(k) for k in keys}
    os.environ["SDV_PY_WNBA_RAW_JSON_DIR"] = str(root)
    os.environ["SDV_PY_WNBA_RAW_JSON_READONLY"] = "1"
    try:
        yield
    finally:
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
