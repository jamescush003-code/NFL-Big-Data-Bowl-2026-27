# NOTES

## How to run
```bash
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python src/01_load_data.py        # unzip / download + data/SCHEMA.md
.venv/bin/python src/02_build_wr_table.py   # data/processed/wr_master.{parquet,csv}
.venv/bin/python src/03_career_data.py      # data/processed/wr_career_master.{parquet,csv}
.venv/bin/python src/04_wr_success_score.py # data/processed/wr_success_scores.csv
```

## Environment
- System Python is 3.9; `nflreadpy` needs >= 3.10, so a Python 3.12 venv (`.venv`, via uv) is used instead of falling back to `nfl_data_py`.
- No Kaggle credentials were found, but the folder already held the full competition zip (Chrome left it named `Unconfirmed 215638.crdownload`; it is a complete zip). `01_load_data.py` accepts any real zip in the folder and only calls kagglehub if none exists.
- The prompt's "Ponytail" section was an unfilled placeholder, so plain shell/python commands were used.

## What the data actually is (BDB 2027)
- 510 players, all **drafted/signed in 2023, 2024 or 2025**; 106 are WRs (`nfl_position == "WR"`). Games cover 2023–2025 PRE/REG/POST.
- Key is `nfl_id` (snake_case, not `nflId`). Tables: `players`, `player_play` (one row per pool player per pass play), `games`, `game_tracking_<season>`, `combine_results`, `combine_tracking`, `player_career_successes`.
- The pool does **not** contain every WR from those classes (e.g. Zay Flowers, Malik Nabers, Marvin Harrison Jr., Tetairoa McMillan, Emeka Egbuka are absent). Rankings are only within this pool.
- Checked against reality: Puka Nacua 2023 = 160 targets / 1,486 yds in `player_play`, matching official totals, so play coverage looks complete.

## Assumptions
- Regular season only, everywhere (comparable across players; not everyone gets playoff games).
- TDs in `wr_master` are parsed from `play_description` ("TOUCHDOWN", excluding "NULLIFIED"). The score uses official nflverse TDs instead.
- `player_play` only has rows for pool players, so team-level targets aren't available there; `wr_master` has **targets per route** as the role stat, and true **target share** comes from nflverse (player targets / team targets in the weeks he played).
- Tracking: streamed in 64 MB blocks, filtered to WR ids, reduced to max speed per (player, play), kept for route plays only. `top_speed_mph` = 95th percentile of per-route max speed (robust to tracking spikes).
- Career window = all nflverse regular seasons 2023 through the current 2026 season (in progress), so volume/longevity include 2026. **Efficiency stats (YPRR, catch rate, EPA/target) use BDB 2023–25 only**, because routes run only exist there.
- Games played = REG games with >0 offensive snaps (nflverse snap counts), falling back to stat rows, then BDB `career_games_active`.
- Games started and honors come from the competition's `player_career_successes.csv` (covers through 2025). nflverse has no starts or awards data.
- WRs with zero NFL regular-season games (20 of 106) are left out of the score (they'd only pile up as ties at 0).

## Name / ID match
- nflverse `load_players()` has an `nfl_id` column: **100/106 (94.3%) matched by ID**. Name+position fallback (normalized, suffixes stripped) found 0 more.
- The 6 unmatched (Jadon Haselwood, Kaden Prather, Elijhah Badger, Roc Taylor, Kobe Hudson, Jacolby George) never played an NFL regular-season game and aren't in nflverse — so **100% of WRs who played are matched**.

## Inputs dropped / caveats
- Combine data (`combine_results`, `combine_tracking`) is pre-NFL, not career success, so it's not in the score or the WR table.
- Honors: `player_career_successes` is position-agnostic, so a return-specialist Pro Bowl/All-Pro counts (Marvin Mims gets a high honors score this way). It's 5% of the score; left as-is rather than hand-edited.
- Catch rate penalizes deep threats; it's in efficiency because it was requested. Drop it in `04_wr_success_score.py` if you'd rather.

## Score method (`src/04_wr_success_score.py`)
- **Production**: yards, receptions, TDs. Each = 60% percentile of per-game rate (shrunk toward league rate with 8 pseudo-games) + 40% percentile of career total.
- **Efficiency**: YPRR (shrunk with 150 pseudo-routes), catch rate and EPA/target (50 pseudo-targets each). Shrinkage implements the "min sample" rule: a 50-target player sits halfway to league average, a 10-target player near it.
- **Role**: career target share, shrunk with 300 pseudo team-targets.
- **Longevity**: games played, games started, seasons.
- **Honors**: 3 × AP 1st team + 2 × AP 2nd team + 1 × Pro Bowl (original ballot).
- Each input → percentile among scored WRs (0–100); component = mean of its inputs; final = weighted average, min-max rescaled to 0–100.

## Changing the weights
Edit the config block at the top of `src/04_wr_success_score.py`:
```python
WEIGHTS = {"production": 0.35, "efficiency": 0.30, "role": 0.15, "longevity": 0.15, "honors": 0.05}
PER_GAME_WEIGHT = 0.6
SHRINK_K = {"targets": 50, "routes": 150, "games": 8, "team_targets": 300}
HONOR_POINTS = {"ap_all_pro_1st_team": 3, "ap_all_pro_2nd_team": 2, "pro_bowl_original_ballot": 1}
```
Weights don't need to sum to 1 (they're normalized). Then rerun only step 4.
