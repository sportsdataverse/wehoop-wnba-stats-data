"""Stage 17 -- metric_curves.

Thin shim over the tested build package: the pipeline logic lives in
``wnba_data_build``; this file exists so the stage sequence is readable from a
directory listing.

Stage numbers follow the ``DATASETS`` registry order in
``wnba_data_build/datasets.py``, which is the intended build order --
``metric_curves`` (17) derives from ``shots`` (15). Stage 16 is reserved for
``rolling_windows`` (F3b), which the roadmap orders before this one; a number is
a stable dataset identity, so the hole stays rather than being compacted.

FG% by shot distance (sdv-py ``sportsdataverse.metric_curves``) for the league,
every team and every shooter, per season: regular-season + playoff attempts
(``season_type_id`` 2 / 4, derived from the game id's type digit because the
WNBA shots carry no such column), 1-ft bins to 35 ft then 35-50 and 50-95, ids
as text with ``id_source`` ``"wnba_stats"``. Reads this run's ``shots`` frame when
stage 15 is in the same invocation (the daily processor), else the committed
``{--base}/shots/parquet/shots_{season}.parquet`` -- so a standalone backfill
needs no raw store at all. Seasons are calendar years, the shots' span (1997+).

Equivalent to::

    python -m wnba_data_build --datasets metric_curves --seasons <year>
"""

from __future__ import annotations

import sys

from wnba_data_build.cli import main

DATASET = "metric_curves"

if __name__ == "__main__":
    # DATASET is appended, not prepended: argparse keeps the LAST occurrence of
    # an option, so a stray --datasets on the command line cannot make stage 17
    # build something other than metric_curves.
    sys.exit(main([*sys.argv[1:], "--datasets", DATASET]))
