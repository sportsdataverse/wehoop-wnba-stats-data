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
from sportsdataverse.metric_curves import (
    OUTPUT_SCHEMA,
    SHOT_ATTEMPT_COLUMNS,
    metric_curves,
    shot_attempts,
)
from sportsdataverse.rolling_windows import OUTPUT_SCHEMA as ROLLING_SCHEMA
from sportsdataverse.rolling_windows import SHOT_COLUMNS, rolling_windows, shot_events

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


def build_season_dataset(root: str | Path, dataset: Dataset, season: int) -> pl.DataFrame:
    """One season-level dataset, binding every captured parameter variant."""
    if dataset.endpoint is None:
        raise ValueError(f"{dataset.key} is derived; build it with its own builder")

    frames: list[pl.DataFrame] = []

    # Unparameterized capture lives at {endpoint}/{season}.json
    single = raw.read_season(root, dataset.endpoint, season)
    variants: list[tuple[str | None, Any]] = []
    if single is not None:
        variants.append((None, single))
    else:
        # Variants were discovered by globbing a local directory, which a URL root
        # cannot do -- every season-level family "skipped: no rows" over HTTP.
        for stem in raw.season_variants(root, dataset.endpoint, season):
            payload = raw.read_season(root, dataset.endpoint, season, stem)
            if payload is not None:
                variants.append((stem, payload))

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
        frames.append(frame_from_result_set(headers, rows, {"season": season, "game_id": gid}))

    if not frames:
        return pl.DataFrame()
    return pl.concat(frames, how="diagonal_relaxed")


def build(root: str | Path, dataset: Dataset, season: int) -> pl.DataFrame:
    """Dispatch to the season- or game-level builder for ``dataset``."""
    if dataset.level == "game":
        return build_game_dataset(root, dataset, season)
    return build_season_dataset(root, dataset, season)


# -- play-by-play + shots ------------------------------------------------------
#
# playbyplayv3 does not use the resultSets envelope: its rows live under
# game.actions as dicts, so it needs its own extractor rather than result_set().


def pbp_rows(payload: Any) -> list[dict[str, Any]]:
    """Action rows from one captured ``playbyplayv3`` payload."""
    if not isinstance(payload, dict):
        return []
    return [a for a in (payload.get("game") or {}).get("actions") or [] if isinstance(a, dict)]


def build_pbp(root: str | Path, season: int, game_ids: list[str] | None = None) -> pl.DataFrame:
    """Season play-by-play, bound across every captured game.

    Columns are snake-cased from the v3 camelCase field names. Rows are kept in
    capture order within a game and games in id order, so the frame is stable
    across rebuilds.
    """
    if game_ids is None:
        game_ids = raw.season_game_ids(root, season) or raw.available_games(
            root, "playbyplayv3", season
        )
    frames: list[pl.DataFrame] = []
    for gid, payload in raw.iter_game_payloads(root, "playbyplayv3", game_ids):
        rows = pbp_rows(payload)
        if not rows:
            continue
        df = pl.DataFrame(rows, infer_schema_length=None, strict=False)
        df = df.rename({c: snake(c) for c in df.columns})
        frames.append(df.with_columns(game_id=pl.lit(gid), season=pl.lit(season)))
    if not frames:
        return pl.DataFrame()
    return pl.concat(frames, how="diagonal_relaxed")


#: Field-goal actions carry shot geometry; everything else in pbp does not.
_SHOT_COLUMNS = (
    "game_id",
    "season",
    "period",
    "clock",
    "team_id",
    "team_tricode",
    "person_id",
    "player_name",
    "action_type",
    "sub_type",
    "shot_result",
    "shot_value",
    "shot_distance",
    "x_legacy",
    "y_legacy",
    "description",
    "score_home",
    "score_away",
)


