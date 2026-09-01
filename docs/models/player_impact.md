# WNBA player impact — the six-engine suite


The consolidated player-impact suite publishes one row per player-season
(regular season and playoffs) on the `wnba_player_impact` release tag,
with six engines’ columns side by side:

| engine | what it contributes |
|----|----|
| RAPM | possession on/off ridge (`o_rapm` / `d_rapm` / `rapm`) |
| adj-RAPM | RAPM with an SPM-derived prior (previous season’s RS+PO blend) |
| SPM | box-score plus/minus, coefficients fit on RS RAPM targets |
| BPM 2.0 | box logs + listed positions (`obpm` / `dbpm` / `bpm`) |
| DARKO-style | cross-season Kalman filter + aging curve (projects next season) |
| WAR | RAPM rating × calibrated pts-per-win, replacement level −2.0 |

Seasons build earliest-to-latest because two engines carry state
forward: SPM coefficients are fit ONCE per season on regular-season RAPM
(a ~15-game playoff sample would train noise on noise), and adj-RAPM’s
prior is the *previous* season’s possession-weighted RS+PO SPM blend — a
gap season deliberately breaks the prior chain. DARKO runs a per-season
Kalman step over the RAPM panel with an aging curve; playoff form enters
as a possession-weighted blend rather than a second time step, because a
second step would apply a season of aging twice.

The substrate is the committed `wehoop-wnba-stats-raw` store (per-game
playbyplay / rotation / boxscore payloads plus season-level captures),
read offline through the raw-store backend — `readonly` means OFFLINE: a
store miss raises rather than silently completing over the network, so a
build is reproducible or loudly incomplete, never quietly mixed. This
document, by contrast, evaluates the **published releases**: every
number and figure below is recomputed at render time from the release
assets themselves, which is exactly what a consumer downloads.

## Training data

<div id="qbusokaycd" style="padding-left:0px;padding-right:0px;padding-top:10px;padding-bottom:10px;overflow-x:auto;overflow-y:auto;width:auto;height:auto;">
<style>
#qbusokaycd table {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Helvetica Neue', 'Fira Sans', 'Droid Sans', Arial, sans-serif;
          -webkit-font-smoothing: antialiased;
          -moz-osx-font-smoothing: grayscale;
        }
&#10;#qbusokaycd thead, tbody, tfoot, tr, td, th { border-style: none; }
 tr { background-color: transparent; }
