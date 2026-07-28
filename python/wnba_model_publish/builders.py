"""Build the consolidated per-season WNBA player-impact table.

One ``wnba_player_impact_{season}.parquet`` per season, one row per
player-season-season_type (Regular Season + Playoffs), joining the sdv-py
model-zoo outputs on ``player_id``. The model suite is the league-agnostic
``sportsdataverse.nba`` zoo — the same RAPM / adj-RAPM / SPM / BPM / WAR /
DARKO engines behind ``nba_player_impact`` — fed WNBA possessions
(``nba_possessions(game_id, league_id="10")``) and WNBA box logs
(``nba_box_logs(..., league_id="10")`` through the ``wnba_stats_*`` wrappers):

* RAPM (``nba_rapm``) — the anchor population: every player with possession
  lineup data that season.
* adj-RAPM (``nba_adj_rapm``) — cross-season prior = the possession-weighted
  **blend of the previous season's Regular Season + Playoffs SPM**
  (``_blend_by_poss`` over ``AdjRapmModel.from_spm``), threaded
  earliest-to-latest; the first season of an invocation gets an empty prior.
  Within a season, the Playoffs pass instead takes **that same season's
  Regular Season SPM** as its prior -- the anchor that makes a short
  playoff sample usable at all.
* SPM (``train_spm`` + ``nba_spm``) — coefficients are fitted **once per
  season, on the Regular Season** box features + RAPM target, and reused for
  the Playoffs pass (re-fitting on a short playoff sample would train
  noise on noise); a season's Regular Season output never depends on which
  other seasons the invocation happened to include.
* BPM 2.0 (``nba_bpm``) — box logs + listed positions.
* WAR (``nba_war``) — ``pts_per_win`` calibrated per season from the team game
  logs (OLS wins ~ total margin); ``replacement_level`` defaults to ``-2.0``
  per 100 (the basketball-reference VORP convention) because the module
  intentionally ships no invented default.
* DARKO (``nba_darko``) — Kalman forecast off the multi-season RAPM panel
  accumulated **within this invocation**; seasons before the panel has two
  distinct seasons carry null ``darko_*`` columns.

Season-year convention: WNBA seasons are SINGLE CALENDAR YEARS (2024 is just
2024) — there is no start/end-year split anywhere in this module, unlike the
NBA sibling. The raw store's per-game AND season-level halves are both filed
under the calendar year.

Fidelity note for single-season runs (the nightly cron): pass a few trailing
seasons (e.g. ``--seasons 2021:2025``) — the per-game possession cache makes
prior seasons cheap, and they give adj-RAPM a real prior and DARKO a real
panel. Re-uploading trailing seasons is safe (``--clobber``).

Live access notes: stats.wnba.com behaves like stats.nba.com (hangs on
datacenter/cloud IPs). With ``raw_store_dir`` pointing at a committed
``wehoop-wnba-stats-raw/wnba_stats/json`` tree the build is offline except
for the player-variant leaguegamelog call (the WNBA store does not yet carry
``{season_type}_p.json`` captures), which needs a residential IP or proxy.
"""

from __future__ import annotations

import datetime as _dt
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Callable, Optional, Sequence

import polars as pl
from sportsdataverse.nba import (
    AdjRapmModel,
    box_features,
    calibrate_pts_per_win,
    nba_adj_rapm,
    nba_bpm,
    nba_box_logs,
    nba_darko,
    nba_player_ages,
    nba_player_identity,
    nba_player_positions,
    nba_raw_store_season_frame,
    nba_spm,
    nba_war,
    train_spm,
)

# nba_rapm is NOT re-exported from the sportsdataverse.nba package (verified on
# main) — it lives in the nba_rapm submodule.
from sportsdataverse.nba.nba_possessions import nba_possessions
from sportsdataverse.nba.nba_rapm import nba_rapm
from sportsdataverse.nba.nba_season_compile import (
    PIPELINE_VERSION,
    _game_cache_key,
    _index_select,
)
from sportsdataverse.wnba.wnba_stats import (
    wnba_stats_leaguedashplayerbiostats,
    wnba_stats_leaguegamelog,
    wnba_stats_playerindex,
)

_LOG = logging.getLogger(__name__)

_WNBA_LEAGUE_ID = "10"

#: Zero-arg callable yielding a proxy URL (``RoundRobin.next`` matches this).
ProxyProvider = Callable[[], Optional[str]]

#: basketball-reference VORP replacement level, points per 100 possessions
#: relative to league average. ``nba_war`` requires an explicit value.
DEFAULT_REPLACEMENT_LEVEL = -2.0

_DARKO_COLS = ["darko_filtered_skill", "darko_projected_rating", "darko_projected_sd"]


