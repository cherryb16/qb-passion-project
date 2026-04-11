# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Goal

STRAT 412 Passion Project — **QB Translation: Which college QB traits predict early NFL success?**

For QBs drafted 2008–2023 who had ≥2 college seasons and played ≥16 NFL games in their first two seasons, run a regression to identify which observable college characteristics best predict early NFL efficiency.

**Managerial framing**: "If I'm an NFL GM, which college QB stats should I prioritize when drafting?"

**Outcome variable**: NFL efficiency metrics (ANY/A, passer rating, pressure rate) from first two NFL seasons.

**Final deliverable deadline**: April 15, 2026 — slide deck, data files, YouTube presentation to Learning Suite.

---

## Data Sources

| Source | What | How Accessed |
|---|---|---|
| Pro-Football-Reference | NFL draft history 2008–2023 | Manually downloaded XLS exports → `data/raw/draft/` |
| Pro-Football-Reference | NFL advanced passing stats 2008–2025 | Manually downloaded XLS exports → `data/raw/passing/` |
| College Football Data API | College stats: PPA, usage, explosiveness, traditional passing/rushing | Free API (cfbd key required) — `scripts/04_college_stats.py` |
| Sportsradar NCAAFB v7 | Backup/supplemental college stats | API key in env var `SPORTRADAR_KEY` |

## Data Status

### Done
- `data/raw/draft/sportsref_download*.xls` — PFR draft files, 2008–2023 (16 files, manually downloaded)
- `data/raw/passing/sportsref_download*.xls` — PFR NFL advanced passing stats, 2008–2025 (manually downloaded)
- `data/raw/qbs_drafted.csv` — 187 drafted QBs, 2008–2023 → `01_draft_list.py`
- `data/raw/nfl_passing_all.csv` — 1,857 player-seasons of NFL passing stats → `02_nfl_passing_stats.py`
- `data/processed/qb_cohort.csv` — 31 QBs (2017–2023 draft, ≥16 NFL games, ≥8 starts, advanced stats era) → `03_build_cohort.py`

### In Progress
- **College stats** — `04_college_stats.py` pulls from CFBD API (needs `CFBD_KEY` env var)
  - Fetches per season year (8 calls total): passing stats, rushing stats, PPA, player usage
  - Caches raw responses to `data/raw/cfbd_raw_stats.json`
  - Outputs `data/processed/qb_college_features.csv`

### Still Needed
- **Feature engineering**: Merge cohort NFL outcomes with college features → single modelling table
- **Regression model**: Linear regression in Python, feature importance/coefficients
- **Tableau dashboard**: QB radar profiles, correlation plots, filter by draft round/conference

### Known Data Gaps
- NFL advanced stats (pressure %, air yards, accuracy) only available 2018–2025; older seasons have standard stats only
- College CFBD data coverage: traditional stats back to ~2004, PPA/usage back to ~2014 (covers all 31 cohort QBs)
- 2020 COVID year: some 2021 draftees had an extra eligibility year — senior season may be 2021 not 2020

---

## Running the Pipeline

Scripts run in order. Activate the shared venv first:

```bash
source ~/.venv/bin/activate
cd /Users/cherrybrayden/Documents/GitHub/qb-passion-project
```

```bash
python scripts/01_draft_list.py         # raw/draft/*.xls → data/raw/qbs_drafted.csv  [DONE]
python scripts/02_nfl_passing_stats.py  # raw/passing/*.xls → data/raw/nfl_passing_all.csv  [DONE]
python scripts/03_build_cohort.py       # draft + NFL stats → data/processed/qb_cohort.csv  [DONE]

export CFBD_KEY="your_key_here"
python scripts/04_college_stats.py      # CFBD API → data/processed/qb_college_features.csv  [IN PROGRESS]

# TODO: feature merge, regression, Tableau
```

---

## Data Architecture

```
data/raw/draft/*.xls          (PFR draft exports, 2008–2023, one file per year)
    └─ 01_draft_list.py ─────► data/raw/qbs_drafted.csv
                                    (qb_name, draft_year, round, pick, team, college)

data/raw/passing/*.xls        (PFR passing stat exports, 2009–2023)
    └─ 02_nfl_passing_stats.py ► data/raw/nfl_passing_all.csv
                                    (Player, season, G, GS, Att, ANY/A, Rate, + advanced stats)

data/raw/qbs_drafted.csv  ──┐
data/raw/nfl_passing_all.csv ┴─► 03_build_cohort.py ──► data/processed/qb_cohort.csv
                                                              (filtered cohort, ~50–80 QBs)

[TBD] college passing stats ──► feature engineering ──► regression model ──► Tableau
```

## Key Implementation Details

- **PFR draft files**: `sportsref_download.xls` = 2008, `sportsref_download (1).xls` = 2009, … index N = 2008+N. Multi-level HTML headers flattened in `01_draft_list.py`.
- **PFR passing files**: `sportsref_download (16).xls` = 2023 advanced, even files 16–26 = 2023–2018 advanced (multi-level headers). Files 28–36 = 2017–2009 standard stats (single-level). Odd files (17–27) are small subsets of same year — skipped. File 37 = 2001 — skipped.
- **Advanced vs standard stats**: Advanced files (2018–2023) have pressure %, air yards, accuracy %. Standard files (2009–2017) have ANY/A, passer rating, TD%, Int%, sack %. Both have G and GS.
- **Cohort filters**: ≥2 college seasons as QB, ≥16 NFL games played across first two seasons.
- **Reproducibility requirement**: All analysis must be traceable raw data → scripts → final numbers. Graders follow the full pipeline without guessing.