#qbusokaycd p { margin: 0; padding: 0; }
 #qbusokaycd .gt_table { display: table; border-collapse: collapse; line-height: normal; margin-left: auto; margin-right: auto; color: #333333; font-size: 16px; font-weight: normal; font-style: normal; background-color: #FFFFFF; width: auto; border-top-style: solid; border-top-width: 2px; border-top-color: #A8A8A8; border-right-style: none; border-right-width: 2px; border-right-color: #D3D3D3; border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #A8A8A8; border-left-style: none; border-left-width: 2px; border-left-color: #D3D3D3; }
 #qbusokaycd .gt_caption { padding-top: 4px; padding-bottom: 4px; }
 #qbusokaycd .gt_title { color: #333333; font-size: 125%; font-weight: initial; padding-top: 4px; padding-bottom: 4px; padding-left: 5px; padding-right: 5px; border-bottom-color: #FFFFFF; border-bottom-width: 0; }
 #qbusokaycd .gt_subtitle { color: #333333; font-size: 85%; font-weight: initial; padding-top: 3px; padding-bottom: 5px; padding-left: 5px; padding-right: 5px; border-top-color: #FFFFFF; border-top-width: 0; }
 #qbusokaycd .gt_heading { background-color: #FFFFFF; text-align: center; border-bottom-color: #FFFFFF; border-left-style: none; border-left-width: 1px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 1px; border-right-color: #D3D3D3; }
 #qbusokaycd .gt_bottom_border { border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; }
 #qbusokaycd .gt_col_headings { border-top-style: solid; border-top-width: 2px; border-top-color: #D3D3D3; border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; border-left-style: none; border-left-width: 1px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 1px; border-right-color: #D3D3D3; }
 #qbusokaycd .gt_col_heading { color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: normal; text-transform: inherit; border-left-style: none; border-left-width: 1px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 1px; border-right-color: #D3D3D3; vertical-align: bottom; padding-top: 5px; padding-bottom: 5px; padding-left: 5px; padding-right: 5px; overflow-x: hidden; }
 #qbusokaycd .gt_column_spanner_outer { color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: normal; text-transform: inherit; padding-top: 0; padding-bottom: 0; padding-left: 4px; padding-right: 4px; }
 #qbusokaycd .gt_column_spanner_outer:first-child { padding-left: 0; }
 #qbusokaycd .gt_column_spanner_outer:last-child { padding-right: 0; }
 #qbusokaycd .gt_column_spanner { border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; vertical-align: bottom; padding-top: 5px; padding-bottom: 5px; overflow-x: hidden; display: inline-block; width: 100%; }
 #qbusokaycd .gt_spanner_row { border-bottom-style: hidden; }
 #qbusokaycd .gt_group_heading { padding-top: 8px; padding-bottom: 8px; padding-left: 5px; padding-right: 5px; color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: initial; text-transform: inherit; border-top-style: solid; border-top-width: 2px; border-top-color: #D3D3D3; border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; border-left-style: none; border-left-width: 1px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 1px; border-right-color: #D3D3D3; vertical-align: middle; text-align: left; }
 #qbusokaycd .gt_empty_group_heading { padding: 0.5px; color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: initial; border-top-style: solid; border-top-width: 2px; border-top-color: #D3D3D3; border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; vertical-align: middle; }
 #qbusokaycd .gt_from_md> :first-child { margin-top: 0; }
 #qbusokaycd .gt_from_md> :last-child { margin-bottom: 0; }
 #qbusokaycd .gt_row { padding-top: 8px; padding-bottom: 8px; padding-left: 5px; padding-right: 5px; margin: 10px; border-top-style: solid; border-top-width: 1px; border-top-color: #D3D3D3; border-left-style: none; border-left-width: 1px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 1px; border-right-color: #D3D3D3; vertical-align: middle; overflow-x: hidden; }
 #qbusokaycd .gt_stub { color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: initial; text-transform: inherit; border-right-style: solid; border-right-width: 2px; border-right-color: #D3D3D3; padding-left: 5px; padding-right: 5px; }
 #qbusokaycd .gt_indent_1 { text-indent: 5px; }
 #qbusokaycd .gt_indent_2 { text-indent: calc(5px * 2); }
 #qbusokaycd .gt_indent_3 { text-indent: calc(5px * 3); }
 #qbusokaycd .gt_indent_4 { text-indent: calc(5px * 4); }
 #qbusokaycd .gt_indent_5 { text-indent: calc(5px * 5); }
 #qbusokaycd .gt_stub_row_group { color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: initial; text-transform: inherit; border-right-style: solid; border-right-width: 2px; border-right-color: #D3D3D3; padding-left: 5px; padding-right: 5px; vertical-align: top; }
 #qbusokaycd .gt_row_group_first td { border-top-width: 2px; }
 #qbusokaycd .gt_row_group_first th { border-top-width: 2px; }
 #qbusokaycd .gt_striped { color: #333333; background-color: #F4F4F4; }
 #qbusokaycd .gt_table_body { border-top-style: solid; border-top-width: 2px; border-top-color: #D3D3D3; border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; }
 #qbusokaycd .gt_summary_row { color: #333333; background-color: #FFFFFF; text-transform: inherit; padding-top: 8px; padding-bottom: 8px; padding-left: 5px; padding-right: 5px; }
 #qbusokaycd .gt_first_summary_row { border-top-style: solid; border-top-width: 2px; border-top-color: #D3D3D3; }
 #qbusokaycd .gt_last_summary_row_top { border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; }
 #qbusokaycd .gt_grand_summary_row { color: #333333; background-color: #FFFFFF; text-transform: inherit; padding-top: 8px; padding-bottom: 8px; padding-left: 5px; padding-right: 5px; }
 #qbusokaycd .gt_first_grand_summary_row_bottom { border-top-style: double; border-top-width: 6px; border-top-color: #D3D3D3; }
 #qbusokaycd .gt_last_grand_summary_row_top { border-bottom-style: double; border-bottom-width: 6px; border-bottom-color: #D3D3D3; }
 #qbusokaycd .gt_sourcenotes { color: #333333; background-color: #FFFFFF; border-bottom-style: none; border-bottom-width: 2px; border-bottom-color: #D3D3D3; border-left-style: none; border-left-width: 2px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 2px; border-right-color: #D3D3D3; }
 #qbusokaycd .gt_sourcenote { font-size: 90%; padding-top: 4px; padding-bottom: 4px; padding-left: 5px; padding-right: 5px; text-align: left; }
 #qbusokaycd .gt_left { text-align: left; }
 #qbusokaycd .gt_center { text-align: center; }
 #qbusokaycd .gt_right { text-align: right; font-variant-numeric: tabular-nums; }
 #qbusokaycd .gt_font_normal { font-weight: normal; }
 #qbusokaycd .gt_font_bold { font-weight: bold; }
 #qbusokaycd .gt_font_italic { font-style: italic; }
 #qbusokaycd .gt_super { font-size: 65%; }
 #qbusokaycd .gt_footnotes { color: font-color(#FFFFFF); background-color: #FFFFFF; border-bottom-style: none; border-bottom-width: 2px; border-bottom-color: #D3D3D3; border-left-style: none; border-left-width: 2px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 2px; border-right-color: #D3D3D3; }
 #qbusokaycd .gt_footnote { margin: 0px; font-size: 90%; padding-top: 4px; padding-bottom: 4px; padding-left: 5px; padding-right: 5px; }
 #qbusokaycd .gt_sourcenotes { color: #333333; background-color: #FFFFFF; border-bottom-style: none; border-bottom-width: 2px; border-bottom-color: #D3D3D3; border-left-style: none; border-left-width: 2px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 2px; border-right-color: #D3D3D3; }
 #qbusokaycd .gt_sourcenote { font-size: 90%; padding-top: 4px; padding-bottom: 4px; padding-left: 5px; padding-right: 5px; text-align: left; }
 #qbusokaycd .gt_footnote_marks { font-size: 75%; vertical-align: 0.4em; position: initial; }
 #qbusokaycd .gt_asterisk { font-size: 100%; vertical-align: 0; }
 &#10;</style>

| Published wnba_player_impact assets — last 12 of 30 seasons (1997–2026) |  |  |  |
|----|----|----|----|
| one row per player-season-seasontype; computed at render time from the release |  |  |  |
| season | player_rows | playoff_rows | off_possessions |
| 2015 | 245 | 86 | 170,665 |
| 2016 | 240 | 82 | 173,685 |
| 2017 | 242 | 85 | 171,960 |
| 2018 | 238 | 81 | 173,185 |
| 2019 | 243 | 87 | 172,585 |
| 2020 | 226 | 81 | 117,505 |
| 2021 | 235 | 81 | 165,495 |
| 2022 | 249 | 83 | 190,035 |
| 2023 | 235 | 79 | 206,750 |
| 2024 | 246 | 89 | 207,145 |
| 2025 | 272 | 91 | 242,005 |
| 2026 | 221 | 0 | 161,325 |

&#10;</div>

## Exploratory data analysis

<img src="player_impact_files/figure-commonmark/cell-4-output-1.png"
width="420" height="300"
alt="Engine distributions, latest regular season — all engines center near zero on the per-100 scale except WAR (a counting stat)." />

<img src="player_impact_files/figure-commonmark/cell-5-output-1.png"
width="420" height="300"
alt="Cross-engine agreement, latest regular season (Pearson r) — engines measure related but distinct things." />

