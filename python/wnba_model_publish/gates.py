"""Publish floors for ``wnba_player_impact`` — the numeric gates the registry listed as TODO.

Diff-ported from the NBA twin (``nba_model_publish/gates.py``) with the floors
**re-measured on the WNBA release**, never inherited: WNBA seasons are single
calendar years, a rated season is a fraction of the NBA's player count, and a
~40-game regular season gives each RAPM fit far fewer possessions — so every
threshold comes from this league's own observations.

One deliberate structural divergence: **no oracle gates**. The NBA twin gates
concurrent validity against published Ryan Davis RAPM / Dunks & Threes EPM
CSVs; no equivalent public WNBA player-impact metric is available here, so
rather than ship an always-SKIPPED gate that could be mistaken for coverage,
the oracle family is absent and the internal five carry the publish decision.

Floors were observed with ``python -m wnba_model_publish gates --from-release``
against the 2026-07-29 publish and each sits strictly below its observation.
Never lower one to make a publish pass — debug the build; a re-derivation must
state the new observation beside the constant.
"""

from __future__ import annotations

import io
import json
import math
from pathlib import Path
from typing import Iterable, Optional

import polars as pl

TAG = "wnba_player_impact"
RELEASE_BASE = f"https://github.com/sportsdataverse/sportsdataverse-data/releases/download/{TAG}"

#: gate -> floor, each carrying the observation that set it. Measured
#: 2026-09-01 on the 2026-07-29 published release, all 30 seasons (1997-2026).
#: The forward floors are roughly half the NBA twin's: a ~40-game WNBA season
#: leaves less signal per RAPM fit, so the panel is genuinely less persistent
#: season to season. Re-measured, not inherited.
FLOORS: dict[str, Optional[float]] = {
    "rs_rows_min": 80,  # observed min 98 (1997, the inaugural 28-game season); 221 in 2026
    "r_rapm_adj_min": 0.65,  # observed min 0.751 (2023)
    "r_spm_rapm_min": 0.18,  # observed min 0.237 (2026); median ~0.43
    "r_rapm_yoy_min": 0.10,  # observed min 0.146 (2004)
    "r_darko_fwd_min": 0.05,  # observed min 0.080 (2004); n-weighted mean 0.284
}


def _pearson(df: pl.DataFrame, a: str, b: str) -> Optional[float]:
    """Pearson r; ``None`` when the pair cannot support one, NaN when it is degenerate.

    The two are NOT the same and must not be folded together. ``None`` means "not
    measurable" and is reported SKIPPED; NaN means the pair had enough rows but a
    column was CONSTANT, which is a real defect. Returning None for a constant
    column let ``_min_of`` drop the season and ``gate_report`` mark the gate
    SKIPPED -- and since ``check_publish_floors`` blocks only on FAIL, a constant
    ``spm`` or ``adj_rapm`` could publish under a gate that never ran.
    """
    sub = df.select(a, b).drop_nulls()
    if sub.height < 3:
        return None
    r = sub.select(pl.corr(a, b)).item()
    return float("nan") if r is None else float(r)


def _rs(frame: pl.DataFrame) -> pl.DataFrame:
    return frame.filter(pl.col("season_type") == "Regular Season")


def internal_metrics(frames: dict[int, pl.DataFrame]) -> dict[str, dict]:
    """Per-season diagnostics on the Regular Season rows.

    ``frames`` maps the (calendar) season to that season's impact frame.
    Adjacent seasons present in ``frames`` also get the forward pair metrics
    (``r_rapm_yoy`` = RAPM(t) vs RAPM(t+1); ``r_darko_fwd`` = the projection
    made in t vs realized RAPM in t+1), keyed on t.
    """
    out: dict[str, dict] = {}
    for season in sorted(frames):
        rs = _rs(frames[season])
        row = {
            "rs_rows": rs.height,
            "r_rapm_adj": _pearson(rs, "rapm", "adj_rapm"),
            "r_spm_rapm": _pearson(rs, "spm", "rapm"),
            "r_rapm_yoy": None,
            "r_darko_fwd": None,
            "n_fwd": 0,
        }
        nxt = frames.get(season + 1)
        if nxt is not None:
            pair = rs.select("player_id", "rapm", "darko_projected_rating").join(
                _rs(nxt).select("player_id", pl.col("rapm").alias("next_rapm")),
                on="player_id",
                how="inner",
            )
            row["r_rapm_yoy"] = _pearson(pair, "rapm", "next_rapm")
            row["r_darko_fwd"] = _pearson(pair, "darko_projected_rating", "next_rapm")
            row["n_fwd"] = pair.drop_nulls().height
        out[str(season)] = row
    return out


