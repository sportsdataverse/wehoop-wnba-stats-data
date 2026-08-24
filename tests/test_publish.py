"""Release-exists hardening -- see ``publish._gh_release_exists`` for the incident.

Offline: ``subprocess.run`` is monkeypatched so nothing here touches ``gh`` or
the network.
"""

from __future__ import annotations

import subprocess

import pytest
from wnba_data_build import publish


def test_gh_release_exists_true_on_zero_exit(monkeypatch):
    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(publish.subprocess, "run", fake_run)
    assert publish._gh_release_exists("tag", "repo") is True


def test_gh_release_exists_false_on_genuine_not_found(monkeypatch):
    def fake_run(*args, **kwargs):
        raise subprocess.CalledProcessError(1, args, stderr="release not found")

    monkeypatch.setattr(publish.subprocess, "run", fake_run)
    assert publish._gh_release_exists("tag", "repo") is False


def test_gh_release_exists_raises_loudly_on_other_failure(monkeypatch):
    # Regression: a rate-limit / auth / network failure must never be read as
    # "release missing" -- that's the 2026-08-23 incident (fail-open crashed
    # a backfill mid-publish because `gh release create` ran on a live tag).
    def fake_run(*args, **kwargs):
        raise subprocess.CalledProcessError(1, args, stderr="API rate limit exceeded")

    monkeypatch.setattr(publish.subprocess, "run", fake_run)
    with pytest.raises(RuntimeError, match="rate limit"):
        publish._gh_release_exists("tag", "repo")


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
