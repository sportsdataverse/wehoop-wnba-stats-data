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

<div id="esdegqywpi" style="padding-left:0px;padding-right:0px;padding-top:10px;padding-bottom:10px;overflow-x:auto;overflow-y:auto;width:auto;height:auto;">
<style>
#esdegqywpi table {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Helvetica Neue', 'Fira Sans', 'Droid Sans', Arial, sans-serif;
          -webkit-font-smoothing: antialiased;
          -moz-osx-font-smoothing: grayscale;
        }
&#10;#esdegqywpi thead, tbody, tfoot, tr, td, th { border-style: none; }
 tr { background-color: transparent; }
#esdegqywpi p { margin: 0; padding: 0; }
 #esdegqywpi .gt_table { display: table; border-collapse: collapse; line-height: normal; margin-left: auto; margin-right: auto; color: #333333; font-size: 16px; font-weight: normal; font-style: normal; background-color: #FFFFFF; width: auto; border-top-style: solid; border-top-width: 2px; border-top-color: #A8A8A8; border-right-style: none; border-right-width: 2px; border-right-color: #D3D3D3; border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #A8A8A8; border-left-style: none; border-left-width: 2px; border-left-color: #D3D3D3; }
 #esdegqywpi .gt_caption { padding-top: 4px; padding-bottom: 4px; }
 #esdegqywpi .gt_title { color: #333333; font-size: 125%; font-weight: initial; padding-top: 4px; padding-bottom: 4px; padding-left: 5px; padding-right: 5px; border-bottom-color: #FFFFFF; border-bottom-width: 0; }
 #esdegqywpi .gt_subtitle { color: #333333; font-size: 85%; font-weight: initial; padding-top: 3px; padding-bottom: 5px; padding-left: 5px; padding-right: 5px; border-top-color: #FFFFFF; border-top-width: 0; }
 #esdegqywpi .gt_heading { background-color: #FFFFFF; text-align: center; border-bottom-color: #FFFFFF; border-left-style: none; border-left-width: 1px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 1px; border-right-color: #D3D3D3; }
 #esdegqywpi .gt_bottom_border { border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; }
 #esdegqywpi .gt_col_headings { border-top-style: solid; border-top-width: 2px; border-top-color: #D3D3D3; border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; border-left-style: none; border-left-width: 1px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 1px; border-right-color: #D3D3D3; }
 #esdegqywpi .gt_col_heading { color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: normal; text-transform: inherit; border-left-style: none; border-left-width: 1px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 1px; border-right-color: #D3D3D3; vertical-align: bottom; padding-top: 5px; padding-bottom: 5px; padding-left: 5px; padding-right: 5px; overflow-x: hidden; }
 #esdegqywpi .gt_column_spanner_outer { color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: normal; text-transform: inherit; padding-top: 0; padding-bottom: 0; padding-left: 4px; padding-right: 4px; }
 #esdegqywpi .gt_column_spanner_outer:first-child { padding-left: 0; }
 #esdegqywpi .gt_column_spanner_outer:last-child { padding-right: 0; }
 #esdegqywpi .gt_column_spanner { border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; vertical-align: bottom; padding-top: 5px; padding-bottom: 5px; overflow-x: hidden; display: inline-block; width: 100%; }
 #esdegqywpi .gt_spanner_row { border-bottom-style: hidden; }
 #esdegqywpi .gt_group_heading { padding-top: 8px; padding-bottom: 8px; padding-left: 5px; padding-right: 5px; color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: initial; text-transform: inherit; border-top-style: solid; border-top-width: 2px; border-top-color: #D3D3D3; border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; border-left-style: none; border-left-width: 1px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 1px; border-right-color: #D3D3D3; vertical-align: middle; text-align: left; }
 #esdegqywpi .gt_empty_group_heading { padding: 0.5px; color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: initial; border-top-style: solid; border-top-width: 2px; border-top-color: #D3D3D3; border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; vertical-align: middle; }
 #esdegqywpi .gt_from_md> :first-child { margin-top: 0; }
 #esdegqywpi .gt_from_md> :last-child { margin-bottom: 0; }
 #esdegqywpi .gt_row { padding-top: 8px; padding-bottom: 8px; padding-left: 5px; padding-right: 5px; margin: 10px; border-top-style: solid; border-top-width: 1px; border-top-color: #D3D3D3; border-left-style: none; border-left-width: 1px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 1px; border-right-color: #D3D3D3; vertical-align: middle; overflow-x: hidden; }
 #esdegqywpi .gt_stub { color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: initial; text-transform: inherit; border-right-style: solid; border-right-width: 2px; border-right-color: #D3D3D3; padding-left: 5px; padding-right: 5px; }
 #esdegqywpi .gt_indent_1 { text-indent: 5px; }
 #esdegqywpi .gt_indent_2 { text-indent: calc(5px * 2); }
 #esdegqywpi .gt_indent_3 { text-indent: calc(5px * 3); }
 #esdegqywpi .gt_indent_4 { text-indent: calc(5px * 4); }
 #esdegqywpi .gt_indent_5 { text-indent: calc(5px * 5); }
 #esdegqywpi .gt_stub_row_group { color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: initial; text-transform: inherit; border-right-style: solid; border-right-width: 2px; border-right-color: #D3D3D3; padding-left: 5px; padding-right: 5px; vertical-align: top; }
 #esdegqywpi .gt_row_group_first td { border-top-width: 2px; }
 #esdegqywpi .gt_row_group_first th { border-top-width: 2px; }
 #esdegqywpi .gt_striped { color: #333333; background-color: #F4F4F4; }
 #esdegqywpi .gt_table_body { border-top-style: solid; border-top-width: 2px; border-top-color: #D3D3D3; border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; }
 #esdegqywpi .gt_summary_row { color: #333333; background-color: #FFFFFF; text-transform: inherit; padding-top: 8px; padding-bottom: 8px; padding-left: 5px; padding-right: 5px; }
 #esdegqywpi .gt_first_summary_row { border-top-style: solid; border-top-width: 2px; border-top-color: #D3D3D3; }
 #esdegqywpi .gt_last_summary_row_top { border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; }
 #esdegqywpi .gt_grand_summary_row { color: #333333; background-color: #FFFFFF; text-transform: inherit; padding-top: 8px; padding-bottom: 8px; padding-left: 5px; padding-right: 5px; }
 #esdegqywpi .gt_first_grand_summary_row_bottom { border-top-style: double; border-top-width: 6px; border-top-color: #D3D3D3; }
 #esdegqywpi .gt_last_grand_summary_row_top { border-bottom-style: double; border-bottom-width: 6px; border-bottom-color: #D3D3D3; }
 #esdegqywpi .gt_sourcenotes { color: #333333; background-color: #FFFFFF; border-bottom-style: none; border-bottom-width: 2px; border-bottom-color: #D3D3D3; border-left-style: none; border-left-width: 2px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 2px; border-right-color: #D3D3D3; }
 #esdegqywpi .gt_sourcenote { font-size: 90%; padding-top: 4px; padding-bottom: 4px; padding-left: 5px; padding-right: 5px; text-align: left; }
 #esdegqywpi .gt_left { text-align: left; }
 #esdegqywpi .gt_center { text-align: center; }
 #esdegqywpi .gt_right { text-align: right; font-variant-numeric: tabular-nums; }
 #esdegqywpi .gt_font_normal { font-weight: normal; }
 #esdegqywpi .gt_font_bold { font-weight: bold; }
 #esdegqywpi .gt_font_italic { font-style: italic; }
 #esdegqywpi .gt_super { font-size: 65%; }
 #esdegqywpi .gt_footnotes { color: font-color(#FFFFFF); background-color: #FFFFFF; border-bottom-style: none; border-bottom-width: 2px; border-bottom-color: #D3D3D3; border-left-style: none; border-left-width: 2px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 2px; border-right-color: #D3D3D3; }
 #esdegqywpi .gt_footnote { margin: 0px; font-size: 90%; padding-top: 4px; padding-bottom: 4px; padding-left: 5px; padding-right: 5px; }
 #esdegqywpi .gt_sourcenotes { color: #333333; background-color: #FFFFFF; border-bottom-style: none; border-bottom-width: 2px; border-bottom-color: #D3D3D3; border-left-style: none; border-left-width: 2px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 2px; border-right-color: #D3D3D3; }
 #esdegqywpi .gt_sourcenote { font-size: 90%; padding-top: 4px; padding-bottom: 4px; padding-left: 5px; padding-right: 5px; text-align: left; }
 #esdegqywpi .gt_footnote_marks { font-size: 75%; vertical-align: 0.4em; position: initial; }
 #esdegqywpi .gt_asterisk { font-size: 100%; vertical-align: 0; }
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
| 2026 | 231 | 0 | 239,695 |

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
needed — the columns are the exact attributions.

