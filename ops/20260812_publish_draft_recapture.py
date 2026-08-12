#!/usr/bin/env python
"""One-off publish: push the rebuilt `draft` artifacts onto `wnba_stats_draft`.

Dated one-off. The daily/annual flow publishes through
``python -m wnba_data_build --publish``, whose ``upload_artifacts`` is
deliberately best-effort -- one failed file is logged and the rest still go. That
is right for an ADDITIVE season top-up, and wrong here: this publish OVERWRITES
assets that are already serving data, so a half-verified run would leave the tag
in a state nobody can name.

So it reuses the cutover protocol instead of the daily one
(``v3_cutover.upload_one`` / ``remote_assets``): write a REPLACE MANIFEST naming
every asset that would be overwritten with its current remote size and
updated-at BEFORE touching anything, then upload per-file, re-fetch each asset,
verify it, and stop on the first mismatch. ``verify_download=True`` -- these are
small files, so the exact sha256 round-trip is affordable and the release API
exposes no digest to check against otherwise. Verified uploads are recorded as
receipts, so a re-run after a stop resumes rather than re-uploading.

**What it is repairing.** ``drafthistory`` captures were 30 byte-identical copies
of one unfiltered payload (sdv-py #362), so ``draft_2026`` was published as 1,201
rows -- the entire 1997-2025 draft history stamped ``season=2026`` -- while the
real 45-pick 2026 class was absent from the tag entirely.

Run from the repo root, after building into ``build_out_draft/``::

    ./.venv/Scripts/python.exe ops/20260812_publish_draft_recapture.py            # manifest only
    ./.venv/Scripts/python.exe ops/20260812_publish_draft_recapture.py --publish
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ARTIFACTS = REPO / "build_out_draft" / "wnba_stats_draft"
TAG = "wnba_stats_draft"
GH_REPO = "sportsdataverse/sportsdataverse-data"

sys.path.insert(0, str(REPO / "python"))

from wnba_data_build.v3_cutover import (  # noqa: E402
    load_receipts,
    remote_assets,
    sha256_file,
    upload_one,
)


def _log(msg: str) -> None:
    print(f"[{datetime.now(timezone.utc).strftime('%F %T')}Z] {msg}", flush=True)


def _rows() -> list[dict]:
    """One upload row per local artifact, in the shape ``upload_one`` expects."""
    files = sorted(p for p in ARTIFACTS.iterdir() if p.is_file())
    if not files:
        raise SystemExit(f"FAIL: no artifacts under {ARTIFACTS}")
    return [
        {
            "tag": TAG,
            "asset": p.name,
            "path": p,
            "key": f"{TAG}/{p.name}",
            "size": p.stat().st_size,
            "sha256": sha256_file(p),
        }
        for p in files
    ]


def _manifest(rows: list[dict], remote: dict) -> str:
    """The REPLACE MANIFEST -- what an upload would overwrite, before it happens."""
    replace = [r for r in rows if r["asset"] in remote]
    add = [r for r in rows if r["asset"] not in remote]
    orphan = sorted(set(remote) - {r["asset"] for r in rows})

    out = [
        f"# REPLACE MANIFEST -- {TAG} @ {GH_REPO}",
        f"_generated {datetime.now(timezone.utc).strftime('%F %T')}Z_",
        "",
        f"{len(replace)} asset(s) OVERWRITTEN, {len(add)} added, {len(orphan)} left untouched.",
        "",
        "## OVERWRITE (existing assets destroyed)",
        "",
        "| asset | remote size | remote updatedAt | -> local size |",
        "|---|--:|---|--:|",
    ]
    out += [
        f"| `{r['asset']}` | {remote[r['asset']]['size']} |"
        f" {remote[r['asset']]['updatedAt']} | {r['size']} |"
        for r in replace
    ]
    out += ["", "## ADD (new assets)", ""]
    out += [f"- `{r['asset']}` ({r['size']} bytes)" for r in add] or ["- (none)"]
    out += ["", "## UNTOUCHED (already on the tag, not in this build)", ""]
    out += [f"- `{a}`" for a in orphan] or ["- (none)"]
    return "\n".join(out) + "\n"


def main(argv: list[str]) -> int:
    rows = _rows()
    remote = remote_assets(TAG, GH_REPO)
    manifest = _manifest(rows, remote)

    (REPO / "logs").mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = REPO / "logs" / f"draft_replace_manifest_{stamp}.md"
    path.write_text(manifest, encoding="utf-8")
    _log(f"manifest -> {path}")
    print(manifest)

    if "--publish" not in argv:
        _log("manifest only; pass --publish to upload. Nothing was touched.")
        return 0

    done = load_receipts(REPO)
    todo = [r for r in rows if done.get(r["key"], {}).get("sha256") != r["sha256"]]
    _log(f"uploading {len(todo)} of {len(rows)} assets ({len(rows) - len(todo)} already verified)")
    for i, row in enumerate(todo, 1):
        # No try/except: a verification failure must stop the run with everything
        # after it un-uploaded, not be logged and skipped past.
        upload_one(row, GH_REPO, REPO, verify_download=True)
        _log(f"  [{i}/{len(todo)}] {row['asset']} verified ({row['size']} bytes)")

    after = remote_assets(TAG, GH_REPO)
    missing = [r["asset"] for r in rows if r["asset"] not in after]
    bad = [
        r["asset"] for r in rows if r["asset"] in after and after[r["asset"]]["size"] != r["size"]
    ]
    if missing or bad:
        raise SystemExit(f"FAIL: post-publish sweep -- missing={missing} size-mismatch={bad}")
    _log(f"OK: {len(rows)} assets on {TAG}, every one size-verified against its local build")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
