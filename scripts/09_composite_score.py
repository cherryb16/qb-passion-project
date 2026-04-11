"""
scripts/09_composite_score.py

Builds a composite NFL success score (0-100) for each cohort QB
and a recruitment bias indicator that compares recruiting prestige to actual
NFL performance.

Components and weights:
  accuracy-focused (higher weight):
    nfl_ontgt_pct   weight=2   higher = better
    nfl_badth_pct   weight=2   lower  = better  (inverted)
    nfl_cmp_pct     weight=1.5 higher = better
  efficiency:
    nfl_any_a       weight=1   higher = better  (Adjusted Net Yards/Attempt)
    nfl_rate        weight=1   higher = better  (passer rating)
    nfl_qbr         weight=1   higher = better  (ESPN QBR)
    nfl_td_pct      weight=1   higher = better
    nfl_int_pct     weight=1   lower  = better  (inverted)
  pressure handling:
    nfl_prss_pct    weight=1   lower  = better  (inverted)
  rushing:
    nfl_rush_yds_per_att weight=1 higher = better

Inputs:
    data/processed/qb_cohort.csv        -- NFL stats per QB
    data/processed/qb_college_features.csv -- college stats + recruiting data

Output:
    data/processed/qb_composite_scores.csv
"""

import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler

# ---------------------------------------------------------------------------
# 1. Load data
# ---------------------------------------------------------------------------
cohort = pd.read_csv("data/processed/qb_cohort.csv")
college = pd.read_csv("data/processed/qb_college_features.csv")

# ---------------------------------------------------------------------------
# 2. Merge: keep only the columns we need from each source
# ---------------------------------------------------------------------------
# From cohort: NFL performance metrics + identifiers
cohort_cols = [
    "qb_name", "draft_year", "draft_round", "draft_pick", "nfl_team",
    "college",
    # raw counting stats needed to derive completion %
    "nfl_cmp", "nfl_att",
    # accuracy metrics
    "nfl_ontgt_pct",        # on-target throw % -- higher is better
    "nfl_badth_pct",        # bad-throw % -- lower is better
    "nfl_cmp_pct",          # completion % -- higher is better
    # efficiency metrics
    "nfl_any_a",            # adjusted net yards per attempt -- higher is better
    "nfl_rate",             # passer rating -- higher is better
    "nfl_qbr",              # ESPN QBR -- higher is better
    "nfl_td_pct",           # TD% -- higher is better
    "nfl_int_pct",          # Int% -- lower is better
    # pressure handling
    "nfl_prss_pct",         # pressure rate -- lower is better
    # rushing
    "nfl_rush_yds_per_att", # rushing yards per attempt -- higher is better
]
cohort_slim = cohort[[c for c in cohort_cols if c in cohort.columns]].copy()

# From college: recruiting data + conference
college_cols = [
    "qb_name",
    "col_conference",
    "recruit_stars",
    "recruit_rating",   # 247Sports composite, 0-1 scale; NaN for some QBs
]
college_slim = college[college_cols].copy()

# Merge on qb_name (one row per QB)
df = cohort_slim.merge(college_slim, on="qb_name", how="left")

# ---------------------------------------------------------------------------
# 3. Define the composite score components
#    Each entry: (column_name, weight, invert)
#    invert=True  -> lower raw value is better -> we flip: 1 - normalized
#    invert=False -> higher raw value is better -> use normalized directly
# ---------------------------------------------------------------------------
COMPONENTS = [
    # Accuracy (upweighted — most predictive of QB skill independent of OL/scheme)
    ("nfl_ontgt_pct",        2.0,  False),  # on-target % -- higher = better
    ("nfl_badth_pct",        2.0,  True),   # bad-throw % -- lower = better
    ("nfl_cmp_pct",          1.5,  False),  # completion % -- higher = better
    # Efficiency
    ("nfl_any_a",            1.0,  False),  # adjusted net yards/attempt
    ("nfl_rate",             1.0,  False),  # passer rating
    ("nfl_qbr",              1.0,  False),  # ESPN QBR
    ("nfl_td_pct",           1.0,  False),  # TD%
    ("nfl_int_pct",          1.0,  True),   # Int% -- lower = better
    # Pressure handling
    ("nfl_prss_pct",         1.0,  True),   # pressure rate -- lower = better
    # Rushing contribution
    ("nfl_rush_yds_per_att", 1.0,  False),  # rushing yards per attempt
]

# ---------------------------------------------------------------------------
# 4. Min-max scale each component; apply weights; sum to composite score
# ---------------------------------------------------------------------------
scaler = MinMaxScaler()

norm_cols = []
weight_map = {}

