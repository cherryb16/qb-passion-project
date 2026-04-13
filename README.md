# QB Translation: Which College QB Traits Predict Early NFL Success?

**STRAT 412 Passion Project** | Brayden Cherry

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
# 1. Clone the repo and activate the shared virtual environment
source ~/.venv/bin/activate
cd /path/to/qb-passion-project

# 2. Install dependencies
pip install -r requirements.txt

# 3. Add API keys and MySQL credentials to .env.local
#    (file is git-ignored — never commit it)
#    CFBD_KEY=...
#    SPORTRADAR_KEY=...
#    MYSQL_HOST=localhost
#    MYSQL_USER=root
#    MYSQL_PASSWORD=...
#    MYSQL_DATABASE=qb_analysis
```

---

## Running the Pipeline

Scripts must be run in order from the project root. Each script reads from
the previous script's output.

```bash
python scripts/01_draft_list.py        # raw/draft/*.xls  → data/raw/qbs_drafted.csv
python scripts/02_nfl_passing_stats.py # raw/passing/*.xls → data/raw/nfl_passing_all.csv
python scripts/03_filter_cohort.py     # define eligible QB set → data/processed/qb_cohort.csv
python scripts/04_college_stats.py     # CFBD API → data/processed/qb_college_features.csv
python scripts/05_nfl_rushing_stats.py # raw/rushing/*.xls → rushing cols added to qb_cohort.csv
python scripts/06_sportradar_college.py# Sportradar API → data/raw/sportradar_profiles.json
python scripts/07_feature_merge.py     # combine all → data/processed/qb_model_table.csv
python scripts/08_clustering.py        # PCA + K-Means → data/processed/qb_clusters.csv
python scripts/09_composite_score.py   # composite NFL score + recruit bias → qb_composite_scores.csv
python scripts/10_build_sql.py         # load CSVs into MySQL → runs 10 analytical queries
```

---

## Output Files

| File | Contents | Coverage |
|---|---|---|
| `data/raw/qbs_drafted.csv` | 198 drafted QBs, 2008–2024 | Complete |
| `data/raw/nfl_passing_all.csv` | 1,766 player-seasons, 2018–2025 | Complete |
| `data/raw/nfl_rushing_all.csv` | 2,921 player-seasons, 2018–2025 | Complete |
| `data/raw/sportradar_profiles.json` | Career profiles for 44 QBs | 44/44 cohort QBs |
| `data/processed/qb_cohort.csv` | 40 QBs with full NFL stats + rushing | 40/40 |
| `data/processed/qb_college_features.csv` | College stats + recruit ratings | 39/40 CFBD, 34/40 recruit ratings |
| `data/processed/qb_model_table.csv` | 40 QBs × 48 cols, all sources merged | Ready for analysis |
| `data/processed/qb_composite_scores.csv` | 0–100 NFL success score + recruit bias | 40/40 |
| `data/processed/qb_clusters.csv` | PCA scores + K-Means cluster assignments | 40/40 |

---

## SQL Database

The MySQL database (`qb_analysis`) contains 5 tables and 10 pre-written analytical queries.

**Tables:**

| Table | Contents |
|---|---|
| `qb_cohort` | NFL stats + identifiers for all 40 cohort QBs |
| `college_features` | College stats + recruiting data per QB |
| `composite_scores` | 0–100 NFL success score, recruit bias |
| `model_table` | Merged 48-column feature table used for modeling |
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
| Pocket Specialist | High completion %, low rushing — pure passers |
| Athletic Scrambler | High rush yards/att, lower passing efficiency |
| Developmental | Lower across the board — raw prospects |

---

## Known Data Gaps

- `col_explosiveness` and `col_sos_rating` — CFBD free tier returns null for SP+ fields
- Recruit ratings missing for 6 QBs (Josh Allen, Bailey Zappe, Desmond Ridder, Aidan O'Connell, Mason Rudolph, Ryan Finley) — small-school QBs not tracked by 247Sports

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
│   └── 10_build_sql.sql    ← schema + analytical queries (MySQL)
├── .env.local              (git-ignored — API keys + DB credentials)
├── requirements.txt
└── README.md
```
