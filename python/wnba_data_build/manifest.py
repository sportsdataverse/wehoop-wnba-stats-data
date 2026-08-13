"""The per-tag ``<tag>_in_data_repo.csv`` manifest: build it, and check it agrees.

wehoop's ``load_wnba_stats_*_manifest()`` reads this CSV to answer "which seasons
does this tag publish?" without downloading a single season payload. Its columns
are fixed by that contract: ``season``, ``row_count``, ``generated_at_utc``,
``source_endpoint``.

Why this module exists
----------------------
Nothing on the Python side wrote it. The manifest was emitted by the R creation
chain (``R/manifest_upload_helper.R`` -> ``sportsdataversedata::sportsdataverse_save``),
and :func:`~wnba_data_build.publish.upload_artifacts` — which is what every Python
build and backfill publishes through — uploads season assets and stops. So a
Python-side backfill could put 30 seasons on a tag and leave the manifest frozen
at whatever the last R run wrote, understating coverage by decades with no signal.
That is exactly what happened: seven tags carried full history behind a one-row
manifest dated 2026-05-30.

Publishing stays a deliberate module invocation — this module does not bolt a
write onto the publish path. Instead :func:`check_tag` makes the disagreement
*detectable*: the CLIs run it after they upload, so a stale manifest is a loud
failure rather than a silent one.

Rows are derived from what is ACTUALLY on the release — the asset list, each
parquet's footer, and GitHub's own ``updatedAt`` — never from a local build
directory, which can be stale or partial in either direction.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

import polars as pl

from .datasets import RELEASE_TAGS
from .publish import _SEASON_RE, Runner, _gh_runner, upload_artifacts

_REPO = "sportsdataverse/sportsdataverse-data"
_DOWNLOAD = "https://github.com/{repo}/releases/download/{tag}/{asset}"

#: Column contract read by wehoop's ``load_wnba_stats_*_manifest()``. Order matters.
MANIFEST_COLUMNS: tuple[str, ...] = ("season", "row_count", "generated_at_utc", "source_endpoint")

#: Every tag this repo publishes to. ``leaguedash`` is not in ``DATASETS`` (it has
#: its own builder + CLI) but it is a published tag and needs the same guarantee.
ALL_TAGS: tuple[str, ...] = RELEASE_TAGS + ("wnba_stats_leaguedash",)

#: ``source_endpoint`` for a tag that has no manifest yet to inherit it from. Only
#: leaguedash is in this position; every other tag's value is preserved verbatim
#: from the manifest already on the release, so a rebuild never invents provenance.
_NEW_TAG_ENDPOINTS: dict[str, str] = {
    # 24 per-season tables under one tag; row_count is the season total across them.
    "wnba_stats_leaguedash": "stats.wnba.com/leaguedash* (24 tables per season)",
}


def manifest_asset(tag: str) -> str:
    """Asset name of *tag*'s manifest CSV."""
    return f"{tag}_in_data_repo.csv"


def _asset_url(tag: str, asset: str, repo: str) -> str:
    return _DOWNLOAD.format(repo=repo, tag=tag, asset=asset)


def release_assets(
    tag: str, repo: str, *, runner: Optional[Runner] = None
) -> list[tuple[str, str]]:
    """``(name, updated_at)`` for every asset on *tag*; empty list if no such release.

    Mirrors :func:`~wnba_data_build.publish.published_seasons`' failure policy: a
    missing release is an empty result, but any other ``gh`` failure (auth, rate
    limit) is raised rather than mistaken for "nothing published".
    """
    import subprocess

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
                ".assets[] | [.name, .updatedAt] | @tsv",
            ]
        )
    except subprocess.CalledProcessError as exc:
        if "not found" in (exc.stderr or "").lower():
            return []
        raise
    rows = []
    for line in (out or "").splitlines():
        name, _, updated = line.partition("\t")
        if name:
            rows.append((name, updated))
    return rows


def season_assets(
    tag: str, repo: str, *, runner: Optional[Runner] = None
) -> dict[int, list[tuple[str, str]]]:
    """Parquet assets on *tag*, grouped by the season parsed out of the filename.

    Parquet is the anchor because it is the one format every season ships (rds/csv
    coverage is uneven), so a season is counted once and not once per format. A tag
    with several tables per season (leaguedash) simply yields several entries.
    """
    grouped: dict[int, list[tuple[str, str]]] = {}
    for name, updated in release_assets(tag, repo, runner=runner):
        m = _SEASON_RE.search(name)
        if m:
            grouped.setdefault(int(m.group(1)), []).append((name, updated))
    return grouped


def read_manifest(tag: str, repo: str) -> Optional[pl.DataFrame]:
    """The manifest currently on *tag*, or None when the tag has no manifest asset.

    ``releases/download/`` is CDN-cached and can serve the previous body for a
    minute or so after an upload — verified during the 2026-08-13 refresh, where
    two freshly-clobbered manifests read back at their old size while the release
    API already reported the new one. Confirm a just-uploaded manifest against
    ``gh release view --json assets`` (size/updatedAt), not this reader.
    """
    try:
        return pl.read_csv(_asset_url(tag, manifest_asset(tag), repo))
    except Exception:
        return None


def manifest_seasons(tag: str, repo: str) -> Optional[set[int]]:
    """Season set the published manifest declares, or None when there is no manifest."""
    df = read_manifest(tag, repo)
    if df is None or "season" not in df.columns:
        return None
    return set(df.get_column("season").cast(pl.Int64).to_list())


