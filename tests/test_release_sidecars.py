"""The release sidecars R's sportsdataverse_save() attaches to every tag.

This repo's hand-rolled ``gh release upload`` dropped them, which left published
tags carrying a timestamp.json frozen at the last R run while the data kept
moving -- a consumer reading it to decide whether to re-download got a confident
wrong answer.
"""

import json
from pathlib import Path

import pytest
from wnba_data_build.publish import PKG_FUNCTION, upload_artifacts

SIDECAR_NAMES = [
    "timestamp.txt",
    "timestamp.json",
    "package_function.txt",
    "package_function.json",
]
TAG = "wnba_stats_pbp"


def _stage(tmp_path):
    d = tmp_path / "artifacts"
    d.mkdir()
    (d / "thing_2025.parquet").write_bytes(b"x")
    return d


def test_upload_stamps_the_tag_last(tmp_path):
    calls: list[list[str]] = []

    upload_artifacts(
        _stage(tmp_path),
        tag=TAG,
        repo="sportsdataverse/sportsdataverse-data",
        runner=lambda args: calls.append(args),
        exists_check=lambda t, r: True,
    )

    names = [Path(c[3]).name for c in calls if c[:2] == ["release", "upload"]]
    assert names == ["thing_2025.parquet", *SIDECAR_NAMES]
    assert all(c[2] == TAG and c[-1] == "--clobber" for c in calls)


def test_nothing_uploaded_means_no_stamp(tmp_path):
    """A run that published nothing must not move the timestamp."""
    empty = tmp_path / "artifacts"
    empty.mkdir()
    calls: list[list[str]] = []

    upload_artifacts(
        empty,
        tag=TAG,
        repo="r/r",
        runner=lambda args: calls.append(args),
        exists_check=lambda t, r: True,
    )

    assert not any(c[:2] == ["release", "upload"] for c in calls)


def test_dry_run_stamps_nothing(tmp_path):
    calls: list[list[str]] = []

    upload_artifacts(
        _stage(tmp_path),
        tag=TAG,
        repo="r/r",
        dry_run=True,
        runner=lambda args: calls.append(args),
        exists_check=lambda t, r: True,
    )

    assert calls == []


def test_sidecars_carry_the_loader_and_a_timestamp(tmp_path):
    seen: dict[str, str] = {}

    def _runner(argv: list[str]) -> None:
        # read inside the runner: the temp dir is cleaned up behind the upload
        path = Path(argv[3])
        if path.name.startswith(("timestamp.", "package_function.")):
            seen[path.name] = path.read_text()

    upload_artifacts(
        _stage(tmp_path),
        tag=TAG,
        repo="r/r",
        runner=_runner,
        exists_check=lambda t, r: True,
    )

    assert seen["package_function.txt"].strip() == PKG_FUNCTION[TAG] == "wehoop::load_wnba_stats_pbp_manifest()"
    assert json.loads(seen["package_function.json"])["package_function"] == PKG_FUNCTION[TAG]
    assert json.loads(seen["timestamp.json"])["last_updated"].strip()


@pytest.mark.parametrize(("tag", "expected"), sorted(PKG_FUNCTION.items()))
def test_every_mapping_reaches_the_sidecar_verbatim(tmp_path, tag, expected):
    """Pin every tag's loader name, not just the one the happy path uses.

    A wrong value here ships to consumers as the canonical way to read the tag,
    so each mapping is asserted on the bytes that actually land.
    """
    seen: dict[str, str] = {}

    def _runner(argv: list[str]) -> None:
        path = Path(argv[3])
        if path.name.startswith(("timestamp.", "package_function.")):
            seen[path.name] = path.read_text()

    upload_artifacts(
        _stage(tmp_path),
        tag=tag,
        repo="r/r",
        runner=_runner,
        exists_check=lambda t, r: True,
    )

    # Exact content, not .strip(): the sidecar IS the published contract. The trailing
    # newline is part of it -- sportsdataverse.release writes pkg_function + \n
    # for parity with R upload.R L62-80 -- so pin it rather than let .strip() hide it.
    assert seen["package_function.txt"] == expected + "\n"
    assert json.loads(seen["package_function.json"])["package_function"] == expected


def test_a_custom_pattern_upload_does_not_stamp_the_data_sidecars(tmp_path):
    """A model card is not a data refresh.

    ``uploaded`` counts every file that went up, including a custom-pattern artifact,
    so an unguarded stamp would move ``timestamp.*`` on a run where no data asset
    changed -- telling consumers the tag refreshed when it did not.
    """
    stage = _stage(tmp_path)
    (Path(stage) / "wnba_player_impact_2025_card.json").write_text("{}", encoding="utf-8")
    calls: list[list[str]] = []

    upload_artifacts(
        stage,
        tag="wnba_player_impact",
        repo="r/r",
        runner=lambda argv: calls.append(argv),
        exists_check=lambda t, r: True,
        pattern="*_card.json",
    )

    uploaded = [Path(c[3]).name for c in calls if c[:2] == ["release", "upload"]]
    assert "wnba_player_impact_2025_card.json" in uploaded
    assert not [n for n in uploaded if n.startswith(("timestamp.", "package_function."))], (
        "a custom-pattern upload must not stamp the data sidecars"
    )
