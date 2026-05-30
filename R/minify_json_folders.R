# One-off helper: minify (un-prettify) the per-game JSON cache in place.
# Sequential by design -- this repo avoids furrr/future entirely (see the pbp
# scrapers' rate-limit notes); this is local file I/O with no API calls, so
# plain purrr::walk is fine.

team_box_list <- list.files(path = glue::glue('wbb/json/final/'))
team_box_game_ids <- as.integer(gsub('.json', '', team_box_list))

purrr::walk(team_box_game_ids, function(x){
  resp <- glue::glue('wbb/json/final/{x}.json') %>%
    jsonlite::fromJSON()
  jsonlite::write_json(resp, glue::glue('wbb/json/final/{x}.json'), prettify = 0)
  invisible(NULL)
})


team_box_list <- list.files(path = glue::glue('wbb/json/raw/'))
team_box_game_ids <- as.integer(gsub('.json', '', team_box_list))

purrr::walk(team_box_game_ids, function(x){
  resp <- glue::glue('wbb/json/raw/{x}.json') %>%
    jsonlite::fromJSON()
  jsonlite::write_json(resp, glue::glue('wbb/json/raw/{x}.json'), prettify = 0)
  invisible(NULL)
})