def build_shots(pbp: pl.DataFrame) -> pl.DataFrame:
    """Shot attempts derived from play-by-play.

    Derived rather than fetched: every field the shots dataset needs is already in
    the pbp capture, so this costs no request and cannot drift from the pbp it is
    built from. Selects only the shot-relevant columns, keeping whichever are
    present -- the v3 field set varies across seasons. ``shot_distance`` is the
    feed's, except on the threes the feed reports as 0 ft: those are restored from
    ``x_legacy``/``y_legacy`` (null when the three has no location).
    """
    if pbp.is_empty() or "is_field_goal" not in pbp.columns:
        return pl.DataFrame()
    shots = pbp.filter(pl.col("is_field_goal") == 1)
    keep = [c for c in _SHOT_COLUMNS if c in shots.columns]
    shots = shots.select(keep) if keep else shots
    if not {"shot_value", "shot_distance", "x_legacy", "y_legacy"} <= set(shots.columns):
        return shots
    # playbyplayv3 ships shotDistance 0 for every three under 23.5 ft -- a feed rule,
    # not the line: the same cutoff in every season 1997-2026, so it masks most WNBA
    # threes before the 2013 line move and the 22-ft corner and 22.15-ft arc since. Every other shot's shotDistance is exactly floor(sqrt(x^2 + y^2)/10
    # + 0.5) of the legacy coordinates (tenths of a foot, hoop at the origin), measured
    # on all 30 released seasons; stats.wnba.com shotchartdetail ships 22-23 ft for
    # the same 2025 shots. So restore those threes by the feed's own rule. A three at
    # legacy (0, 0) has no location: null, never an impossible 0 ft.
    x, y = pl.col("x_legacy").cast(pl.Float64), pl.col("y_legacy").cast(pl.Float64)
    masked = (pl.col("shot_value") == 3) & (pl.col("shot_distance") == 0)
    unlocated = x.is_null() | y.is_null() | ((x == 0) & (y == 0))
    feet = ((x**2 + y**2).sqrt() / 10 + 0.5).floor()
    return shots.with_columns(
        pl.when(masked & unlocated)
        .then(None)
        .when(masked)
        .then(feet)
        .otherwise(pl.col("shot_distance"))
        .cast(shots.schema["shot_distance"])
        .alias("shot_distance")
    )


#: What :func:`committed_shots` reads: the curve adapter's columns, with ``game_id``
#: standing in for ``season_type_id`` (derived below -- the WNBA shots carry none).
_CURVE_SHOT_COLUMNS = tuple(c for c in SHOT_ATTEMPT_COLUMNS if c != "season_type_id") + ("game_id",)


def committed_shots(
    base: str | Path, season: int, columns: tuple[str, ...] = _CURVE_SHOT_COLUMNS
) -> pl.DataFrame:
    """One season of the committed ``shots`` tree, projected to ``columns`` (default: the curve adapter's).

    Reads ``{base}/shots/parquet/shots_{season}.parquet`` -- the file the daily
    processor commits (calendar year in the name = ``season``). An absent season is
    an empty frame, which :func:`build_metric_curves` turns into the empty contract.
    """
    path = Path(base) / "shots" / "parquet" / f"shots_{season}.parquet"
    if not path.is_file():
        return pl.DataFrame()
    return pl.read_parquet(path, columns=list(columns))


def with_season_type_id(shots: pl.DataFrame) -> pl.DataFrame:
    """Stamp ``season_type_id`` from the game id's type digit (the WNBA shots carry none).

    A stats.wnba.com game id is league ``"10"``, the type digit, the season's last
    two digits and the game number: ``"1022500001"`` -> ``"2"`` regular season,
    ``"1042500111"`` -> ``"4"`` playoffs. The digit is ``game_id[2]``; ``game_id[3]``
    is the season's tens digit, ``"2"`` on every 2020s id, so a read one place over
    would count every game as regular season. Every committed season holds only
    ``"2"`` and ``"4"`` today.
    """
    if "season_type_id" in shots.columns:
        return shots
    return shots.with_columns(season_type_id=pl.col("game_id").cast(pl.Utf8).str.slice(2, 1))


