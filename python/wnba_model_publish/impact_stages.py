"""Per-engine pipelines for the WNBA player-impact suite (Track C individualization).

One numbered stage per engine, parquet handoffs under
``build_out/impact_engines/{season}/`` (WNBA seasons are calendar years):

    01 possessions -> poss_{rs,po}.parquet
    02 rapm        -> rapm_{rs,po}.parquet
    03 spm         -> spm_{rs,po}.parquet + spm_blend.parquet (forward prior
                      carry) + identity_{rs,po}.parquet + meta.json (pts_per_win)
    04 adj_rapm    -> adj_{rs,po}.parquet   (RS prior = PREV season's blend;
                                             PO prior = THIS season's RS SPM)
    05 bpm         -> bpm_{rs,po}.parquet
    06 war         -> war_{rs,po}.parquet
    07 darko       -> darko.parquet in the LAST season's dir (needs >= 2 seasons)

Every engine call goes through the ``builders`` module seam (``B.nba_rapm``
etc. — the engines are the shared sdv-py NBA implementations, league-bound via
``_WNBA_LEAGUE_ID``), so hermetic stubs cover these stages the same way as the
monolith. The consolidated one-shot build+publish (``wnba_model_publish
impact``, stage 08) remains the production CI path and the schema authority.
Semantics mirror the monolith, including the ``_repair_team_logs`` pass and
the ``_canon_gamelog_ids`` fetch wrapper.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import polars as pl

import wnba_model_publish.builders as B

STYPE_SLUGS = {"Regular Season": "rs", "Playoffs": "po"}
DEFAULT_ENGINES_DIR = "build_out/impact_engines"


def parse_seasons(values: list[str]) -> list[int]:
    """1 value = single season; 2 = inclusive range; 3+ = explicit list."""
    years = [int(v) for v in values]
    if len(years) == 2:
        lo, hi = years
        return list(range(lo, hi + 1))
    return sorted(years)


def parse_season_types(spec: str) -> list[str]:
    types = [t.strip() for t in spec.split(",") if t.strip()]
    return [t for t in ("Regular Season", "Playoffs") if t in types]


def _year_dir(engines_dir: str | Path, season: int) -> Path:
    d = Path(engines_dir) / str(season)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _read(path: Path) -> Optional[pl.DataFrame]:
    return pl.read_parquet(path) if path.is_file() else None


def _need(path: Path, producer: str) -> pl.DataFrame:
    if not path.is_file():
        raise SystemExit(f"missing {path} — run {producer} first")
    return pl.read_parquet(path)


def _gamelog_fetch(raw_store_dir: Optional[str]):
    return B._canon_gamelog_ids(
        B._store_backed("leaguegamelog", B.wnba_stats_leaguegamelog, None, raw_store_dir)
    )


def _box_logs(s_str: str, stype: str, fetch):
    logs = B.nba_box_logs(s_str, league_id=B._WNBA_LEAGUE_ID, season_type=stype, fetch=fetch)
    logs["team"] = B._repair_team_logs(logs["team"], logs["player"])
    return logs


def run_possessions(
    seasons,
    *,
    season_types,
    engines_dir=DEFAULT_ENGINES_DIR,
    lineup_source="auto",
    cache_dir=None,
    delay_s=0.6,
    raw_store_dir=None,
) -> int:
    wrote = 0
    for season in sorted(seasons):
        d = _year_dir(engines_dir, season)
        for stype in season_types:
            poss = B._compile_wnba_season(
                season,
                stype,
                lineup_source=lineup_source,
                cache_dir=cache_dir,
                delay_s=delay_s,
                raw_store_dir=raw_store_dir,
            )
            slug = STYPE_SLUGS[stype]
            if poss.height == 0:
                print(f"[possessions] {season} {slug}: EMPTY — nothing written")
                continue
            poss.write_parquet(d / f"poss_{slug}.parquet")
            print(f"[possessions] {season} {slug}: {poss.height:,} rows")
            wrote += 1
    return wrote


def run_rapm(seasons, *, season_types, engines_dir=DEFAULT_ENGINES_DIR) -> int:
    wrote = 0
    for season in sorted(seasons):
        d = _year_dir(engines_dir, season)
        for stype in season_types:
            slug = STYPE_SLUGS[stype]
            poss = _read(d / f"poss_{slug}.parquet")
            if poss is None:
                print(f"[rapm] {season} {slug}: no possessions artifact; skipped")
                continue
            rapm = B.nba_rapm(poss)
            if rapm.height == 0:
                if stype == "Regular Season":
                    raise SystemExit(f"[rapm] {season} rs: RAPM came back EMPTY")
                print(f"[rapm] {season} {slug}: empty (PO anomaly); skipped")
                continue
            rapm.write_parquet(d / f"rapm_{slug}.parquet")
            print(f"[rapm] {season} {slug}: {rapm.height:,} players")
            wrote += 1
    return wrote


def run_spm(seasons, *, season_types, engines_dir=DEFAULT_ENGINES_DIR, raw_store_dir=None) -> int:
    lg = _gamelog_fetch(raw_store_dir)
    wrote = 0
    for season in sorted(seasons):
        d = _year_dir(engines_dir, season)
        s_str = B._season_str(season)
        rapm_rs = _need(d / "rapm_rs.parquet", "wnba_model_02_rapm")
        coef = None
        spm_rs = spm_po = None
        for stype in season_types:
            slug = STYPE_SLUGS[stype]
            if stype == "Playoffs" and not (d / "rapm_po.parquet").is_file():
                print(f"[spm] {season} po: no playoff rapm artifact; skipped")
                continue
            logs = _box_logs(s_str, stype, lg)
            bf = B.box_features(logs["player"], logs["team"])
            if stype == "Regular Season":
                coef = B.train_spm(bf, rapm_rs.select("player_id", "o_rapm", "d_rapm"))
                pts_per_win = B.calibrate_pts_per_win(B._team_season(logs["team"]))
                (d / "meta.json").write_text(
                    json.dumps({"pts_per_win": pts_per_win}), encoding="utf-8"
                )
            assert coef is not None, "playoff pass requires the regular-season coef"
            spm = B.nba_spm(bf, coef)
            spm.write_parquet(d / f"spm_{slug}.parquet")
            B.nba_player_identity(logs["player"]).write_parquet(d / f"identity_{slug}.parquet")
            if stype == "Regular Season":
                spm_rs = spm
            else:
                spm_po = spm
            print(f"[spm] {season} {slug}: {spm.height:,} players")
            wrote += 1
        if spm_rs is not None:
            blend = (
                B._blend_by_poss(spm_rs, spm_po, ["ospm", "dspm", "spm"], "min")
                if spm_po is not None
                else spm_rs
            )
            blend.write_parquet(d / "spm_blend.parquet")
    return wrote


def run_adj_rapm(seasons, *, season_types, engines_dir=DEFAULT_ENGINES_DIR) -> int:
    wrote = 0
    for season in sorted(seasons):
        d = _year_dir(engines_dir, season)
        for stype in season_types:
            slug = STYPE_SLUGS[stype]
            poss = _read(d / f"poss_{slug}.parquet")
            if poss is None:
                print(f"[adj_rapm] {season} {slug}: no possessions artifact; skipped")
                continue
            if stype == "Regular Season":
                prev = _read(Path(engines_dir) / str(season - 1) / "spm_blend.parquet")
            else:
                prev = _read(d / "spm_rs.parquet")
            prior = B.AdjRapmModel.from_spm(prev).prior if prev is not None else {}
            adj = B.nba_adj_rapm(poss, prior)
            adj.write_parquet(d / f"adj_{slug}.parquet")
            print(
                f"[adj_rapm] {season} {slug}: {adj.height:,} players"
                f" (prior={'yes' if prior else 'empty'})"
            )
            wrote += 1
    return wrote


def run_bpm(seasons, *, season_types, engines_dir=DEFAULT_ENGINES_DIR, raw_store_dir=None) -> int:
    lg = _gamelog_fetch(raw_store_dir)
    pidx = B._store_backed("playerindex", B.wnba_stats_playerindex, None, raw_store_dir)
    wrote = 0
    for season in sorted(seasons):
        d = _year_dir(engines_dir, season)
        s_str = B._season_str(season)
        positions = B.nba_player_positions(s_str, league_id=B._WNBA_LEAGUE_ID, fetch=pidx)
        for stype in season_types:
            slug = STYPE_SLUGS[stype]
            logs = _box_logs(s_str, stype, lg)
            bpm = B.nba_bpm(logs["player"], logs["team"], positions)
            bpm.write_parquet(d / f"bpm_{slug}.parquet")
            print(f"[bpm] {season} {slug}: {bpm.height:,} players")
            wrote += 1
    return wrote


def run_war(
    seasons,
    *,
    season_types,
    engines_dir=DEFAULT_ENGINES_DIR,
    replacement_level=B.DEFAULT_REPLACEMENT_LEVEL,
) -> int:
    wrote = 0
    for season in sorted(seasons):
        d = _year_dir(engines_dir, season)
        meta_path = d / "meta.json"
        if not meta_path.is_file():
            raise SystemExit(f"missing {meta_path} — run wnba_model_03_spm first")
        pts_per_win = json.loads(meta_path.read_text(encoding="utf-8"))["pts_per_win"]
        for stype in season_types:
            slug = STYPE_SLUGS[stype]
            rapm = _read(d / f"rapm_{slug}.parquet")
            if rapm is None:
                print(f"[war] {season} {slug}: no rapm artifact; skipped")
                continue
            war = B.nba_war(
                rapm.select("player_id", pl.col("rapm").alias("rating")),
                rapm.select("player_id", (pl.col("off_poss") + pl.col("def_poss")).alias("poss")),
                replacement_level=replacement_level,
                pts_per_win=pts_per_win,
            )
            war.write_parquet(d / f"war_{slug}.parquet")
            print(f"[war] {season} {slug}: {war.height:,} players")
            wrote += 1
    return wrote


def run_darko(seasons, *, engines_dir=DEFAULT_ENGINES_DIR, raw_store_dir=None) -> int:
    bios = B._store_backed(
        "leaguedashplayerbiostats", B.wnba_stats_leaguedashplayerbiostats, None, raw_store_dir
    )
    panel_frames: list[pl.DataFrame] = []
    age_frames: list[pl.DataFrame] = []
    years = sorted(seasons)
    for season in years:
        d = Path(engines_dir) / str(season)
        rapm_rs = _read(d / "rapm_rs.parquet")
        if rapm_rs is None:
            print(f"[darko] {season}: no rs rapm artifact; season skipped")
            continue
        rapm_po = _read(d / "rapm_po.parquet")
        sel = lambda f: f.select(  # noqa: E731
            "player_id",
            pl.col("rapm").alias("rating"),
            (pl.col("off_poss") + pl.col("def_poss")).alias("weight"),
        )
        panel_frames.append(
            B._blend_by_poss(
                sel(rapm_rs), sel(rapm_po) if rapm_po is not None else None, ["rating"], "weight"
            ).with_columns(pl.lit(season, dtype=pl.Int64).alias("season"))
        )
        age_frames.append(
            B.nba_player_ages(
                B._season_str(season), league_id=B._WNBA_LEAGUE_ID, fetch=bios
            ).with_columns(pl.lit(season, dtype=pl.Int64).alias("season"))
        )
    if not panel_frames:
        raise SystemExit("[darko] no seasons had rs rapm artifacts")
    panel = pl.concat(panel_frames)
    if panel["season"].n_unique() < 2:
        print("[darko] < 2 panel seasons — Kalman filter needs a sequence; nothing written")
        return 0
    darko = B.nba_darko(panel, pl.concat(age_frames))
    out = _year_dir(engines_dir, years[-1]) / "darko.parquet"
    darko.write_parquet(out)
    print(f"[darko] panel {panel['season'].n_unique()} seasons -> {out} ({darko.height:,} rows)")
    return 1
