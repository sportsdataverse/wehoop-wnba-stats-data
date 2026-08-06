"""Stage 12 -- officials.

Thin shim over the tested build package: the pipeline logic lives in
``wnba_data_build``; this file exists so the stage sequence is readable from a
directory listing.

Stage numbers follow the ``DATASETS`` registry order in
``wnba_data_build/datasets.py``, which is the intended build order --
``shots`` (15) derives from ``pbp`` (10). The number is a stable dataset
identity, NOT an execution schedule: the daily driver builds every dataset in
one invocation and remains the sequence truth.

Equivalent to::

    python -m wnba_data_build --datasets officials --seasons <year>
"""

from __future__ import annotations

import sys

from wnba_data_build.cli import main

DATASET = "officials"

if __name__ == "__main__":
    # DATASET is appended, not prepended: argparse keeps the LAST occurrence of
    # an option, so a stray --datasets on the command line cannot make stage 12
    # build something other than officials.
    sys.exit(main([*sys.argv[1:], "--datasets", DATASET]))