def _season_str(year: int) -> str:
    """WNBA season year -> stats.wnba.com season string (2024 -> ``"2024"``).

    The WNBA plays within one calendar year, so unlike the NBA there is no
    ``"2023-24"`` form — the API label IS the year.
    """
    return str(year)


def _default_cache_dir() -> Path:
    root = os.environ.get("SDV_PY_WNBA_CACHE_DIR") or str(Path.home() / ".sdv_py_wnba_cache")
    return Path(root) / "possessions"


def _compile_wnba_season(
    season: int,
    season_type: str,
    *,
    lineup_source: str = "auto",
    cache_dir: Optional[str] = None,
    delay_s: float = 0.6,
    proxy_provider: Optional[ProxyProvider] = None,
    raw_store_dir: Optional[str] = None,
) -> pl.DataFrame:
    """Compile a WNBA season's possession stint matrix (cached + resumable).

    WNBA sibling of ``sportsdataverse.nba.compile_nba_season``: discovers game
    ids from the committed ``leaguegamelog/{season}/{variant}.json`` capture
    (calendar-year dir — the WNBA store has no start/end-year split) or the
    live ``wnba_stats_leaguegamelog``, then per game loads the cached parquet
    or builds possessions via the league-agnostic
    ``nba_possessions(game_id, "10", lineup_source=...)`` core, which serves
    every per-game payload from *raw_store_dir* when set (read-only, the
    ``-raw`` sweep stays the only writer).

    Args:
        season: WNBA season calendar year (e.g. ``2024``).
        season_type: ``"Regular Season"`` or ``"Playoffs"``.
        lineup_source: On-court lineup producer (``"auto"`` tries rotation then
            falls back to pbp-derived — the fallback is what makes pre-rotation
            era seasons compilable at all).
        cache_dir: Per-game parquet cache root; defaults to
            ``$SDV_PY_WNBA_CACHE_DIR`` or ``~/.sdv_py_wnba_cache/possessions``.
        delay_s: Sleep after each LIVE per-game fetch (cached games don't sleep).
        proxy_provider: Zero-arg proxy-URL callable, drawn per call.
        raw_store_dir: Committed WNBA raw store root (local
            ``wnba_stats/json`` checkout or ``http(s)://`` base); ``None``
            leaves the per-game path on its env-var defaults.

    Returns:
        Season possession frame (+ ``season`` and ``game_date`` columns).
        Empty typed frame when the season/type has no games.

    Raises:
        ValueError: if a compiled game is missing from the season game index
            (a null ``game_date`` would silently poison downstream joins).
    """
    cdir = Path(cache_dir) if cache_dir else _default_cache_dir()
    cdir.mkdir(parents=True, exist_ok=True)

    index: Optional[pl.DataFrame] = None
    if raw_store_dir:
        parsed = nba_raw_store_season_frame(
            "leaguegamelog",
            season,  # calendar year — the WNBA sweep files under the API year
            _slug(season_type),
            raw_store_dir=raw_store_dir,
        )
        if parsed is not None and "game_id" in parsed.columns:
            idx = _index_select(parsed)
            index = idx if not idx.is_empty() else None
    if index is None:
        log = wnba_stats_leaguegamelog(
            season=_season_str(season),
            season_type_all_star=season_type,
            league_id=_WNBA_LEAGUE_ID,
            proxy_url=proxy_provider() if proxy_provider is not None else None,
        )
        index = _index_select(log)

    game_ids = list(dict.fromkeys(index["game_id"].to_list()))
    frames: list[pl.DataFrame] = []
    total = len(game_ids)

    for i, gid in enumerate(game_ids, 1):
        cache_path = cdir / _game_cache_key(gid)
        if cache_path.exists():
            try:
                frames.append(pl.read_parquet(cache_path))
                continue
            except Exception as exc:  # corrupt cache -> fall through to re-fetch
                _LOG.warning("re-fetch %s: bad cache (%s)", gid, exc)
        # gamerotation captures are PARTIAL in the WNBA store (every season has
        # gaps), and lineup_source="auto" fires a live rotation fetch per
        # missing game -- ~13s each, hours over a backfill. When the store is a
        # local dir, gate on the capture's existence: rotation-derived lineups
        # where captured, pbp-derived otherwise, and never a live rotation call.
        eff_lineup = lineup_source
        if (
            raw_store_dir
            and lineup_source == "auto"
            and not str(raw_store_dir).startswith("http")
            and not (Path(raw_store_dir) / "gamerotation" / str(season) / f"{gid}.json").exists()
        ):
            eff_lineup = "pbp"
        try:
            poss = nba_possessions(
                gid,
                _WNBA_LEAGUE_ID,
                lineup_source=eff_lineup,
                proxy_url=proxy_provider() if proxy_provider is not None else None,
                raw_store_dir=raw_store_dir,
                # Pure consumer: the -raw repo's own sweep is the only writer.
                raw_store_readonly=True if raw_store_dir else None,
            )
        except Exception as exc:
            _LOG.warning("skip game %s (%d/%d): fetch failed: %s", gid, i, total, exc)
            continue
        if delay_s and not raw_store_dir:
            time.sleep(delay_s)
        if poss.is_empty():
            _LOG.info("skip game %s (%d/%d): no possessions", gid, i, total)
            continue
        poss.write_parquet(cache_path)
        frames.append(poss)
        _LOG.info("compiled %s (%d/%d)", gid, i, total)

    if frames:
        out = pl.concat(frames, how="diagonal_relaxed").join(index, on="game_id", how="left")
        n_missing = int(out["game_date"].null_count())
        if n_missing:
            raise ValueError(f"game_date join failed for {n_missing} possessions — season game index incomplete")
        return out.with_columns(pl.lit(season).alias("season"))
    return pl.DataFrame(schema={"game_id": pl.Utf8, "game_date": pl.Date, "season": pl.Int64})


