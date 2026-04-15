# QB Translation: Which College QB Traits Predict Early NFL Success?

**STRAT 412 Passion Project** | Brayden Cherry

---

## Index

- [Overview](#overview)
- [Cohort](#cohort)
- [Data Sources](#data-sources)
- [Setup](#setup)
- [Environment Management](#environment-management)
- [Running the Pipeline](#running-the-pipeline)
- [Output Files](#output-files)
- [SQL Database](#sql-database)
- [Composite Score Methodology](#composite-score-methodology)
- [QB Archetypes (K-Means Clusters)](#qb-archetypes-k-means-clusters)
- [Known Data Gaps](#known-data-gaps)
- [Tableau Dashboards](#tableau-dashboards)
- [Project Structure](#project-structure)

---

## Overview

For every QB drafted 2018–2024 who played at least 16 NFL games and made at least 8 starts in their first two seasons, this project builds a composite NFL success score (0–100) and identifies which college traits best predict it.

**Managerial framing:** *If I'm an NFL GM, which college QB stats should I prioritize when drafting?*

**Analysis approach:**
- Composite NFL success score combining accuracy, efficiency, pressure handling, and rushing
- PCA + K-Means clustering to identify QB archetypes
- Recruit prestige vs. actual NFL output bias indicator

**Three-platform deliverable:** Python (data pipeline + scoring) · SQL (querying/aggregation) · Tableau (dashboards)

---

## Cohort

40 QBs drafted 2018–2024 who met the eligibility threshold (≥16 NFL games played, ≥8 starts in first two seasons).

---

## Data Sources

| Source | What | How Accessed |
|---|---|---|
| Pro-Football-Reference | NFL draft history 2008–2024 | Manually downloaded XLS → `data/raw/draft/{year}-draft.xls` |
| Pro-Football-Reference | NFL passing stats (advanced + standard) 2018–2025 | Manually downloaded XLS → `data/raw/passing/` |
| Pro-Football-Reference | NFL rushing stats 2018–2025 | Manually downloaded XLS → `data/raw/rushing/` |
| College Football Data API (CFBD) | College passing/rushing, PPA, usage, team win %, recruiting | Free API — key in `.env.local` |
| Sportradar NCAAFB v7 | College sack data (supplemental) | Trial API — key in `.env.local` |

---

## Setup

```bash
# 1. Clone the repo and enter it
cd /path/to/qb-passion-project

# 2. Sync the local uv-managed environment
uv sync

# 3. Add API keys to `.env.local`
#    (file is git-ignored — never commit it)
#    CFBD_KEY=...
#    SPORTRADAR_KEY=...
```

---

## Environment Management

This repo now uses `uv` as the default Python environment manager.

Common commands:

```bash
# Create/update the local .venv from pyproject.toml
uv sync

# Run Python in the project environment
uv run python --version

# Add a dependency
uv add <package>

# Add a dev-only dependency
uv add --dev <package>
```

Notes:
- `uv sync` creates and maintains a local `.venv/` in the repo.
- `uv` uses a project-local cache at `.uv-cache/`, so this repo does not depend on `~/.cache/uv`.
- `pyproject.toml` is the source of truth for Python dependencies.
- `requirements.txt` is still present for compatibility, but `uv` should be the default workflow going forward.

---

## Running the Pipeline

Scripts must be run in order from the project root. Each script reads from
the previous script's output.

```bash
uv run python scripts/01_draft_list.py         # raw/draft/*.xls  → data/raw/qbs_drafted.csv
uv run python scripts/02_nfl_passing_stats.py  # raw/passing/*.xls → data/raw/nfl_passing_all.csv
uv run python scripts/03_filter_cohort.py      # define eligible QB set → data/processed/qb_cohort.csv
uv run python scripts/04_college_stats.py      # CFBD API → data/processed/qb_college_features.csv
uv run python scripts/05_nfl_rushing_stats.py  # raw/rushing/*.xls → rushing cols added to qb_cohort.csv
uv run python scripts/06_sportradar_college.py # Sportradar API → data/raw/sportradar_profiles.json
uv run python scripts/07_feature_merge.py      # combine all → data/processed/qb_model_table.csv
uv run python scripts/08_clustering.py         # PCA + K-Means → data/processed/qb_clusters.csv
uv run python scripts/09_composite_score.py    # composite NFL score + recruit bias → qb_composite_scores.csv
uv run python scripts/10_build_sql.py          # load CSVs into SQLite → runs 10 analytical queries
```

---

## Output Files

| File | Contents | Coverage |
|---|---|---|
| `data/raw/qbs_drafted.csv` | 198 drafted QBs, 2008–2024 | Complete |
| `data/raw/nfl_passing_all.csv` | 1,766 player-seasons, 2018–2025 | Complete |
| `data/raw/nfl_rushing_all.csv` | 2,921 player-seasons, 2018–2025 | Complete |
| `data/raw/sportradar_profiles.json` | Sportradar player profile payloads | Supplemental source |
| `data/processed/qb_cohort.csv` | 40 QBs with full NFL stats + rushing | 40/40 |
| `data/processed/qb_college_features.csv` | College stats + recruit ratings | 40 rows; 34/40 recruit ratings |
| `data/processed/qb_model_table.csv` | 40 QBs × 43 cols, all sources merged | Ready for analysis |
| `data/processed/qb_composite_scores.csv` | 0–100 NFL success score + recruit bias | 40/40 |
| `data/processed/qb_clusters.csv` | PCA scores + K-Means cluster assignments | 40/40 |

---

## SQL Database

The SQLite database (`data/qb_analysis.db`) contains 5 tables and 10 pre-written analytical queries.

**Tables:**

| Table | Contents |
|---|---|
| `qb_cohort` | NFL stats + identifiers for all 40 cohort QBs |
| `college_features` | College stats + recruiting data per QB |
| `composite_scores` | 0–100 NFL success score, recruit bias |
| `model_table` | Merged 43-column feature table used for modeling |
| `qb_clusters` | PCA scores + K-Means cluster assignments |

**Running the SQL:**

```bash
# Option A: Python loader (recommended — builds the .db file automatically)
python scripts/10_build_sql.py

# Option B: SQLite CLI (after running the Python loader to create the .db)
sqlite3 data/qb_analysis.db
sqlite> .read scripts/10_build_sql.sql
```

**Queries in `scripts/10_build_sql.sql`:**
1. Average composite NFL score by draft round
2. Top 10 QBs by composite NFL success score
3. Most overvalued QBs (high recruit rating, low NFL output)
4. Most undervalued QBs (low recruit rating, high NFL output)
5. Cluster summary by QB archetype
6. College completion % bucket vs avg NFL score
7. Average NFL score by college conference (min 3 QBs)
8. Round 1 busts (first-round picks scoring below 45)
9. Late-round overachievers (rounds 3–7 scoring above cohort mean)
10. College PPA quartile vs avg NFL score

---

## Composite Score Methodology

The composite NFL success score is a weighted average of 10 normalized components (0–1 scale each):

| Component | Weight | Direction |
|---|---|---|
| On-target % | 2.0× | Higher = better |
| Bad throw % | 1.5× | Lower = better |
| Completion % | 1.5× | Higher = better |
| ANY/A | 1.0× | Higher = better |
| Passer rating | 1.0× | Higher = better |
| QBR | 1.0× | Higher = better |
| TD % | 1.0× | Higher = better |
| INT % | 1.0× | Lower = better |
| Pressure % allowed | 1.0× | Lower = better |
| Rushing yards/att | 1.0× | Higher = better |

Accuracy metrics are upweighted 1.5–2× because they are more stable indicators than counting stats. Pocket time, IAY/att, and games started are excluded intentionally.

**Recruit bias** = recruit_rating_scaled − composite_nfl_score. Positive values indicate overvalued recruits; negative values indicate undervalued recruits.

---

## QB Archetypes (K-Means Clusters)

Four archetypes identified via PCA + K-Means on college features:

| Cluster | Description |
|---|---|
| Elite Multi-Dimensional | High PPA, high completion %, strong rushing — best overall college producers |
| Efficient Passers | High completion %, strong passing efficiency, modest rushing |
| Raw Dual-Threats | Higher rushing profile with less refined passing efficiency |
| Pure Pocket Passers | Lower-rush archetype built around traditional pocket play |

---

## Known Data Gaps

- Expected recruiting-data nulls remain for 6 QBs: Aidan O'Connell, Bailey Zappe, Baker Mayfield, Desmond Ridder, Josh Allen, and Ryan Finley
- Trey Lance is in the cohort but is missing key college modeling fields such as `col_cmp_pct` and `col_ppa_pass`

---

## Tableau Dashboards

Connect Tableau directly to `data/processed/qb_model_table.csv` and `qb_composite_scores.csv`.

Planned dashboards:
- **QB Radar Chart** — multi-axis chart of each QB's normalized score components
- **Recruit Bias Scatter** — recruit rating (x) vs. composite NFL score (y), labeled outliers
- **College → NFL Correlation** — scatter plots of top college predictors vs. NFL composite score
- **Archetype Dashboard** — cluster membership map, filterable by draft year / conference / round

---

## Project Structure

```
qb-passion-project/
├── data/
│   ├── raw/
│   │   ├── draft/          {year}-draft.xls
│   │   ├── passing/        {year}-advanced.xls, {year}-standard.xls
│   │   ├── rushing/        {year}-rushing.xls
│   │   ├── qbs_drafted.csv
│   │   ├── nfl_passing_all.csv
│   │   ├── nfl_rushing_all.csv
│   │   └── sportradar_profiles.json
│   └── processed/
│       ├── qb_cohort.csv
│       ├── qb_college_features.csv
│       ├── qb_model_table.csv
│       ├── qb_composite_scores.csv
│       └── qb_clusters.csv
├── scripts/
│   ├── 01_draft_list.py
│   ├── 02_nfl_passing_stats.py
│   ├── 03_filter_cohort.py
│   ├── 04_college_stats.py
│   ├── 05_nfl_rushing_stats.py
│   ├── 06_sportradar_college.py
│   ├── 07_feature_merge.py
│   ├── 08_clustering.py
│   ├── 09_composite_score.py
│   ├── 10_build_sql.py     ← CSV loader (Python)
│   └── 10_build_sql.sql    ← SQLite analytical queries
├── .env.local              (git-ignored — API keys)
├── requirements.txt
└── README.md
```
