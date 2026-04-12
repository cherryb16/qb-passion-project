# Checkpoint 4 — Slide Deck Outline
## QB Translation: Which College QB Profiles Predict NFL Success?

---

## Slide 1: Situation — The NFL Draft Is a $100M Guessing Game

- NFL teams invest enormous capital in QB picks — top-5 picks carry $30–50M+ guaranteed rookie contracts
- Scouting is subjective and inconsistent; front offices disagree on what college production actually signals
- The league has shifted toward analytics, but QB evaluation remains one of the least systematized positions
- This project asks: can we use observable college data to make that guessing game less of a guess?

**Visual:** Opening stat callout — "Since 2018, 40 QBs were drafted and got a real shot in the NFL (≥16 games, ≥8 starts). Their composite NFL success scores ranged from 20 to 88 out of 100 — a 68-point gap driven by something."

---

## Slide 2: Complication — Recruiting Hype ≠ NFL Results

- High-profile recruits (4- and 5-star) frequently underperform relative to their draft slot — and vice versa
- Correlation between 247Sports recruit rating and our composite NFL success score: **r = −0.10** (essentially zero)
- Traditional college stats (yards, TDs) are volume-dependent and context-blind
- There is no standard framework GMs use to translate college efficiency into expected NFL outcomes

**Visual:** Scatter plot — 247Sports recruit rating (x-axis) vs. composite NFL success score (y-axis)
- Label obvious outliers: Josh Rosen (99.3 recruit / 29.4 NFL score), Anthony Richardson (92.0 / 24.1), Brock Purdy (85.9 / 87.9), Lamar Jackson (88.2 / 79.2)
- Flat/slightly negative trend line reinforces r = −0.10

---

## Slide 3: Question

**Central Question:**

> "Which college QB characteristics — efficiency metrics, PPA, usage, mobility, and recruiting profile — best predict early NFL success, and do recruiting rankings introduce a systematic bias in how QBs are evaluated?"

- Sub-question A: Can we cluster college QB profiles into meaningful archetypes?
- Sub-question B: Do certain archetypes consistently outperform or underperform expectations?
- Sub-question C: Does 247Sports recruit rating predict NFL success better, worse, or independently of college production?

**Visual:** Framework diagram — College Inputs (PPA, completion %, usage, rushing, recruit rating) → Python Pipeline → Composite NFL Score (0–100) → Clustering & Bias Analysis

---

## Slide 4: Answer (Preview)

- **Recruit ratings are essentially uncorrelated with NFL success** (r = −0.10): teams are paying a premium for the wrong signal
- **College completion % is the strongest college predictor** (r = +0.33, p < 0.10): throwing accurately in college translates
- **Recruiting bias is substantial**: the top 5 most "overvalued" QBs by recruit prestige averaged a composite score of 32.3 — well below the cohort mean of 57.8
- **Late-round and undersized QBs punched above their weight**: Brock Purdy (Rd 7, score 87.9), Gardner Minshew (Rd 6, 67.3)
- **Recommendation**: NFL front offices should weight college completion % and efficiency-adjusted metrics over recruiting pedigree

**Visual:** Side-by-side bar — top 5 "overvalued" (high recruit rating, low NFL score) vs. top 5 "undervalued" (low recruit rating, high NFL score)

---

## Slide 5: Method — Data & Sample

**Sample:** 40 QBs drafted 2018–2024 who received a real NFL opportunity (≥16 games played, ≥8 starts in first two seasons)

| Source | What | Coverage |
|--------|------|----------|
| Pro-Football-Reference | NFL passing stats (advanced + standard) 2018–2025 | 40/40 QBs |
| Pro-Football-Reference | NFL rushing stats 2018–2025 | 40/40 QBs |
| College Football Data API (CFBD) | College passing, PPA, usage, team win % | 39/40 QBs |
| Sportradar NCAAFB v7 | College sack data | 40/40 QBs |
| 247Sports (via CFBD) | Recruiting composite rating | 34/40 QBs |

**Composite NFL Success Score components (weighted):**
- On-target throw % (weight 2×), Bad throw % inverted (2×), Completion % (1.5×)
- ANY/A, Passer rating, QBR, TD%, Int% inverted, Pressure rate inverted, Rush yards/attempt (each 1×)

