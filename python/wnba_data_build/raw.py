"""Reader for the ``wehoop-wnba-stats-raw`` store — the only input this repo has.

Every dataset compiled here is reshaped from payloads that ``wehoop-wnba-stats-raw``
already captured, so a compile makes **no network calls** and is reproducible from a
checkout. That is what makes the builders testable: point ``root`` at a fixture tree
and the whole pipeline runs offline.

The store has two layouts, because the endpoints are keyed differently:

``{endpoint}/{season}/{game_id}.json``
    Per-game payloads (``playbyplayv3``, ``boxscoretraditionalv3``, ``gamerotation``,
    ``boxscoresummaryv2``). The season directory is decoded from the game id by
    :func:`season_of`. The writer decodes it independently, inside sdv-py's raw
    store, so the two could drift apart and silently look at different directories
    — ``test_raw.py`` pins them equal across every game id in the real store.

``{endpoint}/{season}/{variant}.json`` or ``{endpoint}/{season}.json``
    Season-level payloads (rosters, season stats, lineups, standings, draft, and the
    ``leaguegamelog`` game index), written by the raw repo's ``season_capture``.

``root`` may be a local checkout or the ``raw.githubusercontent.com`` base URL, so a
job can run against a sibling clone on disk or read the tree straight from GitHub.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterator
from pathlib import Path
from typing import Any

RAW_BASE = (
    "https://raw.githubusercontent.com/sportsdataverse/wehoop-wnba-stats-raw/main/wnba_stats/json"
)

# Per-game endpoints live under the game-keyed store; season-level ones do not.
GAME_ENDPOINTS = (
    "playbyplayv3",
    "boxscoretraditionalv3",
    "gamerotation",
    "boxscoresummaryv2",
)


# ``Path("https://x")`` collapses the ``//`` after the scheme (``https:/x`` on POSIX,
# ``https:\x`` on Windows). The CLI wraps ``--root`` in ``Path``, so a URL root arrived
# here mangled, failed the ``startswith("https://")`` test, and was read as a local
# directory that does not exist -- every family "skipped: no rows" and the run was
# green. Accept the mangled form and repair it at the one place URLs are built.
_URL_SCHEME = re.compile(r"^(https?):[\\/]+")


def _is_url(root: str | Path) -> bool:
    return bool(_URL_SCHEME.match(str(root)))


def _url_base(root: str | Path) -> str:
    """``scheme://host/path`` with no trailing slash, whether ``root`` is a str or a Path."""
    return _URL_SCHEME.sub(r"\1://", str(root)).replace("\\", "/").rstrip("/")


#: The only origins that ever receive the token. ``root`` is caller-supplied, so a
#: typo'd or hostile root must not be handed a credential.
_GITHUB_AUTH_HOSTS = frozenset({"raw.githubusercontent.com", "api.github.com"})


def _auth_headers(url: str) -> dict[str, str]:
    """``Authorization`` for ``url`` -- empty unless it is an HTTPS GitHub endpoint.

    ``wehoop-wnba-stats-raw`` was PRIVATE until 2026-09-02, and the raw host answers
    an unauthenticated read with 404 -- indistinguishable from "never captured", so
    the daily workflow (which exports both tokens but never sent them) read every
    family as empty. The repo is public now, so the token is no longer required to
    read it; keep sending it anyway. It costs nothing, it lifts the contents-API
    listing quota from 60/hour to 5,000, and it means the reader does not silently
    break again if the repo is ever made private. Either name the runner sets works.

    The scheme + host test keeps the token off any other destination: plaintext HTTP
    would put it on the wire, and a non-GitHub host has no business receiving it.
    """
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https" or parts.hostname not in _GITHUB_AUTH_HOSTS:
        return {}
    tok = os.environ.get("GITHUB_PAT") or os.environ.get("GH_TOKEN") or ""
    return {"Authorization": f"token {tok}"} if tok else {}


