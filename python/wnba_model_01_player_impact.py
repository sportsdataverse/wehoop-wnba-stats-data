"""Stage 01 — WNBA player-impact suite (RAPM / adj-RAPM / SPM / BPM / DARKO / WAR).

Thin numbered entry over ``wnba_model_publish impact``; args forward verbatim (injects the ``impact`` subcommand).
Dispatch-only BY DESIGN (rate-budgeted; stats.wnba.com hangs on datacenter IPs — multi-season runs go residential).
Usage::

    python -m wnba_model_01_player_impact --seasons 2026 --dry-run
    scripts/wnba_models.sh 01
"""
from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    from wnba_model_publish.cli import main as _main

    argv = list(argv) if argv is not None else sys.argv[1:]
    return _main(["impact", *argv])


if __name__ == "__main__":
    raise SystemExit(main())