The SPM coefficient vector itself now ships as an additive sidecar,
`wnba_player_impact_spm_coefficients.json`: one record per season with
the offense and defense ridge coefficients, the feature names, the fit
population’s per-100 feature standard deviations, and the train-time fit
metrics. So this section shows the fitted model rather than describing
where it lives.

<div id="dtavkjbefa" style="padding-left:0px;padding-right:0px;padding-top:10px;padding-bottom:10px;overflow-x:auto;overflow-y:auto;width:auto;height:auto;">
<style>
#dtavkjbefa table {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Helvetica Neue', 'Fira Sans', 'Droid Sans', Arial, sans-serif;
          -webkit-font-smoothing: antialiased;
          -moz-osx-font-smoothing: grayscale;
        }
&#10;#dtavkjbefa thead, tbody, tfoot, tr, td, th { border-style: none; }
 tr { background-color: transparent; }
#dtavkjbefa p { margin: 0; padding: 0; }
 #dtavkjbefa .gt_table { display: table; border-collapse: collapse; line-height: normal; margin-left: auto; margin-right: auto; color: #333333; font-size: 16px; font-weight: normal; font-style: normal; background-color: #FFFFFF; width: auto; border-top-style: solid; border-top-width: 2px; border-top-color: #A8A8A8; border-right-style: none; border-right-width: 2px; border-right-color: #D3D3D3; border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #A8A8A8; border-left-style: none; border-left-width: 2px; border-left-color: #D3D3D3; }
 #dtavkjbefa .gt_caption { padding-top: 4px; padding-bottom: 4px; }
 #dtavkjbefa .gt_title { color: #333333; font-size: 125%; font-weight: initial; padding-top: 4px; padding-bottom: 4px; padding-left: 5px; padding-right: 5px; border-bottom-color: #FFFFFF; border-bottom-width: 0; }
 #dtavkjbefa .gt_subtitle { color: #333333; font-size: 85%; font-weight: initial; padding-top: 3px; padding-bottom: 5px; padding-left: 5px; padding-right: 5px; border-top-color: #FFFFFF; border-top-width: 0; }
 #dtavkjbefa .gt_heading { background-color: #FFFFFF; text-align: center; border-bottom-color: #FFFFFF; border-left-style: none; border-left-width: 1px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 1px; border-right-color: #D3D3D3; }
 #dtavkjbefa .gt_bottom_border { border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; }
 #dtavkjbefa .gt_col_headings { border-top-style: solid; border-top-width: 2px; border-top-color: #D3D3D3; border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; border-left-style: none; border-left-width: 1px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 1px; border-right-color: #D3D3D3; }
 #dtavkjbefa .gt_col_heading { color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: normal; text-transform: inherit; border-left-style: none; border-left-width: 1px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 1px; border-right-color: #D3D3D3; vertical-align: bottom; padding-top: 5px; padding-bottom: 5px; padding-left: 5px; padding-right: 5px; overflow-x: hidden; }
 #dtavkjbefa .gt_column_spanner_outer { color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: normal; text-transform: inherit; padding-top: 0; padding-bottom: 0; padding-left: 4px; padding-right: 4px; }
 #dtavkjbefa .gt_column_spanner_outer:first-child { padding-left: 0; }
 #dtavkjbefa .gt_column_spanner_outer:last-child { padding-right: 0; }
 #dtavkjbefa .gt_column_spanner { border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; vertical-align: bottom; padding-top: 5px; padding-bottom: 5px; overflow-x: hidden; display: inline-block; width: 100%; }
 #dtavkjbefa .gt_spanner_row { border-bottom-style: hidden; }
 #dtavkjbefa .gt_group_heading { padding-top: 8px; padding-bottom: 8px; padding-left: 5px; padding-right: 5px; color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: initial; text-transform: inherit; border-top-style: solid; border-top-width: 2px; border-top-color: #D3D3D3; border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; border-left-style: none; border-left-width: 1px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 1px; border-right-color: #D3D3D3; vertical-align: middle; text-align: left; }
 #dtavkjbefa .gt_empty_group_heading { padding: 0.5px; color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: initial; border-top-style: solid; border-top-width: 2px; border-top-color: #D3D3D3; border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; vertical-align: middle; }
 #dtavkjbefa .gt_from_md> :first-child { margin-top: 0; }
 #dtavkjbefa .gt_from_md> :last-child { margin-bottom: 0; }
 #dtavkjbefa .gt_row { padding-top: 8px; padding-bottom: 8px; padding-left: 5px; padding-right: 5px; margin: 10px; border-top-style: solid; border-top-width: 1px; border-top-color: #D3D3D3; border-left-style: none; border-left-width: 1px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 1px; border-right-color: #D3D3D3; vertical-align: middle; overflow-x: hidden; }
 #dtavkjbefa .gt_stub { color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: initial; text-transform: inherit; border-right-style: solid; border-right-width: 2px; border-right-color: #D3D3D3; padding-left: 5px; padding-right: 5px; }
 #dtavkjbefa .gt_indent_1 { text-indent: 5px; }
 #dtavkjbefa .gt_indent_2 { text-indent: calc(5px * 2); }
 #dtavkjbefa .gt_indent_3 { text-indent: calc(5px * 3); }
 #dtavkjbefa .gt_indent_4 { text-indent: calc(5px * 4); }
 #dtavkjbefa .gt_indent_5 { text-indent: calc(5px * 5); }
 #dtavkjbefa .gt_stub_row_group { color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: initial; text-transform: inherit; border-right-style: solid; border-right-width: 2px; border-right-color: #D3D3D3; padding-left: 5px; padding-right: 5px; vertical-align: top; }
 #dtavkjbefa .gt_row_group_first td { border-top-width: 2px; }
 #dtavkjbefa .gt_row_group_first th { border-top-width: 2px; }
 #dtavkjbefa .gt_striped { color: #333333; background-color: #F4F4F4; }
 #dtavkjbefa .gt_table_body { border-top-style: solid; border-top-width: 2px; border-top-color: #D3D3D3; border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; }
 #dtavkjbefa .gt_summary_row { color: #333333; background-color: #FFFFFF; text-transform: inherit; padding-top: 8px; padding-bottom: 8px; padding-left: 5px; padding-right: 5px; }
 #dtavkjbefa .gt_first_summary_row { border-top-style: solid; border-top-width: 2px; border-top-color: #D3D3D3; }
 #dtavkjbefa .gt_last_summary_row_top { border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; }
 #dtavkjbefa .gt_grand_summary_row { color: #333333; background-color: #FFFFFF; text-transform: inherit; padding-top: 8px; padding-bottom: 8px; padding-left: 5px; padding-right: 5px; }
 #dtavkjbefa .gt_first_grand_summary_row_bottom { border-top-style: double; border-top-width: 6px; border-top-color: #D3D3D3; }
 #dtavkjbefa .gt_last_grand_summary_row_top { border-bottom-style: double; border-bottom-width: 6px; border-bottom-color: #D3D3D3; }
 #dtavkjbefa .gt_sourcenotes { color: #333333; background-color: #FFFFFF; border-bottom-style: none; border-bottom-width: 2px; border-bottom-color: #D3D3D3; border-left-style: none; border-left-width: 2px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 2px; border-right-color: #D3D3D3; }
 #dtavkjbefa .gt_sourcenote { font-size: 90%; padding-top: 4px; padding-bottom: 4px; padding-left: 5px; padding-right: 5px; text-align: left; }
 #dtavkjbefa .gt_left { text-align: left; }
 #dtavkjbefa .gt_center { text-align: center; }
 #dtavkjbefa .gt_right { text-align: right; font-variant-numeric: tabular-nums; }
 #dtavkjbefa .gt_font_normal { font-weight: normal; }
 #dtavkjbefa .gt_font_bold { font-weight: bold; }
 #dtavkjbefa .gt_font_italic { font-style: italic; }
 #dtavkjbefa .gt_super { font-size: 65%; }
 #dtavkjbefa .gt_footnotes { color: font-color(#FFFFFF); background-color: #FFFFFF; border-bottom-style: none; border-bottom-width: 2px; border-bottom-color: #D3D3D3; border-left-style: none; border-left-width: 2px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 2px; border-right-color: #D3D3D3; }
 #dtavkjbefa .gt_footnote { margin: 0px; font-size: 90%; padding-top: 4px; padding-bottom: 4px; padding-left: 5px; padding-right: 5px; }
 #dtavkjbefa .gt_sourcenotes { color: #333333; background-color: #FFFFFF; border-bottom-style: none; border-bottom-width: 2px; border-bottom-color: #D3D3D3; border-left-style: none; border-left-width: 2px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 2px; border-right-color: #D3D3D3; }
 #dtavkjbefa .gt_sourcenote { font-size: 90%; padding-top: 4px; padding-bottom: 4px; padding-left: 5px; padding-right: 5px; text-align: left; }
 #dtavkjbefa .gt_footnote_marks { font-size: 75%; vertical-align: 0.4em; position: initial; }
 #dtavkjbefa .gt_asterisk { font-size: 100%; vertical-align: 0; }
 &#10;</style>

