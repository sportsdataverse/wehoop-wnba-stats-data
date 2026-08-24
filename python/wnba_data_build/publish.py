"""Publish built parquet to sportsdataverse-data GitHub releases (gh CLI).

Ported verbatim from hoopR-nba-stats-data's ``nba_data_build/publish.py`` —
this module is fully tag/repo-agnostic (no NBA/WNBA specifics).
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import Callable, Iterable, Optional

_GH_TIMEOUT = 600
# Every released dataset ships all three formats to the tag.
_RELEASE_EXTS: tuple[str, ...] = ("parquet", "rds", "csv")

# Season detection stays anchored on the canonical parquet so a season is counted
# once, not once per format.
_SEASON_RE = re.compile(r"_(\d{4})\.parquet$")

Runner = Callable[[list[str]], str]
ExistsCheck = Callable[[str, str], bool]


def _gh_runner(args: list[str]) -> str:
    """Run `gh <args>`, returning stdout. Raises on non-zero."""
    return subprocess.run(
        ["gh", *args], check=True, capture_output=True, text=True, timeout=_GH_TIMEOUT
    ).stdout


def _gh_release_exists(tag: str, repo: str) -> bool:
    """True when ``tag`` exists on ``repo``.

    Only a genuine "not found" answer from ``gh`` counts as absence -- a rate
    limit / auth / network failure must never be read as "release missing"
    (that misreading is what makes the caller run ``release create`` on a tag
    that already exists and crash the whole publish run, as happened during a
    GitHub GraphQL rate-limit window on 2026-08-23).
    """
    try:
        subprocess.run(
            ["gh", "release", "view", tag, "--repo", repo],
            check=True,
            capture_output=True,
            text=True,
            timeout=_GH_TIMEOUT,
        )
        return True
    except subprocess.CalledProcessError as exc:
        # subprocess.TimeoutExpired is intentionally NOT caught here — a spurious
        # False would trigger a `gh release create` that then fails because the
        # release already exists.
        stderr = (exc.stderr or "").strip()
        if "not found" in stderr.lower():
            return False
        raise RuntimeError(f"gh release view {tag} --repo {repo} failed: {stderr}") from exc


def _publishable(path: Path) -> bool:
    """False for staging leftovers that must never reach a release.

    Writers stage to a dotfile ``.{stem}.{ext}.{hash}.partial`` and rename. A
    failed rename (Windows AV/indexer lock) strands that file in the directory
    this function globs, where its truncated bytes would upload under a
    plausible name. Suffix and dot-prefix are both checked because a custom
    ``pattern`` can reach names the extension globs would not.
    """
    return not path.name.startswith(".") and not path.name.endswith(".partial")


def plan_uploads(
    artifacts_dir: Path,
    seasons: Optional[Iterable[int]] = None,
    *,
    pattern: str = "*.parquet",
    exts: tuple[str, ...] = _RELEASE_EXTS,
) -> list[Path]:
    """Return the files under *artifacts_dir* to upload (sorted).

    Two selection modes (backported from hoopR-nba-stats-data's publish.py):

    * default (``pattern="*.parquet"``): glob each extension in *exts* and,
      when *seasons* is given, keep only files ending in ``_{season}.{ext}``
      for one of those seasons. *exts* defaults to all three release formats
      — the release is the distribution channel (rds/csv are not committed to
      this repo) and ``wehoop::load_wnba_stats_*()`` reads the ``.rds``.
      Season scoping avoids re-uploading the whole backfill-to-date on every
      single-season call (O(n^2) across a multi-season backfill).
    * custom *pattern* (e.g. a model-card ``*_card.json`` sidecar): returned
      unscoped, *exts* ignored.
    """
    if pattern != "*.parquet":
        return sorted(f for f in Path(artifacts_dir).glob(pattern) if _publishable(f))
    files = sorted(
        f for ext in exts for f in Path(artifacts_dir).glob(f"*.{ext}") if _publishable(f)
    )
    if seasons is None:
        return files
    suffixes = tuple(f"_{s}.{ext}" for s in seasons for ext in exts)
    return [f for f in files if f.name.endswith(suffixes)]


def published_seasons(tag: str, repo: str, *, runner: Optional[Runner] = None) -> set[int]:
    """Season start-years already on the release, parsed from `_{season}.parquet` asset names.

    Returns an empty set if the release does not exist.
    """
    run = runner or _gh_runner
    try:
        out = run(
            [
                "release",
                "view",
                tag,
                "--repo",
                repo,
                "--json",
                "assets",
                "--jq",
                ".assets[].name",
            ]
        )
    except subprocess.CalledProcessError as exc:
        # A missing release is expected on the first run -> empty set. Any OTHER gh
        # failure (auth, permission, rate limit) must surface, not masquerade as
        # "nothing published" (which would trigger a full, multi-hour recompile).
        stderr = (exc.stderr or "").lower()
        if "not found" in stderr:
            return set()
        raise
    return {int(m.group(1)) for line in (out or "").splitlines() if (m := _SEASON_RE.search(line))}


def upload_artifacts(
    artifacts_dir: Path,
    tag: str,
    repo: str,
    *,
    seasons: Optional[Iterable[int]] = None,
    pattern: str = "*.parquet",
    exts: tuple[str, ...] = _RELEASE_EXTS,
    notes: Optional[str] = None,
    dry_run: bool = False,
    runner: Optional[Runner] = None,
    exists_check: Optional[ExistsCheck] = None,
) -> dict[str, object]:
    """Upload each parquet under *artifacts_dir* to release *tag* on *repo* (creating it if needed).

    ``seasons`` scopes the upload set (see :func:`plan_uploads`) -- pass the
    seasons this invocation actually built, not the whole directory. Each
    file uploads best-effort: one failed ``gh release upload`` is logged and
    skipped rather than aborting every file still queued behind it.

    ``runner`` (default: real `gh` subprocess) and ``exists_check`` are injectable for tests.

    Returns:
        dict with keys:
            ``uploaded``: int count of files uploaded (0 if *dry_run* is True).
            ``failed``: list of asset filenames whose upload raised.
            ``files``: list of asset filenames that were (or would be) uploaded.
    """
    run = runner or _gh_runner
    exists = exists_check or _gh_release_exists
    files = plan_uploads(artifacts_dir, seasons, pattern=pattern, exts=exts)
    if dry_run:
        return {"uploaded": 0, "failed": [], "files": [f.name for f in files]}
    if not exists(tag, repo):
        try:
            run(
                [
                    "release",
                    "create",
                    tag,
                    "--repo",
                    repo,
                    "--title",
                    tag,
                    "--notes",
                    notes or f"{tag} datasets (WNBA model zoo)",
                ]
            )
        except subprocess.CalledProcessError as exc:
            # Belt-and-suspenders for the race exists() didn't catch (e.g. a
            # concurrent run created the tag between the check and here).
            stderr = (exc.stderr or "").lower() if isinstance(exc.stderr, str) else ""
            if "already exists" in stderr:
                print(f"release {tag} already exists on {repo} -- continuing", file=sys.stderr)
            else:
                raise
    uploaded: list[str] = []
    failed: list[str] = []
    for f in files:
        try:
            run(["release", "upload", tag, str(f), "--repo", repo, "--clobber"])
            uploaded.append(f.name)
        except subprocess.CalledProcessError as exc:
            print(f"WARNING: upload failed for {f.name}: {exc}", file=sys.stderr)
            failed.append(f.name)
    return {
        "uploaded": len(uploaded),
        "failed": failed,
        "files": [f.name for f in files],
    }
