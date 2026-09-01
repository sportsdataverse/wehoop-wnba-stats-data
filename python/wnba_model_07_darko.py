"""Stage 07 — DARKO engine (cross-season Kalman panel over stage-02 RAPM).

Thin numbered pipeline for ONE engine of the WNBA player-impact suite;
compute + handoff semantics live in ``wnba_model_publish.impact_stages``
(parquet handoffs under build_out/impact_engines). The consolidated
build+publish is stage 08 (``wnba_model_08_impact``). Single home:
models/manifest.yaml.

Usage::

    python -m wnba_model_07_darko --seasons 2024 2025 [--raw-store-dir ...]
    scripts/wnba_models.sh 07
"""
from __future__ import annotations

import argparse


def main(argv: list[str] | None = None) -> int:
    from wnba_model_publish import impact_stages as S

    ap = argparse.ArgumentParser(prog="python -m wnba_model_07_darko")
    ap.add_argument("--seasons", nargs="+", required=True, metavar="YEAR",
                    help="calendar years; two values = inclusive range")
    ap.add_argument("--engines-dir", default=S.DEFAULT_ENGINES_DIR)
    ap.add_argument("--raw-store-dir", default=None,
                    help="committed -raw JSON store (dir or URL); direct fetch otherwise")
    a = ap.parse_args(argv)
    n = S.run_darko(S.parse_seasons(a.seasons), engines_dir=a.engines_dir, raw_store_dir=a.raw_store_dir)
    print(f"[darko] wrote {n} artifact group(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