class _StripAuthOnCrossHostRedirect(urllib.request.HTTPRedirectHandler):
    """Drop ``Authorization`` when a redirect leaves the host it was minted for.

    urllib copies request headers onto the redirected request, so without this a
    302 to another origin would forward the token to whoever served the redirect.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        new = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new is not None and (
            urllib.parse.urlsplit(newurl).hostname != urllib.parse.urlsplit(req.full_url).hostname
        ):
            new.headers.pop("Authorization", None)
            new.unredirected_hdrs.pop("Authorization", None)
        return new


_OPENER = urllib.request.build_opener(_StripAuthOnCrossHostRedirect)


def _urlopen(req: urllib.request.Request, timeout: int = 60) -> Any:
    """Single HTTP seam: redirect-safe opener, and the one place tests patch."""
    return _OPENER.open(req, timeout=timeout)


def _http_retries() -> int:
    """Transient-error attempts beyond the first. ``SDV_PY_HTTP_RETRIES`` bounds it."""
    try:
        return max(0, int(os.environ.get("SDV_PY_HTTP_RETRIES", "3")))
    except ValueError:
        return 3


def _get_json(url: str, extra_headers: dict[str, str] | None = None) -> Any | None:
    """GET ``url`` as JSON. ``None`` ONLY for a genuine 404/410; transients RAISE.

    The one HTTP policy for this module, shared by the payload reader and the
    contents-API listing so they cannot drift apart.

    Absence and failure must stay distinguishable. A 404 means the store never
    captured this file. Everything else — 5xx, a 403 rate-limit from the contents
    API, a dropped connection, a timeout — is TRANSIENT, and mapping it to
    "absent" is how a build silently publishes a short season on a green run: a
    single season reads ~1,800 files, so one blip is one missing game nobody sees.
    Both call sites used to swallow exactly these. Retry with backoff, then raise;
    a failed build is recoverable, a quietly-truncated release is not.

    ``SDV_PY_HTTP_RETRIES`` bounds the attempts (CI wants a small number: the
    default 15x30s retry budget elsewhere in SDV is a hang, not resilience).
    """
    attempts = _http_retries() + 1
    for attempt in range(1, attempts + 1):
        try:
            headers = {**_auth_headers(url), **(extra_headers or {})}
            with _urlopen(urllib.request.Request(url, headers=headers)) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            if exc.code in (404, 410):
                return None  # never captured; retrying cannot change the answer
            if attempt == attempts:
                raise
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            if attempt == attempts:
                raise
        time.sleep(min(2 ** (attempt - 1), 8))
    return None


def _read_json(root: str | Path, rel: str) -> Any | None:
    """Load ``rel`` under ``root`` from disk or over HTTP; ``None`` when absent."""
    if _is_url(root):
        return _get_json(f"{_url_base(root)}/{rel}")
    path = Path(root) / rel
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def season_of(game_id: str) -> int:
    """Season (single calendar year) encoded in a 10-digit WNBA game id.

    ``1022600071`` -> 2026. Digits 3-4 are the two-digit year behind the ``10``
    league prefix and the season-type digit; years >= 90 are 19xx (the league
    started in 1997).
    """
    gid = str(game_id).zfill(10)
    yy = int(gid[3:5])
    return 1900 + yy if yy >= 90 else 2000 + yy


def game_payload_path(root: str | Path, endpoint: str, game_id: str) -> Path:
    """On-disk path of a per-game payload (local roots only)."""
    return Path(root) / endpoint / str(season_of(game_id)) / f"{str(game_id).zfill(10)}.json"


def read_game(root: str | Path, endpoint: str, game_id: str) -> Any | None:
    """One per-game payload, or ``None`` if the raw store never captured it."""
    gid = str(game_id).zfill(10)
    return _read_json(root, f"{endpoint}/{season_of(gid)}/{gid}.json")


def read_season(
    root: str | Path, endpoint: str, season: int, variant: str | None = None
) -> Any | None:
    """One season-level payload, or ``None`` if absent.

    ``variant`` matches the raw repo's slug (``advanced_playoffs``, ``regular-season``,
    a team id for ``commonteamroster``); omit it for unparameterized endpoints.
    """
    rel = f"{endpoint}/{season}/{variant}.json" if variant else f"{endpoint}/{season}.json"
    return _read_json(root, rel)


def available_games(root: str | Path, endpoint: str, season: int) -> list[str]:
    """Game ids captured for ``endpoint`` in ``season`` (local roots only).

    Enumerating a URL root is not supported — GitHub serves files, not listings —
    so callers working against RAW_BASE should drive from :func:`season_game_ids`.
    """
    if _is_url(root):
        raise ValueError("available_games needs a local root; use season_game_ids for URLs")
    d = Path(root) / endpoint / str(season)
    if not d.is_dir():
        return []
    return sorted(p.stem for p in d.glob("*.json"))


def season_game_ids(root: str | Path, season: int) -> list[str]:
    """Every game id for ``season`` from the captured ``leaguegamelog`` payloads.

    This is the authoritative index — it covers games whose per-game payloads have
    not been captured yet, which :func:`available_games` by definition cannot.
    """
    out: set[str] = set()
    for stype in ("regular-season", "playoffs"):
        payload = read_season(root, "leaguegamelog", season, stype)
        if not isinstance(payload, dict):
            continue
        for rs in payload.get("resultSets") or []:
            headers = [str(h).upper() for h in rs.get("headers") or []]
            if "GAME_ID" not in headers:
                continue
            idx = headers.index("GAME_ID")
            for row in rs.get("rowSet") or []:
                if row[idx] is not None:
                    out.add(str(row[idx]).zfill(10))
    return sorted(out)


_RAW_GITHUB = re.compile(r"^https://raw\.githubusercontent\.com/([^/]+)/([^/]+)/([^/]+)/(.+)$")


def season_variants(root: str | Path, endpoint: str, season: int) -> list[str]:
    """Variant stems captured under ``{endpoint}/{season}/`` (``regular-season``,
    ``advanced_playoffs``, a team id for ``commonteamroster``).

    A local root globs the directory. raw.githubusercontent.com serves files, not
    listings, so a raw-GitHub root asks the contents API for the same directory with
    the same token; any other URL host yields ``[]``.
    """
    if not _is_url(root):
        d = Path(root) / endpoint / str(season)
        return sorted(p.stem for p in d.glob("*.json")) if d.is_dir() else []
    m = _RAW_GITHUB.match(_url_base(root))
    if not m:
        return []
    owner, repo, ref, path = m.groups()
    api = (
        f"https://api.github.com/repos/{owner}/{repo}/contents/{path}/{endpoint}/{season}?ref={ref}"
    )
    # _get_json, not a bare try/except: a 403 rate-limit or a 5xx here used to
    # return [] -- "this season has no variants" -- and every leaguedash/standings
    # family then built zero rows on a green run. Only a real 404 is absence.
    listing = _get_json(api, {"Accept": "application/vnd.github+json"})
    if not isinstance(listing, list):
        return []
    names = (str(e.get("name", "")) for e in listing if isinstance(e, dict))
    return sorted(n[:-5] for n in names if n.endswith(".json"))


def iter_game_payloads(
    root: str | Path, endpoint: str, game_ids: list[str]
) -> Iterator[tuple[str, Any]]:
    """Yield ``(game_id, payload)`` for each captured game, skipping misses.

    A generator so a season compiles without holding every payload at once — a
    season of play-by-play is hundreds of MB of JSON.
    """
    for gid in game_ids:
        payload = read_game(root, endpoint, gid)
        if payload is not None:
            yield gid, payload


def result_set(payload: Any, name: str | None = None) -> tuple[list[str], list[list[Any]]]:
    """``(headers, rows)`` from a stats.com ``resultSets`` envelope.

    Returns the named set, or the first non-empty one when ``name`` is omitted.
    Empty/malformed payloads give ``([], [])`` rather than raising, so callers can
    build a zero-row frame with the documented schema instead of null-checking.
    """
    if not isinstance(payload, dict):
        return [], []
    sets = payload.get("resultSets") or payload.get("resultSet") or []
    if isinstance(sets, dict):
        sets = [sets]
    for rs in sets:
        if not isinstance(rs, dict):
            continue
        if name is not None and str(rs.get("name")) != name:
            continue
        headers = [str(h) for h in rs.get("headers") or []]
        rows = [list(r) for r in rs.get("rowSet") or []]
        if name is not None or rows:
            return headers, rows
    return [], []