| Fitted SPM coefficients — 2026 (ridge, alpha = 100) |  |  |  |  |  |
|----|----|----|----|----|----|
| source: repo copy (wnba_player_impact_spm_coefficients.json); fit on 221 regular-season players, train r(spm, rapm) = 0.237 |  |  |  |  |  |
| feature | o_coef | d_coef | feature SD | \|o_coef\|×SD | \|d_coef\|×SD |
| pts | 0.018 | 0.001 | 8.224 | 0.149 | 0.005 |
| fga | −0.009 | −0.008 | 5.537 | 0.047 | 0.042 |
| ast | 0.012 | 0.004 | 3.085 | 0.036 | 0.013 |
| fg3m | 0.023 | 0.012 | 1.521 | 0.035 | 0.018 |
| tov | −0.020 | −0.012 | 1.700 | 0.033 | 0.020 |
| fta | −0.003 | 0.005 | 6.512 | 0.022 | 0.036 |
| oreb | 0.012 | 0.028 | 1.818 | 0.022 | 0.051 |
| pf | 0.005 | −0.015 | 3.746 | 0.017 | 0.057 |
| stl | 0.014 | 0.016 | 1.197 | 0.016 | 0.019 |
| dreb | 0.001 | 0.010 | 4.087 | 0.005 | 0.042 |
| blk | 0.002 | 0.018 | 1.293 | 0.002 | 0.024 |

&#10;</div>

<img src="player_impact_files/figure-commonmark/cell-8-output-1.png"
width="420" height="300"
alt="Offensive SPM importance — points per 100 attributable to a 1-SD move in each per-100 box feature." />

The sidecar is reproducible from the published data itself: refitting
each season on its released `o_rapm`/`d_rapm` target plus the same
committed box logs — through the same early-era team-log repair the
build applies, without which the pre-2005 per-100 features are garbage —
recovers the published `spm` column **to floating-point precision in all
30 seasons** (the largest per-season maximum absolute difference is on
the order of 1e-15, e.g. 2021 at 5.55e-15; exact zero is not the claim
and would not be a meaningful one for a refit ridge solve). Both halves
of the check are stored per record — `reproduces_published_spm_r`
(correlation) and `reproduces_published_spm_max_abs_diff` (the level
check the correlation alone cannot make: r = 1.0 survives any affine
rescale) — so a refit that did *not* reproduce the release would show up
in the artifact instead of passing silently.

<img src="player_impact_files/figure-commonmark/cell-9-output-1.png"
width="420" height="300"
alt="adj-RAPM vs RAPM, latest regular season — the SPM prior shrinks, it does not overwrite." />

## Evaluation

**DARKO forward validation** is the suite’s headline out-of-sample test:
the projection made in season t (`darko_projected_rating`, which sees
nothing after t) against the realized RAPM in season t+1. Recomputed at
render time over every adjacent published season pair:

<div id="jrcudrlkjj" style="padding-left:0px;padding-right:0px;padding-top:10px;padding-bottom:10px;overflow-x:auto;overflow-y:auto;width:auto;height:auto;">
<style>
#jrcudrlkjj table {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Helvetica Neue', 'Fira Sans', 'Droid Sans', Arial, sans-serif;
          -webkit-font-smoothing: antialiased;
          -moz-osx-font-smoothing: grayscale;
        }
&#10;#jrcudrlkjj thead, tbody, tfoot, tr, td, th { border-style: none; }
 tr { background-color: transparent; }
