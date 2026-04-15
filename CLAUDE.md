# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Goal

STRAT 412 Passion Project — **QB Translation: Which college QB traits predict early NFL success?**

For QBs drafted 2018–2024 who played ≥16 NFL games and made ≥8 starts in their first two seasons, build a composite NFL success score and identify which college traits best predict it.

**Managerial framing**: "If I'm an NFL GM, which college QB stats should I prioritize when drafting?"

**Analysis approach**: Composite NFL success score (0–100) combining accuracy, efficiency, pressure handling, and rushing. PCA + K-Means clustering to identify QB archetypes. Recruitment bias indicator (recruit prestige vs. actual NFL output).

**Three-platform deliverable**: Python (data pipeline + scoring), SQL (querying/aggregation), Tableau (dashboards).

**Final deliverable deadline**: April 15, 2026 — slide deck, data files, YouTube presentation to Learning Suite.

---

## Data Sources

| Source | What | How Accessed |
|---|---|---|
| Pro-Football-Reference | NFL draft history 2008–2024 | Manually downloaded XLS → `data/raw/draft/{year}-draft.xls` |
| Pro-Football-Reference | NFL passing stats (advanced + standard) 2018–2025 | Manually downloaded XLS → `data/raw/passing/{year}-advanced.xls` / `{year}-standard.xls` |
| Pro-Football-Reference | NFL rushing stats 2018–2025 | Manually downloaded XLS → `data/raw/rushing/{year}-rushing.xls` |
| College Football Data API (CFBD) | College passing/rushing, PPA, usage, team win %, recruiting | Free API — key in `.env.local` as `CFBD_KEY` |
| Sportradar NCAAFB v7 | College sack data (supplemental) | Trial API — key in `.env.local` as `SPORTRADAR_KEY` |

---

## Current Data Status

### Pipeline: fully working — runs clean 01 → 09

| File | Contents | Coverage |
|------|----------|----------|
| `data/raw/qbs_drafted.csv` | 198 drafted QBs, 2008–2024 | Complete |
| `data/raw/nfl_passing_all.csv` | 1,766 player-seasons, 2018–2025 | Complete |
| `data/raw/nfl_rushing_all.csv` | 2,921 player-seasons, 2018–2025 | Complete |
| `data/raw/sportradar_profiles.json` | Sportradar player profile payloads | Supplemental source |
| `data/processed/qb_cohort.csv` | 40 QBs with full NFL stats + rushing | 40/40 all outcome cols |
| `data/processed/qb_college_features.csv` | College stats + recruit ratings | 40 rows; 34/40 recruit ratings |
| `data/processed/qb_model_table.csv` | 40 QBs × 43 cols, all sources merged | Ready for analysis |
| `data/processed/qb_composite_scores.csv` | 0–100 NFL success score + recruit bias | 40/40 scored |
| `data/processed/qb_clusters.csv` | PCA scores + K-Means cluster assignments | 40/40 |
| `data/qb_analysis.db` | SQLite DB — 5 tables, 10 analytical queries | Complete |

### Known Data Gaps
- Expected recruiting-data nulls remain for 6 QBs: Aidan O'Connell, Bailey Zappe, Baker Mayfield, Desmond Ridder, Josh Allen, and Ryan Finley
- Trey Lance is in the cohort but is missing key college modeling fields such as `col_cmp_pct` and `col_ppa_pass`

---

## What Still Needs to Be Done

### 1. Build Tableau Dashboards
Tableau workbook should include at least:
- **QB Radar Chart**: multi-axis chart showing each QB's normalized scores across all composite components
- **Recruit Bias Scatter**: recruit rating (x) vs. composite NFL score (y) — label outliers
- **College → NFL Correlation**: scatter plots of top college predictors vs. NFL composite score
- **Archetype Dashboard**: cluster membership map, filter by draft year / conference / round
- Data source: connect directly to `data/processed/qb_model_table.csv` and `qb_composite_scores.csv`

