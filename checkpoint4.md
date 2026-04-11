# Checkpoint 4 — Slide Deck Outline
## QB Translation: Which College QB Profiles Predict NFL Success?

---

## Slide 1: Situation — The NFL Draft Is a $100M Guessing Game

- NFL teams invest enormous capital in QB picks — top-5 picks carry $30–50M guaranteed rookie contracts
- Scouting is subjective and inconsistent; front offices disagree on what college production actually signals
- The league has shifted toward analytics, but QB evaluation remains one of the least systematized positions
- This project asks: can we use observable college data to make that guessing game less of a guess?

**Visual:** Opening stat callout — e.g., "Since 2017, 18 QBs were drafted in the first two rounds. Only 9 became viable starters." (or actual cohort number once confirmed)

---

## Slide 2: Complication — Recruiting Hype ≠ NFL Results

- NFL teams and media over-index on recruiting rankings and draft pedigree rather than college production trends
- High-profile recruits (4- and 5-star) frequently underperform relative to their draft slot — and vice versa
- Traditional college stats (yards, TDs) are volume-dependent and context-blind; a QB on a great team looks better than one on a bad one
- There is no standard framework GMs use to translate college efficiency into expected NFL outcomes

**Visual:** Scatter plot teaser — 247Sports recruit rating vs. composite NFL success score (showing weak or noisy correlation)

---

## Slide 3: Question

**Central Question:**

> "Which college QB characteristics — efficiency metrics, PPA, usage, mobility, and recruiting profile — best predict early NFL success, and do recruiting rankings introduce a systematic bias in how QBs are evaluated?"

- Sub-question A: Can we cluster college QB profiles into meaningful archetypes (e.g., pocket passer vs. dual-threat vs. high-usage game manager)?
- Sub-question B: Do certain archetypes consistently outperform or underperform their draft position in the NFL?
- Sub-question C: Does 247Sports recruit rating predict NFL success better, worse, or independently of college production stats?

**Visual:** Simple framework diagram — College Inputs (PPA, usage, efficiency, mobility, recruiting) → Model → NFL Success Score

---

## Slide 4: Answer (Preview)

- College predictive passing value (PPA) and usage rate are stronger predictors of early NFL success than recruiting rank
- PCA + K-Means clustering reveals 3–4 distinct QB archetypes in our cohort — and they have meaningfully different NFL outcomes
- Recruiting bias is real: QBs with lower recruit ratings but high PPA/efficiency are undervalued relative to their eventual NFL output
- Recommendation: NFL front offices should weight college efficiency-adjusted metrics over recruiting pedigree in early-round QB evaluation

**Visual:** Summary results table — archetype clusters with average NFL success score per cluster

---

## Slide 5: Method — Data & Sample

- Sample: 31 QBs drafted 2017–2023 with ≥16 NFL games played in first two seasons (Pro Football Reference)
- College stats sourced from College Football Data API: per-season passing stats, PPA (predicted points added), player usage rate, rushing stats
- Recruiting data sourced from 247Sports composite ratings
- NFL outcome variable: composite success score combining ANY/A, passer rating, and (where available) pressure rate — normalized and weighted

**Visual:** Data pipeline diagram — PFR raw XLS → `01–03_*.py` scripts → cohort CSV + CFBD API → college features CSV → merged modelling table

---

## Slide 6: Method — Scoring, PCA, and Clustering

- Composite NFL success score built in Python: weighted sum of normalized ANY/A (40%), passer rating (40%), and pressure rate inverse (20%); scaled 0–100
- PCA applied to college feature matrix (passing efficiency, PPA, usage, rushing yards/attempt, recruit rating) to reduce dimensionality — first 2–3 components explain ~X% of variance
- K-Means clustering (k=3 or 4, chosen via elbow method) applied to PCA output to identify QB archetypes
- SQL used for aggregation queries: average stats by cluster, archetype breakdown by draft round and conference

**Visual:** PCA biplot showing college feature loadings + K-Means cluster assignments labeled by QB name

---

## Slide 7: Results — QB Archetypes

- **Cluster 1 — Efficient Pocket Passers**: High PPA, high passer rating, low rush attempts, moderate usage — best average NFL success scores
- **Cluster 2 — High-Usage Dual Threats**: High rush yards/attempt and usage rate, moderate PPA — mixed NFL outcomes, high variance
- **Cluster 3 — Low-Efficiency, High-Recruit**: High 247Sports rating, below-average PPA and college efficiency — lowest average NFL success scores
- (Cluster 4 if applicable): Game managers / low-usage, low-recruit late-round QBs — small sample, moderate outcomes

**Visual:** Tableau radar charts — one per archetype showing average college stat profile; color-coded by cluster

---

## Slide 8: Results — Recruiting Bias Analysis

- Correlation between 247Sports composite recruit rating and NFL success score: r = ~X (weak/moderate — to be filled in with actual result)
- Correlation between college PPA and NFL success score: r = ~X (stronger)
- QBs in the top quartile for PPA but bottom half for recruit rating outperformed their draft slot on average
- Example callouts: 1–2 specific QBs who were underrated recruits but high-PPA college players who succeeded in the NFL (and vice versa)

**Visual:** Scatter plot — 247Sports recruit rating (x-axis) vs. composite NFL success score (y-axis); points labeled by QB, colored by cluster

---

## Slide 9: Results — Regression Coefficients

- Linear regression: NFL success score ~ college PPA + usage rate + recruit rating + rush efficiency + draft round
- Key finding: PPA and usage rate have the largest positive coefficients; recruit rating coefficient is small and potentially non-significant
- Draft round acts as a confounder — controlling for it strengthens the PPA relationship
- Model fit: R² = ~X (to be filled in); regression run in Python (scikit-learn / statsmodels)

**Visual:** Horizontal bar chart of standardized regression coefficients with confidence intervals; highlight PPA and usage in a distinct color

---

## Slide 10: Recommendations & Conclusions

- **Draft smarter, not by reputation**: Prioritize PPA and college usage rate over recruiting rankings when evaluating QB prospects
- **Target Cluster 1 archetypes**: Efficient pocket passers with high PPA have the most consistent early NFL outcomes — worth taking earlier than the market implies
- **Be skeptical of Cluster 3**: High-recruit, low-efficiency QBs carry real bust risk; franchises should demand efficiency evidence before committing early picks
- **Limitations**: Small sample (n=31), NFL success measured only through year 2, PPA data begins ~2014 — results directional, not definitive
- **Next steps**: Expand cohort backward to 2010s with traditional stats; add Tableau interactive dashboard for GM-facing scouting tool

**Visual:** Tableau dashboard screenshot (or mockup) — QB radar profiles filterable by archetype, draft round, conference

---

*Presentation time target: ~5.5 minutes | Slide count: 10 | Deliverable deadline: April 15, 2026*
