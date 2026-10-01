"""Stage 16 -- rolling_windows.

Thin shim over the tested build package: the pipeline logic lives in
``wnba_data_build``; this file exists so the stage sequence is readable from a
directory listing.

Stage numbers follow the ``DATASETS`` registry order in
``wnba_data_build/datasets.py``, which is the intended build order --
``rolling_windows`` (16) derives from ``schedules`` (08) and ``shots`` (15) and
builds before ``metric_curves`` (17).

Rolling shooting form (sdv-py ``sportsdataverse.rolling_windows``): every shooter's
last 50 / 200 field-goal and three-point attempts, against the window before, the
window entering the season and the career before it. Regular-season + playoff
attempts (``season_type_id`` 2 / 4, derived from the game id's type digit because
the WNBA shots carry no such column), ids as text with ``id_source``
``"wnba_stats"``. Reads this run's ``shots`` and ``schedules`` frames when they are
in the same invocation (the daily processor), else the committed
``{--base}/shots/parquet/shots_{season}.parquet`` and
``{--base}/schedules/parquet/wnba_stats_schedule_{season}.parquet``; every earlier
committed shots season and ``{--base}/wnba_stats_schedule_master.parquet`` supply
the career history and its game dates, so a standalone backfill needs no raw store
at all. Seasons are calendar years, the shots' span (1997+).

Equivalent to::

    python -m wnba_data_build --datasets rolling_windows --seasons <year>
"""

from __future__ import annotations

import sys

from wnba_data_build.cli import main

DATASET = "rolling_windows"

if __name__ == "__main__":
    # DATASET is appended, not prepended: argparse keeps the LAST occurrence of
    # an option, so a stray --datasets on the command line cannot make stage 16
    # build something other than rolling_windows.
    sys.exit(main([*sys.argv[1:], "--datasets", DATASET]))
