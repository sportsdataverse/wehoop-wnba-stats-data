"""``python -m wnba_data_build.matchups_cli`` -- compile ``wnba_stats_matchups``.

WNBA sibling of hoopR-nba-stats-data's ``nba_data_build/matchups_cli.py``.

``leagueseasonmatchups`` is player-vs-player season totals: one row per (offensive
player, defensive player) pair, at ``{season}/{season_type}_{per_mode}.json`` in the
raw store (calendar-year seasons; the season is also the asset year). Assets keep the
NBA sibling's endpoint-prefixed names (``leagueseasonmatchups_regular-season_totals_2025``)
so one loader reads both leagues. The WNBA raw store has no ``matchupsrollup`` capture,
so this tag carries the pair table only.

**Playoffs are derived from ``boxscorematchupsv3``.** stats.wnba.com, like stats.nba.com,
serves no playoff rows for ``leagueseasonmatchups`` (measured 2026-11-20: 0 rows with
blank or per-team filters, HTTP 500 for any ``PORound``), so every ``playoffs_*`` payload
is an empty envelope. When one is, :func:`derived_matchups` sums the season's playoff
games (game id ``104…``) into the same columns. The same sum over the regular-season
``102…`` games reproduces the official regular-season pair table (2023-2026; numbers in
the PR that added this module). A real non-empty payload always wins.

Rows exist for 2023-2026 only: every earlier ``leagueseasonmatchups`` payload has an
empty ``rowSet`` and every earlier ``boxscorematchupsv3`` game has no players (measured
2026-11-20). Makes no network calls.

Example::

    python -m wnba_data_build.matchups_cli --root ../wehoop-wnba-stats-raw/wnba_stats/json
    python -m wnba_data_build.matchups_cli --root <raw> --seasons 2026 --publish
"""

from __future__ import annotations

import argparse
import json
import logging
import re
from pathlib import Path
from typing import Optional

import polars as pl
from sportsdataverse.nba import parse_nba_stats_result_sets

from . import raw as raw_store
from .io import write_release_formats
from .manifest import check_tags
from .publish import upload_artifacts

logger = logging.getLogger(__name__)

_REPO = "sportsdataverse/sportsdataverse-data"
_TAG = "wnba_stats_matchups"
_ENDPOINT = "leagueseasonmatchups"
FIRST_SEASON = 2023
LAST_SEASON = 2026

_STEM = re.compile(r"^(?P<season_type>regular-season|playoffs)_(?P<per_mode>pergame|totals)$")
#: game id ``10 2 25 00001``: the third digit is the season type
_TYPE_DIGIT = {"regular-season": "2", "playoffs": "4"}

#: season-table column <- per-game ``boxscorematchupsv3`` statistic.
#: ``matchupMinutesSort`` is seconds, despite the name.
_SUMS = {
    "partial_poss": "partialPossessions",
    "player_pts": "playerPoints",
    "team_pts": "teamPoints",
    "matchup_ast": "matchupAssists",
    "matchup_tov": "matchupTurnovers",
    "matchup_blk": "matchupBlocks",
    "matchup_fgm": "matchupFieldGoalsMade",
    "matchup_fga": "matchupFieldGoalsAttempted",
    "matchup_fg3_m": "matchupThreePointersMade",
    "matchup_fg3_a": "matchupThreePointersAttempted",
    "help_blk": "helpBlocks",
    "help_fgm": "helpFieldGoalsMade",
    "help_fga": "helpFieldGoalsAttempted",
    "matchup_ftm": "matchupFreeThrowsMade",
    "matchup_fta": "matchupFreeThrowsAttempted",
    "sfl": "shootingFouls",
    "matchup_time_sec": "matchupMinutesSort",
}
#: averaged by the pergame table; help_* stay totals there (and are 0 in both sources)
_PER_GAME = [c for c in _SUMS if not c.startswith("help_") and c != "matchup_time_sec"]
#: the official table rounds half-up (13/16 -> 0.813); polars' default is half-to-even
_HALF = "half_away_from_zero"


