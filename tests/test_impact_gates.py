"""Publish floors + the SPM coefficient sidecar (hermetic — no network, no model compute).

Diff-ported from the NBA twin minus the oracle family, which this league does
not have (see ``wnba_model_publish/gates.py``). Player counts here mirror the
WNBA's real scale (~160 rated players a season, not ~500), so a fixture that
silently assumed NBA-sized samples would not pass unnoticed.

The floors themselves were derived from the real published release (see
``wnba_model_publish/gates.py``); these tests pin the MACHINERY: a degraded
build fails, an uncomputable metric is SKIPPED rather than PASS, and the
gate blocks the publish path instead of merely printing.
"""

from __future__ import annotations

import json

import numpy as np
import polars as pl
import pytest
from wnba_model_publish import gates as G
from wnba_model_publish.builders import SPM_SIDECAR_NAME, write_spm_coefficients

_SKILL = np.random.default_rng(11).normal(0, 2.0, 160)


def _season(season: int, *, noise: float = 0.25, seed: int = 0) -> pl.DataFrame:
    """A WNBA-sized season whose engines agree strongly and whose players persist.

    One shared latent skill vector across seasons is what makes the forward
    gates (RAPM year-over-year, DARKO forward) computable at all — regenerating
    skill per season would model a league of strangers.
    """
    n = len(_SKILL)
    rng = np.random.default_rng(seed + season)

    def jit(scale):
        return _SKILL + rng.normal(0, scale, n)

    return pl.DataFrame(
        {
            "player_id": pl.Series(np.arange(1, n + 1), dtype=pl.Int64),
            "season": pl.Series([season] * n, dtype=pl.Int64),
            "season_type": ["Regular Season"] * n,
            "rapm": jit(noise),
            "adj_rapm": jit(noise),
            "spm": jit(noise),
            "darko_projected_rating": jit(noise),
            "min": rng.uniform(200, 2500, n),
        }
    )


def _frames(seasons=(2024, 2025)) -> dict[int, pl.DataFrame]:
    return {s: _season(s) for s in seasons}


def _status(report: dict, gate: str) -> str:
    return next(c["status"] for c in report["checks"] if c["gate"] == gate)


def test_a_healthy_build_passes_every_floor():
    report = G.gate_report(_frames())
    assert [c["status"] for c in report["checks"]] == ["PASS"] * len(report["checks"]), report[
        "checks"
    ]


def test_a_degraded_engine_fails_rather_than_passing_quietly():
    """Shuffling adj_rapm breaks its agreement with RAPM — the gate must catch it."""
    frames = _frames()
    frames[2025] = frames[2025].with_columns(pl.col("adj_rapm").shuffle(seed=7))
    report = G.gate_report(frames)
    assert _status(report, "r_rapm_adj_min") == "FAIL"


def test_an_uncomputable_metric_is_skipped_not_passed():
    """One season has no t+1, so the forward gates cannot be evaluated at all.

    SKIPPED must never read as PASS: a single-season invocation would otherwise
    "pass" the DARKO forward floor without measuring anything.
    """
    report = G.gate_report(_frames(seasons=(2025,)))
    assert _status(report, "r_darko_fwd_min") == "SKIPPED"
    assert _status(report, "r_rapm_yoy_min") == "SKIPPED"


def test_check_publish_floors_blocks_and_records_in_the_card(tmp_path):
    frames = _frames()
    frames[2025] = frames[2025].with_columns(pl.col("adj_rapm").shuffle(seed=7))
    for season, frame in frames.items():
        frame.write_parquet(tmp_path / f"{G.TAG}_{season}.parquet")
    card = tmp_path / f"{G.TAG}_card.json"
    card.write_text(json.dumps({"dataset": G.TAG}), encoding="utf-8")

    with pytest.raises(SystemExit, match="publish BLOCKED"):
        G.check_publish_floors(tmp_path, frames)

    recorded = json.loads(card.read_text(encoding="utf-8"))["publish_gates"]
    assert recorded["seasons_gated"] == [2024, 2025]
    assert any(c["status"] == "FAIL" for c in recorded["checks"])


def test_every_floor_has_a_gate_and_every_gate_a_floor():
    """A floor nobody evaluates is decoration; a gate with no floor never blocks."""
    evaluated = {c["gate"] for c in G.gate_report(_frames())["checks"]}
    assert evaluated == set(G.FLOORS)


