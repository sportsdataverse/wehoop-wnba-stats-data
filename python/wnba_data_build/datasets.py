"""Registry of the published WNBA stats datasets — the R creation scripts' contract.

Each entry names where a dataset comes from in the raw store and where it goes on
``sportsdataverse-data``, so the builders stay declarative and the release tags
live in one place rather than scattered across ten scripts.

``wehoop_type`` is not decoration: the R producers stamp it via
``wehoop:::make_wehoop_data(type, timestamp)`` and it is what
``print.wehoop_data`` shows as the header. The strings are copied verbatim from
the scripts they replace so published artifacts keep identifying themselves the
same way.

Datasets whose source is ``None`` are *derived* rather than reshaped from a single
endpoint (shots comes out of play-by-play), and are built by dedicated code.
"""

from __future__ import annotations

from typing import NamedTuple


class Dataset(NamedTuple):
    """One published dataset."""

    key: str
    #: Raw-store endpoint, or None when the dataset is derived from another.
    endpoint: str | None
    #: resultSet name within the payload; None takes the first non-empty set.
    result_set: str | None
    #: Released filename stem; the season is appended (``standings_2025``).
    stem: str
    release_tag: str
    #: Stamped as the rds's ``wehoop_type``.
    wehoop_type: str
    #: "season" = one payload per season; "game" = one per game, bound per season.
    level: str = "season"
    #: Earliest season upstream actually covers. Seasons before it are refused by
    #: the builder rather than published as a well-formed frame holding a
    #: fraction of a season -- see ``officials``.
    first_season: int | None = None


_R = "from wehoop data repository"

DATASETS: tuple[Dataset, ...] = (
    Dataset(
        "standings",
        "leaguestandingsv3",
        None,
        "standings",
        "wnba_stats_standings",
        f"WNBA Stats League Standings V3 {_R}",
    ),
    Dataset(
        "player_season_stats",
        "leaguedashplayerstats",
        None,
        "player_season_stats",
        "wnba_stats_player_season_stats",
        f"WNBA Stats Player Season Stats {_R}",
    ),
    Dataset(
        "team_season_stats",
        "leaguedashteamstats",
        None,
        "team_season_stats",
        "wnba_stats_team_season_stats",
        f"WNBA Stats Team Season Stats {_R}",
    ),
    Dataset(
        "lineups",
        "leaguedashlineups",
        None,
        "lineups",
        "wnba_stats_lineups",
        f"WNBA Stats Lineups {_R}",
    ),
    Dataset(
        "rosters",
        "commonteamroster",
        "CommonTeamRoster",
        "rosters",
        "wnba_stats_rosters",
        f"WNBA Stats Rosters {_R}",
    ),
    Dataset(
        "coaches",
        "commonteamroster",
        "Coaches",
        "coaches",
        "wnba_stats_coaches",
        f"WNBA Stats Coaches {_R}",
    ),
    Dataset(
        "draft",
        "drafthistory",
        None,
        "draft",
        "wnba_stats_draft",
        f"WNBA Stats Draft History {_R}",
    ),
    Dataset(
        "schedules",
        "leaguegamelog",
        None,
        "wnba_stats_schedule",
        "wnba_stats_schedules",
        f"WNBA Stats Schedule {_R}",
    ),
    Dataset(
        "player_game_logs",
        "leaguegamelog",
        None,
        "player_game_logs",
        "wnba_stats_player_game_logs",
        f"WNBA Stats Player Game Logs {_R}",
    ),
    # -- per-game, bound into one frame per season --------------------------------
    Dataset(
        "pbp",
        "playbyplayv3",
        None,
        "play_by_play",
        "wnba_stats_pbp",
        f"WNBA Stats Play-by-Play {_R}",
        level="game",
    ),
    Dataset(
        "game_rosters",
        "boxscoresummaryv2",
        "InactivePlayers",
        "game_rosters",
        "wnba_stats_game_rosters",
        f"WNBA Stats Game Rosters {_R}",
        level="game",
    ),
    Dataset(
        "officials",
        "boxscoresummaryv2",
        "Officials",
        "officials",
        "wnba_stats_officials",
        f"WNBA Stats Officials {_R}",
        level="game",
        # stats.wnba.com starts officiating crews in 2004, and starts them
        # complete: 240/240 games in 2004 versus 2/158 in 1998, 1/203 in 1999,
        # 2/274 in 2001, 1/273 in 2002 (1997/2000/2003 carry none at all).
        # Those stray games build into a valid 3-6 row frame that looks like a
        # season and isn't, so the floor is enforced here rather than left to
        # whoever next passes --seasons 1998.
        first_season=2004,
    ),
    Dataset(
        "player_boxscores",
        "boxscoretraditionalv3",
        None,
        "player_boxscores",
        "wnba_stats_player_boxscores",
        f"WNBA Stats Player Boxscores {_R}",
        level="game",
    ),
    Dataset(
        "team_boxscores",
        "boxscoretraditionalv3",
        None,
        "team_boxscores",
        "wnba_stats_team_boxscores",
        f"WNBA Stats Team Boxscores {_R}",
        level="game",
    ),
    # -- derived ------------------------------------------------------------------
    Dataset(
        "shots",
        None,
        None,
        "shots",
        "wnba_stats_shots",
        f"WNBA Stats Shots {_R}",
        level="derived",
    ),
    # -- derived from the committed tree (stages 16-17, F3b-T3 / F4-T4) -------------
    #
    # Built by sdv-py over the season's `shots` -- the frame this run just built,
    # or the committed `wnba_stats/shots/parquet/shots_{Y}.parquet` when shots is
    # not in the run (cli.build_dataset). `rolling_windows` also reads every
    # earlier committed shots season (career history), dated by the committed
    # schedule master plus this season's `schedules`.
    Dataset(
        "rolling_windows",
        None,
        None,
        "rolling_windows",
        "wnba_stats_rolling_windows",
        f"WNBA Stats Rolling Shooting Windows {_R}",
        level="derived",
    ),
    Dataset(
        "metric_curves",
        None,
        None,
        "metric_curves",
        "wnba_stats_metric_curves",
        f"WNBA Stats Metric Curves {_R}",
        level="derived",
    ),
)