def _join_on_player(base: pl.DataFrame, right: pl.DataFrame, name: str) -> pl.DataFrame:
    """Left-join *right* onto *base* on ``player_id`` with the guard rails.

    Asserts join-key dtype agreement (everything in the zoo emits
    ``player_id: Int64``), key uniqueness on the right side, and that the join
    did not change the base height (a duplicate-key explosion or key-dtype
    mismatch would).
    """
    assert right.schema["player_id"] == pl.Int64, f"{name}: player_id dtype {right.schema['player_id']} != Int64"
    assert base.schema["player_id"] == right.schema["player_id"], f"{name}: join-key dtype mismatch"
    assert right["player_id"].n_unique() == right.height, f"{name}: duplicate player_id rows"
    joined = base.join(right, on="player_id", how="left")
    assert joined.height == base.height, f"{name}: join changed height {base.height} -> {joined.height}"
    return joined


def _repair_team_logs(team: pl.DataFrame, player: pl.DataFrame) -> pl.DataFrame:
    """Repair early-era stats.wnba.com team game logs from the player logs.

    Two team-log columns are garbage before ~2005 and poison BPM (which applies
    fixed published coefficients to per-100 features):

    * ``min`` — the per-team-game minutes column reads 8.0 (2000), 0.9 (2002),
      or a string (1997/2003). ``box_features`` divides by ``team_min / 5``, so
      per-100 rates exploded ~25x (2000) or zeroed out (2003). Team minutes are
      BY DEFINITION the sum of that team's player minutes, and the player logs
      are pristine in every era (sums = 200 + 25/OT), so the sum replaces the
      column outright — identical where the column was already right.
    * ``tov`` — near-zero before 2001 (real team TOV is ~13-17). A team's TOV
      includes team-attributed turnovers (shot-clock, 8-second) that player
      rows legitimately lack, so where the column is sane it is >= the player
      sum: ``max(column, player_sum)`` keeps the sane column and replaces the
      garbage zeros.
    """
    if team.is_empty() or player.is_empty():
        return team
    sums = player.group_by("game_id", "team_id").agg(
        pl.col("min").cast(pl.Float64, strict=False).sum().alias("_min_sum"),
        pl.col("tov").cast(pl.Float64, strict=False).sum().alias("_tov_sum"),
    )
    return (
        team.join(sums, on=["game_id", "team_id"], how="left")
        .with_columns(
            pl.col("_min_sum").fill_null(0.0).alias("min"),
            pl.max_horizontal(
                pl.col("tov").cast(pl.Float64, strict=False).fill_null(0.0),
                pl.col("_tov_sum").fill_null(0.0),
            ).alias("tov"),
        )
        .drop("_min_sum", "_tov_sum")
    )


def _team_season(team_logs: pl.DataFrame) -> pl.DataFrame:
    """Team game logs -> one row per team-season (``team_id, wins, total_margin``).

    WNBA games have no ties, so ``plus_minus > 0`` is a win.
    """
    return team_logs.group_by("team_id").agg(
        (pl.col("plus_minus") > 0).sum().alias("wins"),
        pl.col("plus_minus").sum().alias("total_margin"),
    )


