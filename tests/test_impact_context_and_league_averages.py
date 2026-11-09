"""Hermetic tests: the WNBA impact build attaches rank context and writes league averages.

The sportsdataverse model functions are stubbed at the builders-module seam (as the NBA
sibling's test_model_publish_builders.py does), so this exercises the orchestration: the
``nba_player_impact_context`` columns land on the published table and the
``wnba_player_impact_league_averages_{season}`` files land beside it in all three formats,
inside the season-scoped upload set. The ranking maths is tested in sportsdataverse-py.
"""

from __future__ import annotations

import polars as pl
import pytest
import wnba_model_publish.builders as B
from sportsdataverse._common.league_context import LEAGUE_AVERAGES_SCHEMA
from sportsdataverse.nba.nba_player_impact import IMPACT_RANKED

PLAYERS = [1, 2, 3]


class _Coef:
    feature_names = ["pts", "ast"]
    o_coef = [0.10, 0.05]
    d_coef = [-0.02, 0.01]
    o_intercept = -2.0
    d_intercept = 0.5


def _ids(n: int = len(PLAYERS)) -> pl.Series:
    return pl.Series("player_id", PLAYERS[:n], dtype=pl.Int64)


def _with_poss(frame: pl.DataFrame, poss: int) -> pl.DataFrame:
    return frame.with_columns(
        off_poss=pl.lit(poss, dtype=pl.Int64), def_poss=pl.lit(poss, dtype=pl.Int64)
    )


def _stub(monkeypatch, poss: int) -> None:
    n = len(PLAYERS)
    rapm = pl.DataFrame(
        {"player_id": _ids(), "o_rapm": [1.0] * n, "d_rapm": [0.5] * n, "rapm": [1.5] * n}
    )
    adj = pl.DataFrame(
        {
            "player_id": _ids(),
            "o_adj_rapm": [1.1] * n,
            "d_adj_rapm": [0.4] * n,
            "adj_rapm": [1.5] * n,
        }
    )
    monkeypatch.setattr(
        B,
        "_compile_wnba_season",
        lambda season, stype, **kw: pl.DataFrame({"game_id": [f"10{season}"], "points": [2]}),
    )
    monkeypatch.setattr(B, "nba_rapm", lambda p, **kw: _with_poss(rapm, poss))
    monkeypatch.setattr(B, "nba_adj_rapm", lambda p, prior, **kw: _with_poss(adj, poss))
    monkeypatch.setattr(
        B,
        "nba_box_logs",
        lambda *a, **kw: {
            # game_id/team_id/min/tov: what _repair_team_logs reads off both frames.
            "player": pl.DataFrame(
                {
                    "player_id": _ids(),
                    "game_id": ["g1"] * n,
                    "team_id": pl.Series([10, 11, 12], dtype=pl.Int64),
                    "min": [40.0] * n,
                    "tov": [2.0] * n,
                }
            ),
            "team": pl.DataFrame(
                {
                    "team_id": pl.Series([10, 11, 12], dtype=pl.Int64),
                    "game_id": ["g1"] * n,
                    "plus_minus": [5, -3, 8],
                    "min": [200.0] * n,
                    "tov": [14.0] * n,
                }
            ),
        },
    )
    monkeypatch.setattr(
        B,
        "box_features",
        lambda p, t, **kw: pl.DataFrame({"player_id": _ids(), "pts": [20.0] * n, "ast": [4.0] * n}),
    )
    monkeypatch.setattr(B, "train_spm", lambda bf, target, **kw: _Coef())
    monkeypatch.setattr(
        B,
        "nba_spm",
        lambda bf, coef, **kw: pl.DataFrame(
            {
                "player_id": _ids(),
                "ospm": [2.0] * n,
                "dspm": [1.0] * n,
                "spm": [3.0] * n,
                "min": [500.0] * n,
                "gp": pl.Series([30] * n, dtype=pl.Int64),
            }
        ),
    )
    monkeypatch.setattr(
        B, "nba_player_positions", lambda s, **kw: pl.DataFrame({"player_id": _ids()})
    )
    monkeypatch.setattr(
        B,
        "nba_bpm",
        lambda p, t, pos, **kw: pl.DataFrame(
            {
                "player_id": _ids(),
                "obpm": [1.0] * n,
                "dbpm": [0.0] * n,
                "bpm": [1.0] * n,
                "min": [500.0] * n,
                "gp": pl.Series([30] * n, dtype=pl.Int64),
            }
        ),
    )
    monkeypatch.setattr(B, "calibrate_pts_per_win", lambda ts: 30.0)
    monkeypatch.setattr(
        B,
        "nba_war",
        lambda ratings, poss_, **kw: pl.DataFrame({"player_id": _ids(), "war": [2.0] * n}),
    )
    monkeypatch.setattr(
        B, "nba_player_ages", lambda s, **kw: pl.DataFrame({"player_id": _ids(), "age": [25.0] * n})
    )

    def _darko(panel, ages, **kw):
        last = int(panel["season"].max())
        return pl.DataFrame(
            {
                "player_id": _ids(),
                "last_season": pl.Series([last] * n, dtype=pl.Int64),
                "forecast_season": pl.Series([last + 1] * n, dtype=pl.Int64),
                "filtered_skill": [1.0] * n,
                "projected_rating": [1.2] * n,
                "projected_sd": [0.3] * n,
            }
        )

    monkeypatch.setattr(B, "nba_darko", _darko)


