"""Hermetic tests for the per-engine WNBA impact stages (wnba_model_01..07).

Every sportsdataverse model function is stubbed on the builders module, so
these validate the STAGE plumbing — parquet handoffs, prior threading across
stage boundaries, darko panel assembly — with zero network and zero compute.
"""

from __future__ import annotations

import json

import polars as pl
import pytest
import wnba_model_publish.builders as B
import wnba_model_publish.impact_stages as S


def _poss(season: int) -> pl.DataFrame:
    return pl.DataFrame({"game_id": [f"10{season}"], "points": pl.Series([2], dtype=pl.Int64)})


def _rapm(players: list[int]) -> pl.DataFrame:
    n = len(players)
    return pl.DataFrame(
        {
            "player_id": pl.Series(players, dtype=pl.Int64),
            "o_rapm": [1.0] * n,
            "d_rapm": [0.5] * n,
            "rapm": [1.5] * n,
            "off_poss": pl.Series([100] * n, dtype=pl.Int64),
            "def_poss": pl.Series([100] * n, dtype=pl.Int64),
        }
    )


def _spm(players: list[int]) -> pl.DataFrame:
    n = len(players)
    return pl.DataFrame(
        {
            "player_id": pl.Series(players, dtype=pl.Int64),
            "ospm": [2.0] * n,
            "dspm": [1.0] * n,
            "spm": [3.0] * n,
            "min": [500.0] * n,
            "gp": pl.Series([30] * n, dtype=pl.Int64),
        }
    )


def _bpm(players: list[int]) -> pl.DataFrame:
    n = len(players)
    return pl.DataFrame(
        {
            "player_id": pl.Series(players, dtype=pl.Int64),
            "obpm": [1.0] * n,
            "dbpm": [0.0] * n,
            "bpm": [1.0] * n,
        }
    )


def _adj(players: list[int]) -> pl.DataFrame:
    n = len(players)
    return pl.DataFrame(
        {
            "player_id": pl.Series(players, dtype=pl.Int64),
            "o_adj_rapm": [1.1] * n,
            "d_adj_rapm": [0.4] * n,
            "adj_rapm": [1.5] * n,
        }
    )


@pytest.fixture()
def stubbed(monkeypatch):
    players = [1, 2, 3]
    seen: dict = {"priors": []}

    monkeypatch.setattr(B, "_compile_wnba_season", lambda season, stype, **kw: _poss(season))
    monkeypatch.setattr(B, "nba_rapm", lambda poss, **kw: _rapm(players))
    monkeypatch.setattr(
        B,
        "nba_box_logs",
        lambda s, **kw: {
            "player": pl.DataFrame({"player_id": players}),
            "team": pl.DataFrame(
                {"team_id": pl.Series([10, 11, 12], dtype=pl.Int64), "plus_minus": [5, -3, 8]}
            ),
        },
    )
    monkeypatch.setattr(B, "_repair_team_logs", lambda team, player: team)
    monkeypatch.setattr(B, "_canon_gamelog_ids", lambda fetch: fetch)
    monkeypatch.setattr(B, "box_features", lambda p, t, **kw: pl.DataFrame({"player_id": players}))
    monkeypatch.setattr(B, "train_spm", lambda bf, target, **kw: object())
    monkeypatch.setattr(B, "nba_spm", lambda bf, coef, **kw: _spm(players))
    monkeypatch.setattr(
        B, "nba_player_positions", lambda s, **kw: pl.DataFrame({"player_id": players})
    )
    monkeypatch.setattr(B, "nba_bpm", lambda pl_, tl, pos, **kw: _bpm(players))
    monkeypatch.setattr(
        B,
        "nba_adj_rapm",
        lambda poss, prior, **kw: (seen["priors"].append(prior), _adj(players))[1],
    )
    monkeypatch.setattr(B, "calibrate_pts_per_win", lambda ts: 25.0)
    monkeypatch.setattr(
        B,
        "nba_war",
        lambda ratings, poss, **kw: pl.DataFrame(
            {"player_id": pl.Series(players, dtype=pl.Int64), "war": [2.0] * 3}
        ),
    )
    monkeypatch.setattr(
        B,
        "nba_player_ages",
        lambda s, **kw: pl.DataFrame(
            {"player_id": pl.Series(players, dtype=pl.Int64), "age": [25.0] * 3}
        ),
    )
    monkeypatch.setattr(
        B,
        "nba_darko",
        lambda panel, ages, **kw: pl.DataFrame(
            {
                "player_id": pl.Series(players, dtype=pl.Int64),
                "last_season": pl.Series([int(panel["season"].max())] * 3, dtype=pl.Int64),
                "filtered_skill": [1.0] * 3,
                "projected_rating": [1.2] * 3,
                "projected_sd": [0.3] * 3,
            }
        ),
    )
    return seen


BOTH = ["Regular Season", "Playoffs"]


def test_engine_chain_end_to_end(stubbed, tmp_path):
    seasons = [2024, 2025]
    kw = dict(season_types=BOTH, engines_dir=tmp_path)
    S.run_possessions(seasons, **kw)
    S.run_rapm(seasons, **kw)
    S.run_spm(seasons, season_types=BOTH, engines_dir=tmp_path)
    S.run_adj_rapm(seasons, **kw)
    S.run_bpm(seasons, season_types=BOTH, engines_dir=tmp_path)
    S.run_war(seasons, **kw)
    assert S.run_darko(seasons, engines_dir=tmp_path) == 1

    d = tmp_path / "2025"
    for stem in (
        "poss_rs",
        "poss_po",
        "rapm_rs",
        "rapm_po",
        "spm_rs",
        "spm_po",
        "spm_blend",
        "identity_rs",
        "adj_rs",
        "adj_po",
        "bpm_rs",
        "war_rs",
    ):
        assert (d / f"{stem}.parquet").is_file(), f"missing {stem}"
    assert (d / "darko.parquet").is_file()
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    assert meta["pts_per_win"] == 25.0


def test_adj_prior_threads_from_prev_season_blend(stubbed, tmp_path):
    rs = ["Regular Season"]
    kw = dict(season_types=rs, engines_dir=tmp_path)
    S.run_possessions([2024, 2025], **kw)
    S.run_rapm([2024, 2025], **kw)
    S.run_spm([2024, 2025], season_types=rs, engines_dir=tmp_path)
    S.run_adj_rapm([2024, 2025], **kw)
    priors = stubbed["priors"]
    assert len(priors) == 2
    assert priors[0] == {}, "2024 RS must see an empty prior (no previous blend)"
    assert priors[1], "2025 RS must see the 2024 spm_blend-derived prior"


def test_darko_refuses_single_season(stubbed, tmp_path):
    kw = dict(season_types=["Regular Season"], engines_dir=tmp_path)
    S.run_possessions([2025], **kw)
    S.run_rapm([2025], **kw)
    assert S.run_darko([2025], engines_dir=tmp_path) == 0
    assert not (tmp_path / "2025" / "darko.parquet").exists()
