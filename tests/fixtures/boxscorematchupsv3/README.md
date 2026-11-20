# `tests/fixtures/boxscorematchupsv3/`

`1042500101.json` is the real 2025 playoff capture of game `1042500101` from
`wehoop-wnba-stats-raw`, trimmed to two offensive players per side and three
defenders each (`jq -c`). Used by `tests/test_matchups_cli.py`, which copies it
into a temporary raw tree under several game ids.
