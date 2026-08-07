"""Typed schema declarations for the released datasets (spec D39).

The models declare the schema, not the rows: they are asserted frame-level at
the write chokepoint (``wnba_data_build.io.write_release_formats``), never
row-by-row (pydantic over a multi-million-row pbp frame is a performance trap).
"""

from __future__ import annotations

import glob
from pathlib import Path

import polars as pl
import pytest
from wnba_data_build.datasets import BY_KEY, DATASETS
from wnba_data_build.models import MODELS, check_frame, check_stem, polars_schema

REPO_ROOT = Path(__file__).resolve().parents[1]

MASTERS = {"schedule_master", "games_in_data_repo"}


def test_every_registry_dataset_has_a_model():
    assert set(MODELS) == {d.key for d in DATASETS} | MASTERS


@pytest.mark.parametrize("dataset", sorted(MODELS), ids=sorted(MODELS))
def test_polars_schema_is_derivable(dataset):
    assert len(polars_schema(dataset)) > 0


@pytest.mark.parametrize("dataset", sorted(MODELS), ids=sorted(MODELS))
def test_game_id_is_declared_utf8(dataset):
    """WNBA game ids carry the "10" league prefix ("1022400001") and are
    pinned Utf8 at every boundary; an int round-trip is a lossy cast bug."""
    schema = polars_schema(dataset)
    if "game_id" in schema:
        assert schema["game_id"] == pl.Utf8, f"{dataset}: game_id is {schema['game_id']}"


def test_entity_ids_are_declared_int64():
    """team_id / person_id are numeric stats.wnba.com ids (join keys)."""
    for dataset in sorted(MODELS):
        schema = polars_schema(dataset)
        for col in ("team_id", "person_id"):
            if col in schema:
                assert schema[col] == pl.Int64, f"{dataset}.{col} is {schema[col]}"


def test_model_rejects_type_coercion():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        MODELS["pbp"](game_id=1022400001)  # int where the padded Utf8 id is declared


def test_check_frame_accepts_a_matching_frame():
    frame = pl.DataFrame(schema=dict(polars_schema("officials")))
    assert check_frame("officials", frame) == []


def test_check_frame_reports_a_missing_column():
    frame = pl.DataFrame({"game_id": ["1022400001"]})
    problems = check_frame("officials", frame)
    assert any("missing column" in p for p in problems)


def test_check_frame_tolerates_widening_but_not_type_changes():
    """An Int32 season read back from an older asset is losslessly Int64; a
    stringly one is not."""
    base = dict(polars_schema("officials"))
    ok = pl.DataFrame(schema={**base, "official_id": pl.Int32})
    assert [p for p in check_frame("officials", ok) if "official_id" in p] == []
    bad = pl.DataFrame(schema={**base, "official_id": pl.Utf8})
    assert any("official_id" in p for p in check_frame("officials", bad))


def test_check_frame_tolerates_an_all_null_column():
    base = dict(polars_schema("officials"))
    frame = pl.DataFrame(schema={**base, "first_name": pl.Null})
    assert [p for p in check_frame("officials", frame) if "first_name" in p] == []


def test_check_stem_resolves_the_seasoned_write_stem():
    frame = pl.DataFrame(schema=dict(polars_schema("standings")))
    assert check_stem("standings_2026", frame) == []
    assert check_stem("standings_2026", pl.DataFrame()) != []
    # The schedules stem is itself prefixed ("wnba_stats_schedule_2026").
    assert check_stem("wnba_stats_schedule_2026", pl.DataFrame()) != []


@pytest.mark.archive
@pytest.mark.parametrize(
    "dataset", sorted(set(MODELS) - MASTERS), ids=sorted(set(MODELS) - MASTERS)
)
def test_model_matches_the_committed_parquet(dataset):
    """The declared schema must describe what the pipeline actually writes."""
    spec = BY_KEY[dataset]
    built = sorted(
        glob.glob(str(REPO_ROOT / "wnba_stats" / dataset / "parquet" / f"{spec.stem}_*.parquet"))
    )
    if not built:
        pytest.skip(f"no committed parquet for {dataset}")
    frame = pl.read_parquet(built[-1], n_rows=1)
    problems = [p for p in check_frame(dataset, frame) if "missing column" in p]
    assert problems == [], "\n".join(problems)


@pytest.mark.archive
@pytest.mark.parametrize("dataset", sorted(MASTERS), ids=sorted(MASTERS))
def test_master_model_matches_the_committed_parquet(dataset):
    path = REPO_ROOT / "wnba_stats" / f"wnba_stats_{dataset}.parquet"
    if not path.exists():
        pytest.skip("no committed master parquet")
    frame = pl.read_parquet(path, n_rows=1)
    assert check_frame(dataset, frame) == []