The correlation matrix is the suite’s honesty check: RAPM and adj-RAPM
agree strongly (the prior stabilizes, it does not overwrite), box
engines (SPM, BPM) form their own cluster, and DARKO’s filtered skill —
which sees every prior season — correlates with everything while
duplicating nothing.

## Attribution

The engines are linear models (ridge, regression, Kalman), so
attribution is native: each engine’s O/D split *is* its decomposition,
and the published columns carry it (`o_rapm`/`d_rapm`, `ospm`/`dspm`,
`obpm`/`dbpm`, `o_adj_rapm`/`d_adj_rapm`). No SHAP approximation is
needed — the columns are the exact attributions. What the release does
*not* carry is the SPM coefficient vector itself (it lives in the build
artifacts under `build_out/impact_engines/`), an omission recorded in
the avenues below.

<img src="player_impact_files/figure-commonmark/cell-6-output-1.png"
width="420" height="300"
alt="adj-RAPM vs RAPM, latest regular season — the SPM prior shrinks, it does not overwrite." />

## Evaluation

**DARKO forward validation** is the suite’s headline out-of-sample test:
the projection made in season t (`darko_projected_rating`, which sees
nothing after t) against the realized RAPM in season t+1. Recomputed at
render time over every adjacent published season pair:

<div id="cibdakttne" style="padding-left:0px;padding-right:0px;padding-top:10px;padding-bottom:10px;overflow-x:auto;overflow-y:auto;width:auto;height:auto;">
<style>
#cibdakttne table {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Helvetica Neue', 'Fira Sans', 'Droid Sans', Arial, sans-serif;
          -webkit-font-smoothing: antialiased;
          -moz-osx-font-smoothing: grayscale;
        }
&#10;#cibdakttne thead, tbody, tfoot, tr, td, th { border-style: none; }
 tr { background-color: transparent; }