def _min_of(values: Iterable[Optional[float]]) -> Optional[float]:
    """Minimum over the measurable values; a single degenerate season poisons it.

    NaN propagates deliberately so the gate FAILs rather than quietly reporting
    the minimum of the seasons that happened to be well-behaved.
    """
    vals = [v for v in values if v is not None]
    if not vals:
        return None
    if any(isinstance(v, float) and math.isnan(v) for v in vals):
        return float("nan")
    return min(vals)


#: Publish-blocking SCALE bands. Every gate in FLOORS above is a CORRELATION or a
#: row count, and a correlation is invariant to an affine rescale -- a season whose
#: ratings all came out 10x too large passes every one of them. That is exactly how
#: mis-scaled "xwOBA" of .44-.73 shipped on 2026-09-01 (baseballr-data 75d29ddbc5).
#:
#: Two-sided bands on the qualified league LEVEL, set strictly outside the values
#: observed on the published release (seasons 1997-2026, measured 2026-09-02 with
#: off_poss >= 300); the comment records the observation that set each one.
#: Never widen a band to make a publish pass -- debug the build.
SCALE_QUALIFY_POSS = 300
SCALE_BANDS: dict[str, tuple[float, float]] = {
    "mean_rapm": (-1.0, 1.0),  # observed |mean| <= 0.19
    "sd_rapm": (0.5, 3.5),  # observed 0.99 - 2.27
    "mean_adj_rapm": (-3.0, 3.0),  # observed |mean| <= 1.00
    "sd_adj_rapm": (3.0, 8.0),  # observed 4.47 - 6.20
}


def scale_checks(frames: dict[int, pl.DataFrame]) -> list[dict]:
    """Evaluate every season's qualified level against SCALE_BANDS.

    A season with too few qualified players to measure is SKIPPED, which is not
    PASS -- the printed table says which seasons actually ran.
    """
    out: list[dict] = []
    for season in sorted(frames):
        frame = frames[season]
        missing = [c for c in ("off_poss", "rapm", "adj_rapm") if c not in frame.columns]
        if missing:
            # cannot measure a level without these -- SKIPPED, never PASS
            out.append({"season": season, "gate": "scale", "status": "SKIPPED",
                        "reason": f"frame has no {', '.join(missing)}"})
            continue
        qualified = frame.filter(pl.col("off_poss") >= SCALE_QUALIFY_POSS)
        if qualified.height < 20:
            out.append({"season": season, "gate": "scale", "status": "SKIPPED",
                        "reason": f"only {qualified.height} qualified players"})
            continue
        stats = {
            "mean_rapm": qualified["rapm"].mean(),
            "sd_rapm": qualified["rapm"].std(),
            "mean_adj_rapm": qualified["adj_rapm"].mean(),
            "sd_adj_rapm": qualified["adj_rapm"].std(),
        }
        for name, (lo, hi) in SCALE_BANDS.items():
            observed = stats[name]
            if observed is None:
                out.append({"season": season, "gate": name, "status": "SKIPPED",
                            "reason": "not computable"})
                continue
            observed = float(observed)
            out.append({
                "season": season, "gate": name, "observed": observed, "band": [lo, hi],
                "status": "PASS" if lo <= observed <= hi else "FAIL",
            })
    return out


def gate_report(frames: dict[int, pl.DataFrame]) -> dict:
    """Compute every diagnostic and evaluate it against ``FLOORS``.

    Pure computation: never raises on a failing gate (the caller decides), and a
    metric the given frames cannot support (a single season has no forward pair)
    is SKIPPED — which is not PASS.
    """
    seasons = internal_metrics(frames)
    per = list(seasons.values())
    summary: dict[str, Optional[float]] = {
        "rs_rows_min": _min_of(r["rs_rows"] for r in per),
        "r_rapm_adj_min": _min_of(r["r_rapm_adj"] for r in per),
        "r_spm_rapm_min": _min_of(r["r_spm_rapm"] for r in per),
        "r_rapm_yoy_min": _min_of(r["r_rapm_yoy"] for r in per),
        "r_darko_fwd_min": _min_of(r["r_darko_fwd"] for r in per),
    }
    fwd = [
        (r["r_darko_fwd"], r["n_fwd"]) for r in per if r["r_darko_fwd"] is not None and r["n_fwd"]
    ]
    summary["r_darko_fwd_wmean"] = (
        (sum(r * n for r, n in fwd) / sum(n for _, n in fwd)) if fwd else None
    )

    checks = []
    for gate, floor in FLOORS.items():
        observed = summary.get(gate)
        if floor is None or observed is None:
            status = "SKIPPED"
        elif isinstance(observed, float) and math.isnan(observed):
            # Degenerate (constant column), not unmeasurable: never SKIPPED.
            status = "FAIL"
        else:
            status = "PASS" if observed >= floor else "FAIL"
        checks.append({"gate": gate, "floor": floor, "observed": observed, "status": status})
    return {"seasons": seasons, "summary": summary, "checks": checks}


