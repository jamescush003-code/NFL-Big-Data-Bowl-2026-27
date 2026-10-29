"""Step 4: link BDB WRs to nflverse and add career totals (all available regular seasons, incl. the current one)."""
import re
from pathlib import Path

import nflreadpy as nfl
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed"


def norm_name(s):
    s = re.sub(r"[^a-z ]", "", str(s).lower().replace("-", " "))
    return " ".join(w for w in s.split() if w not in {"jr", "sr", "ii", "iii", "iv", "v"})


def crosswalk(master, players):
    players = players.assign(nid=pd.to_numeric(players.nfl_id, errors="coerce"))
    by_id = master[["nfl_id"]].merge(players[["nid", "gsis_id", "pfr_id"]].dropna(subset=["nid"]),
                                     left_on="nfl_id", right_on="nid").drop(columns="nid").assign(match="nfl_id")
    rest = master[~master.nfl_id.isin(by_id.nfl_id)].assign(key=lambda d: d.display_name.map(norm_name))
    wr = players[players.position == "WR"].assign(key=lambda d: d.display_name.map(norm_name))
    wr = wr[~wr.key.duplicated(keep=False)]  # ambiguous names can't be matched safely
    by_name = rest.merge(wr[["key", "gsis_id", "pfr_id"]], on="key")[["nfl_id", "gsis_id", "pfr_id"]].assign(match="name+position")
    xw = pd.concat([by_id, by_name], ignore_index=True)
    assert xw.nfl_id.is_unique
    n = len(master)
    print(f"Match: {len(by_id)}/{n} by nfl_id, {len(by_name)} more by name+position -> {len(xw)}/{n} ({len(xw) / n:.1%})")
    missing = master.loc[~master.nfl_id.isin(xw.nfl_id), "display_name"].tolist()
    print("Unmatched:", missing)
    return xw


def career(xw):
    seasons = list(range(2023, nfl.get_current_season() + 1))  # every WR in the pool was drafted 2023+
    ps = nfl.load_player_stats(seasons).to_pandas()
    ps = ps[(ps.season_type == "REG") & ps.player_id.isin(xw.gsis_id)]
    team = nfl.load_team_stats(seasons).to_pandas()
    team = team[team.season_type == "REG"][["season", "week", "team", "targets"]].rename(columns={"targets": "team_targets"})
    ps = ps.merge(team, on=["season", "week", "team"], how="left")
    stat_games = ps.groupby("player_id").agg(
        career_targets=("targets", "sum"), career_receptions=("receptions", "sum"),
        career_receiving_yards=("receiving_yards", "sum"), career_receiving_tds=("receiving_tds", "sum"),
        career_receiving_epa=("receiving_epa", "sum"), career_team_targets=("team_targets", "sum"),
        stat_games=("game_id", "nunique"), stat_seasons=("season", "nunique"), last_stat_season=("season", "max"))

    snaps = nfl.load_snap_counts(seasons).to_pandas()
    snaps = snaps[(snaps.game_type == "REG") & (snaps.offense_snaps > 0) & snaps.pfr_player_id.isin(xw.pfr_id)]
    snap_games = snaps.groupby("pfr_player_id").agg(
        snap_games=("game_id", "nunique"), snap_seasons=("season", "nunique"),
        career_offense_snaps_nv=("offense_snaps", "sum"), avg_offense_snap_pct=("offense_pct", "mean"))

    c = (xw.merge(stat_games, left_on="gsis_id", right_index=True, how="left")
         .merge(snap_games, left_on="pfr_id", right_index=True, how="left"))
    # player_stats only has weeks where a player recorded a stat, so snap counts are the better games-played source
    c["career_games_played"] = c[["snap_games", "stat_games"]].max(axis=1)
    c["career_seasons"] = c[["snap_seasons", "stat_seasons"]].max(axis=1)
    c["career_target_share"] = c.career_targets / c.career_team_targets
    print(f"nflverse seasons used: {seasons[0]}-{seasons[-1]} (REG)")
    return c


if __name__ == "__main__":
    master = pd.read_parquet(OUT / "wr_master.parquet")
    players = nfl.load_players().to_pandas()
    xw = crosswalk(master, players)
    c = career(xw)
    m = master.merge(c, on="nfl_id", how="left").merge(
        players[["gsis_id", "latest_team", "status"]], on="gsis_id", how="left")
    # BDB career table is the fallback for games/seasons if nflverse has nothing; starts only exist there
    m["career_games_played"] = m.career_games_played.fillna(m.career_games_active).fillna(0)
    m["career_seasons"] = m.career_seasons.fillna(m.bdb_seasons).fillna(0)
    m["career_games_started"] = m.career_games_started.fillna(0)
    for col in ["career_targets", "career_receptions", "career_receiving_yards", "career_receiving_tds", "career_receiving_epa"]:
        m[col] = m[col].fillna(0)
    m["team"] = m.latest_team.fillna(m.bdb_team)
    assert m.nfl_id.is_unique
    m.to_parquet(OUT / "wr_career_master.parquet", index=False)
    m.to_csv(OUT / "wr_career_master.csv", index=False)
    print(f"wr_career_master: {len(m)} WRs, {m.columns.size} columns")
    print(m.sort_values("career_receiving_yards", ascending=False)[
        ["display_name", "team", "career_games_played", "career_games_started", "career_seasons",
         "career_targets", "career_receiving_yards", "receiving_yards", "career_receiving_tds", "career_target_share"]
    ].head(12).to_string(index=False))