#cibdakttne p { margin: 0; padding: 0; }
 #cibdakttne .gt_table { display: table; border-collapse: collapse; line-height: normal; margin-left: auto; margin-right: auto; color: #333333; font-size: 16px; font-weight: normal; font-style: normal; background-color: #FFFFFF; width: auto; border-top-style: solid; border-top-width: 2px; border-top-color: #A8A8A8; border-right-style: none; border-right-width: 2px; border-right-color: #D3D3D3; border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #A8A8A8; border-left-style: none; border-left-width: 2px; border-left-color: #D3D3D3; }
 #cibdakttne .gt_caption { padding-top: 4px; padding-bottom: 4px; }
 #cibdakttne .gt_title { color: #333333; font-size: 125%; font-weight: initial; padding-top: 4px; padding-bottom: 4px; padding-left: 5px; padding-right: 5px; border-bottom-color: #FFFFFF; border-bottom-width: 0; }
 #cibdakttne .gt_subtitle { color: #333333; font-size: 85%; font-weight: initial; padding-top: 3px; padding-bottom: 5px; padding-left: 5px; padding-right: 5px; border-top-color: #FFFFFF; border-top-width: 0; }
 #cibdakttne .gt_heading { background-color: #FFFFFF; text-align: center; border-bottom-color: #FFFFFF; border-left-style: none; border-left-width: 1px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 1px; border-right-color: #D3D3D3; }
 #cibdakttne .gt_bottom_border { border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; }
 #cibdakttne .gt_col_headings { border-top-style: solid; border-top-width: 2px; border-top-color: #D3D3D3; border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; border-left-style: none; border-left-width: 1px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 1px; border-right-color: #D3D3D3; }
 #cibdakttne .gt_col_heading { color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: normal; text-transform: inherit; border-left-style: none; border-left-width: 1px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 1px; border-right-color: #D3D3D3; vertical-align: bottom; padding-top: 5px; padding-bottom: 5px; padding-left: 5px; padding-right: 5px; overflow-x: hidden; }
 #cibdakttne .gt_column_spanner_outer { color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: normal; text-transform: inherit; padding-top: 0; padding-bottom: 0; padding-left: 4px; padding-right: 4px; }
 #cibdakttne .gt_column_spanner_outer:first-child { padding-left: 0; }
 #cibdakttne .gt_column_spanner_outer:last-child { padding-right: 0; }
 #cibdakttne .gt_column_spanner { border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; vertical-align: bottom; padding-top: 5px; padding-bottom: 5px; overflow-x: hidden; display: inline-block; width: 100%; }
 #cibdakttne .gt_spanner_row { border-bottom-style: hidden; }
 #cibdakttne .gt_group_heading { padding-top: 8px; padding-bottom: 8px; padding-left: 5px; padding-right: 5px; color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: initial; text-transform: inherit; border-top-style: solid; border-top-width: 2px; border-top-color: #D3D3D3; border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; border-left-style: none; border-left-width: 1px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 1px; border-right-color: #D3D3D3; vertical-align: middle; text-align: left; }
 #cibdakttne .gt_empty_group_heading { padding: 0.5px; color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: initial; border-top-style: solid; border-top-width: 2px; border-top-color: #D3D3D3; border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; vertical-align: middle; }
 #cibdakttne .gt_from_md> :first-child { margin-top: 0; }
 #cibdakttne .gt_from_md> :last-child { margin-bottom: 0; }
 #cibdakttne .gt_row { padding-top: 8px; padding-bottom: 8px; padding-left: 5px; padding-right: 5px; margin: 10px; border-top-style: solid; border-top-width: 1px; border-top-color: #D3D3D3; border-left-style: none; border-left-width: 1px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 1px; border-right-color: #D3D3D3; vertical-align: middle; overflow-x: hidden; }
 #cibdakttne .gt_stub { color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: initial; text-transform: inherit; border-right-style: solid; border-right-width: 2px; border-right-color: #D3D3D3; padding-left: 5px; padding-right: 5px; }
 #cibdakttne .gt_indent_1 { text-indent: 5px; }
 #cibdakttne .gt_indent_2 { text-indent: calc(5px * 2); }
 #cibdakttne .gt_indent_3 { text-indent: calc(5px * 3); }
 #cibdakttne .gt_indent_4 { text-indent: calc(5px * 4); }
 #cibdakttne .gt_indent_5 { text-indent: calc(5px * 5); }
 #cibdakttne .gt_stub_row_group { color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: initial; text-transform: inherit; border-right-style: solid; border-right-width: 2px; border-right-color: #D3D3D3; padding-left: 5px; padding-right: 5px; vertical-align: top; }
 #cibdakttne .gt_row_group_first td { border-top-width: 2px; }
 #cibdakttne .gt_row_group_first th { border-top-width: 2px; }
 #cibdakttne .gt_striped { color: #333333; background-color: #F4F4F4; }
 #cibdakttne .gt_table_body { border-top-style: solid; border-top-width: 2px; border-top-color: #D3D3D3; border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; }
 #cibdakttne .gt_summary_row { color: #333333; background-color: #FFFFFF; text-transform: inherit; padding-top: 8px; padding-bottom: 8px; padding-left: 5px; padding-right: 5px; }
 #cibdakttne .gt_first_summary_row { border-top-style: solid; border-top-width: 2px; border-top-color: #D3D3D3; }
 #cibdakttne .gt_last_summary_row_top { border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; }
 #cibdakttne .gt_grand_summary_row { color: #333333; background-color: #FFFFFF; text-transform: inherit; padding-top: 8px; padding-bottom: 8px; padding-left: 5px; padding-right: 5px; }
 #cibdakttne .gt_first_grand_summary_row_bottom { border-top-style: double; border-top-width: 6px; border-top-color: #D3D3D3; }
 #cibdakttne .gt_last_grand_summary_row_top { border-bottom-style: double; border-bottom-width: 6px; border-bottom-color: #D3D3D3; }
 #cibdakttne .gt_sourcenotes { color: #333333; background-color: #FFFFFF; border-bottom-style: none; border-bottom-width: 2px; border-bottom-color: #D3D3D3; border-left-style: none; border-left-width: 2px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 2px; border-right-color: #D3D3D3; }
 #cibdakttne .gt_sourcenote { font-size: 90%; padding-top: 4px; padding-bottom: 4px; padding-left: 5px; padding-right: 5px; text-align: left; }
 #cibdakttne .gt_left { text-align: left; }
 #cibdakttne .gt_center { text-align: center; }
 #cibdakttne .gt_right { text-align: right; font-variant-numeric: tabular-nums; }
 #cibdakttne .gt_font_normal { font-weight: normal; }
 #cibdakttne .gt_font_bold { font-weight: bold; }
 #cibdakttne .gt_font_italic { font-style: italic; }
 #cibdakttne .gt_super { font-size: 65%; }
 #cibdakttne .gt_footnotes { color: font-color(#FFFFFF); background-color: #FFFFFF; border-bottom-style: none; border-bottom-width: 2px; border-bottom-color: #D3D3D3; border-left-style: none; border-left-width: 2px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 2px; border-right-color: #D3D3D3; }
 #cibdakttne .gt_footnote { margin: 0px; font-size: 90%; padding-top: 4px; padding-bottom: 4px; padding-left: 5px; padding-right: 5px; }
 #cibdakttne .gt_sourcenotes { color: #333333; background-color: #FFFFFF; border-bottom-style: none; border-bottom-width: 2px; border-bottom-color: #D3D3D3; border-left-style: none; border-left-width: 2px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 2px; border-right-color: #D3D3D3; }
 #cibdakttne .gt_sourcenote { font-size: 90%; padding-top: 4px; padding-bottom: 4px; padding-left: 5px; padding-right: 5px; text-align: left; }
 #cibdakttne .gt_footnote_marks { font-size: 75%; vertical-align: 0.4em; position: initial; }
 #cibdakttne .gt_asterisk { font-size: 100%; vertical-align: 0; }
 &#10;</style>

| DARKO forward validation — projection (t) vs realized RAPM (t+1) |  |  |  |
|----|----|----|----|
| out-of-sample by construction; weighted mean r = 0.284 over 28 season pairs |  |  |  |
| season | pearson | MAE | n |
| 2014 | 0.318 | 0.745 | 111 |
| 2015 | 0.209 | 1.318 | 115 |
| 2016 | 0.196 | 1.776 | 110 |
| 2017 | 0.282 | 1.870 | 115 |
| 2018 | 0.179 | 1.461 | 115 |
| 2019 | 0.258 | 1.314 | 103 |
| 2020 | 0.291 | 1.542 | 110 |
| 2021 | 0.314 | 1.677 | 114 |
| 2022 | 0.279 | 1.324 | 116 |
| 2023 | 0.272 | 0.929 | 111 |
| 2024 | 0.308 | 1.699 | 120 |
| 2025 | 0.233 | 1.495 | 143 |

&#10;</div>

<img src="player_impact_files/figure-commonmark/cell-8-output-1.png"
width="420" height="300"
alt="DARKO forward correlation by projection season — modest and stable, capped by RAPM noise in the target." />

<div id="tejmhwalwv" style="padding-left:0px;padding-right:0px;padding-top:10px;padding-bottom:10px;overflow-x:auto;overflow-y:auto;width:auto;height:auto;">
<style>
#tejmhwalwv table {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Helvetica Neue', 'Fira Sans', 'Droid Sans', Arial, sans-serif;
          -webkit-font-smoothing: antialiased;
          -moz-osx-font-smoothing: grayscale;
        }
&#10;#tejmhwalwv thead, tbody, tfoot, tr, td, th { border-style: none; }
 tr { background-color: transparent; }
