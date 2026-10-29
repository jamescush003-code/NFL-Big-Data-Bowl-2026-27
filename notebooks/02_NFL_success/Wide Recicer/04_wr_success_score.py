"""Step 5: career WR Success Score (0-100)."""
from pathlib import Path

import pandas as pd

# ---- config: edit these -------------------------------------------------------------
WEIGHTS = {"production": 0.35, "efficiency": 0.30, "role": 0.15, "longevity": 0.15, "honors": 0.05}
PER_GAME_WEIGHT = 0.6  # production: share from per-game rates; the rest from career totals (rewards longevity)
# shrinkage strength in pseudo-observations: a player with n == k sits halfway between himself and league average
SHRINK_K = {"targets": 50, "routes": 150, "games": 8, "team_targets": 300}
HONOR_POINTS = {"ap_all_pro_1st_team": 3, "ap_all_pro_2nd_team": 2, "pro_bowl_original_ballot": 1}
# --------------------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed"


def shrink(num, n, k):
    """Empirical-Bayes style: pull rate num/n toward the pooled league rate with k pseudo-observations."""
    league = num.sum() / n.sum()
    return (num + k * league) / (n + k)


def pct(s):
    """0-100 percentile among scored WRs (ties averaged)."""
    return (s.rank(method="average") - 1) / (s.notna().sum() - 1) * 100


def score(df):
    d = df[df.career_games_played > 0].copy()
    g = d.career_games_played
    comps = {}

    prod = []
    for stat in ["career_receiving_yards", "career_receptions", "career_receiving_tds"]:
        per_game = shrink(d[stat], g, SHRINK_K["games"])
        prod.append(PER_GAME_WEIGHT * pct(per_game) + (1 - PER_GAME_WEIGHT) * pct(d[stat]))
    comps["production"] = sum(prod) / len(prod)

    # efficiency comes from BDB play data (2023-25 REG), the only source with routes run
    d["yprr_adj"] = shrink(d.receiving_yards, d.routes_run, SHRINK_K["routes"])
    d["catch_rate_adj"] = shrink(d.receptions, d.targets, SHRINK_K["targets"])
    d["epa_per_target_adj"] = shrink(d.epa_total_targets.fillna(0), d.targets, SHRINK_K["targets"])
    comps["efficiency"] = (pct(d.yprr_adj) + pct(d.catch_rate_adj) + pct(d.epa_per_target_adj)) / 3

    d["target_share_adj"] = shrink(d.career_targets, d.career_team_targets.fillna(0), SHRINK_K["team_targets"])
    comps["role"] = pct(d.target_share_adj)

    comps["longevity"] = (pct(g) + pct(d.career_games_started) + pct(d.career_seasons)) / 3

    d["honor_points"] = sum(d[c].fillna(0) * w for c, w in HONOR_POINTS.items())
    comps["honors"] = pct(d.honor_points)

    for name, s in comps.items():
        d[f"{name}_score"] = s.round(1)
    raw = sum(comps[k] * w for k, w in WEIGHTS.items()) / sum(WEIGHTS.values())
    d["WR_Success_Score"] = ((raw - raw.min()) / (raw.max() - raw.min()) * 100).round(1)
    d["rank"] = d.WR_Success_Score.rank(ascending=False, method="min").astype(int)
    return d.sort_values("rank")


def self_check():
    s = shrink(pd.Series([8.0, 2.0, 0.0]), pd.Series([10.0, 10.0, 0.0]), 10)  # league rate 0.5
    assert s.round(3).tolist() == [0.65, 0.35, 0.5], s  # zero-sample player lands exactly on league rate
    assert pct(pd.Series([1, 2, 3])).tolist() == [0, 50, 100]


if __name__ == "__main__":
    self_check()
    df = pd.read_parquet(OUT / "wr_career_master.parquet")
    d = score(df)
    cols = ["rank", "display_name", "team", "draft_year", "career_seasons", "career_games_played",
            "career_targets", "career_receiving_yards", "career_receiving_tds", "honor_points",
            "production_score", "efficiency_score", "role_score", "longevity_score", "honors_score", "WR_Success_Score"]
    out = d[cols].rename(columns={"display_name": "player_name", "career_seasons": "seasons"})
    out.to_csv(OUT / "wr_success_scores.csv", index=False)
    skipped = len(df) - len(d)
    print(f"Scored {len(d)} WRs ({skipped} with no NFL regular-season games left unscored). Weights: {WEIGHTS}")
    show = ["rank", "player_name", "team", "seasons", "production_score", "efficiency_score", "role_score",
            "longevity_score", "honors_score", "WR_Success_Score"]
    print("\nTop 20\n" + out[show].head(20).to_string(index=False))
    print("\nBottom 10\n" + out[show].tail(10).to_string(index=False))
