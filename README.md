# 🏈 NFL Big Data Bowl 2026–27

Plans, experiments, and tests for the **NFL Big Data Bowl 2027** Kaggle competition.

The NFL Big Data Bowl is an annual analytics competition hosted by the NFL on Kaggle. Participants use NFL Next Gen Stats player-tracking data (player location, speed, acceleration, and direction recorded multiple times per second) to build new metrics and insights that help teams, coaches, and fans better understand the game.

This project focuses on **wide receivers**: how explosive they are on the field, how successful their NFL careers have been, and how well their NFL Combine results predicted that success.

---

## 📌 Project Goals

We are building **three separate metrics** that work on their own and can also be combined into a full picture of a receiver.

### 1. ⚡ WR Explosiveness Metric
A tracking-data metric that measures how explosive a receiver is during a play.

**Possible inputs:**
- Peak acceleration off the line of scrimmage
- Time to reach top speed
- Maximum speed reached on a route
- Separation created at the break of a route
- Change of direction speed (deceleration and re-acceleration)
- Yards after catch (YAC) and burst after the catch

**Output:** An explosiveness score per receiver, per play and season-level averages.

### 2. 🏆 WR NFL Success Metric
A career-based metric that measures how successful a receiver has been in the NFL so far.

**Possible inputs:**
- Receiving yards, receptions, and touchdowns
- Yards per route run (YPRR)
- Target share and catch rate
- Expected Points Added (EPA) per target
- Games played / started and career length
- Pro Bowl and All-Pro selections

**Output:** A normalized career success score that adjusts for years in the league so young and veteran receivers can be compared fairly.

### 3. 🏃 WR Combine Success Metric
A metric that evaluates receivers' NFL Combine performance and tests how well it predicts NFL results.

**Possible inputs:**
- 40-yard dash (and 10-yard split)
- Vertical jump and broad jump
- 3-cone drill and 20-yard shuttle
- Height, weight, arm length, and hand size

**Output:** A composite combine score, plus analysis of how it correlates with the Explosiveness Metric (#1) and the NFL Success Metric (#2).

---

## 🔗 How the Metrics Connect

```
Combine Score (#3) ──► does it predict ──► Explosiveness (#1)
        │                                        │
        └──────────► does it predict ──► NFL Success (#2)
```

The key questions:
- Do combine numbers actually show up as explosiveness on the field?
- Does on-field explosiveness lead to long-term NFL success?
- Which combine drills matter most for wide receivers?

---

## 📂 Data Sources

| Source | Used For |
|---|---|
| NFL Big Data Bowl 2027 dataset (Kaggle) | Player tracking data for the Explosiveness Metric |
| Career receiving stats | NFL Success Metric |
| NFL Combine results | Combine Success Metric |

> Competition data must be used in line with the Kaggle competition rules.

---

## 🗂️ Repository Structure (Planned)

```
NFL-Big-Data-Bowl-2026-27/
├── data/              # Raw and processed data (not committed if restricted)
├── notebooks/         # Exploration and experiments
│   ├── 01_explosiveness.ipynb
│   ├── 02_nfl_success.ipynb
│   └── 03_combine_success.ipynb
├── src/               # Reusable code for metric calculations
├── tests/             # Tests for metric logic
├── figures/           # Charts and visuals for the submission
└── README.md
```

---

## 🛣️ Roadmap

- [ ] Download and explore the Big Data Bowl 2027 tracking data
- [ ] Define and calculate the Explosiveness Metric
- [ ] Gather career stats and build the NFL Success Metric
- [ ] Gather combine data and build the Combine Success Metric
- [ ] Test correlations between all three metrics
- [ ] Build visualizations
- [ ] Write up and submit the final Kaggle notebook

---

## 🚀 Getting Started

```bash
git clone https://github.com/<your-username>/NFL-Big-Data-Bowl-2026-27.git
cd NFL-Big-Data-Bowl-2026-27
pip install -r requirements.txt
```

Then download the competition data from Kaggle and place it in the `data/` folder.

---

## 🙌 Acknowledgments

Thanks to the NFL, NFL Next Gen Stats, and Kaggle for hosting the Big Data Bowl.