def _blend_by_poss(
    rs: pl.DataFrame,
    po: Optional[pl.DataFrame],
    value_cols: list[str],
    weight_col: str,
) -> pl.DataFrame:
    """Possession-weighted combination of a regular-season and playoff frame.

    The ONE forward-carrying rule: both the next season's adj-RAPM prior and the
    DARKO panel row use this. A WNBA playoff sample is a handful of games, so a
    straight "most recent estimate wins" carry would let a thin sample override
    a full-season one -- adding playoffs would then DEGRADE every
    regular-season row. Weighting by possessions keeps the full RS sample
    behind the carried value while still letting playoff form move it.

    A player in only one frame keeps that frame's values (not null, not halved).

    Args:
        rs: Regular-season frame; one row per ``player_id``.
        po: Playoff frame, or None/empty -- either returns *rs* untouched.
        value_cols: Columns to weight-average.
        weight_col: Possession-count column; summed in the output.

    Returns:
        One row per ``player_id`` with blended *value_cols* and summed *weight_col*.
    """
    if po is None or po.height == 0:
        return rs

    joined = rs.join(po, on="player_id", how="full", coalesce=True, suffix="_po")
    w_rs = pl.col(weight_col).fill_null(0)
    w_po = pl.col(f"{weight_col}_po").fill_null(0)
    total = w_rs + w_po

    exprs = []
    for c in value_cols:
        v_rs, v_po = pl.col(c), pl.col(f"{c}_po")
        exprs.append(
            pl.when(total == 0)
            .then(v_rs.fill_null(v_po))
            .otherwise((v_rs.fill_null(0) * w_rs + v_po.fill_null(0) * w_po) / total)
            .alias(c)
        )
    exprs.append(total.alias(weight_col))
    return joined.select("player_id", *exprs)


def _write_model_card(
    out_dir: Path,
    results: list[dict],
    *,
    replacement_level: float,
    lineup_source: str,
    season_types: Sequence[str],
) -> Path:
    card = {
        "dataset": "wnba_player_impact",
        "description": (
            "Consolidated per-season WNBA player-impact table: RAPM, adj-RAPM, "
            "SPM, BPM 2.0, WAR, and DARKO forecasts joined on player_id. One "
            "parquet per season, one row per player-season-season_type. Base "
            "population = players with possession lineup data (RAPM-rated)."
        ),
        "grain": ["player_id", "season", "season_type"],
        "season_types": list(season_types),
        "source": "stats.wnba.com (playbyplayv3 / gamerotation / boxscoretraditionalv3 / leaguegamelog / playerindex / leaguedashplayerbiostats)",
        "producer": "wehoop-wnba-stats-data/python/wnba_model_publish",
        "season_convention": (
            "WNBA seasons are single calendar years (2024 = the 2024 summer "
            "season); the season column, filenames, and the raw-store keys all "
            "use that same year."
        ),
        "models": {
            "rapm": "sportsdataverse.nba.nba_rapm (single-season ridge; league-agnostic core fed WNBA possessions)",
            "adj_rapm": (
                "sportsdataverse.nba.nba_adj_rapm. Within a season, the Playoffs "
                "fit takes that season's Regular Season SPM as its prior -- that "
                "anchor is what makes a short playoff sample usable. Across "
                "seasons the prior is the possession-weighted blend of the "
                "season's Regular Season + Playoffs SPM, so a thin playoff "
                "sample never overrides a full regular season (empty for the "
                "first season of an invocation)."
            ),
            "spm": (
                "sportsdataverse.nba.train_spm + nba_spm. Coefficients are "
                "trained ONCE per season, on the Regular Season box features + "
                "RAPM target, and reused for the Playoffs pass -- re-fitting on "
                "a short playoff sample would train noise on noise. Playoff "
                "figures are therefore on the same scale as regular-season ones "
                "but rest on far fewer possessions; treat them as directional."
            ),
            "bpm": "sportsdataverse.nba.nba_bpm (BPM 2.0, season granularity)",
            "war": (
                "sportsdataverse.nba.nba_war on the RAPM rating; pts_per_win "
                "calibrated ONCE per season from Regular Season team game logs "
                "(OLS wins ~ total margin) and reused for the Playoffs pass; "
                f"replacement_level = {replacement_level} per 100 "
                "(basketball-reference VORP convention)"
            ),
            "darko": (
                "sportsdataverse.nba.nba_darko on a SEASON-GRANULAR panel: one "
                "row per player-season whose rating is the possession-weighted "
                "blend of Regular Season + Playoffs (DARKO's aging curve and "
                "process variance are per-season quantities, so playoffs enter "
                "as a blend, not a second time step). DARKO projects the NEXT "
                "season, so both season_type rows carry the same projection; "
                "darko_* columns are null until the panel spans >= 2 seasons"
            ),
        },
        "possession_pipeline_version": PIPELINE_VERSION,
        "lineup_source": lineup_source,
        "seasons": [{"season": r["season"], "rows": r["rows"]} for r in results],
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
    }
    path = out_dir / "wnba_player_impact_card.json"
    path.write_text(json.dumps(card, indent=2))
    return path