def test_impact_carries_rank_context_for_every_ranked_metric(monkeypatch, tmp_path):
    _stub(monkeypatch, poss=100)
    results = B.build_wnba_player_impact([2025], tmp_path)
    df = pl.read_parquet(results[0]["path"])
    for m in IMPACT_RANKED:
        assert df.schema[f"{m}_n"] == pl.Int64
        assert df.schema[f"{m}_rank"] == pl.Float64
        assert df.schema[f"{m}_pct"] == pl.Float64
    # 3 players is under the 10-player rank cohort: ranks null, sample sizes populated.
    assert df["adj_rapm_rank"].null_count() == df.height
    assert df["adj_rapm_n"].to_list() == [200] * df.height
    assert df["d_adj_rapm_n"].to_list() == [100] * df.height


def test_league_averages_written_beside_each_season_in_three_formats(monkeypatch, tmp_path):
    # Possessions past every WNBA gate, so each metric with a value has a qualified cohort.
    _stub(monkeypatch, poss=4000)
    B.build_wnba_player_impact([2024, 2025], tmp_path)
    boban = {m for m in IMPACT_RANKED if m.startswith("boban_")}
    for season, metrics in ((2024, set(IMPACT_RANKED) - boban), (2025, set(IMPACT_RANKED))):
        stem = tmp_path / f"wnba_player_impact_league_averages_{season}"
        for ext in ("parquet", "csv", "rds"):
            assert stem.with_suffix(f".{ext}").is_file()
        avg = pl.read_parquet(stem.with_suffix(".parquet"))
        assert avg.schema == pl.Schema(LEAGUE_AVERAGES_SCHEMA)
        assert set(avg["category"].unique().to_list()) == {
            "player_impact_playoffs",
            "player_impact_regular_season",
        }
        # BOBAN needs two seasons of panel: null (so unqualified) in the first one.
        assert set(avg["metric"].unique().to_list()) == metrics
        assert avg["level"].unique().to_list() == ["wnba"]
        rs = avg.filter(
            (pl.col("category") == "player_impact_regular_season")
            & (pl.col("metric") == "adj_rapm")
        )
        assert rs["n"].to_list() == [3]
        assert rs["mean"].to_list() == [pytest.approx(1.5)]


def test_league_averages_ride_the_season_scoped_impact_upload(monkeypatch, tmp_path):
    from wnba_data_build.publish import plan_uploads

    _stub(monkeypatch, poss=100)
    B.build_wnba_player_impact([2024, 2025], tmp_path)
    names = {p.name for p in plan_uploads(tmp_path, [2025])}
    assert {
        f"wnba_player_impact_league_averages_2025.{e}" for e in ("parquet", "csv", "rds")
    } <= names
    assert not any("2024" in n for n in names)