#tejmhwalwv p { margin: 0; padding: 0; }
 #tejmhwalwv .gt_table { display: table; border-collapse: collapse; line-height: normal; margin-left: auto; margin-right: auto; color: #333333; font-size: 16px; font-weight: normal; font-style: normal; background-color: #FFFFFF; width: auto; border-top-style: solid; border-top-width: 2px; border-top-color: #A8A8A8; border-right-style: none; border-right-width: 2px; border-right-color: #D3D3D3; border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #A8A8A8; border-left-style: none; border-left-width: 2px; border-left-color: #D3D3D3; }
 #tejmhwalwv .gt_caption { padding-top: 4px; padding-bottom: 4px; }
 #tejmhwalwv .gt_title { color: #333333; font-size: 125%; font-weight: initial; padding-top: 4px; padding-bottom: 4px; padding-left: 5px; padding-right: 5px; border-bottom-color: #FFFFFF; border-bottom-width: 0; }
 #tejmhwalwv .gt_subtitle { color: #333333; font-size: 85%; font-weight: initial; padding-top: 3px; padding-bottom: 5px; padding-left: 5px; padding-right: 5px; border-top-color: #FFFFFF; border-top-width: 0; }
 #tejmhwalwv .gt_heading { background-color: #FFFFFF; text-align: center; border-bottom-color: #FFFFFF; border-left-style: none; border-left-width: 1px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 1px; border-right-color: #D3D3D3; }
 #tejmhwalwv .gt_bottom_border { border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; }
 #tejmhwalwv .gt_col_headings { border-top-style: solid; border-top-width: 2px; border-top-color: #D3D3D3; border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; border-left-style: none; border-left-width: 1px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 1px; border-right-color: #D3D3D3; }
 #tejmhwalwv .gt_col_heading { color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: normal; text-transform: inherit; border-left-style: none; border-left-width: 1px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 1px; border-right-color: #D3D3D3; vertical-align: bottom; padding-top: 5px; padding-bottom: 5px; padding-left: 5px; padding-right: 5px; overflow-x: hidden; }
 #tejmhwalwv .gt_column_spanner_outer { color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: normal; text-transform: inherit; padding-top: 0; padding-bottom: 0; padding-left: 4px; padding-right: 4px; }
 #tejmhwalwv .gt_column_spanner_outer:first-child { padding-left: 0; }
 #tejmhwalwv .gt_column_spanner_outer:last-child { padding-right: 0; }
 #tejmhwalwv .gt_column_spanner { border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; vertical-align: bottom; padding-top: 5px; padding-bottom: 5px; overflow-x: hidden; display: inline-block; width: 100%; }
 #tejmhwalwv .gt_spanner_row { border-bottom-style: hidden; }
 #tejmhwalwv .gt_group_heading { padding-top: 8px; padding-bottom: 8px; padding-left: 5px; padding-right: 5px; color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: initial; text-transform: inherit; border-top-style: solid; border-top-width: 2px; border-top-color: #D3D3D3; border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; border-left-style: none; border-left-width: 1px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 1px; border-right-color: #D3D3D3; vertical-align: middle; text-align: left; }
 #tejmhwalwv .gt_empty_group_heading { padding: 0.5px; color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: initial; border-top-style: solid; border-top-width: 2px; border-top-color: #D3D3D3; border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; vertical-align: middle; }
 #tejmhwalwv .gt_from_md> :first-child { margin-top: 0; }
 #tejmhwalwv .gt_from_md> :last-child { margin-bottom: 0; }
 #tejmhwalwv .gt_row { padding-top: 8px; padding-bottom: 8px; padding-left: 5px; padding-right: 5px; margin: 10px; border-top-style: solid; border-top-width: 1px; border-top-color: #D3D3D3; border-left-style: none; border-left-width: 1px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 1px; border-right-color: #D3D3D3; vertical-align: middle; overflow-x: hidden; }
 #tejmhwalwv .gt_stub { color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: initial; text-transform: inherit; border-right-style: solid; border-right-width: 2px; border-right-color: #D3D3D3; padding-left: 5px; padding-right: 5px; }
 #tejmhwalwv .gt_indent_1 { text-indent: 5px; }
 #tejmhwalwv .gt_indent_2 { text-indent: calc(5px * 2); }
 #tejmhwalwv .gt_indent_3 { text-indent: calc(5px * 3); }
 #tejmhwalwv .gt_indent_4 { text-indent: calc(5px * 4); }
 #tejmhwalwv .gt_indent_5 { text-indent: calc(5px * 5); }
 #tejmhwalwv .gt_stub_row_group { color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: initial; text-transform: inherit; border-right-style: solid; border-right-width: 2px; border-right-color: #D3D3D3; padding-left: 5px; padding-right: 5px; vertical-align: top; }
 #tejmhwalwv .gt_row_group_first td { border-top-width: 2px; }
 #tejmhwalwv .gt_row_group_first th { border-top-width: 2px; }
 #tejmhwalwv .gt_striped { color: #333333; background-color: #F4F4F4; }
 #tejmhwalwv .gt_table_body { border-top-style: solid; border-top-width: 2px; border-top-color: #D3D3D3; border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; }
 #tejmhwalwv .gt_summary_row { color: #333333; background-color: #FFFFFF; text-transform: inherit; padding-top: 8px; padding-bottom: 8px; padding-left: 5px; padding-right: 5px; }
 #tejmhwalwv .gt_first_summary_row { border-top-style: solid; border-top-width: 2px; border-top-color: #D3D3D3; }
 #tejmhwalwv .gt_last_summary_row_top { border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; }
 #tejmhwalwv .gt_grand_summary_row { color: #333333; background-color: #FFFFFF; text-transform: inherit; padding-top: 8px; padding-bottom: 8px; padding-left: 5px; padding-right: 5px; }
 #tejmhwalwv .gt_first_grand_summary_row_bottom { border-top-style: double; border-top-width: 6px; border-top-color: #D3D3D3; }
 #tejmhwalwv .gt_last_grand_summary_row_top { border-bottom-style: double; border-bottom-width: 6px; border-bottom-color: #D3D3D3; }
 #tejmhwalwv .gt_sourcenotes { color: #333333; background-color: #FFFFFF; border-bottom-style: none; border-bottom-width: 2px; border-bottom-color: #D3D3D3; border-left-style: none; border-left-width: 2px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 2px; border-right-color: #D3D3D3; }
 #tejmhwalwv .gt_sourcenote { font-size: 90%; padding-top: 4px; padding-bottom: 4px; padding-left: 5px; padding-right: 5px; text-align: left; }
 #tejmhwalwv .gt_left { text-align: left; }
 #tejmhwalwv .gt_center { text-align: center; }
 #tejmhwalwv .gt_right { text-align: right; font-variant-numeric: tabular-nums; }
 #tejmhwalwv .gt_font_normal { font-weight: normal; }
 #tejmhwalwv .gt_font_bold { font-weight: bold; }
 #tejmhwalwv .gt_font_italic { font-style: italic; }
 #tejmhwalwv .gt_super { font-size: 65%; }
 #tejmhwalwv .gt_footnotes { color: font-color(#FFFFFF); background-color: #FFFFFF; border-bottom-style: none; border-bottom-width: 2px; border-bottom-color: #D3D3D3; border-left-style: none; border-left-width: 2px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 2px; border-right-color: #D3D3D3; }
 #tejmhwalwv .gt_footnote { margin: 0px; font-size: 90%; padding-top: 4px; padding-bottom: 4px; padding-left: 5px; padding-right: 5px; }
 #tejmhwalwv .gt_sourcenotes { color: #333333; background-color: #FFFFFF; border-bottom-style: none; border-bottom-width: 2px; border-bottom-color: #D3D3D3; border-left-style: none; border-left-width: 2px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 2px; border-right-color: #D3D3D3; }
 #tejmhwalwv .gt_sourcenote { font-size: 90%; padding-top: 4px; padding-bottom: 4px; padding-left: 5px; padding-right: 5px; text-align: left; }
 #tejmhwalwv .gt_footnote_marks { font-size: 75%; vertical-align: 0.4em; position: initial; }
 #tejmhwalwv .gt_asterisk { font-size: 100%; vertical-align: 0; }
 &#10;</style>