def format_report(report: dict) -> str:
    lines = [f"{'gate':24s} {'floor':>8s} {'observed':>10s}  status"]
    for c in report["checks"]:
        obs = "n/a" if c["observed"] is None else f"{c['observed']:.3f}"
        floor = "n/a" if c["floor"] is None else f"{c['floor']:.3f}"
        lines.append(f"{c['gate']:24s} {floor:>8s} {obs:>10s}  {c['status']}")
    return "\n".join(lines)


def load_frames_from_dir(out_dir: Path, seasons: Iterable[int]) -> dict[int, pl.DataFrame]:
    frames = {}
    for s in seasons:
        p = Path(out_dir) / f"{TAG}_{s}.parquet"
        if not p.is_file():
            raise SystemExit(f"gates: missing built asset {p}")
        frames[int(s)] = pl.read_parquet(p)
    return frames


def load_frames_from_release(seasons: Iterable[int]) -> dict[int, pl.DataFrame]:
    import requests

    frames = {}
    missing: list[str] = []
    for s in seasons:
        r = requests.get(f"{RELEASE_BASE}/{TAG}_{s}.parquet", timeout=120)
        if r.status_code == 200:
            frames[int(s)] = pl.read_parquet(io.BytesIO(r.content))
        else:
            missing.append(f"{s} (HTTP {r.status_code})")
    # Refuse a PARTIAL read. Silently dropping a season let `gates` pass on the
    # seasons that happened to download and `spm-coefficients` write records for
    # only those -- a floor measured on an unknown subset is not a measurement.
    if missing:
        raise SystemExit(
            "gates: refusing a partial release read; missing " + ", ".join(missing)
        )
    if not frames:
        raise SystemExit("gates: no release assets found for the requested seasons")
    return frames


def check_publish_floors(out_dir: Path, seasons: Iterable[int]) -> dict:
    """Publish-blocking gate: evaluate the built seasons, record the report in the
    model card, and refuse (``SystemExit``) on any FAIL. SKIPPED never blocks and
    never counts as a pass — the printed table says which gates actually ran.
    """
    out_dir = Path(out_dir)
    seasons = sorted(int(s) for s in seasons)
    report = gate_report(load_frames_from_dir(out_dir, seasons))
    scale = scale_checks(load_frames_from_dir(out_dir, seasons))
    report["scale"] = scale
    scale_failed = [c for c in scale if c["status"] == "FAIL"]
    scale_ran = [c for c in scale if c["status"] != "SKIPPED"]
    print(
        f"gates: scale bands (qualified off_poss >= {SCALE_QUALIFY_POSS}) — "
        f"{len(scale_ran) - len(scale_failed)}/{len(scale_ran)} pass"
    )
    print("gates: publish floors (models/REGISTRY.md)\n" + format_report(report))
    card = out_dir / f"{TAG}_card.json"
    if card.is_file():
        payload = json.loads(card.read_text(encoding="utf-8"))
        payload["publish_gates"] = {"seasons_gated": seasons, **report}
        card.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    if scale_failed:
        raise SystemExit(
            "gates: publish SCALE BLOCKED — "
            + "; ".join(
                f"{c['season']} {c['gate']} observed {c['observed']:.4f} "
                f"outside band {c['band'][0]}..{c['band'][1]}"
                for c in scale_failed
            )
            + " (a correlation gate cannot see a rescale; never widen a band to pass)"
        )
    failed = [c for c in report["checks"] if c["status"] == "FAIL"]
    if failed:
        raise SystemExit(
            "gates: publish BLOCKED — "
            + "; ".join(
                f"{c['gate']} observed {c['observed']:.3f} < floor {c['floor']}" for c in failed
            )
            + " (never lower a floor to pass: debug the build)"
        )
    return report