def test_spm_sidecar_round_trips_with_the_fields_the_writeup_reads(tmp_path):
    record = {
        "season": 2024,
        "feature_names": ["pts", "ast"],
        "feature_sd": [8.0, 4.0],
        "o_coef": [0.11, 0.07],
        "d_coef": [-0.01, 0.02],
        "o_intercept": -3.0,
        "d_intercept": 1.0,
        "train_r_spm_vs_rapm": 0.42,
    }
    path = write_spm_coefficients(tmp_path, [record])
    assert path.name == SPM_SIDECAR_NAME
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["seasons"] == [2024]
    got = payload["records"][0]
    assert (
        len(got["o_coef"])
        == len(got["d_coef"])
        == len(got["feature_names"])
        == len(got["feature_sd"])
    )


def test_a_constant_column_fails_the_gate_it_cannot_skip_it():
    """A degenerate correlation is a DEFECT, not an unmeasurable metric.

    ``pl.corr`` returns NaN when a column is constant. Folding that into the
    ``None``/SKIPPED bucket meant a build whose ``spm`` collapsed to a single
    value sailed through ``check_publish_floors``, which blocks only on FAIL.
    """
    frames = {2024: _season(2024), 2025: _season(2025)}
    frames[2025] = frames[2025].with_columns(pl.lit(1.0).alias("spm"))
    report = G.gate_report(frames)
    spm = next(c for c in report["checks"] if c["gate"] == "r_spm_rapm_min")
    assert spm["status"] == "FAIL", report["checks"]
    # and a genuinely unmeasurable metric is still SKIPPED, not FAIL
    one = G.gate_report({2024: _season(2024)})
    assert next(c for c in one["checks"] if c["gate"] == "r_rapm_yoy_min")["status"] == "SKIPPED"


def test_the_sidecar_keeps_seasons_this_run_did_not_rebuild(tmp_path):
    """A one-season refit must not truncate a multi-season sidecar."""
    write_spm_coefficients(tmp_path, [{"season": 2024, "coef": [1.0]}, {"season": 2025, "coef": [2.0]}])
    write_spm_coefficients(tmp_path, [{"season": 2025, "coef": [9.9]}])
    payload = json.loads((tmp_path / SPM_SIDECAR_NAME).read_text(encoding="utf-8"))
    assert payload["seasons"] == [2024, 2025]
    by_season = {r["season"]: r for r in payload["records"]}
    assert by_season[2024]["coef"] == [1.0]   # preserved
    assert by_season[2025]["coef"] == [9.9]   # current run wins


def test_the_canonical_sidecar_takes_only_the_published_seasons(tmp_path):
    """A trailing-window build publishes one season: only that record may move."""
    import pytest
    from wnba_model_publish.builders import merge_spm_coefficients

    published = {"records": [{"season": s, "coef": [float(s)]} for s in range(1997, 2027)]}
    # the nightly's build sidecar: a 2021:2026 window, every fit different
    write_spm_coefficients(tmp_path, [{"season": s, "coef": [-1.0]} for s in range(2021, 2027)])

    merge_spm_coefficients(tmp_path, [2026], published)

    payload = json.loads((tmp_path / SPM_SIDECAR_NAME).read_text(encoding="utf-8"))
    by_season = {r["season"]: r["coef"] for r in payload["records"]}
    assert payload["seasons"] == list(range(1997, 2027))       # full history kept
    assert by_season[2026] == [-1.0]                            # the published season moved
    assert all(by_season[s] == [float(s)] for s in range(1997, 2026))  # warm-up fits did not
    with pytest.raises(SystemExit):
        merge_spm_coefficients(tmp_path, [2030], published)    # a season it never built


def test_no_published_sidecar_yet_starts_from_the_build(tmp_path):
    from wnba_model_publish.builders import merge_spm_coefficients

    write_spm_coefficients(tmp_path, [{"season": 2025, "coef": [1.0]}, {"season": 2026, "coef": [2.0]}])
    merge_spm_coefficients(tmp_path, [2026], None)
    payload = json.loads((tmp_path / SPM_SIDECAR_NAME).read_text(encoding="utf-8"))
    assert payload["seasons"] == [2026]


# --- the model card on the release is canonical (card-merge) -----------------


def _card(seasons, *, stamp, gated=None, checks="full"):
    """A card shaped like _write_model_card + check_publish_floors output."""
    gated = list(seasons) if gated is None else gated
    return {
        "dataset": "wnba_player_impact",
        "models": {"rapm": stamp},
        "lineup_source": "auto",
        "possession_pipeline_version": 5,
        "season_types": ["Regular Season", "Playoffs"],
        "seasons": [{"season": s, "rows": 100 + s % 100} for s in seasons],
        "generated_at": stamp,
        "publish_gates": {
            "seasons_gated": gated,
            "seasons": {str(s): {"rs_rows": s, "r_rapm_yoy": 0.3} for s in gated},
            "summary": {"r_rapm_yoy_min": 0.29 if checks == "full" else None},
            "checks": [{"gate": "r_rapm_yoy_min", "status": "PASS" if checks == "full" else "SKIPPED"}],
            "scale": [{"season": s, "gate": "sd_rapm", "status": "PASS", "stamp": stamp} for s in gated],
        },
    }