#jrcudrlkjj p { margin: 0; padding: 0; }
 #jrcudrlkjj .gt_table { display: table; border-collapse: collapse; line-height: normal; margin-left: auto; margin-right: auto; color: #333333; font-size: 16px; font-weight: normal; font-style: normal; background-color: #FFFFFF; width: auto; border-top-style: solid; border-top-width: 2px; border-top-color: #A8A8A8; border-right-style: none; border-right-width: 2px; border-right-color: #D3D3D3; border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #A8A8A8; border-left-style: none; border-left-width: 2px; border-left-color: #D3D3D3; }
 #jrcudrlkjj .gt_caption { padding-top: 4px; padding-bottom: 4px; }
 #jrcudrlkjj .gt_title { color: #333333; font-size: 125%; font-weight: initial; padding-top: 4px; padding-bottom: 4px; padding-left: 5px; padding-right: 5px; border-bottom-color: #FFFFFF; border-bottom-width: 0; }
 #jrcudrlkjj .gt_subtitle { color: #333333; font-size: 85%; font-weight: initial; padding-top: 3px; padding-bottom: 5px; padding-left: 5px; padding-right: 5px; border-top-color: #FFFFFF; border-top-width: 0; }
 #jrcudrlkjj .gt_heading { background-color: #FFFFFF; text-align: center; border-bottom-color: #FFFFFF; border-left-style: none; border-left-width: 1px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 1px; border-right-color: #D3D3D3; }
 #jrcudrlkjj .gt_bottom_border { border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; }
 #jrcudrlkjj .gt_col_headings { border-top-style: solid; border-top-width: 2px; border-top-color: #D3D3D3; border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; border-left-style: none; border-left-width: 1px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 1px; border-right-color: #D3D3D3; }
 #jrcudrlkjj .gt_col_heading { color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: normal; text-transform: inherit; border-left-style: none; border-left-width: 1px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 1px; border-right-color: #D3D3D3; vertical-align: bottom; padding-top: 5px; padding-bottom: 5px; padding-left: 5px; padding-right: 5px; overflow-x: hidden; }
 #jrcudrlkjj .gt_column_spanner_outer { color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: normal; text-transform: inherit; padding-top: 0; padding-bottom: 0; padding-left: 4px; padding-right: 4px; }
 #jrcudrlkjj .gt_column_spanner_outer:first-child { padding-left: 0; }
 #jrcudrlkjj .gt_column_spanner_outer:last-child { padding-right: 0; }
 #jrcudrlkjj .gt_column_spanner { border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; vertical-align: bottom; padding-top: 5px; padding-bottom: 5px; overflow-x: hidden; display: inline-block; width: 100%; }
 #jrcudrlkjj .gt_spanner_row { border-bottom-style: hidden; }
 #jrcudrlkjj .gt_group_heading { padding-top: 8px; padding-bottom: 8px; padding-left: 5px; padding-right: 5px; color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: initial; text-transform: inherit; border-top-style: solid; border-top-width: 2px; border-top-color: #D3D3D3; border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; border-left-style: none; border-left-width: 1px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 1px; border-right-color: #D3D3D3; vertical-align: middle; text-align: left; }
 #jrcudrlkjj .gt_empty_group_heading { padding: 0.5px; color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: initial; border-top-style: solid; border-top-width: 2px; border-top-color: #D3D3D3; border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; vertical-align: middle; }
 #jrcudrlkjj .gt_from_md> :first-child { margin-top: 0; }
 #jrcudrlkjj .gt_from_md> :last-child { margin-bottom: 0; }
 #jrcudrlkjj .gt_row { padding-top: 8px; padding-bottom: 8px; padding-left: 5px; padding-right: 5px; margin: 10px; border-top-style: solid; border-top-width: 1px; border-top-color: #D3D3D3; border-left-style: none; border-left-width: 1px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 1px; border-right-color: #D3D3D3; vertical-align: middle; overflow-x: hidden; }
 #jrcudrlkjj .gt_stub { color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: initial; text-transform: inherit; border-right-style: solid; border-right-width: 2px; border-right-color: #D3D3D3; padding-left: 5px; padding-right: 5px; }
 #jrcudrlkjj .gt_indent_1 { text-indent: 5px; }
 #jrcudrlkjj .gt_indent_2 { text-indent: calc(5px * 2); }
 #jrcudrlkjj .gt_indent_3 { text-indent: calc(5px * 3); }
 #jrcudrlkjj .gt_indent_4 { text-indent: calc(5px * 4); }
 #jrcudrlkjj .gt_indent_5 { text-indent: calc(5px * 5); }
 #jrcudrlkjj .gt_stub_row_group { color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: initial; text-transform: inherit; border-right-style: solid; border-right-width: 2px; border-right-color: #D3D3D3; padding-left: 5px; padding-right: 5px; vertical-align: top; }
 #jrcudrlkjj .gt_row_group_first td { border-top-width: 2px; }
 #jrcudrlkjj .gt_row_group_first th { border-top-width: 2px; }
 #jrcudrlkjj .gt_striped { color: #333333; background-color: #F4F4F4; }
 #jrcudrlkjj .gt_table_body { border-top-style: solid; border-top-width: 2px; border-top-color: #D3D3D3; border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; }
 #jrcudrlkjj .gt_summary_row { color: #333333; background-color: #FFFFFF; text-transform: inherit; padding-top: 8px; padding-bottom: 8px; padding-left: 5px; padding-right: 5px; }
 #jrcudrlkjj .gt_first_summary_row { border-top-style: solid; border-top-width: 2px; border-top-color: #D3D3D3; }
 #jrcudrlkjj .gt_last_summary_row_top { border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; }
 #jrcudrlkjj .gt_grand_summary_row { color: #333333; background-color: #FFFFFF; text-transform: inherit; padding-top: 8px; padding-bottom: 8px; padding-left: 5px; padding-right: 5px; }
 #jrcudrlkjj .gt_first_grand_summary_row_bottom { border-top-style: double; border-top-width: 6px; border-top-color: #D3D3D3; }
 #jrcudrlkjj .gt_last_grand_summary_row_top { border-bottom-style: double; border-bottom-width: 6px; border-bottom-color: #D3D3D3; }
 #jrcudrlkjj .gt_sourcenotes { color: #333333; background-color: #FFFFFF; border-bottom-style: none; border-bottom-width: 2px; border-bottom-color: #D3D3D3; border-left-style: none; border-left-width: 2px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 2px; border-right-color: #D3D3D3; }
 #jrcudrlkjj .gt_sourcenote { font-size: 90%; padding-top: 4px; padding-bottom: 4px; padding-left: 5px; padding-right: 5px; text-align: left; }
 #jrcudrlkjj .gt_left { text-align: left; }
 #jrcudrlkjj .gt_center { text-align: center; }
 #jrcudrlkjj .gt_right { text-align: right; font-variant-numeric: tabular-nums; }
 #jrcudrlkjj .gt_font_normal { font-weight: normal; }
 #jrcudrlkjj .gt_font_bold { font-weight: bold; }
 #jrcudrlkjj .gt_font_italic { font-style: italic; }
 #jrcudrlkjj .gt_super { font-size: 65%; }
 #jrcudrlkjj .gt_footnotes { color: font-color(#FFFFFF); background-color: #FFFFFF; border-bottom-style: none; border-bottom-width: 2px; border-bottom-color: #D3D3D3; border-left-style: none; border-left-width: 2px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 2px; border-right-color: #D3D3D3; }
 #jrcudrlkjj .gt_footnote { margin: 0px; font-size: 90%; padding-top: 4px; padding-bottom: 4px; padding-left: 5px; padding-right: 5px; }
 #jrcudrlkjj .gt_sourcenotes { color: #333333; background-color: #FFFFFF; border-bottom-style: none; border-bottom-width: 2px; border-bottom-color: #D3D3D3; border-left-style: none; border-left-width: 2px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 2px; border-right-color: #D3D3D3; }
 #jrcudrlkjj .gt_sourcenote { font-size: 90%; padding-top: 4px; padding-bottom: 4px; padding-left: 5px; padding-right: 5px; text-align: left; }
 #jrcudrlkjj .gt_footnote_marks { font-size: 75%; vertical-align: 0.4em; position: initial; }
 #jrcudrlkjj .gt_asterisk { font-size: 100%; vertical-align: 0; }
 &#10;</style>

| DARKO forward validation — projection (t) vs realized RAPM (t+1) |  |  |  |
|----|----|----|----|
| out-of-sample by construction; weighted mean r = 0.288 over 28 season pairs |  |  |  |
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
| 2025 | 0.324 | 1.459 | 147 |

&#10;</div>

<img src="player_impact_files/figure-commonmark/cell-11-output-1.png"
width="420" height="300"
alt="DARKO forward correlation by projection season — modest and stable, capped by RAPM noise in the target." />

<div id="pgrjhrujui" style="padding-left:0px;padding-right:0px;padding-top:10px;padding-bottom:10px;overflow-x:auto;overflow-y:auto;width:auto;height:auto;">
<style>
#pgrjhrujui table {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Helvetica Neue', 'Fira Sans', 'Droid Sans', Arial, sans-serif;
          -webkit-font-smoothing: antialiased;
          -moz-osx-font-smoothing: grayscale;
        }
&#10;#pgrjhrujui thead, tbody, tfoot, tr, td, th { border-style: none; }
 tr { background-color: transparent; }
