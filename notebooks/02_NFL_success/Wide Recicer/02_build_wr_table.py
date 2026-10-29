"""Step 3: one row per WR from the competition data (player_play + games + tracking + career successes)."""
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.csv as pv

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
SEASON_TYPES = ["REG"]  # regular season only, to match nflverse career totals
MPS_TO_MPH = 2.04545  # tracking speed is yards/second


def load_wrs():
    players = pd.read_csv(RAW / "players.csv")
    print("nfl_position values:", sorted(players.nfl_position.unique()))
    return players[players.nfl_position == "WR"].copy()


def per_play_tracking(wr_ids):
    """Max speed per (WR, play), streamed one block at a time and filtered to WR ids before pandas sees it."""
    ids = pa.array(sorted(wr_ids), pa.int64())
    parts = []
    for csv in sorted(RAW.glob("game_tracking_*.csv")):
        reader = pv.open_csv(
            csv,
            read_options=pv.ReadOptions(block_size=64 << 20),
            convert_options=pv.ConvertOptions(include_columns=["game_id", "play_id", "nfl_id", "s"],
                                              null_values=["NA", ""]),
        )
        for batch in reader:
            batch = batch.filter(pc.is_in(batch["nfl_id"], value_set=ids))
            if batch.num_rows:
                parts.append(batch.to_pandas().groupby(["nfl_id", "game_id", "play_id"]).s.max())
        print(f"  streamed {csv.name}")
    # a play can straddle two blocks, so take the max of partial maxes
    return pd.concat(parts).groupby(level=[0, 1, 2]).max().rename("play_max_speed").reset_index()


def build():
    wrs = load_wrs()
    games = pd.read_csv(RAW / "games.csv")
    pp = pd.read_csv(RAW / "player_play.csv", low_memory=False)
    pp = pp[pp.nfl_id.isin(wrs.nfl_id)].merge(games[["game_id", "season", "season_type"]], on="game_id")
    pp = pp[pp.season_type.isin(SEASON_TYPES) & (pp.play_nullified_by_penalty != "Y")]

    pp["is_route"] = pp.route_ran.notna()
    pp["is_target"] = pp.target.fillna(False).astype(bool)
    pp["is_rec"] = pp.is_target & (pp.pass_result == "C")
    desc = pp.play_description.fillna("")
    # shortcut: TD parsed from play text; a rare defensive return TD after a catch would count. nflverse TDs are used for scoring.
    pp["is_td"] = pp.is_rec & desc.str.contains("TOUCHDOWN") & ~desc.str.contains("NULLIFIED")
    pp["is_slot"] = pp.lined_up_position == "SLOT_WR"
    pp["yacoe"] = pp.yards_after_catch - pp.expected_yards_after_catch

    tgt = pp[pp.is_target]
    rec = pp[pp.is_rec]
    g = pp.groupby("nfl_id")
    t = pp.assign(tgt_epa=pp.expected_points_added.where(pp.is_target),
                  tgt_air=pp.pass_length.where(pp.is_target),
                  rec_yds=pp.rec_yards.where(pp.is_rec),
                  rec_yac=pp.yards_after_catch.where(pp.is_rec),
                  rec_yacoe=pp.yacoe.where(pp.is_rec)).groupby("nfl_id")
    stats = pd.DataFrame({
        "bdb_games": g.game_id.nunique(),
        "bdb_seasons": g.season.nunique(),
        "routes_run": g.is_route.sum(),
        "targets": g.is_target.sum(),
        "receptions": g.is_rec.sum(),
        "receiving_yards": t.rec_yds.sum(),
        "receiving_tds": g.is_td.sum(),
        "epa_total_targets": t.tgt_epa.sum(),
        "air_yards": t.tgt_air.sum(),
        "yac": t.rec_yac.sum(),
        "yac_over_expected": t.rec_yacoe.sum(),
        "avg_separation_at_throw": g.separation_at_pass_forward.mean(),
        "avg_cushion": g.cushion.mean(),
        "slot_rate": g.is_slot.mean(),
    })
    stats["catch_rate"] = stats.receptions / stats.targets
    stats["targets_per_route"] = stats.targets / stats.routes_run
    stats["yards_per_route_run"] = stats.receiving_yards / stats.routes_run
    stats["epa_per_target"] = stats.epa_total_targets / stats.targets
    stats["adot"] = stats.air_yards / stats.targets
    stats["yac_per_rec"] = stats.yac / stats.receptions
    stats["yacoe_per_rec"] = stats.yac_over_expected / stats.receptions
    stats["avg_separation_on_targets"] = tgt.groupby("nfl_id").separation_at_pass_forward.mean()
    last = pp.sort_values(["season", "game_id"]).groupby("nfl_id").tail(1).set_index("nfl_id")
    stats["bdb_team"] = last.team_abbr

    # tracking: speed on route plays only
    trk = per_play_tracking(set(wrs.nfl_id)).merge(
        pp.loc[pp.is_route, ["nfl_id", "game_id", "play_id"]], on=["nfl_id", "game_id", "play_id"])
    trk["play_max_speed"] *= MPS_TO_MPH
    tg = trk.groupby("nfl_id").play_max_speed
    stats["tracked_routes"] = tg.size()
    stats["avg_route_max_speed_mph"] = tg.mean()
    stats["top_speed_mph"] = tg.quantile(0.95)  # 95th pct of per-route max: robust to tracking spikes

    career = pd.read_csv(RAW / "player_career_successes.csv")
    keep = ["nfl_id", "display_name", "draft_year", "draft_round", "draft_overall_pick", "college_name", "birth_date"]
    master = (wrs[keep].merge(stats, left_on="nfl_id", right_index=True, how="left")
              .merge(career, on="nfl_id", how="left"))
    counts = ["bdb_games", "bdb_seasons", "routes_run", "targets", "receptions", "receiving_yards", "receiving_tds", "tracked_routes"]
    master[counts] = master[counts].fillna(0).astype(int)
    assert master.nfl_id.is_unique, "expected one row per WR"
    return master


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    m = build()
    m.to_parquet(OUT / "wr_master.parquet", index=False)
    m.to_csv(OUT / "wr_master.csv", index=False)
    print(f"wr_master: {len(m)} WRs, {m.columns.size} columns, {int((m.routes_run > 0).sum())} with a regular-season route")
    print(m.sort_values("receiving_yards", ascending=False)[
        ["display_name", "bdb_team", "routes_run", "targets", "receiving_yards", "receiving_tds",
         "yards_per_route_run", "top_speed_mph"]].head(10).to_string(index=False))
