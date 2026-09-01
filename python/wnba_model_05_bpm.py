"""Stage 05 — BPM 2.0 engine (box logs + listed positions).

Thin numbered pipeline for ONE engine of the WNBA player-impact suite;
compute + handoff semantics live in ``wnba_model_publish.impact_stages``
(parquet handoffs under build_out/impact_engines). The consolidated
build+publish is stage 08 (``wnba_model_08_impact``). Single home:
models/manifest.yaml.

Usage::

    python -m wnba_model_05_bpm --seasons 2024 2025 [--raw-store-dir ...]
    scripts/wnba_models.sh 05
"""
from __future__ import annotations

import argparse


def main(argv: list[str] | None = None) -> int:
    from wnba_model_publish import impact_stages as S

    ap = argparse.ArgumentParser(prog="python -m wnba_model_05_bpm")
    ap.add_argument("--seasons", nargs="+", required=True, metavar="YEAR",
                    help="calendar years; two values = inclusive range")
    ap.add_argument("--engines-dir", default=S.DEFAULT_ENGINES_DIR)
    ap.add_argument("--season-types", default="Regular Season,Playoffs",
                    metavar="CSV")
    ap.add_argument("--raw-store-dir", default=None,
                    help="committed -raw JSON store (dir or URL); direct fetch otherwise")
    a = ap.parse_args(argv)
    n = S.run_bpm(S.parse_seasons(a.seasons), season_types=S.parse_season_types(a.season_types), engines_dir=a.engines_dir, raw_store_dir=a.raw_store_dir)
    print(f"[bpm] wrote {n} artifact group(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