#pgrjhrujui p { margin: 0; padding: 0; }
 #pgrjhrujui .gt_table { display: table; border-collapse: collapse; line-height: normal; margin-left: auto; margin-right: auto; color: #333333; font-size: 16px; font-weight: normal; font-style: normal; background-color: #FFFFFF; width: auto; border-top-style: solid; border-top-width: 2px; border-top-color: #A8A8A8; border-right-style: none; border-right-width: 2px; border-right-color: #D3D3D3; border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #A8A8A8; border-left-style: none; border-left-width: 2px; border-left-color: #D3D3D3; }
 #pgrjhrujui .gt_caption { padding-top: 4px; padding-bottom: 4px; }
 #pgrjhrujui .gt_title { color: #333333; font-size: 125%; font-weight: initial; padding-top: 4px; padding-bottom: 4px; padding-left: 5px; padding-right: 5px; border-bottom-color: #FFFFFF; border-bottom-width: 0; }
 #pgrjhrujui .gt_subtitle { color: #333333; font-size: 85%; font-weight: initial; padding-top: 3px; padding-bottom: 5px; padding-left: 5px; padding-right: 5px; border-top-color: #FFFFFF; border-top-width: 0; }
 #pgrjhrujui .gt_heading { background-color: #FFFFFF; text-align: center; border-bottom-color: #FFFFFF; border-left-style: none; border-left-width: 1px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 1px; border-right-color: #D3D3D3; }
 #pgrjhrujui .gt_bottom_border { border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; }
 #pgrjhrujui .gt_col_headings { border-top-style: solid; border-top-width: 2px; border-top-color: #D3D3D3; border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; border-left-style: none; border-left-width: 1px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 1px; border-right-color: #D3D3D3; }
 #pgrjhrujui .gt_col_heading { color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: normal; text-transform: inherit; border-left-style: none; border-left-width: 1px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 1px; border-right-color: #D3D3D3; vertical-align: bottom; padding-top: 5px; padding-bottom: 5px; padding-left: 5px; padding-right: 5px; overflow-x: hidden; }
 #pgrjhrujui .gt_column_spanner_outer { color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: normal; text-transform: inherit; padding-top: 0; padding-bottom: 0; padding-left: 4px; padding-right: 4px; }
 #pgrjhrujui .gt_column_spanner_outer:first-child { padding-left: 0; }
 #pgrjhrujui .gt_column_spanner_outer:last-child { padding-right: 0; }
 #pgrjhrujui .gt_column_spanner { border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; vertical-align: bottom; padding-top: 5px; padding-bottom: 5px; overflow-x: hidden; display: inline-block; width: 100%; }
 #pgrjhrujui .gt_spanner_row { border-bottom-style: hidden; }
 #pgrjhrujui .gt_group_heading { padding-top: 8px; padding-bottom: 8px; padding-left: 5px; padding-right: 5px; color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: initial; text-transform: inherit; border-top-style: solid; border-top-width: 2px; border-top-color: #D3D3D3; border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; border-left-style: none; border-left-width: 1px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 1px; border-right-color: #D3D3D3; vertical-align: middle; text-align: left; }
 #pgrjhrujui .gt_empty_group_heading { padding: 0.5px; color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: initial; border-top-style: solid; border-top-width: 2px; border-top-color: #D3D3D3; border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; vertical-align: middle; }
 #pgrjhrujui .gt_from_md> :first-child { margin-top: 0; }
 #pgrjhrujui .gt_from_md> :last-child { margin-bottom: 0; }
 #pgrjhrujui .gt_row { padding-top: 8px; padding-bottom: 8px; padding-left: 5px; padding-right: 5px; margin: 10px; border-top-style: solid; border-top-width: 1px; border-top-color: #D3D3D3; border-left-style: none; border-left-width: 1px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 1px; border-right-color: #D3D3D3; vertical-align: middle; overflow-x: hidden; }
 #pgrjhrujui .gt_stub { color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: initial; text-transform: inherit; border-right-style: solid; border-right-width: 2px; border-right-color: #D3D3D3; padding-left: 5px; padding-right: 5px; }
 #pgrjhrujui .gt_indent_1 { text-indent: 5px; }
 #pgrjhrujui .gt_indent_2 { text-indent: calc(5px * 2); }
 #pgrjhrujui .gt_indent_3 { text-indent: calc(5px * 3); }
 #pgrjhrujui .gt_indent_4 { text-indent: calc(5px * 4); }
 #pgrjhrujui .gt_indent_5 { text-indent: calc(5px * 5); }
 #pgrjhrujui .gt_stub_row_group { color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: initial; text-transform: inherit; border-right-style: solid; border-right-width: 2px; border-right-color: #D3D3D3; padding-left: 5px; padding-right: 5px; vertical-align: top; }
 #pgrjhrujui .gt_row_group_first td { border-top-width: 2px; }
 #pgrjhrujui .gt_row_group_first th { border-top-width: 2px; }
 #pgrjhrujui .gt_striped { color: #333333; background-color: #F4F4F4; }
 #pgrjhrujui .gt_table_body { border-top-style: solid; border-top-width: 2px; border-top-color: #D3D3D3; border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; }
 #pgrjhrujui .gt_summary_row { color: #333333; background-color: #FFFFFF; text-transform: inherit; padding-top: 8px; padding-bottom: 8px; padding-left: 5px; padding-right: 5px; }
 #pgrjhrujui .gt_first_summary_row { border-top-style: solid; border-top-width: 2px; border-top-color: #D3D3D3; }
 #pgrjhrujui .gt_last_summary_row_top { border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; }
 #pgrjhrujui .gt_grand_summary_row { color: #333333; background-color: #FFFFFF; text-transform: inherit; padding-top: 8px; padding-bottom: 8px; padding-left: 5px; padding-right: 5px; }
 #pgrjhrujui .gt_first_grand_summary_row_bottom { border-top-style: double; border-top-width: 6px; border-top-color: #D3D3D3; }
 #pgrjhrujui .gt_last_grand_summary_row_top { border-bottom-style: double; border-bottom-width: 6px; border-bottom-color: #D3D3D3; }
 #pgrjhrujui .gt_sourcenotes { color: #333333; background-color: #FFFFFF; border-bottom-style: none; border-bottom-width: 2px; border-bottom-color: #D3D3D3; border-left-style: none; border-left-width: 2px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 2px; border-right-color: #D3D3D3; }
 #pgrjhrujui .gt_sourcenote { font-size: 90%; padding-top: 4px; padding-bottom: 4px; padding-left: 5px; padding-right: 5px; text-align: left; }
 #pgrjhrujui .gt_left { text-align: left; }
 #pgrjhrujui .gt_center { text-align: center; }
 #pgrjhrujui .gt_right { text-align: right; font-variant-numeric: tabular-nums; }
 #pgrjhrujui .gt_font_normal { font-weight: normal; }
 #pgrjhrujui .gt_font_bold { font-weight: bold; }
 #pgrjhrujui .gt_font_italic { font-style: italic; }
 #pgrjhrujui .gt_super { font-size: 65%; }
 #pgrjhrujui .gt_footnotes { color: font-color(#FFFFFF); background-color: #FFFFFF; border-bottom-style: none; border-bottom-width: 2px; border-bottom-color: #D3D3D3; border-left-style: none; border-left-width: 2px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 2px; border-right-color: #D3D3D3; }
 #pgrjhrujui .gt_footnote { margin: 0px; font-size: 90%; padding-top: 4px; padding-bottom: 4px; padding-left: 5px; padding-right: 5px; }
 #pgrjhrujui .gt_sourcenotes { color: #333333; background-color: #FFFFFF; border-bottom-style: none; border-bottom-width: 2px; border-bottom-color: #D3D3D3; border-left-style: none; border-left-width: 2px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 2px; border-right-color: #D3D3D3; }
 #pgrjhrujui .gt_sourcenote { font-size: 90%; padding-top: 4px; padding-bottom: 4px; padding-left: 5px; padding-right: 5px; text-align: left; }
 #pgrjhrujui .gt_footnote_marks { font-size: 75%; vertical-align: 0.4em; position: initial; }
 #pgrjhrujui .gt_asterisk { font-size: 100%; vertical-align: 0; }
 &#10;</style>

| Reliability context for the forward validation |  |  |
|----|----|----|
| the projection's ceiling is bounded by how noisy the RAPM target itself is |  |  |
| check | pearson | pairs |
| RAPM year-over-year reliability (same player, adjacent seasons) | 0.271 | 3383 |
| adj-RAPM vs RAPM agreement (2026 RS) | 0.773 | 231 |

&#10;</div>

The forward-r is honest but modest, and the reliability row is why:
DARKO cannot correlate with next-season RAPM more than next-season RAPM
correlates with anything stable.

### Separating projection error from target noise

A single season of RAPM is a noisy realization of a player’s true level,
so a low forward correlation confounds *the projection being wrong* with
*the target being noisy*. Averaging the target over more post-projection
seasons (possession-weighted) reduces the target’s noise without
touching the projection. Restricting all three rows to the **same**
player-seasons keeps the comparison honest — a longer target window
would otherwise also change the population:

<div id="dybquarxbx" style="padding-left:0px;padding-right:0px;padding-top:10px;padding-bottom:10px;overflow-x:auto;overflow-y:auto;width:auto;height:auto;">
<style>
#dybquarxbx table {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Helvetica Neue', 'Fira Sans', 'Droid Sans', Arial, sans-serif;
          -webkit-font-smoothing: antialiased;
          -moz-osx-font-smoothing: grayscale;
        }
&#10;#dybquarxbx thead, tbody, tfoot, tr, td, th { border-style: none; }
 tr { background-color: transparent; }