**Visual:** Data pipeline diagram — raw XLS + API calls → Python scripts 01–07 → model table → scoring + analysis

---

## Slide 6: Method — Scoring, Clustering & SQL

**Composite Score:**
- Each component min-max normalized to 0–1 across the 40-QB cohort
- Weighted average → scaled to 0–100
- "Inverted" metrics (bad throw %, Int%, pressure rate) flipped so higher always = better

**Clustering (PCA + K-Means):**
- PCA applied to college feature matrix to identify key variance axes
- K-Means (k = 3–4, elbow method) clusters QBs into archetypes based on college profile
- Cluster labels assigned based on centroid characteristics

**SQL (SQLite — `data/qb_analysis.db`):**
- Tables: `qb_cohort`, `college_features`, `composite_scores`, `model_table`
- Example queries: average composite score by draft round, recruit bias by conference, top college predictors

**Visual:** SQL query screenshot showing average composite score by draft round

---

## Slide 7: Results — Composite Score Rankings

**Cohort summary:** Mean score = 57.8 | Std = 16.9 | Range = 20.0 – 87.9

| Rank | QB | Draft Year | Round | Score |
|------|----|-----------|-------|-------|
| 1 | Brock Purdy | 2022 | **7** | 87.9 |
| 2 | Drake Maye | 2024 | 1 | 84.9 |
| 3 | Joe Burrow | 2020 | 1 | 84.1 |
| 4 | Jayden Daniels | 2024 | 1 | 81.0 |
| 5 | Justin Herbert | 2020 | 1 | 80.2 |
| … | … | … | … | … |
| 36 | Zach Wilson | 2021 | 1 | 33.6 |
| 37 | Josh Rosen | 2018 | 1 | 29.4 |
| 38 | D. Thompson-Robinson | 2023 | 5 | 29.5 |
| 39 | Anthony Richardson | 2023 | 1 | 24.1 |
| 40 | Ryan Finley | 2019 | 4 | 20.0 |

**Key insight:** Round 1 picks appear at both extremes — draft round alone is a poor predictor of outcomes.

**Visual:** Horizontal bar chart, all 40 QBs sorted by score, bars colored by draft round

---

## Slide 8: Results — Recruiting Bias Analysis

**The numbers:**
- Recruit rating vs. NFL success score: **r = −0.10** (not significant)
- College completion % vs. NFL success: **r = +0.33** (marginally significant)
- College PPA vs. NFL success: **r = +0.18**

**Most overvalued QBs** (high recruit prestige, low NFL output):
| QB | Recruit Rating | NFL Score | Bias |
|----|---------------|-----------|------|
| Josh Rosen | 99.3 | 29.4 | +69.9 |
| Dorian Thompson-Robinson | 98.1 | 29.5 | +68.7 |
| Anthony Richardson | 92.0 | 24.1 | +67.9 |
| J.J. McCarthy | 98.7 | 35.6 | +63.1 |
| Dwayne Haskins | 95.6 | 42.8 | +52.8 |

**Most undervalued QBs** (lower recruit prestige, high NFL output):
| QB | Recruit Rating | NFL Score | Bias |
|----|---------------|-----------|------|
| Brock Purdy | 85.9 | 87.9 | −2.0 |
| Joe Burrow | 90.0 | 84.1 | +5.9 |
| Justin Herbert | 86.1 | 80.2 | +5.9 |
| Lamar Jackson | 88.2 | 79.2 | +9.0 |

**Visual:** Tableau scatter — recruit rating (x) vs. NFL composite score (y), labeled by QB name, regression line shown flat

---

## Slide 9: Results — QB Archetypes (PCA + K-Means)

**PCA:** 3 components explain 78.7% of college feature variance
- PC1 (50%): **Passing efficiency axis** — driven by PPA, yards/attempt, 3rd-down usage
- PC2 (18%): **Volume/usage axis** — driven by INT rate, pass usage, overall usage
- PC3 (11%): **Mobility axis** — driven by sack rate, rush yards/attempt

**K-Means k=4** (elbow at k=4 by inertia drop: 213 → 156 → 123 → 99):

