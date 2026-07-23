"""Reshape raw-store captures into the published season frames.

Pure functions over payloads already on disk — no network, so a season compiles
from a fixture tree and every builder is testable offline.

Season-level datasets are one payload per season, optionally spread over parameter
variants (measure type x season type x per mode) which are bound into a single
frame with the varying parameters carried as columns. Game-level datasets are one
payload per game, bound per season.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import polars as pl

from wnba_data_build import raw
from wnba_data_build.datasets import Dataset

#: Split a word boundary, then a lower/digit-to-upper boundary. Two passes rather
#: than one lookahead so trailing acronyms survive: a naive split-before-capital
#: turns ``LeagueID`` into ``league_i_d``, and these are join keys -- a mangled id
#: column name breaks joins downstream instead of erroring here.
_WORD_THEN_CAP = re.compile(r"(.)([A-Z][a-z]+)")
_LOWER_THEN_CAP = re.compile(r"([a-z0-9])([A-Z])")


def snake(name: str) -> str:
    """``TEAM_ID`` / ``teamId`` / ``LeagueID`` -> ``team_id`` / ``league_id``.

    stats.com mixes SHOUTING_SNAKE (v2 resultSets) with camelCase (v3) and embeds
    acronyms in both, while the published datasets are snake_case throughout.
    """
    if name.isupper():
        return name.lower()
    out = _WORD_THEN_CAP.sub(r"\1_\2", name)
    out = _LOWER_THEN_CAP.sub(r"\1_\2", out)
    return out.lower().replace("__", "_")


def frame_from_result_set(
    headers: list[str], rows: list[list[Any]], extra: dict[str, Any] | None = None
) -> pl.DataFrame:
    """Build a frame from a resultSet, snake-casing columns.

    ``strict=False`` because stats.com occasionally flips a column's type between
    rows (an id arriving as int in one row and str in another); erroring there
    would abandon a whole season over one cell.
    """
    if not headers:
        return pl.DataFrame()
    cols = [snake(h) for h in headers]
    df = pl.DataFrame(
        {c: [r[i] if i < len(r) else None for r in rows] for i, c in enumerate(cols)},
        strict=False,
    )
    for key, value in (extra or {}).items():
        df = df.with_columns(pl.lit(value).alias(key))
    return df


def _variant_columns(variant: str | None) -> dict[str, str]:
    """Carry a capture's varying parameters into the frame as columns.

    Variant slugs are ``{season_type}_{measure_type}_{per_mode}`` (whichever axes an
    endpoint supports). Binding several variants without these would silently stack
    rows that mean different things -- Base next to Advanced with no way to tell.
    """
    if not variant:
        return {}
    parts = variant.split("_")
    names = ("season_type", "measure_type", "per_mode")
    return {n: p for n, p in zip(names, parts)}


def build_season_dataset(
    root: str | Path, dataset: Dataset, season: int
) -> pl.DataFrame:
    """One season-level dataset, binding every captured parameter variant."""
    if dataset.endpoint is None:
        raise ValueError(f"{dataset.key} is derived; build it with its own builder")

    frames: list[pl.DataFrame] = []
    base = Path(root) / dataset.endpoint / str(season)

    # Unparameterized capture lives at {endpoint}/{season}.json
    single = raw.read_season(root, dataset.endpoint, season)
    variants: list[tuple[str | None, Any]] = []
    if single is not None:
        variants.append((None, single))
    elif base.is_dir():
        for path in sorted(base.glob("*.json")):
            payload = raw.read_season(root, dataset.endpoint, season, path.stem)
            if payload is not None:
                variants.append((path.stem, payload))

    for variant, payload in variants:
        headers, rows = raw.result_set(payload, dataset.result_set)
        if not headers:
            continue
        extra = {"season": season, **_variant_columns(variant)}
        frames.append(frame_from_result_set(headers, rows, extra))

    if not frames:
        return pl.DataFrame()
    return frames[0] if len(frames) == 1 else pl.concat(frames, how="diagonal_relaxed")


def build_game_dataset(
    root: str | Path, dataset: Dataset, season: int, game_ids: list[str] | None = None
) -> pl.DataFrame:
    """One game-level dataset, bound across a season's captured games.

    Games with no capture are skipped rather than failing the season: a sweep is
    always partially complete, and a missing game should cost that game only.
    """
    if dataset.endpoint is None:
        raise ValueError(f"{dataset.key} is derived; build it with its own builder")

    if game_ids is None:
        game_ids = raw.season_game_ids(root, season) or raw.available_games(
            root, dataset.endpoint, season
        )

    frames: list[pl.DataFrame] = []
    for gid, payload in raw.iter_game_payloads(root, dataset.endpoint, game_ids):
        headers, rows = raw.result_set(payload, dataset.result_set)
        if not headers:
            continue
        frames.append(
            frame_from_result_set(headers, rows, {"season": season, "game_id": gid})
        )

    if not frames:
        return pl.DataFrame()
    return pl.concat(frames, how="diagonal_relaxed")


def build(root: str | Path, dataset: Dataset, season: int) -> pl.DataFrame:
    """Dispatch to the season- or game-level builder for ``dataset``."""
    if dataset.level == "game":
        return build_game_dataset(root, dataset, season)
    return build_season_dataset(root, dataset, season)
