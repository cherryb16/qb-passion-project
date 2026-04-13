# QB Translation Project — Status & Task Breakdown
**As of April 11, 2026 | Deadline: April 15, 2026 (4 days)**

---

## What Is Done

### Data Pipeline — 100% Complete
All 10 scripts run cleanly end-to-end. Every output file is populated.

| Output File | Status |
|---|---|
| `data/raw/qbs_drafted.csv` | 198 drafted QBs, 2008–2024 |
| `data/raw/nfl_passing_all.csv` | 1,766 player-seasons |
| `data/raw/nfl_rushing_all.csv` | 2,921 player-seasons |
| `data/processed/qb_cohort.csv` | 40 QBs, full NFL stats |
| `data/processed/qb_college_features.csv` | 39/40 CFBD stats, 34/40 recruit ratings |
| `data/processed/qb_model_table.csv` | 40 QBs × 48 columns — main analysis table |
| `data/processed/qb_composite_scores.csv` | 0–100 NFL success score for all 40 QBs |
| `data/processed/qb_clusters.csv` | PCA + K-Means archetypes for all 40 QBs |
| `data/qb_analysis.db` | SQLite DB — 5 tables, 10 analytical queries |

### Analysis — Complete
| Output | Status |
|---|---|
| `data/processed/corr_heatmap.png` | Pearson correlation heatmap (college predictors vs NFL outcomes) |
| `data/processed/regression_coefficients.png` | Standardized OLS coefficient charts per NFL outcome |
| `data/processed/top_scatter_plots.png` | Top 6 college → NFL predictor scatter plots with trendlines |

---

## What Still Needs to Be Done

### 1. Tableau Dashboards (Required)
Four dashboards to build in Tableau Desktop. Data sources are ready — connect to:
- `data/processed/qb_model_table.csv`
- `data/processed/qb_composite_scores.csv`

| Dashboard | What to Build |
|---|---|
| QB Radar Chart | Spider/radar chart — each QB's normalized scores across all composite components |
| Recruit Bias Scatter | Recruit rating (x-axis) vs. composite NFL score (y-axis) — label outlier QBs |
| College → NFL Correlation | Scatter plots of top college predictors vs. NFL composite score |
| Archetype Dashboard | Cluster membership map with filters for draft year, conference, round |

### 2. Slide Deck (Required)
Narrative deck presenting findings to a managerial (GM) audience. Should tell a story, not just show charts.

Suggested structure:
- The question: what college QB traits translate to the NFL?
- The cohort: 40 QBs drafted 2018–2024, first 2 seasons
- How we scored NFL success (composite metric)
- Key findings: top college predictors (regression results)
- Archetypes: what QB clusters look like
- Recruit bias: who over/underperformed their hype
- GM recommendation: what to prioritize when drafting
- Data sources, methodology, limitations

### 3. YouTube Presentation (Required)
Record and upload the slide deck walkthrough to YouTube, then submit link to Learning Suite.

### 4. Fix Recruit Rating Coverage (Optional — Low Priority)
Currently 34/40 QBs have recruit ratings. The CFBD `/recruiting/players` endpoint likely has a position string mismatch. Fetching without a position filter and filtering client-side could push to 38–40/40. Worth doing only if time allows before the other deliverables are finished.

---

## Task Breakdown by Person

### Person A — Tableau Dashboards

**Goal**: Build all four Tableau dashboards and export them as images/workbook for the slide deck.

| # | Task |
|---|---|
| A1 | Open Tableau Desktop, connect to `qb_model_table.csv` and `qb_composite_scores.csv` as data sources |
| A2 | Build **QB Radar Chart** — normalized composite component scores per QB; add a QB name filter |
| A3 | Build **Recruit Bias Scatter** — recruit_rating (x) vs composite_score (y); annotate Josh Allen, Brock Purdy, and other outliers |
| A4 | Build **College → NFL Correlation** — scatter plots for top 3–4 college predictors (col_cmp_pct, col_td_int_ratio, col_ppa_pass) vs composite_score |
| A5 | Build **Archetype Dashboard** — color-code by cluster label; add filters for draft_year, conference, draft_round |
| A6 | Export all four dashboards as high-res images for use in the slide deck |

