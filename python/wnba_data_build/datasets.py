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
    ),
    Dataset(
        "player_boxscores", "boxscoretraditionalv3", None, "player_boxscores",
        "wnba_stats_player_boxscores", f"WNBA Stats Player Boxscores {_R}", level="game",
    ),
    Dataset(
        "team_boxscores", "boxscoretraditionalv3", None, "team_boxscores",
        "wnba_stats_team_boxscores", f"WNBA Stats Team Boxscores {_R}", level="game",
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
)

BY_KEY: dict[str, Dataset] = {d.key: d for d in DATASETS}

#: Every release tag this repo publishes to.
RELEASE_TAGS: tuple[str, ...] = tuple(dict.fromkeys(d.release_tag for d in DATASETS))
