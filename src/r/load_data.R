#src/r/load_data.R
#Shared functions for loading competition data from data/
# Everyone should load data through these so we all use the same versions 

library(data.table)
data_dir <- here::here("data")

#Smaller tables: safe to load all at once
load_core_tables <- function(){
  list(
    players = fread(file.path(data_dir, "players.csv")),
    combine = fread(file.path(data_dir, "combine_results.csv")),
    careers = fread(file.path(data_dir, "player_career_successes.csv")),
    games   = fread(file.path(data_dir, "games.csv")),
    plays   = fread(file.path(data_dir, "player_play.csv"))
  )
}

# Large tracking tables: load only when needed
load_combine_tracking <- function(){
  fread(file.path(data_dir, "combine_tracking.csv"))
}

load_game_tracking <- function(season){
  fread(file.path(data_dir, paste0("game_tracking_", season, ".csv")))
}