| Reliability context for the forward validation |  |  |
|----|----|----|
| the projection's ceiling is bounded by how noisy the RAPM target itself is |  |  |
| check | pearson | pairs |
| RAPM year-over-year reliability (same player, adjacent seasons) | 0.266 | 3379 |
| adj-RAPM vs RAPM agreement (2026 RS) | 0.792 | 221 |

&#10;</div>

The forward-r is honest but modest, and the reliability row is why:
DARKO cannot correlate with next-season RAPM more than next-season RAPM
correlates with anything stable. The engines were additionally
proxy-validated against the published oracle CSVs at build time (beating
the minutes-played baseline by ~10%); numeric publish-blocking floors
remain a recorded TODO in `models/REGISTRY.md`.

## Results

<div id="tzsmpdgxzm" style="padding-left:0px;padding-right:0px;padding-top:10px;padding-bottom:10px;overflow-x:auto;overflow-y:auto;width:auto;height:auto;">
<style>
#tzsmpdgxzm table {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Helvetica Neue', 'Fira Sans', 'Droid Sans', Arial, sans-serif;
          -webkit-font-smoothing: antialiased;
          -moz-osx-font-smoothing: grayscale;
        }
&#10;#tzsmpdgxzm thead, tbody, tfoot, tr, td, th { border-style: none; }
 tr { background-color: transparent; }