def check_tag(tag: str, repo: str, *, runner: Optional[Runner] = None) -> Optional[str]:
    """None when *tag*'s manifest season-set equals its asset-derived season-set.

    Otherwise a one-line description of the disagreement. Set equality is the
    assertion — a matching row *count* would pass while naming the wrong seasons.
    """
    assets = set(season_assets(tag, repo, runner=runner))
    if not assets:
        return None  # nothing published under this tag; nothing to be stale about
    declared = manifest_seasons(tag, repo)
    if declared is None:
        return f"{tag}: {len(assets)} season(s) published but NO manifest asset"
    if declared == assets:
        return None
    missing = sorted(assets - declared)
    extra = sorted(declared - assets)
    parts = [f"{tag}: manifest declares {len(declared)} season(s), assets carry {len(assets)}"]
    if missing:
        parts.append(f"published but unlisted: {missing}")
    if extra:
        parts.append(f"listed but not published: {extra}")
    return "; ".join(parts)


def check_tags(tags, repo: str, *, runner: Optional[Runner] = None) -> list[str]:
    """Every disagreement across *tags* (empty list = all agree)."""
    return [msg for tag in tags if (msg := check_tag(tag, repo, runner=runner)) is not None]


def build_manifest(
    tag: str,
    repo: str,
    *,
    source_endpoint: Optional[str] = None,
    runner: Optional[Runner] = None,
) -> pl.DataFrame:
    """Rebuild *tag*'s manifest from the live release.

    ``row_count`` comes from each parquet's footer (``scan_parquet`` reads metadata
    only — no payload download) summed over the season's assets, and
    ``generated_at_utc`` from GitHub's own newest ``updatedAt`` for that season, so
    both describe the published bytes rather than a local build.

    ``source_endpoint`` defaults to the value already published for this tag —
    provenance is preserved, never re-derived. A tag with no manifest to inherit
    from must be given one (see ``_NEW_TAG_ENDPOINTS``).
    """
    if source_endpoint is None:
        prior = read_manifest(tag, repo)
        if prior is not None and "source_endpoint" in prior.columns and prior.height > 0:
            source_endpoint = str(prior.get_column("source_endpoint")[0])
        else:
            source_endpoint = _NEW_TAG_ENDPOINTS.get(tag)
        if source_endpoint is None:
            raise SystemExit(
                f"{tag}: no published manifest to inherit source_endpoint from; "
                "pass --source-endpoint"
            )

    grouped = season_assets(tag, repo, runner=runner)
    if not grouped:
        raise SystemExit(f"{tag}: no season parquet assets on the release; refusing to write")

    rows = []
    for season in sorted(grouped):
        assets = grouped[season]
        total = 0
        for name, _ in assets:
            total += pl.scan_parquet(_asset_url(tag, name, repo)).select(pl.len()).collect().item()
        rows.append(
            {
                "season": season,
                "row_count": total,
                "generated_at_utc": max(updated for _, updated in assets),
                "source_endpoint": source_endpoint,
            }
        )
    return pl.DataFrame(rows).select(MANIFEST_COLUMNS)


def write_manifest(df: pl.DataFrame, out_dir: Path, tag: str) -> Path:
    """Write *df* as *tag*'s manifest CSV under *out_dir*, returning the path."""
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / manifest_asset(tag)
    df.write_csv(path)
    return path


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="wnba_data_build.manifest")
    ap.add_argument(
        "action",
        choices=("check", "build"),
        help="check: fail if any tag's manifest disagrees with its assets. "
        "build: regenerate the manifest CSV from the live release.",
    )
    ap.add_argument("--tags", nargs="+", default=list(ALL_TAGS), help="tags to act on")
    ap.add_argument("--repo", default=_REPO, help="release repo")
    ap.add_argument("--out", default="build_out", help="where build writes the CSVs")
    ap.add_argument(
        "--source-endpoint",
        default=None,
        help="override the inherited source_endpoint (build only; one tag at a time)",
    )
    ap.add_argument(
        "--publish",
        action="store_true",
        help="upload the rebuilt manifest CSV — and nothing else — to its tag",
    )
    return ap


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    if args.action == "check":
        problems = check_tags(args.tags, args.repo)
        for msg in problems:
            print(f"MANIFEST DRIFT: {msg}", file=sys.stderr)
        if problems:
            print(
                f"{len(problems)} tag(s) disagree. Rebuild with: "
                "python -m wnba_data_build.manifest build --tags <tag> --publish",
                file=sys.stderr,
            )
            return 1
        print(f"manifest OK: {len(args.tags)} tag(s) agree with their published assets")
        return 0

    if args.source_endpoint is not None and len(args.tags) != 1:
        raise SystemExit("--source-endpoint applies to a single --tags value")

    for tag in args.tags:
        df = build_manifest(tag, args.repo, source_endpoint=args.source_endpoint)
        path = write_manifest(df, Path(args.out) / tag, tag)
        print(f"built {tag}: {df.height} season(s) -> {path}")
        if args.publish:
            # pattern= mode uploads exactly this one CSV; season assets are untouched.
            result = upload_artifacts(path.parent, tag, args.repo, pattern=manifest_asset(tag))
            print(f"publish {tag}: {result}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