def _proxied(wrapper: Callable[..., Any], provider: Optional[ProxyProvider]) -> Callable[..., Any]:
    """Wrap a ``wnba_stats_*`` callable so each call draws a fresh proxy from *provider*.

    ``nba_box_logs`` / ``nba_player_positions`` / ``nba_player_ages`` each take a
    ``fetch=`` seam documented as "an injectable stats-wrapper replacement" —
    so the proxied form is just the same wrapper with a rotating ``proxy_url``.
    Returns *wrapper* unchanged when there is no provider (local/residential runs).
    """
    if provider is None:
        return wrapper

    def _f(*args: Any, **kwargs: Any) -> Any:
        return wrapper(*args, proxy_url=provider(), **kwargs)

    return _f


def _slug(value: str) -> str:
    """Season-type / per-mode value -> the raw scraper's variant slug component."""
    return str(value).lower().replace(" ", "-")


def _store_variant(endpoint: str, kwargs: dict) -> Optional[str]:
    """Committed-capture variant slug for a season-level call, or ``None`` when the
    store cannot honestly serve it.

    The ``-raw`` scraper writes season-level captures as
    ``{endpoint}/{season}/{variant}.json`` (swept parameters) or
    ``{endpoint}/{season}.json`` (unparameterized). This maps a live call's kwargs
    onto that layout so the committed payload is served instead of the network.

    Returns the sentinel ``""`` for an unparameterized endpoint (bare season file),
    ``None`` when the call does NOT match what was captured -- the caller must then
    fall back to live rather than serve a mismatched payload.
    """
    if endpoint == "playerindex":
        return ""  # unparameterized: {endpoint}/{season}.json
    stype = _slug(kwargs.get("season_type_all_star") or "Regular Season")
    if endpoint == "leaguedashplayerbiostats":
        per_mode = _slug(kwargs.get("per_mode_simple") or "Totals")
        return f"{stype}_{per_mode}"
    if endpoint == "leaguegamelog":
        # Two captures per season type, and they are NOT interchangeable: team
        # rows carry no PLAYER_ID, so serving them to a player-log call would push
        # team rows into player-log processing. The sweep's default
        # (player_or_team="T") keeps the bare ``{season_type}.json`` name; a
        # player top-up would land additively beside it as ``{season_type}_p.json``
        # (the WNBA store does not carry those yet — the player call falls
        # through to live).
        pt = str(kwargs.get("player_or_team_abbreviation") or "T").upper()
        return stype if pt == "T" else f"{stype}_p"
    return None


def _store_backed(
    endpoint: str,
    wrapper: Callable[..., Any],
    provider: Optional[ProxyProvider],
    raw_store_dir: Optional[str],
) -> Callable[..., Any]:
    """Season-level ``fetch=`` seam that reads the committed raw store first.

    Makes the build clone-free/offline in CI: the committed capture (a local
    ``-raw`` checkout OR an ``http(s)://`` base such as raw.githubusercontent /
    a CDN) is parsed and returned; only a genuine miss touches stats.wnba.com,
    through the proxied wrapper. With no store configured this IS ``_proxied``.
    """
    proxied = _proxied(wrapper, provider)
    if not raw_store_dir:
        return proxied

    def _f(*args: Any, **kwargs: Any) -> Any:
        variant = _store_variant(endpoint, kwargs)
        season = _season_store_year(kwargs.get("season"))
        if variant is not None and season is not None:
            frame = nba_raw_store_season_frame(endpoint, season, variant or None, raw_store_dir=raw_store_dir)
            if frame is not None:
                return frame
        return proxied(*args, **kwargs)

    return _f


def _canon_gamelog_ids(fetch: Callable[..., Any]) -> Callable[..., Any]:
    """Cast the id join keys to canonical Int64 at the fetch boundary.

    The store parser and the live wrapper have been observed emitting
    ``team_id`` as str vs i64 depending on source, and ``box_features`` joins
    the player and team logs on ``("game_id", "team_id")`` — one mixed-source
    season crashes the whole backfill with a SchemaError. Fix the dtype once,
    here, for every caller. A cast failure (e.g. a float-origin ``"123.0"``
    id string) raises loudly rather than papering over bad data.
    """

    def _f(*args: Any, **kwargs: Any) -> Any:
        frame = fetch(*args, **kwargs)
        if not isinstance(frame, pl.DataFrame):
            return frame
        casts = [
            pl.col(c).cast(pl.Int64)
            for c in ("team_id", "player_id")
            if c in frame.columns and frame.schema[c] != pl.Int64
        ]
        return frame.with_columns(casts) if casts else frame

    return _f