#dybquarxbx p { margin: 0; padding: 0; }
 #dybquarxbx .gt_table { display: table; border-collapse: collapse; line-height: normal; margin-left: auto; margin-right: auto; color: #333333; font-size: 16px; font-weight: normal; font-style: normal; background-color: #FFFFFF; width: auto; border-top-style: solid; border-top-width: 2px; border-top-color: #A8A8A8; border-right-style: none; border-right-width: 2px; border-right-color: #D3D3D3; border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #A8A8A8; border-left-style: none; border-left-width: 2px; border-left-color: #D3D3D3; }
 #dybquarxbx .gt_caption { padding-top: 4px; padding-bottom: 4px; }
 #dybquarxbx .gt_title { color: #333333; font-size: 125%; font-weight: initial; padding-top: 4px; padding-bottom: 4px; padding-left: 5px; padding-right: 5px; border-bottom-color: #FFFFFF; border-bottom-width: 0; }
 #dybquarxbx .gt_subtitle { color: #333333; font-size: 85%; font-weight: initial; padding-top: 3px; padding-bottom: 5px; padding-left: 5px; padding-right: 5px; border-top-color: #FFFFFF; border-top-width: 0; }
 #dybquarxbx .gt_heading { background-color: #FFFFFF; text-align: center; border-bottom-color: #FFFFFF; border-left-style: none; border-left-width: 1px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 1px; border-right-color: #D3D3D3; }
 #dybquarxbx .gt_bottom_border { border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; }
 #dybquarxbx .gt_col_headings { border-top-style: solid; border-top-width: 2px; border-top-color: #D3D3D3; border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; border-left-style: none; border-left-width: 1px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 1px; border-right-color: #D3D3D3; }
 #dybquarxbx .gt_col_heading { color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: normal; text-transform: inherit; border-left-style: none; border-left-width: 1px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 1px; border-right-color: #D3D3D3; vertical-align: bottom; padding-top: 5px; padding-bottom: 5px; padding-left: 5px; padding-right: 5px; overflow-x: hidden; }
 #dybquarxbx .gt_column_spanner_outer { color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: normal; text-transform: inherit; padding-top: 0; padding-bottom: 0; padding-left: 4px; padding-right: 4px; }
 #dybquarxbx .gt_column_spanner_outer:first-child { padding-left: 0; }
 #dybquarxbx .gt_column_spanner_outer:last-child { padding-right: 0; }
 #dybquarxbx .gt_column_spanner { border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; vertical-align: bottom; padding-top: 5px; padding-bottom: 5px; overflow-x: hidden; display: inline-block; width: 100%; }
 #dybquarxbx .gt_spanner_row { border-bottom-style: hidden; }
 #dybquarxbx .gt_group_heading { padding-top: 8px; padding-bottom: 8px; padding-left: 5px; padding-right: 5px; color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: initial; text-transform: inherit; border-top-style: solid; border-top-width: 2px; border-top-color: #D3D3D3; border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; border-left-style: none; border-left-width: 1px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 1px; border-right-color: #D3D3D3; vertical-align: middle; text-align: left; }
 #dybquarxbx .gt_empty_group_heading { padding: 0.5px; color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: initial; border-top-style: solid; border-top-width: 2px; border-top-color: #D3D3D3; border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; vertical-align: middle; }
 #dybquarxbx .gt_from_md> :first-child { margin-top: 0; }
 #dybquarxbx .gt_from_md> :last-child { margin-bottom: 0; }
 #dybquarxbx .gt_row { padding-top: 8px; padding-bottom: 8px; padding-left: 5px; padding-right: 5px; margin: 10px; border-top-style: solid; border-top-width: 1px; border-top-color: #D3D3D3; border-left-style: none; border-left-width: 1px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 1px; border-right-color: #D3D3D3; vertical-align: middle; overflow-x: hidden; }
 #dybquarxbx .gt_stub { color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: initial; text-transform: inherit; border-right-style: solid; border-right-width: 2px; border-right-color: #D3D3D3; padding-left: 5px; padding-right: 5px; }
 #dybquarxbx .gt_indent_1 { text-indent: 5px; }
 #dybquarxbx .gt_indent_2 { text-indent: calc(5px * 2); }
 #dybquarxbx .gt_indent_3 { text-indent: calc(5px * 3); }
 #dybquarxbx .gt_indent_4 { text-indent: calc(5px * 4); }
 #dybquarxbx .gt_indent_5 { text-indent: calc(5px * 5); }
 #dybquarxbx .gt_stub_row_group { color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: initial; text-transform: inherit; border-right-style: solid; border-right-width: 2px; border-right-color: #D3D3D3; padding-left: 5px; padding-right: 5px; vertical-align: top; }
 #dybquarxbx .gt_row_group_first td { border-top-width: 2px; }
 #dybquarxbx .gt_row_group_first th { border-top-width: 2px; }
 #dybquarxbx .gt_striped { color: #333333; background-color: #F4F4F4; }
 #dybquarxbx .gt_table_body { border-top-style: solid; border-top-width: 2px; border-top-color: #D3D3D3; border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; }
 #dybquarxbx .gt_summary_row { color: #333333; background-color: #FFFFFF; text-transform: inherit; padding-top: 8px; padding-bottom: 8px; padding-left: 5px; padding-right: 5px; }
 #dybquarxbx .gt_first_summary_row { border-top-style: solid; border-top-width: 2px; border-top-color: #D3D3D3; }
 #dybquarxbx .gt_last_summary_row_top { border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; }
 #dybquarxbx .gt_grand_summary_row { color: #333333; background-color: #FFFFFF; text-transform: inherit; padding-top: 8px; padding-bottom: 8px; padding-left: 5px; padding-right: 5px; }
 #dybquarxbx .gt_first_grand_summary_row_bottom { border-top-style: double; border-top-width: 6px; border-top-color: #D3D3D3; }
 #dybquarxbx .gt_last_grand_summary_row_top { border-bottom-style: double; border-bottom-width: 6px; border-bottom-color: #D3D3D3; }
 #dybquarxbx .gt_sourcenotes { color: #333333; background-color: #FFFFFF; border-bottom-style: none; border-bottom-width: 2px; border-bottom-color: #D3D3D3; border-left-style: none; border-left-width: 2px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 2px; border-right-color: #D3D3D3; }
 #dybquarxbx .gt_sourcenote { font-size: 90%; padding-top: 4px; padding-bottom: 4px; padding-left: 5px; padding-right: 5px; text-align: left; }
 #dybquarxbx .gt_left { text-align: left; }
 #dybquarxbx .gt_center { text-align: center; }
 #dybquarxbx .gt_right { text-align: right; font-variant-numeric: tabular-nums; }
 #dybquarxbx .gt_font_normal { font-weight: normal; }
 #dybquarxbx .gt_font_bold { font-weight: bold; }
 #dybquarxbx .gt_font_italic { font-style: italic; }
 #dybquarxbx .gt_super { font-size: 65%; }
 #dybquarxbx .gt_footnotes { color: font-color(#FFFFFF); background-color: #FFFFFF; border-bottom-style: none; border-bottom-width: 2px; border-bottom-color: #D3D3D3; border-left-style: none; border-left-width: 2px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 2px; border-right-color: #D3D3D3; }
 #dybquarxbx .gt_footnote { margin: 0px; font-size: 90%; padding-top: 4px; padding-bottom: 4px; padding-left: 5px; padding-right: 5px; }
 #dybquarxbx .gt_sourcenotes { color: #333333; background-color: #FFFFFF; border-bottom-style: none; border-bottom-width: 2px; border-bottom-color: #D3D3D3; border-left-style: none; border-left-width: 2px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 2px; border-right-color: #D3D3D3; }
 #dybquarxbx .gt_sourcenote { font-size: 90%; padding-top: 4px; padding-bottom: 4px; padding-left: 5px; padding-right: 5px; text-align: left; }
 #dybquarxbx .gt_footnote_marks { font-size: 75%; vertical-align: 0.4em; position: initial; }
 #dybquarxbx .gt_asterisk { font-size: 100%; vertical-align: 0; }
 &#10;</style>

| DARKO against a multi-season blended target |  |  |  |  |  |  |
|----|----|----|----|----|----|----|
| same player-seasons in every row; only the target's noise changes |  |  |  |  |  |  |
| target | n | r (DARKO) | r (carry-forward RAPM) | MAE (DARKO) | MAE (carry-forward) | sd_target |
| next season only | 1885 | 0.259 | 0.270 | 1.447 | 1.486 | 1.550 |
| 2-season RAPM | 1885 | 0.269 | 0.277 | 1.327 | 1.368 | 1.299 |
| 3-season RAPM | 1885 | 0.287 | 0.296 | 1.252 | 1.299 | 1.152 |

