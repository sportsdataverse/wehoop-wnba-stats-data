"""The manifest drift check — the guard that would have caught the 2026-05-30 staleness.

Offline: ``gh`` is replaced by a fake runner and the published manifest by a
monkeypatched reader, so nothing here touches the network.
"""

from __future__ import annotations

import polars as pl
import pytest
from wnba_data_build import manifest as m

_TAG = "wnba_stats_rosters"
_REPO = "sportsdataverse/sportsdataverse-data"


def _runner(seasons, *, tables=("rosters",)):
    """Fake `gh release view --json assets` emitting one parquet per (table, season)."""

    def run(_args):
        return "\n".join(
            f"{t}_{s}.parquet\t2026-08-12T23:0{i % 10}:00Z"
            for i, s in enumerate(seasons)
            for t in tables
        )

    return run


def _publish(monkeypatch, seasons):
    """Pin the *published* manifest to `seasons` (None = no manifest asset)."""
    df = (
        None
        if seasons is None
        else pl.DataFrame(
            {
                "season": list(seasons),
                "row_count": [1] * len(seasons),
                "generated_at_utc": ["2026-05-30T11:50:45Z"] * len(seasons),
                "source_endpoint": ["stats.wnba.com/commonteamroster"] * len(seasons),
            }
        )
    )
    monkeypatch.setattr(m, "read_manifest", lambda tag, repo: df)


def test_agreeing_manifest_passes(monkeypatch):
    _publish(monkeypatch, [2024, 2025, 2026])
    assert m.check_tag(_TAG, _REPO, runner=_runner([2024, 2025, 2026])) is None


def test_the_actual_defect_is_caught(monkeypatch):
    """30 seasons of assets behind a one-row 2026 manifest — tonight's bug."""
    _publish(monkeypatch, [2026])
    msg = m.check_tag(_TAG, _REPO, runner=_runner(range(1997, 2027)))
    assert msg is not None
    assert "declares 1 season(s), assets carry 30" in msg
    assert "1997" in msg


def test_manifest_listing_an_unpublished_season_is_caught(monkeypatch):
    """Drift in the other direction must fail too, not just under-listing."""
    _publish(monkeypatch, [2025, 2026])
    msg = m.check_tag(_TAG, _REPO, runner=_runner([2026]))
    assert msg is not None and "listed but not published: [2025]" in msg


def test_equal_counts_but_different_seasons_is_caught(monkeypatch):
    """Set equality, not row count — a count-only check would pass this."""
    _publish(monkeypatch, [2024, 2025])
    msg = m.check_tag(_TAG, _REPO, runner=_runner([2025, 2026]))
    assert msg is not None and "2024" in msg and "2026" in msg


def test_missing_manifest_is_caught(monkeypatch):
    """leaguedash's case: assets published, no manifest asset at all."""
    _publish(monkeypatch, None)
    msg = m.check_tag(_TAG, _REPO, runner=_runner([2025, 2026]))
    assert msg is not None and "NO manifest asset" in msg


def test_empty_release_is_not_a_failure(monkeypatch):
    """A tag with nothing published has no coverage to misstate."""
    _publish(monkeypatch, None)
    assert m.check_tag(_TAG, _REPO, runner=lambda _a: "") is None


def test_multi_table_tag_counts_each_season_once(monkeypatch):
    """leaguedash ships 24 parquets per season; that is still one season."""
    _publish(monkeypatch, [2025, 2026])
    runner = _runner([2025, 2026], tables=("player_master", "team_master", "standings"))
    assert m.check_tag("wnba_stats_leaguedash", _REPO, runner=runner) is None
    assert set(m.season_assets("wnba_stats_leaguedash", _REPO, runner=runner)) == {2025, 2026}


def test_check_tags_collects_every_problem(monkeypatch):
    _publish(monkeypatch, [2026])
    problems = m.check_tags([_TAG, "wnba_stats_shots"], _REPO, runner=_runner([2025, 2026]))
    assert len(problems) == 2


def test_gh_failure_that_is_not_a_missing_release_surfaces():
    """An auth/rate-limit failure must raise, never read as 'nothing published'."""
    import subprocess

    def boom(_args):
        raise subprocess.CalledProcessError(1, "gh", stderr="HTTP 401: Bad credentials")

    with pytest.raises(subprocess.CalledProcessError):
        m.release_assets(_TAG, _REPO, runner=boom)


def test_missing_release_reads_as_empty():
    import subprocess

    def missing(_args):
        raise subprocess.CalledProcessError(1, "gh", stderr="release not found")

    assert m.release_assets(_TAG, _REPO, runner=missing) == []


def test_manifest_columns_match_the_wehoop_contract(monkeypatch):
    """wehoop's load_*_manifest() documents exactly these four columns, in order."""
    assert m.MANIFEST_COLUMNS == ("season", "row_count", "generated_at_utc", "source_endpoint")