**Key columns for Tableau**:
- Composite score components: in `qb_composite_scores.csv`
- Cluster labels: `cluster` column in `qb_clusters.csv` (join on qb_name)
- College predictors: `col_cmp_pct`, `col_td_int_ratio`, `col_ppa_pass`, `col_sack_rate`, `recruit_rating`
- NFL outcomes: `nfl_ontgt_pct`, `nfl_badth_pct`, `nfl_prss_pct`

---

### Person B — Slide Deck

**Goal**: Build the full slide deck (PowerPoint or Google Slides) using outputs already produced.

| # | Task |
|---|---|
| B1 | Set up slide deck structure — title slide, agenda, methodology, findings, recommendations, appendix |
| B2 | Write the "Why This Matters" framing — NFL draft economics, cost of a bad QB pick |
| B3 | Add cohort overview slide — who the 40 QBs are, draft years, eligibility criteria |
| B4 | Add composite score methodology slide — 10 components, weighting logic, 0–100 scale |
| B5 | Drop in `regression_coefficients.png` and `corr_heatmap.png`; write 2–3 bullet insights per chart |
| B6 | Add scatter plot slides using `top_scatter_plots.png` — interpret the strongest predictors |
| B7 | Drop in Tableau visuals from Person A (A6 exports) — one slide per dashboard with written insight |
| B8 | Write the GM Recommendation slide — top 3 college stats to prioritize, what to ignore |
| B9 | Add limitations slide — data gaps (6 missing recruit ratings, SP+ null fields), sample size (n=40) |
| B10 | Final polish — consistent formatting, font, colors; check all chart labels are readable |

**Key findings already computed (use these)**:
- The Python regression script prints the top correlations in the terminal — run `python scripts/08_regression.py` to get current GM takeaways
- Composite score ranges and distributions are in `qb_composite_scores.csv`
- Cluster descriptions are in `qb_clusters.csv`

---

### Person C — YouTube Presentation + Optional Data Fix

**Goal**: Record and upload the presentation; optionally improve recruit rating coverage.

| # | Task |
|---|---|
| C1 | Review the final slide deck (coordinate with Person B) |
| C2 | Write a speaker script or talking points for each slide (target: 8–12 minutes total) |
| C3 | Record the presentation — screen share slides + voiceover, or camera + slides |
| C4 | Edit the recording (trim silence, fix audio levels) — iMovie, QuickTime, or any editor |
| C5 | Upload to YouTube (unlisted or public per course requirements) |
| C6 | Submit YouTube link to Learning Suite before April 15 deadline |
| C7 | *(Optional)* Fix CFBD recruit rating coverage: open `scripts/04_college_stats.py`, find the `/recruiting/players` call, remove the position filter param, re-run the script, then re-run scripts 07 → 10 to propagate the update |

---

## Dependencies & Sequencing

```
Person A (Tableau) ──────────────────────┐
                                          ▼
                               Person B (Slide Deck) ──► Person C (Record + Submit)
```

- Person B can start with the Python-generated charts (already done) and fill in Tableau slides once Person A delivers exports
- Person C needs the final slide deck from Person B before recording
- Person A and the optional data fix (C7) are fully independent of each other

---

## Files to Know

| File | Who Needs It |
|---|---|
| `data/processed/qb_model_table.csv` | Person A (Tableau data source) |
| `data/processed/qb_composite_scores.csv` | Person A, Person B |
| `data/processed/qb_clusters.csv` | Person A |
| `data/processed/corr_heatmap.png` | Person B |
| `data/processed/regression_coefficients.png` | Person B |
| `data/processed/top_scatter_plots.png` | Person B |
| Tableau exports (Person A → B) | Person B, Person C |
| Final slide deck | Person C |