def _write(tmp_path, card):
    from wnba_model_publish.builders import CARD_NAME

    (tmp_path / CARD_NAME).write_text(json.dumps(card), encoding="utf-8")
    return tmp_path / CARD_NAME


def test_a_one_season_merge_keeps_the_other_seasons_and_the_full_history_gates(tmp_path):
    from wnba_model_publish.builders import merge_model_card

    release = _card(range(1997, 2027), stamp="2026-10-12T16:40:29+00:00")
    # the nightly: a partial build (WNBA builds a window, NBA one season) that
    # cannot compute the cross-season gates
    path = _write(tmp_path, _card(range(2021, 2027), stamp="NIGHTLY", checks="partial"))

    merge_model_card(tmp_path, [2026], release)

    card = json.loads(path.read_text(encoding="utf-8"))
    by = {r["season"]: r for r in card["seasons"]}
    assert sorted(by) == list(range(1997, 2027))                     # every season kept
    assert by[2026]["generated_at"] == "NIGHTLY"                     # the published season moved
    assert all(by[s]["generated_at"] != "NIGHTLY" for s in range(1997, 2026))  # warm-ups did not
    assert by[1997]["lineup_source"] == "auto" and by[1997]["rows"] == 197
    g = card["publish_gates"]
    assert g["checks"] == release["publish_gates"]["checks"]          # full-history gates kept
    assert g["summary"]["r_rapm_yoy_min"] == 0.29
    assert g["seasons_gated"] == list(range(1997, 2027))
    assert g["full_history_gates_as_of"] == "2026-10-12T16:40:29+00:00"
    assert sorted(int(k) for k in g["seasons"]) == list(range(1997, 2027))
    assert [c["stamp"] for c in g["scale"] if c["season"] == 2026] == ["NIGHTLY"]
    assert [c["stamp"] for c in g["scale"] if c["season"] == 2025] != ["NIGHTLY"]
    assert card["generated_at"] == "NIGHTLY"

    # merging again on top of the merged card keeps the annotation (idempotent)
    merge_model_card(tmp_path, [2026], json.loads(path.read_text(encoding="utf-8")))
    assert json.loads(path.read_text(encoding="utf-8"))["publish_gates"]["full_history_gates_as_of"] == (
        "2026-10-12T16:40:29+00:00"
    )
    with pytest.raises(SystemExit):
        merge_model_card(tmp_path, [2030], release)                  # a season it never built


def test_a_full_history_build_replaces_the_global_gates(tmp_path):
    from wnba_model_publish.builders import merge_model_card

    release = _card(range(1997, 2027), stamp="OLD")
    path = _write(tmp_path, _card(range(1997, 2027), stamp="FULL"))

    merge_model_card(tmp_path, range(1997, 2027), release)

    card = json.loads(path.read_text(encoding="utf-8"))
    assert {r["generated_at"] for r in card["seasons"]} == {"FULL"}
    assert card["publish_gates"]["full_history_gates_as_of"] == "FULL"
    assert {c["stamp"] for c in card["publish_gates"]["scale"]} == {"FULL"}


def test_a_404_starts_fresh_from_the_build(tmp_path, monkeypatch):
    import requests
    from wnba_model_publish.builders import merge_model_card, published_model_card

    monkeypatch.setattr(requests, "get", lambda *a, **k: _Resp(404))
    assert published_model_card("o/r", "t") is None

    path = _write(tmp_path, _card([2025, 2026], stamp="NEW"))
    merge_model_card(tmp_path, [2026], None)
    card = json.loads(path.read_text(encoding="utf-8"))
    assert [r["season"] for r in card["seasons"]] == [2026]
    assert list(card["publish_gates"]["seasons"]) == ["2026"]
    assert card["publish_gates"]["full_history_gates_as_of"] == "NEW"


@pytest.mark.parametrize("resp", ["500", "not-json"])
def test_an_unreadable_release_card_fails_rather_than_starting_fresh(monkeypatch, resp):
    import requests
    from wnba_model_publish.builders import published_model_card

    monkeypatch.setattr(requests, "get", lambda *a, **k: _Resp(500) if resp == "500" else _Resp(200, "<html>"))
    with pytest.raises(Exception):
        published_model_card("o/r", "t")


class _Resp:
    def __init__(self, status, body="{}"):
        self.status_code, self._body = status, body

    def raise_for_status(self):
        import requests

        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return json.loads(self._body)