### 2. Fix CFBD Recruiting Data (optional improvement)
- The CFBD `/recruiting/players` endpoint returned 0 results — likely a position string mismatch
- Try fetching without a position filter and filtering client-side (same fix applied in script 04 to all-QB pull)
- Would improve recruit_rating coverage from 34/40 to potentially 38–40/40

---

## Running the Pipeline

Use the local `uv` environment:

```bash
cd /Users/cherrybrayden/Documents/GitHub/qb-passion-project
uv sync
```

All API keys load automatically from `.env.local` — no `export` needed.

```bash
uv run python scripts/01_draft_list.py         # raw/draft/*.xls → data/raw/qbs_drafted.csv
uv run python scripts/02_nfl_passing_stats.py  # raw/passing/*.xls → data/raw/nfl_passing_all.csv
uv run python scripts/03_filter_cohort.py      # define eligible QB set → data/processed/qb_cohort.csv
uv run python scripts/04_college_stats.py      # CFBD API → data/processed/qb_college_features.csv
uv run python scripts/05_nfl_rushing_stats.py  # raw/rushing/*.xls → rushing cols added to qb_cohort.csv
uv run python scripts/06_sportradar_college.py # Sportradar API → data/raw/sportradar_profiles.json
uv run python scripts/07_feature_merge.py      # combine all → data/processed/qb_model_table.csv
uv run python scripts/08_clustering.py         # PCA + K-Means → data/processed/qb_clusters.csv
uv run python scripts/09_composite_score.py    # composite NFL score + recruit bias → qb_composite_scores.csv
uv run python scripts/10_build_sql.py          # SQLite DB → data/qb_analysis.db (5 tables, 10 example queries)
```

---

## Data Architecture

```
data/raw/draft/{year}-draft.xls
    └─ 01_draft_list.py ──────────────────► data/raw/qbs_drafted.csv

data/raw/passing/{year}-advanced.xls
data/raw/passing/{year}-standard.xls
    └─ 02_nfl_passing_stats.py ───────────► data/raw/nfl_passing_all.csv

data/raw/qbs_drafted.csv  ──┐
data/raw/nfl_passing_all.csv ┴─► 03_filter_cohort.py ──► data/processed/qb_cohort.csv
                                                               (40 QBs, NFL filter only)
                                                                       │
                    ┌──────────────────────────────────────────────────┤
                    ▼                          ▼                       ▼
     04_college_stats.py          05_nfl_rushing_stats.py   06_sportradar_college.py
  (CFBD → college_features.csv)  (rushing → qb_cohort.csv)  (sacks → sportradar_profiles.json)
                    │                          │                       │
                    └──────────────────────────┴───────────────────────┘
                                               │
                                    07_feature_merge.py
                                               │
                              data/processed/qb_model_table.csv
                                    │                  │
                       09_composite_score.py     [08] PCA + K-Means
                       qb_composite_scores.csv   qb_clusters.csv
                                    │
                             [10] SQL database
                             data/qb_analysis.db
                                    │
                             [11] Tableau dashboards
```

---

## Key Implementation Details

- **PFR files**: named `{year}-{type}.xls` — scripts use exact names, no index mapping needed.
- **Cohort filter** (`03_filter_cohort.py`): ≥16 NFL games, ≥8 starts, `has_advanced_stats=True`, key advanced cols non-null. Defines the QB roster — must run before scripts 04 and 06.
- **Composite score** (`09_composite_score.py`): weighted average of 10 normalized components. Accuracy metrics (on-target %, bad throw %, completion %) upweighted 1.5–2×. pkttime, iay_per_att, and games started intentionally excluded.
- **Sportradar team resolution**: uses dynamic team map from hierarchy endpoint (1,824 teams). Alias table in `06_sportradar_college.py` handles PFR abbreviations (e.g. "North Carolina St." → "NC State").
- **API keys**: stored in `.env.local` (git-ignored). Scripts load it automatically at startup.
- **Reproducibility**: all analysis traces raw data → scripts → final numbers. Graders run the pipeline from scratch — no manual steps beyond dropping XLS files in `data/raw/`.