#tzsmpdgxzm p { margin: 0; padding: 0; }
 #tzsmpdgxzm .gt_table { display: table; border-collapse: collapse; line-height: normal; margin-left: auto; margin-right: auto; color: #333333; font-size: 16px; font-weight: normal; font-style: normal; background-color: #FFFFFF; width: auto; border-top-style: solid; border-top-width: 2px; border-top-color: #A8A8A8; border-right-style: none; border-right-width: 2px; border-right-color: #D3D3D3; border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #A8A8A8; border-left-style: none; border-left-width: 2px; border-left-color: #D3D3D3; }
 #tzsmpdgxzm .gt_caption { padding-top: 4px; padding-bottom: 4px; }
 #tzsmpdgxzm .gt_title { color: #333333; font-size: 125%; font-weight: initial; padding-top: 4px; padding-bottom: 4px; padding-left: 5px; padding-right: 5px; border-bottom-color: #FFFFFF; border-bottom-width: 0; }
 #tzsmpdgxzm .gt_subtitle { color: #333333; font-size: 85%; font-weight: initial; padding-top: 3px; padding-bottom: 5px; padding-left: 5px; padding-right: 5px; border-top-color: #FFFFFF; border-top-width: 0; }
 #tzsmpdgxzm .gt_heading { background-color: #FFFFFF; text-align: center; border-bottom-color: #FFFFFF; border-left-style: none; border-left-width: 1px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 1px; border-right-color: #D3D3D3; }
 #tzsmpdgxzm .gt_bottom_border { border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; }
 #tzsmpdgxzm .gt_col_headings { border-top-style: solid; border-top-width: 2px; border-top-color: #D3D3D3; border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; border-left-style: none; border-left-width: 1px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 1px; border-right-color: #D3D3D3; }
 #tzsmpdgxzm .gt_col_heading { color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: normal; text-transform: inherit; border-left-style: none; border-left-width: 1px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 1px; border-right-color: #D3D3D3; vertical-align: bottom; padding-top: 5px; padding-bottom: 5px; padding-left: 5px; padding-right: 5px; overflow-x: hidden; }
 #tzsmpdgxzm .gt_column_spanner_outer { color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: normal; text-transform: inherit; padding-top: 0; padding-bottom: 0; padding-left: 4px; padding-right: 4px; }
 #tzsmpdgxzm .gt_column_spanner_outer:first-child { padding-left: 0; }
 #tzsmpdgxzm .gt_column_spanner_outer:last-child { padding-right: 0; }
 #tzsmpdgxzm .gt_column_spanner { border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; vertical-align: bottom; padding-top: 5px; padding-bottom: 5px; overflow-x: hidden; display: inline-block; width: 100%; }
 #tzsmpdgxzm .gt_spanner_row { border-bottom-style: hidden; }
 #tzsmpdgxzm .gt_group_heading { padding-top: 8px; padding-bottom: 8px; padding-left: 5px; padding-right: 5px; color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: initial; text-transform: inherit; border-top-style: solid; border-top-width: 2px; border-top-color: #D3D3D3; border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; border-left-style: none; border-left-width: 1px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 1px; border-right-color: #D3D3D3; vertical-align: middle; text-align: left; }
 #tzsmpdgxzm .gt_empty_group_heading { padding: 0.5px; color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: initial; border-top-style: solid; border-top-width: 2px; border-top-color: #D3D3D3; border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; vertical-align: middle; }
 #tzsmpdgxzm .gt_from_md> :first-child { margin-top: 0; }
 #tzsmpdgxzm .gt_from_md> :last-child { margin-bottom: 0; }
 #tzsmpdgxzm .gt_row { padding-top: 8px; padding-bottom: 8px; padding-left: 5px; padding-right: 5px; margin: 10px; border-top-style: solid; border-top-width: 1px; border-top-color: #D3D3D3; border-left-style: none; border-left-width: 1px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 1px; border-right-color: #D3D3D3; vertical-align: middle; overflow-x: hidden; }
 #tzsmpdgxzm .gt_stub { color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: initial; text-transform: inherit; border-right-style: solid; border-right-width: 2px; border-right-color: #D3D3D3; padding-left: 5px; padding-right: 5px; }
 #tzsmpdgxzm .gt_indent_1 { text-indent: 5px; }
 #tzsmpdgxzm .gt_indent_2 { text-indent: calc(5px * 2); }
 #tzsmpdgxzm .gt_indent_3 { text-indent: calc(5px * 3); }
 #tzsmpdgxzm .gt_indent_4 { text-indent: calc(5px * 4); }
 #tzsmpdgxzm .gt_indent_5 { text-indent: calc(5px * 5); }
 #tzsmpdgxzm .gt_stub_row_group { color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: initial; text-transform: inherit; border-right-style: solid; border-right-width: 2px; border-right-color: #D3D3D3; padding-left: 5px; padding-right: 5px; vertical-align: top; }
 #tzsmpdgxzm .gt_row_group_first td { border-top-width: 2px; }
 #tzsmpdgxzm .gt_row_group_first th { border-top-width: 2px; }
 #tzsmpdgxzm .gt_striped { color: #333333; background-color: #F4F4F4; }
 #tzsmpdgxzm .gt_table_body { border-top-style: solid; border-top-width: 2px; border-top-color: #D3D3D3; border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; }
 #tzsmpdgxzm .gt_summary_row { color: #333333; background-color: #FFFFFF; text-transform: inherit; padding-top: 8px; padding-bottom: 8px; padding-left: 5px; padding-right: 5px; }
 #tzsmpdgxzm .gt_first_summary_row { border-top-style: solid; border-top-width: 2px; border-top-color: #D3D3D3; }
 #tzsmpdgxzm .gt_last_summary_row_top { border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; }
 #tzsmpdgxzm .gt_grand_summary_row { color: #333333; background-color: #FFFFFF; text-transform: inherit; padding-top: 8px; padding-bottom: 8px; padding-left: 5px; padding-right: 5px; }
 #tzsmpdgxzm .gt_first_grand_summary_row_bottom { border-top-style: double; border-top-width: 6px; border-top-color: #D3D3D3; }
 #tzsmpdgxzm .gt_last_grand_summary_row_top { border-bottom-style: double; border-bottom-width: 6px; border-bottom-color: #D3D3D3; }
 #tzsmpdgxzm .gt_sourcenotes { color: #333333; background-color: #FFFFFF; border-bottom-style: none; border-bottom-width: 2px; border-bottom-color: #D3D3D3; border-left-style: none; border-left-width: 2px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 2px; border-right-color: #D3D3D3; }
 #tzsmpdgxzm .gt_sourcenote { font-size: 90%; padding-top: 4px; padding-bottom: 4px; padding-left: 5px; padding-right: 5px; text-align: left; }
 #tzsmpdgxzm .gt_left { text-align: left; }
 #tzsmpdgxzm .gt_center { text-align: center; }
 #tzsmpdgxzm .gt_right { text-align: right; font-variant-numeric: tabular-nums; }
 #tzsmpdgxzm .gt_font_normal { font-weight: normal; }
 #tzsmpdgxzm .gt_font_bold { font-weight: bold; }
 #tzsmpdgxzm .gt_font_italic { font-style: italic; }
 #tzsmpdgxzm .gt_super { font-size: 65%; }
 #tzsmpdgxzm .gt_footnotes { color: font-color(#FFFFFF); background-color: #FFFFFF; border-bottom-style: none; border-bottom-width: 2px; border-bottom-color: #D3D3D3; border-left-style: none; border-left-width: 2px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 2px; border-right-color: #D3D3D3; }
 #tzsmpdgxzm .gt_footnote { margin: 0px; font-size: 90%; padding-top: 4px; padding-bottom: 4px; padding-left: 5px; padding-right: 5px; }
 #tzsmpdgxzm .gt_sourcenotes { color: #333333; background-color: #FFFFFF; border-bottom-style: none; border-bottom-width: 2px; border-bottom-color: #D3D3D3; border-left-style: none; border-left-width: 2px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 2px; border-right-color: #D3D3D3; }
 #tzsmpdgxzm .gt_sourcenote { font-size: 90%; padding-top: 4px; padding-bottom: 4px; padding-left: 5px; padding-right: 5px; text-align: left; }
 #tzsmpdgxzm .gt_footnote_marks { font-size: 75%; vertical-align: 0.4em; position: initial; }
 #tzsmpdgxzm .gt_asterisk { font-size: 100%; vertical-align: 0; }
 &#10;</style>

