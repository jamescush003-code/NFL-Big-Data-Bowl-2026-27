# What makes up the WR Success Score

The WR Success Score (0–100) measures how successful a receiver's NFL career has been **so far**. It ranks the 86 WRs in the Big Data Bowl 2027 pool (drafted or signed 2023–2025) who have played at least one regular-season game. 100 = the best career in the pool, 0 = the weakest. Scores are relative to this pool only, not to all NFL receivers.

Code: `src/04_wr_success_score.py`. Output: `data/processed/wr_success_scores.csv`.

## The five parts

| Part | Weight | What it asks | Stats used | Source |
|---|---|---|---|---|
| **Production** | 35% | How much has he produced? | Receiving yards, receptions, TDs | nflverse, 2023–2026 |
| **Efficiency** | 30% | How much does he do with his chances? | Yards per route run, catch rate, EPA per target | BDB play data, 2023–2025 |
| **Role** | 15% | How central is he to his offense? | Target share (his targets ÷ team targets in games he played) | nflverse, 2023–2026 |
| **Longevity** | 15% | How long and how often has he been on the field? | Games played, games started, seasons played | nflverse + BDB |
| **Honors** | 5% | Has the league recognized him? | AP All-Pro 1st team (3 pts), 2nd team (2 pts), Pro Bowl (1 pt) | BDB `player_career_successes` |

All stats are regular season only.

## How each part is calculated

1. **Fair rates, not just totals.** Production counts 60% per-game rate and 40% career total. A great second-year player isn't buried by older players, but staying healthy and playing longer still counts.
2. **Small samples get pulled toward average.** A WR who caught 3 of 3 targets isn't treated as the best in the league. Every rate is blended with the league average, and the fewer chances a player had, the stronger the pull:
   - catch rate and EPA per target: 50 "average" targets added
   - yards per route run: 150 "average" routes added
   - per-game production: 8 "average" games added
   - target share: 300 "average" team targets added

   So a 50-target player lands halfway between his own number and the average, and a 500-target player is mostly himself.
3. **Everything becomes a percentile.** Each stat is converted to a 0–100 percentile among the 86 scored WRs (50 = middle of the pack). This lets yards, catch rate, and games started be compared on the same scale.
4. **Each part is the average of its stats' percentiles.**
5. **Final score = the weighted average of the five parts,** stretched so the top player gets 100 and the bottom player gets 0.

## Things to keep in mind

- **Efficiency only covers 2023–2025.** Routes run only exist in the competition data, so 2026 games count toward volume and longevity but not efficiency.
- **Honors aren't WR-specific.** A Pro Bowl or All-Pro earned as a kick or punt returner still counts (this is why Marvin Mims has a high honors score). It's only 5% of the total.
- **Catch rate favors short-area receivers** over deep threats. It's included because it was requested, but it's one of three efficiency stats.
- **Longevity favors the 2023 class,** since those players have had more seasons. That's intentional: it's a career score, not a talent projection.

## Changing it

Edit the config block at the top of `src/04_wr_success_score.py` (`WEIGHTS`, `PER_GAME_WEIGHT`, `SHRINK_K`, `HONOR_POINTS`), then rerun:

```bash
.venv/bin/python src/04_wr_success_score.py
```