&#10;</div>

Two readings, both worth stating plainly:

- **Part of the “modest” forward-r is target noise, but less of it than
  in the NBA.** Holding the projection and the population fixed and only
  widening the target window lifts the correlation from ≈0.26 to ≈0.29
  (the NBA twin, measured the same way, moves ≈0.37 → ≈0.44). Averaging
  more WNBA seasons removes less noise because there are fewer
  possessions in each of them and because rosters turn over faster — so
  a WNBA player’s three-season blend is a blurrier picture of “the same
  player” than an NBA player’s is.
- **The projection is not beating simple persistence on rank.** Carrying
  season-*t* RAPM forward unchanged correlates with every target
  slightly better than the DARKO projection does. Where the projection
  earns its keep is **level**: its MAE is lower against every target,
  which is what shrinkage toward the aging-curve mean buys. Treat
  `darko_projected_rating` as a better-calibrated magnitude, not a
  better ordering — and the gap to persistence is the honest measure of
  what the Kalman step adds.

**The publish floors.** The five internal diagnostics above are now
frozen as **publish-blocking floors** in `models/REGISTRY.md` and
`wnba_model_publish/gates.py`, each set strictly below the value
observed on the 2026-07-29 release across all 30 published seasons; the
gate runs on every `impact` invocation and writes its report into the
card sidecar under `publish_gates`. The floors were **re-measured on
WNBA data rather than inherited from the NBA twin** — the forward ones
land at roughly half the NBA’s, because a ~40-game season leaves less
signal in each RAPM fit. The one gate family the twin has and this repo
does not is the oracle pair: no public WNBA player-impact metric
comparable to Ryan Davis RAPM or Dunks & Threes EPM is available here,
so instead of an always-skipped gate that could be mistaken for
coverage, concurrent validity is simply **not currently gated for the
WNBA** — the earlier claim that these engines were proxy-validated
against published oracle CSVs was inherited from the NBA writeup and did
not hold for this league.

## Results

<div id="knhjgpnwif" style="padding-left:0px;padding-right:0px;padding-top:10px;padding-bottom:10px;overflow-x:auto;overflow-y:auto;width:auto;height:auto;">
<style>
#knhjgpnwif table {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Helvetica Neue', 'Fira Sans', 'Droid Sans', Arial, sans-serif;
          -webkit-font-smoothing: antialiased;
          -moz-osx-font-smoothing: grayscale;
        }
&#10;#knhjgpnwif thead, tbody, tfoot, tr, td, th { border-style: none; }
 tr { background-color: transparent; }
#knhjgpnwif p { margin: 0; padding: 0; }
 #knhjgpnwif .gt_table { display: table; border-collapse: collapse; line-height: normal; margin-left: auto; margin-right: auto; color: #333333; font-size: 16px; font-weight: normal; font-style: normal; background-color: #FFFFFF; width: auto; border-top-style: solid; border-top-width: 2px; border-top-color: #A8A8A8; border-right-style: none; border-right-width: 2px; border-right-color: #D3D3D3; border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #A8A8A8; border-left-style: none; border-left-width: 2px; border-left-color: #D3D3D3; }
 #knhjgpnwif .gt_caption { padding-top: 4px; padding-bottom: 4px; }
 #knhjgpnwif .gt_title { color: #333333; font-size: 125%; font-weight: initial; padding-top: 4px; padding-bottom: 4px; padding-left: 5px; padding-right: 5px; border-bottom-color: #FFFFFF; border-bottom-width: 0; }
 #knhjgpnwif .gt_subtitle { color: #333333; font-size: 85%; font-weight: initial; padding-top: 3px; padding-bottom: 5px; padding-left: 5px; padding-right: 5px; border-top-color: #FFFFFF; border-top-width: 0; }
 #knhjgpnwif .gt_heading { background-color: #FFFFFF; text-align: center; border-bottom-color: #FFFFFF; border-left-style: none; border-left-width: 1px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 1px; border-right-color: #D3D3D3; }
 #knhjgpnwif .gt_bottom_border { border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; }
 #knhjgpnwif .gt_col_headings { border-top-style: solid; border-top-width: 2px; border-top-color: #D3D3D3; border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; border-left-style: none; border-left-width: 1px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 1px; border-right-color: #D3D3D3; }
 #knhjgpnwif .gt_col_heading { color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: normal; text-transform: inherit; border-left-style: none; border-left-width: 1px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 1px; border-right-color: #D3D3D3; vertical-align: bottom; padding-top: 5px; padding-bottom: 5px; padding-left: 5px; padding-right: 5px; overflow-x: hidden; }
 #knhjgpnwif .gt_column_spanner_outer { color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: normal; text-transform: inherit; padding-top: 0; padding-bottom: 0; padding-left: 4px; padding-right: 4px; }
 #knhjgpnwif .gt_column_spanner_outer:first-child { padding-left: 0; }
 #knhjgpnwif .gt_column_spanner_outer:last-child { padding-right: 0; }
 #knhjgpnwif .gt_column_spanner { border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; vertical-align: bottom; padding-top: 5px; padding-bottom: 5px; overflow-x: hidden; display: inline-block; width: 100%; }
 #knhjgpnwif .gt_spanner_row { border-bottom-style: hidden; }
 #knhjgpnwif .gt_group_heading { padding-top: 8px; padding-bottom: 8px; padding-left: 5px; padding-right: 5px; color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: initial; text-transform: inherit; border-top-style: solid; border-top-width: 2px; border-top-color: #D3D3D3; border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; border-left-style: none; border-left-width: 1px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 1px; border-right-color: #D3D3D3; vertical-align: middle; text-align: left; }
 #knhjgpnwif .gt_empty_group_heading { padding: 0.5px; color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: initial; border-top-style: solid; border-top-width: 2px; border-top-color: #D3D3D3; border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; vertical-align: middle; }
 #knhjgpnwif .gt_from_md> :first-child { margin-top: 0; }
 #knhjgpnwif .gt_from_md> :last-child { margin-bottom: 0; }
 #knhjgpnwif .gt_row { padding-top: 8px; padding-bottom: 8px; padding-left: 5px; padding-right: 5px; margin: 10px; border-top-style: solid; border-top-width: 1px; border-top-color: #D3D3D3; border-left-style: none; border-left-width: 1px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 1px; border-right-color: #D3D3D3; vertical-align: middle; overflow-x: hidden; }
 #knhjgpnwif .gt_stub { color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: initial; text-transform: inherit; border-right-style: solid; border-right-width: 2px; border-right-color: #D3D3D3; padding-left: 5px; padding-right: 5px; }
 #knhjgpnwif .gt_indent_1 { text-indent: 5px; }
 #knhjgpnwif .gt_indent_2 { text-indent: calc(5px * 2); }
 #knhjgpnwif .gt_indent_3 { text-indent: calc(5px * 3); }
 #knhjgpnwif .gt_indent_4 { text-indent: calc(5px * 4); }
 #knhjgpnwif .gt_indent_5 { text-indent: calc(5px * 5); }
 #knhjgpnwif .gt_stub_row_group { color: #333333; background-color: #FFFFFF; font-size: 100%; font-weight: initial; text-transform: inherit; border-right-style: solid; border-right-width: 2px; border-right-color: #D3D3D3; padding-left: 5px; padding-right: 5px; vertical-align: top; }
 #knhjgpnwif .gt_row_group_first td { border-top-width: 2px; }
 #knhjgpnwif .gt_row_group_first th { border-top-width: 2px; }
 #knhjgpnwif .gt_striped { color: #333333; background-color: #F4F4F4; }
 #knhjgpnwif .gt_table_body { border-top-style: solid; border-top-width: 2px; border-top-color: #D3D3D3; border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; }
 #knhjgpnwif .gt_summary_row { color: #333333; background-color: #FFFFFF; text-transform: inherit; padding-top: 8px; padding-bottom: 8px; padding-left: 5px; padding-right: 5px; }
 #knhjgpnwif .gt_first_summary_row { border-top-style: solid; border-top-width: 2px; border-top-color: #D3D3D3; }
 #knhjgpnwif .gt_last_summary_row_top { border-bottom-style: solid; border-bottom-width: 2px; border-bottom-color: #D3D3D3; }
 #knhjgpnwif .gt_grand_summary_row { color: #333333; background-color: #FFFFFF; text-transform: inherit; padding-top: 8px; padding-bottom: 8px; padding-left: 5px; padding-right: 5px; }
 #knhjgpnwif .gt_first_grand_summary_row_bottom { border-top-style: double; border-top-width: 6px; border-top-color: #D3D3D3; }
 #knhjgpnwif .gt_last_grand_summary_row_top { border-bottom-style: double; border-bottom-width: 6px; border-bottom-color: #D3D3D3; }
 #knhjgpnwif .gt_sourcenotes { color: #333333; background-color: #FFFFFF; border-bottom-style: none; border-bottom-width: 2px; border-bottom-color: #D3D3D3; border-left-style: none; border-left-width: 2px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 2px; border-right-color: #D3D3D3; }
 #knhjgpnwif .gt_sourcenote { font-size: 90%; padding-top: 4px; padding-bottom: 4px; padding-left: 5px; padding-right: 5px; text-align: left; }
 #knhjgpnwif .gt_left { text-align: left; }
 #knhjgpnwif .gt_center { text-align: center; }
 #knhjgpnwif .gt_right { text-align: right; font-variant-numeric: tabular-nums; }
 #knhjgpnwif .gt_font_normal { font-weight: normal; }
 #knhjgpnwif .gt_font_bold { font-weight: bold; }
 #knhjgpnwif .gt_font_italic { font-style: italic; }
 #knhjgpnwif .gt_super { font-size: 65%; }
 #knhjgpnwif .gt_footnotes { color: font-color(#FFFFFF); background-color: #FFFFFF; border-bottom-style: none; border-bottom-width: 2px; border-bottom-color: #D3D3D3; border-left-style: none; border-left-width: 2px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 2px; border-right-color: #D3D3D3; }
 #knhjgpnwif .gt_footnote { margin: 0px; font-size: 90%; padding-top: 4px; padding-bottom: 4px; padding-left: 5px; padding-right: 5px; }
 #knhjgpnwif .gt_sourcenotes { color: #333333; background-color: #FFFFFF; border-bottom-style: none; border-bottom-width: 2px; border-bottom-color: #D3D3D3; border-left-style: none; border-left-width: 2px; border-left-color: #D3D3D3; border-right-style: none; border-right-width: 2px; border-right-color: #D3D3D3; }
 #knhjgpnwif .gt_sourcenote { font-size: 90%; padding-top: 4px; padding-bottom: 4px; padding-left: 5px; padding-right: 5px; text-align: left; }
 #knhjgpnwif .gt_footnote_marks { font-size: 75%; vertical-align: 0.4em; position: initial; }
 #knhjgpnwif .gt_asterisk { font-size: 100%; vertical-align: 0; }
 &#10;</style>