| Top 15 by WAR — 2026 regular season (min 300 minutes) |  |  |  |  |  |  |  |  |
|----|----|----|----|----|----|----|----|----|
|  | Player | Team | GP | Min | RAPM | adj-RAPM | BPM | WAR |
| <img
src="https://cdn.wnba.com/headshots/wnba/latest/1040x760/1643426.png"
height="40" /> | Olivia Miles | MIN | 26 | 801 | 1.68 | 5.28 | 14.10 | 3.83 |
| <img
src="https://cdn.wnba.com/headshots/wnba/latest/1040x760/1627675.png"
height="40" /> | Courtney Williams | MIN | 28 | 862 | 1.48 | 4.59 | 9.41 | 3.81 |
| <img
src="https://cdn.wnba.com/headshots/wnba/latest/1040x760/1628909.png"
height="40" /> | Kelsey Mitchell | IND | 27 | 871 | 1.41 | 4.90 | 8.27 | 3.79 |
| <img
src="https://cdn.wnba.com/headshots/wnba/latest/1040x760/203825.png"
height="40" /> | Kayla McBride | MIN | 28 | 908 | 1.26 | 1.67 | 11.46 | 3.76 |
| <img
src="https://cdn.wnba.com/headshots/wnba/latest/1040x760/203866.png"
height="40" /> | Kayla Thornton | GSV | 27 | 682 | 2.65 | 17.05 | 4.44 | 3.68 |
| <img
src="https://cdn.wnba.com/headshots/wnba/latest/1040x760/1643425.png"
height="40" /> | Azzi Fudd | DAL | 26 | 823 | 1.35 | 6.44 | 4.37 | 3.42 |
| <img
src="https://cdn.wnba.com/headshots/wnba/latest/1040x760/1629498.png"
height="40" /> | Jackie Young | LVA | 26 | 838 | 1.28 | 4.49 | 9.30 | 3.40 |
| <img
src="https://cdn.wnba.com/headshots/wnba/latest/1040x760/1642784.png"
height="40" /> | Paige Bueckers | DAL | 25 | 839 | 1.20 | 7.15 | 9.51 | 3.32 |
| <img
src="https://cdn.wnba.com/headshots/wnba/latest/1040x760/203833.png"
height="40" /> | Chelsea Gray | LVA | 26 | 858 | 1.10 | 3.77 | 7.42 | 3.29 |
| <img
src="https://cdn.wnba.com/headshots/wnba/latest/1040x760/1629491.png"
height="40" /> | Jessica Shepard | DAL | 27 | 899 | 0.89 | 1.16 | 9.79 | 3.22 |
| <img
src="https://cdn.wnba.com/headshots/wnba/latest/1040x760/203827.png"
height="40" /> | Natasha Howard | MIN | 28 | 831 | 1.11 | 0.28 | 11.79 | 3.19 |
| <img
src="https://cdn.wnba.com/headshots/wnba/latest/1040x760/1628269.png"
height="40" /> | Nia Coffey | MIN | 28 | 733 | 1.32 | 2.71 | 11.24 | 3.07 |
| <img
src="https://cdn.wnba.com/headshots/wnba/latest/1040x760/1627668.png"
height="40" /> | Breanna Stewart | NYL | 26 | 869 | 0.80 | 4.90 | 5.33 | 3.04 |
| <img
src="https://cdn.wnba.com/headshots/wnba/latest/1040x760/1628932.png"
height="40" /> | A'ja Wilson | LVA | 24 | 762 | 1.18 | 4.59 | 11.90 | 2.97 |
| <img
src="https://cdn.wnba.com/headshots/wnba/latest/1040x760/1631007.png"
height="40" /> | Veronica Burton | GSV | 27 | 763 | 1.05 | 3.79 | 12.00 | 2.79 |

&#10;</div>

## Provenance & reproducibility

- **Trained on:** the committed `wehoop-wnba-stats-raw` store
  (possession compile from per-game playbyplay/rotation/boxscore +
  season-level leaguegamelog / playerindex / leaguedashplayerbiostats
  captures), seasons 1997–2026 (the corpus table above lists what the
  release carries), read offline through the raw-store backend.
- **Pipeline:** per-engine numbered stages `wnba_model_01_possessions` …
  `wnba_model_07_darko` (parquet handoffs under
  `build_out/impact_engines/`; hermetic stub tests cover the chain
  including cross-season prior threading), consolidated build+publish as
  `wnba_model_08_impact`. Retrain is dispatch-only BY DESIGN
  (rate-budgeted; `dry_run` defaults true); full-history backfills run
  from the droplet. Single home: `models/manifest.yaml`.
- **This document** evaluates the published `wnba_player_impact` release
  assets downloaded at render time — the exact frames consumers read.
- **Rebuild:** `scripts/render_model_docs.sh` (Quarto → GFM;
  `uv sync --group docs`). Requires network for the release download and
  the headshot CDN.

## Avenues for improvement & open issues

- **Encode the numeric publish floors** — the registry states them as
  TODO; the proxy-validation deltas are exactly the values to freeze.
- **Publish the SPM coefficient vector** — the release carries the
  engine outputs but not the fitted coefficients; shipping them (or a
  per-retrain meta sidecar) would let this document show real
  coefficient importance instead of describing where it lives.
- **Uncertainty** — none of the engines ships an interval; a
  cluster-respecting resample (games, not rows) is the recorded
  standard.
- **DARKO ceiling** — the forward-r is capped by RAPM noise in the
  target; validating against a multi-season blended target would
  separate projection error from target noise.
- **PlayIn season type is unsupported** by design; revisit if the sample
  ever justifies it.
