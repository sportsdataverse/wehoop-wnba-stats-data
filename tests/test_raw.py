"""Reader tests for the raw store.

Most run against a synthetic tree so they work anywhere; the parity and
real-store tests use the sibling ``wehoop-wnba-stats-raw`` checkout when present
and skip otherwise, so CI without the sibling still passes.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from wnba_data_build import raw

REAL_STORE = Path("/mnt/sdv_repos/wehoop-wnba-stats-raw/wnba_stats/json")
needs_real_store = pytest.mark.skipif(
    not REAL_STORE.is_dir(), reason="sibling wehoop-wnba-stats-raw checkout not present"
)


def _write(root: Path, rel: str, payload: object) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload), encoding="utf-8")


def test_season_of_decodes_the_year() -> None:
    assert raw.season_of("1022600071") == 2026
    assert raw.season_of("1029700001") == 1997  # inaugural season, 19xx branch
    assert raw.season_of("1020600064") == 2006


def test_season_of_pads_short_ids() -> None:
    assert raw.season_of("22600071") == raw.season_of("1022600071")


@needs_real_store
def test_season_of_matches_the_writers_decoder_everywhere() -> None:
    """The store's writer decodes the season independently inside sdv-py.

    If the two ever disagree this reader silently looks in the wrong directory and
    every dataset comes back empty, so pin them across the whole real store.
    """
    from sportsdataverse.nba.nba_possessions import _raw_store_path

    checked = 0
    for season_dir in sorted((REAL_STORE / "playbyplayv3").iterdir()):
        if not season_dir.is_dir():
            continue
        for path in list(season_dir.glob("*.json"))[:40]:
            gid = path.stem
            assert raw.season_of(gid) == int(season_dir.name), gid
            expected = _raw_store_path("playbyplayv3", gid, root=str(REAL_STORE))
            assert raw.game_payload_path(REAL_STORE, "playbyplayv3", gid) == expected, gid
            checked += 1
    assert checked > 500, f"expected a broad sample, only checked {checked}"


@needs_real_store
def test_reads_a_real_playbyplay_payload() -> None:
    season_dir = sorted((REAL_STORE / "playbyplayv3").iterdir())[0]
    gid = next(season_dir.glob("*.json")).stem
    payload = raw.read_game(REAL_STORE, "playbyplayv3", gid)
    assert isinstance(payload, dict)
    assert payload.get("game", {}).get("actions"), "expected play-by-play actions"


@needs_real_store
def test_available_games_enumerates_a_real_season() -> None:
    games = raw.available_games(REAL_STORE, "playbyplayv3", 2006)
    assert games and all(g.isdigit() and len(g) == 10 for g in games)


def test_missing_payload_returns_none(tmp_path: Path) -> None:
    """A gap must read as None, not raise — sweeps are always partially complete."""
    assert raw.read_game(tmp_path, "playbyplayv3", "1022600071") is None
    assert raw.read_season(tmp_path, "leaguestandingsv3", 2025) is None


def test_corrupt_payload_returns_none(tmp_path: Path) -> None:
    p = tmp_path / "playbyplayv3" / "2026" / "1022600071.json"
    p.parent.mkdir(parents=True)
    p.write_text("{not json", encoding="utf-8")
    assert raw.read_game(tmp_path, "playbyplayv3", "1022600071") is None


def test_read_season_variant_paths(tmp_path: Path) -> None:
    _write(tmp_path, "leaguedashlineups/2025/base_playoffs.json", {"ok": 1})
    _write(tmp_path, "leaguestandingsv3/2025.json", {"ok": 2})
    assert raw.read_season(tmp_path, "leaguedashlineups", 2025, "base_playoffs") == {"ok": 1}
    assert raw.read_season(tmp_path, "leaguestandingsv3", 2025) == {"ok": 2}


def test_season_game_ids_unions_both_season_types(tmp_path: Path) -> None:
    def log(ids):
        return {"resultSets": [{"headers": ["GAME_ID", "X"], "rowSet": [[i, 1] for i in ids]}]}

    _write(
        tmp_path,
        "leaguegamelog/2025/regular-season.json",
        log(["1022500001", "1022500002"]),
    )
    _write(tmp_path, "leaguegamelog/2025/playoffs.json", log(["1042500001"]))
    assert raw.season_game_ids(tmp_path, 2025) == [
        "1022500001",
        "1022500002",
        "1042500001",
    ]


def test_season_game_ids_zero_pads(tmp_path: Path) -> None:
    """stats.com sometimes returns the id as an int, which drops the leading zero."""
    _write(
        tmp_path,
        "leaguegamelog/2025/regular-season.json",
        {"resultSets": [{"headers": ["GAME_ID"], "rowSet": [[1022500001]]}]},
    )
    assert raw.season_game_ids(tmp_path, 2025) == ["1022500001"]


def test_iter_game_payloads_skips_misses(tmp_path: Path) -> None:
    _write(tmp_path, "playbyplayv3/2025/1022500001.json", {"a": 1})
    got = list(raw.iter_game_payloads(tmp_path, "playbyplayv3", ["1022500001", "1022500002"]))
    assert got == [("1022500001", {"a": 1})]


def test_result_set_named_and_default() -> None:
    payload = {
        "resultSets": [
            {"name": "Empty", "headers": ["A"], "rowSet": []},
            {"name": "Rows", "headers": ["A", "B"], "rowSet": [[1, 2]]},
        ]
    }
    assert raw.result_set(payload, "Rows") == (["A", "B"], [[1, 2]])
    # no name -> first non-empty set, so a leading empty set doesn't mask the data
    assert raw.result_set(payload) == (["A", "B"], [[1, 2]])
    assert raw.result_set(payload, "Empty") == (["A"], [])


def test_result_set_tolerates_garbage() -> None:
    assert raw.result_set(None) == ([], [])
    assert raw.result_set({}) == ([], [])
    assert raw.result_set({"resultSets": {}}) == ([], [])


def test_available_games_rejects_url_roots() -> None:
    """GitHub serves files, not listings — fail loudly rather than return nothing."""
    with pytest.raises(ValueError, match="local root"):
        raw.available_games(raw.RAW_BASE, "playbyplayv3", 2025)


def test_url_root_survives_path_wrapping(monkeypatch: pytest.MonkeyPatch) -> None:
    """The CLI wraps ``--root`` in ``Path``, which collapses ``https://`` to ``https:/``.

    For 33 days the daily workflow passed the raw.githubusercontent root that way,
    the mangled root failed the URL test, was read as a local directory, and every
    family "skipped: no rows" on a green run. A Path-wrapped URL must still fetch.

    The second half of the same no-op: the raw repo is PRIVATE, so the raw host
    404s an unauthenticated read. The token the workflow exports must be sent.
    """
    seen: list[tuple[str, str | None]] = []

    class _Resp:
        def __enter__(self) -> "_Resp":
            return self

        def __exit__(self, *exc: object) -> bool:
            return False

        def read(self) -> bytes:
            return b'{"ok": 1}'

    def _urlopen(req: raw.urllib.request.Request, timeout: int = 60) -> _Resp:
        seen.append((req.full_url, req.get_header("Authorization")))
        return _Resp()

    monkeypatch.setattr(raw.urllib.request, "urlopen", _urlopen)
    monkeypatch.delenv("GITHUB_PAT", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    rel = "leaguestandingsv3/2026/regular-season.json"
    for root in (raw.RAW_BASE, Path(raw.RAW_BASE)):
        assert raw._is_url(root)
        assert raw._read_json(root, rel) == {"ok": 1}
    assert seen == [(f"{raw.RAW_BASE}/{rel}", None)] * 2

    monkeypatch.setenv("GITHUB_PAT", "ghp_test")
    assert raw._read_json(Path(raw.RAW_BASE), rel) == {"ok": 1}
    assert seen[-1] == (f"{raw.RAW_BASE}/{rel}", "token ghp_test")


def test_season_variants_lists_a_raw_github_root_via_the_contents_api(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Season-level families discovered variants by globbing a local dir, so over HTTP
    every one of them 'skipped: no rows'. A raw-GitHub root must list the same
    directory through the contents API, with the same token."""
    seen: list[tuple[str, str | None, str | None]] = []

    class _Resp:
        def __enter__(self) -> "_Resp":
            return self

        def __exit__(self, *exc: object) -> bool:
            return False

        def read(self) -> bytes:
            return (
                b'[{"name": "regular-season.json", "type": "file"},'
                b' {"name": "playoffs.json", "type": "file"},'
                b' {"name": "README.md", "type": "file"}]'
            )

    def _urlopen(req: raw.urllib.request.Request, timeout: int = 60) -> _Resp:
        seen.append((req.full_url, req.get_header("Authorization"), req.get_header("Accept")))
        return _Resp()

    monkeypatch.setattr(raw.urllib.request, "urlopen", _urlopen)
    monkeypatch.setenv("GITHUB_PAT", "ghp_test")
    got = raw.season_variants(Path(raw.RAW_BASE), "leaguestandingsv3", 2026)
    assert got == ["playoffs", "regular-season"]
    assert seen == [
        (
            "https://api.github.com/repos/sportsdataverse/wehoop-wnba-stats-raw/contents/"
            "wnba_stats/json/leaguestandingsv3/2026?ref=main",
            "token ghp_test",
            "application/vnd.github+json",
        )
    ]
    # a local root still globs, and an unknown host cannot list
    _write(tmp_path, "leaguestandingsv3/2026/regular-season.json", {})
    assert raw.season_variants(tmp_path, "leaguestandingsv3", 2026) == ["regular-season"]
    assert raw.season_variants("https://example.com/x", "leaguestandingsv3", 2026) == []
