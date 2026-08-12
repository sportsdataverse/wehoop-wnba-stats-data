"""Program V (design §9, D28) v3 backfill: D26b-named season parquets into staging.

WNBA mirror of ``hoopR-nba-stats-data``'s ``nba_data_build.v3_backfill``. Builds the
four v3 families -- ``schedule`` / ``play_by_play`` / ``possessions`` / ``lineups`` --
for a range of seasons entirely from the committed ``wehoop-wnba-stats-raw`` store
(no network; the sdv-py engine is pinned read-only on the store by
:mod:`.from_raw`). Output goes to a **staging** directory (default
``{repo}/v3_staging``, gitignored) with the D26b cutover names::

    wnba_schedule_2010.parquet       # WNBA seasons are bare years
    wnba_play_by_play_2010.parquet
    wnba_possessions_2010.parquet
    wnba_lineups_2010.parquet

The committed tree is untouched until the section-9.3 gate (:mod:`.v3_gate`)
passes; the cutover move + tag swap (D26d) is a separate operator decision.

Resumability is two-level: a per-game frame cache (``{repo}/.wnba_pipeline_cache``)
and a season whose four staged parquets exist is skipped unless ``--rebuild``.
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Union

import polars as pl

from . import raw
from .from_raw import ProcessedGame, process_game

FAMILIES = ("schedule", "play_by_play", "possessions", "lineups")

#: ProcessedGame field backing each non-schedule family.
_FRAME_OF = {
    "play_by_play": "enhanced_pbp",
    "possessions": "possessions",
    "lineups": "on_court",
}

_FRAME_NAMES = tuple(_FRAME_OF.values())

_GAMELOG_VARIANTS = ("regular-season", "playoffs")

_PLAYER_SLOT_RE = re.compile(r"^(?:off|def|home|away)_player_[1-5]$")


def _log(msg: str) -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[{stamp}] {msg}", flush=True)


def repo_root_default() -> Path:
    """Repo root inferred from this file (…/python/wnba_data_build/v3_backfill.py)."""
    return Path(__file__).resolve().parents[2]


def season_paths(staging: Union[str, Path], season: int) -> dict[str, Path]:
    """D26b staged parquet path per family for one (bare-year) season."""
    staging = Path(staging)
    return {fam: staging / f"wnba_{fam}_{season}.parquet" for fam in FAMILIES}


def season_done(staging: Union[str, Path], season: int) -> bool:
    """True when all four staged parquets exist (the resume checkpoint)."""
    return all(p.exists() for p in season_paths(staging, season).values())


_SCHEDULE_SCHEMA: dict[str, type[pl.DataType]] = {
    "game_id": pl.Utf8,
    "season": pl.Int64,
    "season_type": pl.Utf8,
    "game_date": pl.Utf8,
    "matchup": pl.Utf8,
    "home_team_id": pl.Int64,
    "home_team_abbreviation": pl.Utf8,
    "home_team_name": pl.Utf8,
    "home_pts": pl.Int64,
    "home_wl": pl.Utf8,
    "away_team_id": pl.Int64,
    "away_team_abbreviation": pl.Utf8,
    "away_team_name": pl.Utf8,
    "away_pts": pl.Int64,
    "away_wl": pl.Utf8,
}


def schedule_from_gamelog(raw_root: Union[str, Path], season: int) -> pl.DataFrame:
    """Game-level schedule pivoted from the raw ``leaguegamelog`` team rows.

    One row per game; the home side is the team whose MATCHUP contains ``vs.``.
    Utf8 zero-filled ``game_id``. Empty frame with the documented schema when
    nothing was captured.
    """
    games: dict[str, dict[str, Any]] = {}
    for variant in _GAMELOG_VARIANTS:
        payload = raw.read_season(raw_root, "leaguegamelog", season, variant)
        if not isinstance(payload, dict):
            continue
        for rs in payload.get("resultSets") or []:
            headers = [str(h).upper() for h in rs.get("headers") or []]
            if "GAME_ID" not in headers:
                continue
            idx = {h: i for i, h in enumerate(headers)}

            def col(row: list[Any], name: str) -> Any:
                i = idx.get(name)
                return row[i] if i is not None and i < len(row) else None

            for row in rs.get("rowSet") or []:
                gid_raw = col(row, "GAME_ID")
                if gid_raw is None:
                    continue
                gid = str(gid_raw).zfill(10)
                rec = games.setdefault(
                    gid,
                    {
                        "game_id": gid,
                        "season": season,
                        "season_type": variant,
                        "game_date": None,
                        "matchup": None,
                    },
                )
                matchup = str(col(row, "MATCHUP") or "")
                side = "home" if " vs. " in matchup else "away"
                rec["game_date"] = rec["game_date"] or col(row, "GAME_DATE")
                if side == "home":
                    rec["matchup"] = matchup or rec["matchup"]
                pts = col(row, "PTS")
                rec[f"{side}_team_id"] = col(row, "TEAM_ID")
                rec[f"{side}_team_abbreviation"] = col(row, "TEAM_ABBREVIATION")
                rec[f"{side}_team_name"] = col(row, "TEAM_NAME")
                rec[f"{side}_pts"] = int(pts) if pts is not None else None
                rec[f"{side}_wl"] = col(row, "WL")
            break
    rows_out = [
        {k: g.get(k) for k in _SCHEDULE_SCHEMA}
        for g in sorted(games.values(), key=lambda g: str(g["game_id"]))
    ]
    return pl.DataFrame(rows_out, schema=_SCHEDULE_SCHEMA)


def _coerce_id_dtypes(df: pl.DataFrame) -> pl.DataFrame:
    """Pin join-key dtypes after a ``diagonal_relaxed`` concat.

    ``game_id`` -> Utf8; other ``*_id`` columns and on-court player-slot
    columns -> Int64 (mirrors the NBA repo's rollup).
    """
    exprs = []
    for name, dtype in df.schema.items():
        if name == "game_id":
            exprs.append(pl.col(name).cast(pl.Utf8))
        elif (name.endswith("_id") or _PLAYER_SLOT_RE.match(name)) and dtype != pl.Utf8:
            exprs.append(pl.col(name).cast(pl.Int64))
    return df.with_columns(exprs) if exprs else df


def _cache_paths(cache_root: Union[str, Path], season: int, game_id: str) -> dict[str, Path]:
    d = Path(cache_root) / f"games_{season}"
    return {name: d / f"{game_id}_{name}.parquet" for name in _FRAME_NAMES}


def _read_game_cache(
    cache_root: Union[str, Path], season: int, game_id: str
) -> Optional[ProcessedGame]:
    paths = _cache_paths(cache_root, season, game_id)
    if not all(p.exists() for p in paths.values()):
        return None
    return ProcessedGame(
        game_id=str(game_id).zfill(10),
        enhanced_pbp=pl.read_parquet(paths["enhanced_pbp"]),
        on_court=pl.read_parquet(paths["on_court"]),
        possessions=pl.read_parquet(paths["possessions"]),
    )


def _write_game_cache(cache_root: Union[str, Path], season: int, pg: ProcessedGame) -> None:
    paths = _cache_paths(cache_root, season, pg.game_id)
    for name, path in paths.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        getattr(pg, name).write_parquet(path)


def build_season(
    raw_root: Union[str, Path],
    season: int,
    staging: Union[str, Path],
    cache_root: Union[str, Path],
    *,
    rebuild: bool = False,
) -> dict[str, Any]:
    """Build one season's four staged parquets from the raw store.

    Skips entirely (``status="skipped"``) when the four parquets already exist
    and ``rebuild`` is False. A game the engine cannot ground costs that game,
    not the season (mirrors :func:`.from_raw.process_game`).
    """
    if not rebuild and season_done(staging, season):
        return {"season": season, "status": "skipped"}

    t0 = time.time()
    sched = schedule_from_gamelog(raw_root, season)
    game_ids = sched["game_id"].to_list()

    captured = set(raw.available_games(raw_root, "playbyplayv3", season))
    processed: list[ProcessedGame] = []
    uncaptured: list[str] = []
    failed: list[str] = []
    for n, gid in enumerate(game_ids, 1):
        if gid not in captured:
            uncaptured.append(gid)
            continue
        pg = _read_game_cache(cache_root, season, gid)
        if pg is None:
            got = process_game(raw_root, gid)
            if got is None:
                failed.append(gid)
                _log(f"  season {season} game {gid} FAILED (engine returned no pbp)")
                continue
            # Stamp identity onto every frame before caching (process_season parity).
            pg = ProcessedGame(
                game_id=got.game_id,
                enhanced_pbp=got.enhanced_pbp.with_columns(
                    game_id=pl.lit(got.game_id), season=pl.lit(season, dtype=pl.Int64)
                ),
                on_court=got.on_court.with_columns(
                    game_id=pl.lit(got.game_id), season=pl.lit(season, dtype=pl.Int64)
                ),
                possessions=got.possessions.with_columns(
                    game_id=pl.lit(got.game_id), season=pl.lit(season, dtype=pl.Int64)
                ),
            )
            _write_game_cache(cache_root, season, pg)
        processed.append(pg)
        if n % 50 == 0:
            _log(f"  season {season}: {n}/{len(game_ids)} games ({len(failed)} failed)")

    paths = season_paths(staging, season)
    Path(staging).mkdir(parents=True, exist_ok=True)
    rows: dict[str, int] = {}

    sched.write_parquet(paths["schedule"])
    rows["schedule"] = sched.height

    for fam, attr in _FRAME_OF.items():
        frames = [getattr(pg, attr) for pg in processed]
        frames = [f for f in frames if isinstance(f, pl.DataFrame) and not f.is_empty()]
        if frames:
            df = pl.concat(frames, how="diagonal_relaxed")
            df = _coerce_id_dtypes(df)
        else:
            df = pl.DataFrame({"game_id": pl.Series([], dtype=pl.Utf8)})
        df.write_parquet(paths[fam])
        rows[fam] = df.height

    # on_court reconstruction needs a `gamerotation` capture, which is sparse in
    # the raw store for older seasons (2010: 27 of 220 games). Report it per
    # season so a near-empty `lineups` family reads as the upstream capture gap
    # it is, rather than looking like a silent compile failure.
    games_with_lineups = sum(
        1
        for pg in processed
        if isinstance(pg.on_court, pl.DataFrame) and not pg.on_court.is_empty()
    )

    return {
        "season": season,
        "status": "built",
        "games_indexed": len(game_ids),
        "games_uncaptured": len(uncaptured),
        "games_failed": len(failed),
        "games_processed": len(processed),
        "games_with_lineups": games_with_lineups,
        "rows": rows,
        "secs": round(time.time() - t0, 1),
    }


def main(argv: Optional[list[str]] = None) -> int:
    """CLI: ``python -m wnba_data_build.v3_backfill -s 1997 -e 2026``."""
    ap = argparse.ArgumentParser(
        prog="wnba_data_build.v3_backfill",
        description="Program V v3 backfill (D26/D26b/D28): raw store -> staged season parquets.",
    )
    ap.add_argument("-s", "--start-season", type=int, default=1997, help="first season (bare year)")
    ap.add_argument("-e", "--end-season", type=int, default=2026, help="last season (bare year)")
    ap.add_argument(
        "--raw-root",
        default=None,
        help="wehoop-wnba-stats-raw json root (default: sibling checkout wnba_stats/json)",
    )
    ap.add_argument("--staging", default=None, help="staging dir (default: {repo}/v3_staging)")
    ap.add_argument(
        "--cache-dir", default=None, help="per-game cache (default: {repo}/.wnba_pipeline_cache)"
    )
    ap.add_argument(
        "--rebuild", action="store_true", help="rebuild seasons whose staged parquets exist"
    )
    args = ap.parse_args(argv)

    repo = repo_root_default()
    raw_root = (
        Path(args.raw_root)
        if args.raw_root
        else repo.parent / "wehoop-wnba-stats-raw" / "wnba_stats" / "json"
    )
    staging = Path(args.staging) if args.staging else repo / "v3_staging"
    cache_root = Path(args.cache_dir) if args.cache_dir else repo / ".wnba_pipeline_cache"

    if not Path(raw_root).is_dir():
        _log(f"raw store not found at {raw_root} -- pass --raw-root")
        return 2

    _log(
        f"v3 backfill seasons {args.start_season}-{args.end_season} "
        f"raw={raw_root} staging={staging} cache={cache_root}"
    )
    failures = 0
    for season in range(args.start_season, args.end_season + 1):
        try:
            summary = build_season(raw_root, season, staging, cache_root, rebuild=args.rebuild)
        except Exception as exc:  # noqa: BLE001 - keep the range going, report at exit
            failures += 1
            _log(f"season {season} ERROR: {type(exc).__name__}: {exc}")
            continue
        _log(f"season {season}: {summary}")
    _log(f"done ({failures} season-level failures)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