| Cluster | Label | n | Avg NFL Score | Col Cmp% | Col PPA | Rush Y/A | Recruit Rtg |
|---------|-------|---|--------------|----------|---------|----------|-------------|
| 1 | **Efficient Passers** | 5 | **63.5** | 71.6% | 0.616 | 3.80 | 94.7 |
| 3 | **Elite Multi-Dimensional** | 10 | 61.9 | 69.5% | 0.501 | 3.44 | **98.1** |
| 2 | **Raw Dual-Threats** | 7 | 55.2 | 61.0% | 0.288 | **3.73** | 90.2 |
| 0 | **Pure Pocket Passers** | 18 | 54.9 | 65.6% | 0.396 | 1.84 | 90.4 |

**Cluster breakdowns:**

- **Efficient Passers** (n=5, avg score 63.5): Highest college completion % (71.6%) and PPA (0.616), lowest INT rate. QBs: Kyler Murray, Tua Tagovailoa, Mac Jones, Jalen Hurts, Dwayne Haskins. High-floor college profiles — but Haskins (42.8) shows efficient college stats don't guarantee NFL success.

- **Elite Multi-Dimensional** (n=10, avg score 61.9): Blue-chip recruits (avg 98.1), strong PPA + rushing + low turnovers. QBs: Joe Burrow, C.J. Stroud, Jayden Daniels, Caleb Williams, Trevor Lawrence, Bo Nix, Bryce Young, Justin Fields, Baker Mayfield, J.J. McCarthy. High upside but also highest bust exposure — Bryce Young (49.5) and J.J. McCarthy (35.6) drag the average down.

- **Raw Dual-Threats** (n=7, avg score 55.2): High rushing (3.73 y/a), lowest college completion % (61.0%) and PPA (0.288), highest INT rate. QBs: Lamar Jackson, Josh Allen, Anthony Richardson, Sam Howell, Daniel Jones, Will Levis, Spencer Rattler. Most volatile cluster: contains two generational talents (Jackson 79.2, Allen 48.7) alongside major busts (Richardson 24.1, Rattler 63.8).

- **Pure Pocket Passers** (n=18, avg score 54.9): Largest cluster. Minimal rushing (1.84 y/a), moderate efficiency. QBs include: Justin Herbert, Brock Purdy, Drake Maye, Gardner Minshew, Kenny Pickett, Sam Darnold, Zach Wilson, Josh Rosen. Widest range of outcomes (20–88) — cluster membership alone is not predictive here.

**Key insight:** Cluster label is not destiny. The **Efficient Passers** cluster has the best average NFL outcome, but the real differentiator within every cluster is college PPA and completion % — not rush ability or recruit ranking.

**Visual:** PCA biplot — QB names plotted on PC1 (efficiency) vs. PC2 (usage/volume), colored by cluster. Second panel: bar chart of avg NFL score by cluster with individual QB dots overlaid.

---

## Slide 10: Recommendations & Conclusions

**For NFL Front Offices:**
- **Stop over-indexing on recruiting rankings** — the r = −0.10 correlation is statistically indistinguishable from zero
- **Prioritize college completion % and PPA** — r = +0.33 and +0.18 respectively; small but directionally consistent signals
- **Round 1 busts are real**: 5 of the 40 cohort QBs drafted in Round 1 scored below 45 (Rosen 29.4, Wilson 33.6, A. Richardson 24.1, McCarthy 35.6, Haskins 42.8)
- **Late rounds can produce**: Brock Purdy (Rd 7, score 87.9) and Gardner Minshew (Rd 6, 67.3) both outperformed most Round 1 picks

**Limitations:**
- Sample size: n = 40, draft years 2018–2024 only (advanced stats era)
- NFL outcomes measured through first two seasons only — careers evolve
- Recruit ratings missing for 6 QBs (small-school players)
- College stats reflect team context — controlling for strength of schedule is limited by free API tier

**Visual:** Tableau dashboard — QB radar profiles filterable by draft round, conference, cluster archetype

---

*Presentation time target: ~5.5 minutes | Slide count: 10 | Deliverable deadline: April 15, 2026*