def build_metric_curves(shots: pl.DataFrame) -> pl.DataFrame:
    """``metric_curves``: FG% by shot distance for the league, every team and every shooter.

    ``sportsdataverse.metric_curves`` over one season's ``shots`` (this run's
    :func:`build_shots` frame or :func:`committed_shots`). The adapter keeps
    regular-season and playoff attempts only (``season_type_id`` ``"2"`` / ``"4"``),
    bins by ``shot_distance`` (1-ft bins to 35 ft, then 35-50 and 50-95), and stamps
    ``id_source = "wnba_stats"`` with every id as text. Empty shots return the
    empty ``OUTPUT_SCHEMA`` frame.

    The WNBA shots carry no ``season_type_id`` column (the NBA twin stamps one), so
    it is derived here the way that twin derives it: the game id's type digit
    (``"1022500001"`` -> ``"2"`` regular season, ``"4"`` playoffs).
    """
    if shots.is_empty():
        return pl.DataFrame(schema=OUTPUT_SCHEMA)
    shots = with_season_type_id(shots)
    return metric_curves(shot_attempts(shots.select(SHOT_ATTEMPT_COLUMNS), league="wnba"), "wnba")


#: First season of the shots tree: a career baseline starts here.
FIRST_SHOTS_SEASON = 1997
#: ``sportsdataverse.rolling_windows.OUTPUT_SCHEMA`` plus the id namespace column.
ROLLING_WINDOWS_SCHEMA: dict[str, pl.DataType] = {**ROLLING_SCHEMA, "id_source": pl.Utf8}
#: What :func:`build_rolling_windows` reads from the shots: ``shot_events``' columns
#: minus ``season_type_id``, which :func:`with_season_type_id` derives.
_ROLLING_SHOT_COLUMNS = tuple(c for c in SHOT_COLUMNS if c != "season_type_id")


def game_dates(base: str | Path, season: int, schedule: pl.DataFrame | None = None) -> pl.DataFrame:
    """``game_id`` + ``game_date`` for every game the schedule master or ``season``'s schedule knows.

    The committed stage-99 master dates every earlier season, but it is unioned at
    the END of a run from the committed leaguegamelog schedules, so it lacks the
    games this run is building for the first time. Those come from ``schedule``
    (this run's stage-08 ``schedules`` frame), else the committed
    ``{base}/schedules/parquet/wnba_stats_schedule_{season}.parquet``. The two agree
    on all 7,005 games of 1997-2026 (measured 2026-10-01).
    """
    master = pl.read_parquet(
        Path(base) / "wnba_stats_schedule_master.parquet", columns=["game_id", "game_date"]
    )
    if schedule is None:
        path = Path(base) / "schedules" / "parquet" / f"wnba_stats_schedule_{season}.parquet"
        schedule = (
            pl.read_parquet(path, columns=["game_id", "game_date"]) if path.is_file() else None
        )
    frames = [master.select("game_id", pl.col("game_date").cast(pl.Date))]
    if schedule is not None and not schedule.is_empty():
        frames.append(
            schedule.select(
                pl.col("game_id").cast(pl.Utf8),
                pl.col("game_date").cast(pl.Utf8).str.slice(0, 10).str.to_date(),
            )
        )
    return pl.concat(frames).unique("game_id", keep="first", maintain_order=True)