| Top 15 by WAR — 2026 regular season (min 300 minutes) |  |  |  |  |  |  |  |  |
|----|----|----|----|----|----|----|----|----|
|  | Player | Team | GP | Min | RAPM | adj-RAPM | BPM | WAR |
| <img
src="https://cdn.wnba.com/headshots/wnba/latest/1040x760/1627675.png"
height="40" /> | Courtney Williams | MIN | 28 | 862 | 2.46 | 8.45 | 8.20 | 6.68 |
| <img
src="https://cdn.wnba.com/headshots/wnba/latest/1040x760/1631007.png"
height="40" /> | Veronica Burton | GSV | 27 | 763 | 2.87 | 13.12 | 13.48 | 6.51 |
| <img
src="https://cdn.wnba.com/headshots/wnba/latest/1040x760/203825.png"
height="40" /> | Kayla McBride | MIN | 28 | 908 | 1.80 | 2.01 | 10.58 | 6.23 |
| <img
src="https://cdn.wnba.com/headshots/wnba/latest/1040x760/1628909.png"
height="40" /> | Kelsey Mitchell | IND | 27 | 871 | 1.77 | 5.30 | 7.90 | 6.19 |
| <img
src="https://cdn.wnba.com/headshots/wnba/latest/1040x760/1629498.png"
height="40" /> | Jackie Young | LVA | 26 | 838 | 1.91 | 6.09 | 8.08 | 5.97 |
| <img
src="https://cdn.wnba.com/headshots/wnba/latest/1040x760/1643426.png"
height="40" /> | Olivia Miles | MIN | 26 | 801 | 1.88 | 4.69 | 12.61 | 5.84 |
| <img
src="https://cdn.wnba.com/headshots/wnba/latest/1040x760/203827.png"
height="40" /> | Natasha Howard | MIN | 28 | 831 | 1.97 | 4.05 | 10.77 | 5.72 |
| <img
src="https://cdn.wnba.com/headshots/wnba/latest/1040x760/1642291.png"
height="40" /> | Angel Reese | ATL | 25 | 760 | 1.78 | 10.62 | 3.35 | 5.67 |
| <img
src="https://cdn.wnba.com/headshots/wnba/latest/1040x760/203833.png"
height="40" /> | Chelsea Gray | LVA | 26 | 858 | 1.23 | 2.23 | 6.57 | 5.05 |
| <img
src="https://cdn.wnba.com/headshots/wnba/latest/1040x760/203866.png"
height="40" /> | Kayla Thornton | GSV | 27 | 682 | 2.56 | 8.45 | 6.79 | 5.03 |
| <img
src="https://cdn.wnba.com/headshots/wnba/latest/1040x760/1629491.png"
height="40" /> | Jessica Shepard | DAL | 27 | 899 | 1.33 | 4.66 | 8.83 | 4.98 |
| <img
src="https://cdn.wnba.com/headshots/wnba/latest/1040x760/1628932.png"
height="40" /> | A'ja Wilson | LVA | 24 | 762 | 1.41 | 3.43 | 10.80 | 4.86 |
| <img
src="https://cdn.wnba.com/headshots/wnba/latest/1040x760/1631044.png"
height="40" /> | Naz Hillmon | ATL | 25 | 748 | 1.46 | 8.25 | 3.52 | 4.79 |
| <img
src="https://cdn.wnba.com/headshots/wnba/latest/1040x760/1642784.png"
height="40" /> | Paige Bueckers | DAL | 25 | 839 | 0.97 | 1.75 | 8.47 | 4.61 |
| <img
src="https://cdn.wnba.com/headshots/wnba/latest/1040x760/1627668.png"
height="40" /> | Breanna Stewart | NYL | 26 | 869 | 0.73 | 2.08 | 5.55 | 4.34 |

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

**Resolved (2026-09-01, PR \#15):**

- **Numeric publish floors are encoded** — five gates in
  `wnba_model_publish/gates.py`, each floor strictly below the value
  observed on the 2026-07-29 release across all 30 seasons, evaluated on
  every build and recorded in the card sidecar. The table (floor,
  observation, what it catches) lives in `models/REGISTRY.md`. Measured
  on WNBA data, not ported from the NBA twin.
- **The SPM coefficient vector ships** as the additive
  `wnba_player_impact_spm_coefficients.json` sidecar, and the
  Attribution section above shows real coefficient importance from it.
- **DARKO ceiling quantified** — the multi-season blended-target
  comparison separates projection error from target noise and states the
  projection’s standing against a carry-forward baseline.

Still open:

- **Uncertainty** — no engine ships an interval. The NBA twin’s
  prototype (cluster bootstrap by GAME, never by row) measured a median
  RAPM standard error *wider than the cross-sectional spread of RAPM
  itself* on a full 1,230-game season; a WNBA season is a third the
  size, so the same resample here should be expected to be wider still,
  and the prototype has not yet been run on this league’s possessions.
  Shipping it means B ≥ 200 replicates, an additive `rapm_se` column,
  and a floor on the interval’s own stability.
- **No public concurrent-validity oracle** for WNBA player impact. If
  one becomes available, the NBA twin’s oracle gate pair ports over
  directly.
- **PlayIn season type is unsupported** by design; revisit if the sample
  ever justifies it.