for raw_col, weight, invert in COMPONENTS:
    if raw_col not in df.columns:
        print(f"  WARNING: '{raw_col}' not found in data — skipping")
        continue

    norm_col = f"norm_{raw_col}"

    values = pd.to_numeric(df[raw_col], errors="coerce").values.astype(float)
    mask = ~np.isnan(values.flatten())
    if mask.sum() < 2:
        print(f"  WARNING: not enough data for '{raw_col}' — skipping")
        continue

    scaler.fit(values[mask].reshape(-1, 1))
    scaled = np.full(len(df), np.nan)
    scaled[mask] = scaler.transform(values[mask].reshape(-1, 1)).flatten()

    if invert:
        scaled = np.where(np.isnan(scaled), np.nan, 1 - scaled)

    df[norm_col] = scaled
    norm_cols.append(norm_col)
    weight_map[norm_col] = weight

# ---------------------------------------------------------------------------
# 5. Weighted composite score (0–100)
#    Weighted mean of normalized components, scaled to 0-100.
# ---------------------------------------------------------------------------
weights = np.array([weight_map[c] for c in norm_cols])

# Build a matrix of norm values, shape (n_qbs, n_components)
norm_matrix = df[norm_cols].values.astype(float)

# Weighted mean per row, ignoring NaN components
weighted_sums = np.nansum(norm_matrix * weights, axis=1)
weight_totals = np.nansum(np.where(np.isnan(norm_matrix), 0, weights), axis=1)
df["composite_nfl_score"] = np.where(weight_totals > 0, weighted_sums / weight_totals * 100, np.nan)

# ---------------------------------------------------------------------------
# 6. Recruitment bias indicator
#    Scale recruit_rating (already 0-1) to 0-100 for comparability.
#    recruit_bias = recruit_rating_scaled - composite_nfl_score
#      Positive -> QB was overvalued by recruiting services vs NFL output
#      Negative -> QB was undervalued by recruiting services vs NFL output
#    QBs without a recruit_rating get NaN for both fields.
# ---------------------------------------------------------------------------
df["recruit_rating_scaled"] = df["recruit_rating"] * 100   # NaN propagates
df["recruit_bias"] = df["recruit_rating_scaled"] - df["composite_nfl_score"]

# ---------------------------------------------------------------------------
# 7. Select and order output columns
# ---------------------------------------------------------------------------
output_cols = [
    "qb_name",
    "draft_year",
    "draft_round",
    "draft_pick",
    "college",
    "col_conference",
    "recruit_stars",
    "recruit_rating",
    "composite_nfl_score",
    "recruit_rating_scaled",
    "recruit_bias",
] + norm_cols  # append each individual normalized component

df_out = df[output_cols].copy()

# ---------------------------------------------------------------------------
# 8. Save to CSV
# ---------------------------------------------------------------------------
out_path = "data/processed/qb_composite_scores.csv"
df_out.to_csv(out_path, index=False)
print(f"Saved {len(df_out)} rows to {out_path}\n")

# ---------------------------------------------------------------------------
# 9. Print sorted table for quick inspection
# ---------------------------------------------------------------------------
# Round floats for readability
display_cols = [
    "qb_name", "draft_year", "draft_round", "college",
    "composite_nfl_score", "recruit_rating_scaled", "recruit_bias",
]
display = df_out[display_cols].copy()
display["composite_nfl_score"] = display["composite_nfl_score"].round(1)
display["recruit_rating_scaled"] = display["recruit_rating_scaled"].round(1)
display["recruit_bias"] = display["recruit_bias"].round(1)

display = display.sort_values("composite_nfl_score", ascending=False).reset_index(drop=True)
display.index += 1  # rank starts at 1

print("=" * 75)
print("QB COMPOSITE NFL SUCCESS SCORE (sorted best → worst)")
print("=" * 75)
print(display.to_string())
print()

# Overvalued (positive bias) -- recruited above their NFL output
over = df_out[df_out["recruit_bias"] > 0].sort_values("recruit_bias", ascending=False)
print("Most OVERVALUED by recruiting (high recruit rating, lower NFL output):")
for _, row in over.head(5).iterrows():
    print(f"  {row['qb_name']:<25} bias={row['recruit_bias']:+.1f}  "
          f"(recruit={row['recruit_rating_scaled']:.1f}, nfl_score={row['composite_nfl_score']:.1f})")

print()

# Undervalued (negative bias)
under = df_out[df_out["recruit_bias"] < 0].sort_values("recruit_bias", ascending=True)
print("Most UNDERVALUED by recruiting (low recruit rating, higher NFL output):")
for _, row in under.head(5).iterrows():
    print(f"  {row['qb_name']:<25} bias={row['recruit_bias']:+.1f}  "
          f"(recruit={row['recruit_rating_scaled']:.1f}, nfl_score={row['composite_nfl_score']:.1f})")