def build_rolling_windows(
    base: str | Path,
    season: int,
    shots: pl.DataFrame | None = None,
    schedule: pl.DataFrame | None = None,
) -> pl.DataFrame:
    """``rolling_windows``: each shooter's last-N ``fga`` / ``fg3a`` form through ``season``.

    sdv-py's ``shot_events`` + ``rolling_windows`` over the season's shots (``shots``,
    this run's :func:`build_shots` frame, else the committed file) plus every
    committed season since 1997 before it, dated by :func:`game_dates`. History is
    read for the season's shooters only: ``rolling_windows`` keeps rows for entities
    with an event in ``season`` and ranks among them, so the rest of the league's
    history cannot change a row. Regular season + playoffs only (type digit via
    :func:`with_season_type_id`); ids are text with ``id_source = "wnba_stats"``;
    ``season`` is the calendar year, in and out.
    """
    current = shots if shots is not None else committed_shots(base, season, _ROLLING_SHOT_COLUMNS)
    if current.is_empty():
        return pl.DataFrame(schema=ROLLING_WINDOWS_SCHEMA)
    current = current.select(_ROLLING_SHOT_COLUMNS)
    paths = [
        Path(base) / "shots" / "parquet" / f"shots_{y}.parquet"
        for y in range(FIRST_SHOTS_SEASON, season)
    ]
    paths = [p for p in paths if p.is_file()]
    frames = [current]
    if paths:
        history = pl.scan_parquet(paths).select(_ROLLING_SHOT_COLUMNS)
        assert history.collect_schema()["person_id"] == current.schema["person_id"]
        active = current["person_id"].unique().implode()
        frames.insert(0, history.filter(pl.col("person_id").is_in(active)).collect())
    shots_all = with_season_type_id(pl.concat(frames, how="vertical_relaxed"))
    events = shot_events(shots_all, game_dates(base, season, schedule))
    return rolling_windows(events, season).with_columns(id_source=pl.lit("wnba_stats"))


# -- traditional boxscores -----------------------------------------------------
#
# boxscoretraditionalv3 nests: boxScoreTraditional.{homeTeam,awayTeam} each carry
# a players[] list whose rows hold their counting stats in a `statistics` object.
# Flattening lifts those onto the row so the published frame is one row per
# player-game rather than a struct column no R consumer could read.


def _flatten_stats(row: dict[str, Any]) -> dict[str, Any]:
    """Lift a nested ``statistics`` object onto its parent row."""
    out = {k: v for k, v in row.items() if k != "statistics"}
    out.update(row.get("statistics") or {})
    return out


def boxscore_rows(payload: Any, *, team_level: bool) -> list[dict[str, Any]]:
    """Player- or team-level rows from one ``boxscoretraditionalv3`` payload."""
    if not isinstance(payload, dict):
        return []
    box = payload.get("boxScoreTraditional") or {}
    rows: list[dict[str, Any]] = []
    for side in ("homeTeam", "awayTeam"):
        team = box.get(side) or {}
        if not isinstance(team, dict):
            continue
        common = {
            "team_id": team.get("teamId"),
            "team_name": team.get("teamName"),
            "team_tricode": team.get("teamTricode"),
            "side": "home" if side == "homeTeam" else "away",
        }
        if team_level:
            rows.append({**common, **_flatten_stats({"statistics": team.get("statistics") or {}})})
        else:
            for player in team.get("players") or []:
                if isinstance(player, dict):
                    rows.append({**common, **_flatten_stats(player)})
    return rows


def build_boxscores(
    root: str | Path, season: int, *, team_level: bool, game_ids: list[str] | None = None
) -> pl.DataFrame:
    """Season traditional boxscores, player- or team-level, bound across games."""
    if game_ids is None:
        game_ids = raw.season_game_ids(root, season) or raw.available_games(
            root, "boxscoretraditionalv3", season
        )
    frames: list[pl.DataFrame] = []
    for gid, payload in raw.iter_game_payloads(root, "boxscoretraditionalv3", game_ids):
        rows = boxscore_rows(payload, team_level=team_level)
        if not rows:
            continue
        df = pl.DataFrame(rows, infer_schema_length=None, strict=False)
        df = df.rename({c: snake(c) for c in df.columns})
        frames.append(df.with_columns(game_id=pl.lit(gid), season=pl.lit(season)))
    if not frames:
        return pl.DataFrame()
    return pl.concat(frames, how="diagonal_relaxed")