def _payload_frame(path: Path) -> pl.DataFrame:
    """One season payload -> a frame; EMPTY when absent, unreadable or row-less."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("raw_unreadable file=%s error=%s", path, str(exc)[:120])
        return pl.DataFrame()
    frame = parse_nba_stats_result_sets(payload)
    if isinstance(frame, dict):  # multi-set payload: take the first populated set
        frame = next((f for f in frame.values() if f.height), pl.DataFrame())
    return frame


def _stamp(frame: pl.DataFrame, season: int, stem: str) -> pl.DataFrame:
    """Add the columns the payload does not carry, read off the filename.

    Raises on an unknown stem rather than stamping a guess: the filename is the only
    record of which slice a payload is.
    """
    m = _STEM.match(stem)
    if m is None:
        raise ValueError(f"unparseable season_type/per_mode stem: {stem!r}")
    return frame.with_columns(
        season=pl.lit(season, dtype=pl.Int64),
        season_type=pl.lit(m["season_type"]),
        per_mode=pl.lit(m["per_mode"]),
    )


def game_matchups(root: Path, season: int, season_type: str) -> pl.DataFrame:
    """One row per (game, offensive player, defender) from the season's
    ``boxscorematchupsv3`` games of ``season_type``; empty when none carry players."""
    digit = _TYPE_DIGIT[season_type]
    rows = []
    for gid in raw_store.available_games(root, "boxscorematchupsv3", season):
        if gid[2:3] != digit:
            continue
        box = (raw_store.read_game(root, "boxscorematchupsv3", gid) or {}).get("boxScoreMatchups")
        for side in ("homeTeam", "awayTeam"):
            team = (box or {}).get(side) or {}
            for off in team.get("players") or []:
                for d in off.get("matchups") or []:
                    stats = d.get("statistics")
                    if not isinstance(stats, dict):
                        continue  # a stats-less pair would read as a real zero
                    rows.append(
                        {
                            "game_id": gid,
                            "off_player_id": off.get("personId"),
                            "off_player_name": f"{off.get('firstName')} {off.get('familyName')}",
                            "def_player_id": d.get("personId"),
                            "def_player_name": f"{d.get('firstName')} {d.get('familyName')}",
                            **{k: stats.get(v) for k, v in _SUMS.items()},
                        }
                    )
    return pl.DataFrame(rows, infer_schema_length=None) if rows else pl.DataFrame()


def _pct(made: str, att: str) -> pl.Expr:
    return (
        pl.when(pl.col(att) > 0)
        .then((pl.col(made) / pl.col(att)).round(3, mode=_HALF))
        .otherwise(0.0)
    )


def derived_matchups(
    root: Path, season: int, season_type: str = "playoffs"
) -> dict[str, pl.DataFrame]:
    """``{f"{season_type}_totals": ..., f"{season_type}_pergame": ...}`` summed per game.

    Empty dict when no game of that type carries matchups. Columns and dtypes follow
    the season's regular-season payloads, so the two concatenate.
    """
    per_game = game_matchups(root, season, season_type)
    if not per_game.height:
        return {}
    t = per_game.group_by("off_player_id", "def_player_id").agg(
        pl.col("off_player_name", "def_player_name").first(),
        gp=pl.col("game_id").n_unique().cast(pl.Int64),
        **{k: pl.col(k).sum() for k in _SUMS},
    )
    sec = pl.col("matchup_time_sec").round(0, mode=_HALF).cast(pl.Int64)
    totals = t.select(
        season_id=pl.lit(f"{_TYPE_DIGIT[season_type]}{season}"),
        off_player_id="off_player_id",
        off_player_name="off_player_name",
        def_player_id="def_player_id",
        def_player_name="def_player_name",
        gp="gp",
        matchup_min=pl.format("{}:{}", sec // 60, (sec % 60).cast(pl.String).str.zfill(2)),
        partial_poss=pl.col("partial_poss").round(1, mode=_HALF),
        player_pts="player_pts",
        team_pts="team_pts",
        matchup_ast="matchup_ast",
        matchup_tov="matchup_tov",
        matchup_blk="matchup_blk",
        matchup_fgm="matchup_fgm",
        matchup_fga="matchup_fga",
        matchup_fg_pct=_pct("matchup_fgm", "matchup_fga"),
        matchup_fg3_m="matchup_fg3_m",
        matchup_fg3_a="matchup_fg3_a",
        matchup_fg3_pct=_pct("matchup_fg3_m", "matchup_fg3_a"),
        help_blk="help_blk",
        help_fgm="help_fgm",
        help_fga="help_fga",
        help_fg_perc=_pct("help_fgm", "help_fga"),
        matchup_ftm="matchup_ftm",
        matchup_fta="matchup_fta",
        sfl="sfl",
        matchup_time_sec=pl.col("matchup_time_sec").round(1, mode=_HALF),
    ).sort("off_player_id", "def_player_id")
    gp = pl.col("gp")
    pergame = totals.with_columns(
        matchup_min=(pl.col("matchup_time_sec") / 60 / gp).round(1, mode=_HALF),
        **{c: (pl.col(c) / gp).round(1, mode=_HALF) for c in _PER_GAME},
    ).drop("matchup_time_sec")
    frames = {f"{season_type}_totals": totals, f"{season_type}_pergame": pergame}
    for stem, frame in frames.items():
        reg_stem = stem.replace(season_type, "regular-season")
        reg = _payload_frame(root / _ENDPOINT / str(season) / f"{reg_stem}.json")
        if reg.height:  # ponytail: help_fg_perc is Int64 there only because it is always 0
            frames[stem] = frame.select(reg.columns).cast(dict(reg.schema))
    return frames


def _clear(out: Path, seasons: list[int]) -> None:
    """Drop this tag's files for ``seasons`` before rebuilding them.

    Publishing uploads whatever the directory holds for the requested seasons, so a
    file an EARLIER run left -- for a payload that is empty now -- would ride along and
    defeat the empty-asset guard by the back door.
    """
    d = out / _TAG
    for season in seasons:
        for f in d.glob(f"*_{season}.*") if d.is_dir() else []:
            f.unlink()


def build(seasons: list[int], out: Path, *, root: Path) -> dict[str, int]:
    """Compile ``leagueseasonmatchups`` into ``out/wnba_stats_matchups/``.

    An empty payload never writes an asset (a schema-only file would advertise
    coverage the tag does not have); an empty or missing ``playoffs_*`` payload is
    derived from the season's playoff games instead.
    """
    _clear(out, seasons)
    written: dict[str, int] = {}

    def write(stem: str, season: int, frame: pl.DataFrame, source: str) -> None:
        name = f"{_ENDPOINT}_{stem}"
        write_release_formats(_stamp(frame, season, stem), out / _TAG, f"{name}_{season}")
        written[f"{_TAG}/{name}"] = written.get(f"{_TAG}/{name}", 0) + frame.height
        logger.info(
            "write asset=%s season=%s rows=%s source=%s", name, season, frame.height, source
        )

    for season in seasons:
        missing = []
        for season_type in _TYPE_DIGIT:
            for per_mode in ("totals", "pergame"):
                stem = f"{season_type}_{per_mode}"
                frame = _payload_frame(root / _ENDPOINT / str(season) / f"{stem}.json")
                if frame.height:
                    write(stem, season, frame, _ENDPOINT)
                elif season_type == "playoffs":
                    missing.append(stem)
                else:
                    logger.info(
                        "raw_empty endpoint=%s season=%s variant=%s", _ENDPOINT, season, stem
                    )
        if missing:
            derived = derived_matchups(root, season)
            for stem in missing:
                if stem in derived:
                    write(stem, season, derived[stem], "boxscorematchupsv3")
    return written


def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="wnba_data_build.matchups_cli")
    ap.add_argument(
        "--seasons",
        type=int,
        nargs="+",
        default=list(range(FIRST_SEASON, LAST_SEASON + 1)),
        help=f"calendar-year seasons (default {FIRST_SEASON}-{LAST_SEASON}, the ones with rows)",
    )
    ap.add_argument(
        "--root",
        default="wnba_stats/json",
        help="LOCAL raw-store json base (the dir holding {endpoint}/{season}/); playoff "
        "derivation lists game files, which a URL root cannot",
    )
    ap.add_argument("--out", default="build_out/matchups", help="output directory")
    ap.add_argument("--repo", default=_REPO, help="release repo")
    ap.add_argument("--publish", action="store_true", help="upload the tag dir to its release")
    ap.add_argument("--dry-run", action="store_true", help="plan publish without uploading")
    return ap


def main(argv: Optional[list[str]] = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = _parser().parse_args(argv)
    out = Path(args.out)
    written = build(args.seasons, out, root=Path(args.root))
    for key, rows in sorted(written.items()):
        print(f"{key}: {rows} rows")
    if not written:
        print("nothing built -- no season produced rows; not publishing")
        return 0
    if args.publish or args.dry_run:
        result = upload_artifacts(
            out / _TAG, _TAG, args.repo, seasons=args.seasons, dry_run=args.dry_run
        )
        if result["failed"]:
            print(f"WARNING: {len(result['failed'])} file(s) failed to publish: {result['failed']}")
            return 1
        # Season assets do not carry the manifest with them -- see manifest.py.
        if args.publish and not args.dry_run:
            if problems := check_tags([_TAG], args.repo):
                for msg in problems:
                    print(f"MANIFEST DRIFT: {msg}")
                print(
                    "assets uploaded, but the manifest is now stale. Refresh it with: "
                    f"python -m wnba_data_build.manifest build --tags {_TAG} --publish"
                )
                return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