#: Reader-facing description per release tag: the body a tag is created with
#: (``upload_artifacts(notes=)``) and the paragraph its generated dataset page
#: carries. A tag with no entry keeps publish.py's generic body.
RELEASE_NOTES: dict[str, str] = {
    "wnba_stats_rolling_windows": (
        "Rolling shooting form -- every shooter's last N field-goal attempts (`fga`, metric "
        "`fg_pct`) and last N three-point attempts (`fg3a`, metric `fg3_pct`), N = 50 and 200, "
        "computed by `sportsdataverse.rolling_windows` from the committed `wnba_stats_shots`. "
        "One row per (season, player, window_unit, window_n) for every player with an attempt "
        "that season. Windows count ATTEMPTS, not games, and cross season boundaries: `cur` is "
        "the make rate over the last `n` attempts through the season (`n < window_n` only for a "
        "short career, `qualified = false`); `prev` is the window before it, `season_start` the "
        "window entering the season and `career_baseline` every attempt before `cur`'s window -- "
        "each null rather than partial when there is not a full window of history. "
        "`delta_prev_rank` is 1 for the biggest riser among qualified rows with a `prev`. "
        "Attempts are regular-season and playoff shots only (`season_type_id` 2 and 4, read off "
        "the game id's type digit), ordered by game date, period and clock. Ids are "
        'stats.wnba.com ids as text with `id_source = "wnba_stats"`; `entity_name` is the family '
        "name the shots carry. Span 1997-present, the shots' own span (seasons are calendar "
        "years)."
    ),
    "wnba_stats_metric_curves": (
        "FG% by shot distance -- league, team and player curves per season, computed by "
        "`sportsdataverse.metric_curves` from the committed `wnba_stats_shots`. One row per "
        "(season, entity, bucket): 1-ft bins from 0 to 35 ft, then 35-50 and 50-95 ft "
        "(`x_lo` inclusive, `x_hi` exclusive), each carrying `attempts`, `successes` (makes) "
        "and `rate = successes / attempts`; an empty bucket is absent, never a zero row. "
        "Attempts are regular-season and playoff shots only (`season_type_id` 2 and 4, read "
        "off the game id's type digit -- the committed WNBA shots carry no other game type). "
        'Ids are stats.wnba.com ids as text with `id_source = "wnba_stats"`: `entity_id` is '
        "the `team_id` / `person_id` (null on the league row), `team_id` on a player row is "
        "the team of most of that player's attempts. `down` and `epa_per_att` are null on "
        "every row (the cross-league contract's football-only columns). Span 1997-present, "
        "the shots' own span (seasons are calendar years)."
    ),
}

BY_KEY: dict[str, Dataset] = {d.key: d for d in DATASETS}

#: Every release tag this repo publishes to.
RELEASE_TAGS: tuple[str, ...] = tuple(dict.fromkeys(d.release_tag for d in DATASETS))
