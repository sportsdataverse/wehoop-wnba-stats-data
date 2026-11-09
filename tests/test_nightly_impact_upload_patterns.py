"""The nightly impact refresh uploads every current-season artifact the builder writes.

``scripts/nightly_wnba_impact.sh`` publishes by ``upload --pattern`` per glob, so a file
the builder writes but no pattern selects never reaches the release (the league-average
rows were the first such file). This reads the loop's patterns out of the script and
checks them against the names the builder writes for one season.
"""

from __future__ import annotations

import re
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "nightly_wnba_impact.sh"
TAG = "wnba_player_impact"
SEASON = 2026


def _upload_patterns() -> list[str]:
    text = SCRIPT.read_text(encoding="utf-8")
    loop = re.search(r"^for pat in (.+); do$", text, flags=re.MULTILINE)
    assert loop, "nightly script lost its upload loop"
    raw = re.findall(r'"([^"]+)"', loop.group(1))
    return [p.replace("${TAG}", TAG).replace("${SEASON}", str(SEASON)) for p in raw]


def test_nightly_uploads_the_impact_table_and_its_league_averages(tmp_path):
    written = [f"{TAG}_{SEASON}.{ext}" for ext in ("parquet", "csv", "rds")] + [
        f"{TAG}_league_averages_{SEASON}.{ext}" for ext in ("parquet", "csv", "rds")
    ]
    for name in written + [f"{TAG}_card.json", f"{TAG}_spm_coefficients.json"]:
        (tmp_path / name).write_text("x")
    selected = {p.name for pat in _upload_patterns() for p in tmp_path.glob(pat)}
    assert set(written) <= selected
    assert {f"{TAG}_card.json", f"{TAG}_spm_coefficients.json"} <= selected