def _season_store_year(season: Any) -> Optional[int]:
    """``"2024"`` -> ``2024``: the directory a WNBA season-level capture lives in.

    WNBA seasons are single calendar years, so — unlike the NBA store, whose
    two halves are keyed by different years — the API label IS the directory
    for both halves. An ``int`` is taken verbatim.

    Returns ``None`` for anything unparseable, routing that call to live rather
    than guessing at a directory.
    """
    if isinstance(season, int):
        return season
    text = str(season or "")
    if len(text) >= 4 and text[:4].isdigit():
        return int(text[:4])
    return None


def build_wnba_player_impact(
    seasons: list[int],
    out_dir,
    *,
    lineup_source: str = "auto",
    cache_dir: Optional[str] = None,
    delay_s: float = 0.6,
    season_types: Sequence[str] = ("Regular Season", "Playoffs"),
    replacement_level: float = DEFAULT_REPLACEMENT_LEVEL,
    proxy_provider: Optional[ProxyProvider] = None,
    raw_store_dir: Optional[str] = None,
) -> list[dict]:
    """Build per-season consolidated WNBA player-impact tables and write parquet.

    Seasons are processed earliest-to-latest so the adj-RAPM prior and the
    DARKO panel flow forward. Seasons whose possession compile comes back
    empty (not yet played / no data) are skipped with a notice.

    Args:
        seasons: WNBA season calendar years (e.g. ``[1997, ..., 2026]``).
            Sorted ascending internally.
        out_dir: Output directory (created if absent).
        lineup_source: Forwarded to the possession compile (``"auto"`` falls
            back to pbp-derived lineups where gamerotation coverage is sparse —
            most pre-rotation-era WNBA seasons).
        cache_dir: Possession per-game parquet cache directory (default
            resolves to ``$SDV_PY_WNBA_CACHE_DIR`` or
            ``~/.sdv_py_wnba_cache/possessions``).
        delay_s: Sleep between live per-game fetches, seconds (only live
            fetches sleep; cached and store-served games don't).
        season_types: Season types to build, in order. The "Regular Season"
            pass fits the SPM coefficients and pts_per_win; the "Playoffs"
            pass reuses them and takes the regular season's SPM as its
            adj-RAPM prior. Rows are tagged with a ``season_type`` column.
        replacement_level: WAR replacement level, points per 100 possessions.
        proxy_provider: Zero-arg callable returning a proxy URL. stats.wnba.com
            hangs rather than errors on datacenter/cloud IPs, so an unattended
            host without a committed store MUST supply one. Threaded into the
            possession compile AND leaguegamelog, playerindex, and
            leaguedashplayerbiostats.
        raw_store_dir: Committed ``-raw`` JSON store to read instead of the
            live API — a local ``wehoop-wnba-stats-raw/wnba_stats/json``
            checkout OR an ``http(s)://`` base. With it set, per-game payloads
            and the season-level captures are served from the committed tree;
            the one gap is the player-variant leaguegamelog (no
            ``{season_type}_p.json`` captures yet), which falls through to a
            live stats.wnba.com call.

    Returns:
        List of ``{"season": int, "rows": int, "path": str}`` dicts, one per
        season built, in season order.
    """
    season_types = list(season_types)
    if "Playoffs" in season_types and "Regular Season" not in season_types:
        raise ValueError(
            "season_types=['Playoffs'] (or any Playoffs-without-Regular-Season "
            "combination) is not supported: the Playoffs pass reuses the SPM "
            "coef and pts_per_win fitted by the Regular Season pass in the "
            "same invocation, so it cannot run alone. Include 'Regular "
            "Season' in season_types."
        )
    # Canonicalize the order rather than merely validating membership: iterated
    # as-given, ["Playoffs", "Regular Season"] would run the Playoffs pass
    # FIRST and hit `assert coef is not None` after burning the compile.
    season_types = [t for t in ("Regular Season", "Playoffs") if t in season_types]

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    results: list[dict] = []
    prev_spm: Optional[pl.DataFrame] = None
    panel_frames: list[pl.DataFrame] = []
    age_frames: list[pl.DataFrame] = []
    built_season_types: list[str] = []

    # Every stats.wnba.com surface this builder touches must be proxied, not
    # just the possession compile -- an unproxied leaguegamelog/playerindex call
    # hangs the whole run on a datacenter host. Store-backed when raw_store_dir
    # is set; identical to the plain proxied form when it is not.
    _leaguegamelog = _canon_gamelog_ids(
        _store_backed("leaguegamelog", wnba_stats_leaguegamelog, proxy_provider, raw_store_dir)
    )
    _playerindex = _store_backed("playerindex", wnba_stats_playerindex, proxy_provider, raw_store_dir)
    _biostats = _store_backed(
        "leaguedashplayerbiostats",
        wnba_stats_leaguedashplayerbiostats,
        proxy_provider,
        raw_store_dir,
    )

    for season in sorted(seasons):
        s_str = _season_str(season)
        frames: list[pl.DataFrame] = []
        rapm_rs: Optional[pl.DataFrame] = None
        spm_rs: Optional[pl.DataFrame] = None
        rapm_po: Optional[pl.DataFrame] = None
        spm_po: Optional[pl.DataFrame] = None
        coef = None
        pts_per_win = None
        # Season-type-independent -- lazily fetched once per season (guarded
        # below), NOT hoisted here: a gap season (RS empty) must pay ZERO
        # playerindex requests.
        positions: Optional[pl.DataFrame] = None

        for stype in season_types:
            poss = _compile_wnba_season(
                season,
                stype,
                lineup_source=lineup_source,
                cache_dir=cache_dir,
                delay_s=delay_s,
                proxy_provider=proxy_provider,
                raw_store_dir=raw_store_dir,
            )
            if poss.height == 0:
                if stype == "Regular Season":
                    # No RS pass means no fitted coef/pts_per_win -- falling
                    # through to the Playoffs pass would abort the WHOLE
                    # multi-season run. Skip this season entirely instead.
                    print(
                        f"impact: season={season} type={stype!r} REGULAR SEASON "
                        f"EMPTY -- skipping season {season} entirely (no coef/"
                        f"pts_per_win for a Playoffs pass); prior chain reset"
                    )
                    prev_spm = None  # a gap season breaks the prior chain
                    break
                # A season can legitimately have no playoffs (in-progress).
                print(f"impact: season={season} type={stype!r} no possessions; skipped")
                continue

            # Fetched once per season, on the first pass that actually has
            # possessions (normally the Regular Season pass).
            if positions is None:
                positions = nba_player_positions(s_str, league_id=_WNBA_LEAGUE_ID, fetch=_playerindex)

            rapm = nba_rapm(poss)
            if stype == "Regular Season":
                assert rapm.height > 0, f"impact: season={season} {stype} RAPM came back empty"
            elif rapm.height == 0:
                # A short playoff sample going empty must not abort a
                # multi-season backfill: log loudly, skip this season's
                # Playoffs row; the RS SPM carries forward alone.
                print(
                    f"impact: season={season} type={stype!r} RAPM came back "
                    f"empty (season-local anomaly) -- skipping the Playoffs "
                    f"row for season {season}; RS SPM carries forward alone"
                )
                continue

            # Box-log substrate (per-player + per-team leaguegamelog, one call each).
            logs = nba_box_logs(
                s_str,
                league_id=_WNBA_LEAGUE_ID,
                season_type=stype,
                fetch=_leaguegamelog,
            )
            logs["team"] = _repair_team_logs(logs["team"], logs["player"])
            bf = box_features(logs["player"], logs["team"])

            if stype == "Regular Season":
                # Fitted ONCE, on the regular season; the playoff pass reuses both.
                coef = train_spm(bf, rapm.select("player_id", "o_rapm", "d_rapm"))
                pts_per_win = calibrate_pts_per_win(_team_season(logs["team"]))
                prior = AdjRapmModel.from_spm(prev_spm).prior if prev_spm is not None else {}
            else:
                assert coef is not None, "playoff pass requires the regular-season coef"
                # Within the season, the playoff fit is anchored on the RS estimate.
                prior = AdjRapmModel.from_spm(spm_rs).prior if spm_rs is not None else {}

            spm = nba_spm(bf, coef)

            # BPM 2.0 off the same logs + listed positions (fetched once above).
            bpm = nba_bpm(logs["player"], logs["team"], positions)

            # adj-RAPM: prior threaded in above (previous-season SPM for RS,
            # this season's RS SPM for PO).
            adj = nba_adj_rapm(poss, prior)

            # WAR off the RAPM rating; pts_per_win calibrated once, from the
            # regular season's team logs (WNBA has no ties, so plus_minus > 0
            # is a win), and reused for the playoff pass.
            war = nba_war(
                rapm.select("player_id", pl.col("rapm").alias("rating")),
                rapm.select(
                    "player_id",
                    (pl.col("off_poss") + pl.col("def_poss")).alias("poss"),
                ),
                replacement_level=replacement_level,
                pts_per_win=pts_per_win,
            )

            if stype == "Regular Season":
                rapm_rs, spm_rs = rapm, spm
            else:
                rapm_po, spm_po = rapm, spm

            impact = rapm
            impact = _join_on_player(
                impact,
                adj.select("player_id", "o_adj_rapm", "d_adj_rapm", "adj_rapm"),
                "adj_rapm",
            )
            impact = _join_on_player(
                impact,
                spm.select("player_id", "ospm", "dspm", "spm", "min", "gp"),
                "spm",
            )
            impact = _join_on_player(impact, bpm.select("player_id", "obpm", "dbpm", "bpm"), "bpm")
            impact = _join_on_player(impact, war, "war")
            # Human-readable identity from THIS season's logs, so the team is
            # the one she actually played for that year and a mid-season trade
            # stays visible in `teams`.
            impact = _join_on_player(impact, nba_player_identity(logs["player"]), "identity")
            impact = impact.with_columns(
                pl.lit(season, dtype=pl.Int64).alias("season"),
                pl.lit(stype, dtype=pl.Utf8).alias("season_type"),
            )
            # Identity first, then the season keys, then the metrics: a bare
            # `.head()` should answer "who, when" before "how good".
            _lead = [
                c
                for c in (
                    "player_id",
                    "player_name",
                    "team_id",
                    "team_abbreviation",
                    "team_name",
                    "teams",
                    "season",
                    "season_type",
                )
                if c in impact.columns
            ]
            impact = impact.select(*_lead, *[c for c in impact.columns if c not in _lead])
            frames.append(impact)

        if not frames:
            continue

        # --- DARKO panel: ONE row per player-season ---------------------------
        # DARKO is a per-season Kalman filter + aging curve projecting NEXT
        # season. Inserting a playoff time step would apply a season of aging
        # twice and mis-scale the per-season process variance, so playoff form
        # enters as a possession-weighted blend instead of a second step.
        panel_rs = rapm_rs.select(
            "player_id",
            pl.col("rapm").alias("rating"),
            (pl.col("off_poss") + pl.col("def_poss")).alias("weight"),
        )
        panel_po = (
            rapm_po.select(
                "player_id",
                pl.col("rapm").alias("rating"),
                (pl.col("off_poss") + pl.col("def_poss")).alias("weight"),
            )
            if rapm_po is not None
            else None
        )
        panel_frames.append(
            _blend_by_poss(panel_rs, panel_po, ["rating"], "weight").with_columns(
                pl.lit(season, dtype=pl.Int64).alias("season")
            )
        )
        age_frames.append(
            nba_player_ages(s_str, league_id=_WNBA_LEAGUE_ID, fetch=_biostats).with_columns(
                pl.lit(season, dtype=pl.Int64).alias("season")
            )
        )
        panel = pl.concat(panel_frames)
        if panel["season"].n_unique() >= 2:
            darko = nba_darko(panel, pl.concat(age_frames))
            darko_season = darko.filter(pl.col("last_season") == season).select(
                "player_id",
                pl.col("filtered_skill").alias("darko_filtered_skill"),
                pl.col("projected_rating").alias("darko_projected_rating"),
                pl.col("projected_sd").alias("darko_projected_sd"),
            )
        else:
            darko_season = None

        # DARKO projects NEXT season, which is not a playoff-specific quantity:
        # both season_type rows carry the same projection.
        out_frames = []
        for f in frames:
            if darko_season is not None:
                f = _join_on_player(f, darko_season, "darko")
            else:
                f = f.with_columns([pl.lit(None, dtype=pl.Float64).alias(c) for c in _DARKO_COLS])
            out_frames.append(f)
        impact = pl.concat(out_frames, how="vertical")

        # Track what was ACTUALLY built (not merely requested) for the model
        # card: a season with no playoffs must not have the card claim a
        # Playoffs row exists for it. Preserves the canonical season_types order.
        for st in impact["season_type"].unique().to_list():
            if st not in built_season_types:
                built_season_types.append(st)

        path = out_dir / f"wnba_player_impact_{season}.parquet"
        impact.write_parquet(path)
        results.append({"season": season, "rows": impact.height, "path": str(path)})
        print(
            f"impact: season={season} rows={impact.height} types={impact['season_type'].unique().to_list()} -> {path}"
        )

        # --- forward carry ---------------------------------------------------
        # The next season's adj-RAPM prior is the possession-weighted RS+PO
        # blend, NOT the playoff estimate: a thin playoff sample must not
        # override a full-season one as the prior for the following season.
        if spm_po is not None:
            # weight_col="min" (minutes), not possessions -- SPM's own frame
            # doesn't carry a possession count, so minutes is the defensible
            # proxy here (see _blend_by_poss's docstring for the
            # possession-weighted case, the DARKO panel blend above).
            prev_spm = _blend_by_poss(spm_rs, spm_po, ["ospm", "dspm", "spm"], "min")
        else:
            prev_spm = spm_rs

    if results:
        # The card attests what was actually built, not merely what was requested.
        actual_season_types = [t for t in season_types if t in built_season_types]
        card_path = _write_model_card(
            out_dir,
            results,
            replacement_level=replacement_level,
            lineup_source=lineup_source,
            season_types=actual_season_types,
        )
        print(f"impact: model card -> {card_path}")
    return results
