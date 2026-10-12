"""Release listing hardening + skip-unchanged -- see ``publish._release_digests``.

Offline: a fake runner stands in for ``gh`` so nothing here touches the network.
"""

from __future__ import annotations

import subprocess

import pytest
from wnba_data_build import publish


def _raise(stderr):
    def run(args):
        raise subprocess.CalledProcessError(1, args, stderr=stderr)

    return run


def test_release_digests_parses_name_and_digest():
    out = "a_2025.parquet\tsha256:aa\na_2025.rds\tsha256:bb\n"
    assert publish._release_digests("tag", "repo", lambda args: out) == {
        "a_2025.parquet": "sha256:aa",
        "a_2025.rds": "sha256:bb",
    }


def test_release_digests_none_on_genuine_not_found():
    assert publish._release_digests("tag", "repo", _raise("gh: Not Found (HTTP 404)")) is None


def test_release_digests_raises_loudly_on_other_failure():
    # Regression: a rate-limit / auth / network failure must never be read as
    # "release missing" -- that's the 2026-08-23 incident (fail-open crashed
    # a backfill mid-publish because `gh release create` ran on a live tag).
    with pytest.raises(RuntimeError, match="rate limit"):
        publish._release_digests("tag", "repo", _raise("API rate limit exceeded"))


def _stem(tmp_path, rds=b"r1"):
    for ext, body in (("parquet", b"p"), ("csv", b"c"), ("rds", rds)):
        (tmp_path / f"ld_2026.{ext}").write_bytes(body)


def _runner(remote, calls, fail=()):
    def run(args):
        calls.append(args)
        if args[0] == "api":
            return "".join(f"{k}\t{v}\n" for k, v in remote.items())
        if args[:2] == ["release", "upload"] and args[3].endswith(fail):
            raise subprocess.CalledProcessError(1, args, stderr="boom")
        return ""

    return run


def _uploads(calls):
    return [c[3].rsplit("/", 1)[-1] for c in calls if c[:2] == ["release", "upload"]]


def test_unchanged_stem_is_skipped_whole_despite_rds_timestamp(tmp_path):
    """A matching parquet + siblings present = one listing call, nothing else."""
    _stem(tmp_path, rds=b"r2")  # rds bytes moved (timestamp) but the data did not
    remote = {
        "ld_2026.parquet": publish._sha256(tmp_path / "ld_2026.parquet"),
        "ld_2026.csv": "sha256:x",
        "ld_2026.rds": "sha256:y",
    }
    calls = []
    res = publish.upload_artifacts(
        tmp_path, "t", "r", seasons=[2026], runner=_runner(remote, calls)
    )
    assert [c[0] for c in calls] == ["api"]  # no uploads, no sidecar stamp
    assert res["uploaded"] == 0 and len(res["skipped"]) == 3


def test_changed_parquet_uploads_stem_with_parquet_last(tmp_path):
    _stem(tmp_path)
    remote = {"ld_2026.csv": publish._sha256(tmp_path / "ld_2026.csv")}
    calls = []
    res = publish.upload_artifacts(
        tmp_path, "t", "r", seasons=[2026], runner=_runner(remote, calls)
    )
    assert _uploads(calls)[:2] == ["ld_2026.rds", "ld_2026.parquet"]  # csv matched
    assert res["skipped"] == ["ld_2026.csv"] and res["uploaded"] == 2


def test_failed_sibling_holds_the_parquet_back(tmp_path):
    """Else a later run would see a matching parquet and never retry the rds."""
    _stem(tmp_path)
    calls = []
    res = publish.upload_artifacts(
        tmp_path, "t", "r", seasons=[2026], runner=_runner({}, calls, fail=".rds")
    )
    assert "ld_2026.parquet" not in _uploads(calls)
    assert sorted(res["failed"]) == ["ld_2026.parquet", "ld_2026.rds"]


def test_upload_artifacts_tolerates_create_race(tmp_path):
    # exists() said missing, but the injected runner's create call races
    # against a concurrent creator and gh reports "already exists" -- the
    # publish must continue (log + proceed to upload), not crash.
    f = tmp_path / "roster_2025.parquet"
    f.write_bytes(b"x")
    calls = []

    def runner(args):
        calls.append(args)
        if args[:2] == ["release", "create"]:
            raise subprocess.CalledProcessError(1, args, stderr="already exists")
        return ""

    res = publish.upload_artifacts(
        tmp_path,
        "tag",
        "repo",
        runner=runner,
        exists_check=lambda tag, repo: False,
    )
    assert res["uploaded"] == 1
    assert res["failed"] == []
