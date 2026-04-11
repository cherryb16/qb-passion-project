"""
08_feature_merge.py

Merge all data sources into one modelling table:
  1. Backfill col_sacks / col_sack_yds / col_sack_rate in college features
     using Sportradar profiles (last 2 meaningful college seasons, matching CFBD window)
  2. Join qb_cohort (NFL outcomes) + qb_college_features (college predictors)
  3. Save → data/processed/qb_model_table.csv

Output columns (key):
  College predictors  : col_cmp_pct, col_yds_per_att, col_td_int_ratio, col_int_rate,
                        col_rush_yds_per_att, col_ppa_overall, col_ppa_pass, col_ppa_rush,
                        col_usage_overall, col_usage_pass, col_usage_rush,
                        col_usage_third_down, col_sack_rate, recruit_rating
  NFL outcomes        : nfl_prss_pct, nfl_badth_pct, nfl_ontgt_pct,
                        nfl_iay_per_att, nfl_pkttime

Usage:
  python scripts/08_feature_merge.py
"""

import json
import pandas as pd
import numpy as np

PROFILES_PATH   = "data/raw/sportradar_profiles.json"
FEATURES_PATH   = "data/processed/qb_college_features.csv"
COHORT_PATH     = "data/processed/qb_cohort.csv"
OUTPUT_PATH     = "data/processed/qb_model_table.csv"

# ---------------------------------------------------------------------------
# Step 1: Extract sack stats from Sportradar profiles
# ---------------------------------------------------------------------------
with open(PROFILES_PATH) as f:
    profiles = json.load(f)

sack_rows = []

for qb_name, profile in profiles.items():
    seasons = profile.get("seasons", [])

    # Build list of (year, attempts, sacks, sack_yards) for meaningful seasons
    season_stats = []
    for s in seasons:
        for t in s.get("teams", []):
            p = t.get("statistics", {}).get("passing", {})
            att   = p.get("attempts", 0) or 0
            sacks = p.get("sacks", 0) or 0
            syds  = p.get("sack_yards", 0) or 0
            if att >= 20:  # meaningful season
                season_stats.append({
                    "year":      s["year"],
                    "attempts":  att,
                    "sacks":     sacks,
                    "sack_yds":  syds,
                })

    # Take last 2 meaningful seasons (matching CFBD col_seasons_found=2 window)
    last2 = sorted(season_stats, key=lambda x: x["year"])[-2:]

    total_att   = sum(r["attempts"] for r in last2)
    total_sacks = sum(r["sacks"]    for r in last2)
    total_syds  = sum(r["sack_yds"] for r in last2)

    # Sack rate = sacks / (attempts + sacks)  [sacks per dropback]
    sack_rate = total_sacks / (total_att + total_sacks) if (total_att + total_sacks) > 0 else np.nan

    sack_rows.append({
        "qb_name":      qb_name,
        "sr_sacks":     total_sacks,
        "sr_sack_yds":  total_syds,
        "sr_sack_rate": round(sack_rate, 4),
    })

sack_df = pd.DataFrame(sack_rows)
print(f"Sportradar sack data: {len(sack_df)} QBs")
print(sack_df.sort_values("sr_sack_rate", ascending=False).to_string(index=False))

# ---------------------------------------------------------------------------
# Step 2: Backfill sack columns in college features
# ---------------------------------------------------------------------------
features = pd.read_csv(FEATURES_PATH)

features = features.merge(sack_df, on="qb_name", how="left")

features["col_sacks"]     = features["sr_sacks"]
features["col_sack_yds"]  = features["sr_sack_yds"]
features["col_sack_rate"] = features["sr_sack_rate"]

features.drop(columns=["sr_sacks", "sr_sack_yds", "sr_sack_rate"], inplace=True)

# Save updated features
features.to_csv(FEATURES_PATH, index=False)
print(f"\nUpdated {FEATURES_PATH} — col_sack_rate null: {features['col_sack_rate'].isnull().sum()}")

# ---------------------------------------------------------------------------
# Step 3: Merge cohort (NFL outcomes) + college features
# ---------------------------------------------------------------------------
cohort = pd.read_csv(COHORT_PATH)

# NFL outcome columns we care about
outcome_cols = [
    "nfl_prss_pct",     # pressure rate (lower = better)
    "nfl_badth_pct",    # bad throw % (lower = better)
    "nfl_ontgt_pct",    # on-target % (higher = better)
    "nfl_iay_per_att",  # intended air yards per attempt (deeper throws)
    "nfl_pkttime",      # pocket time (time before throwing)
]

# College predictor columns
predictor_cols = [
    "col_cmp_pct",
    "col_yds_per_att",
    "col_td_int_ratio",
    "col_int_rate",
    "col_rush_yds_per_att",
    "col_ppa_overall",
    "col_ppa_pass",
    "col_ppa_rush",
    "col_usage_overall",
    "col_usage_pass",
    "col_usage_rush",
    "col_usage_first_down",
    "col_usage_second_down",
    "col_usage_third_down",
    "col_sack_rate",
    "recruit_rating",
    "recruit_stars",
]

# Keep id cols + outcomes from cohort
cohort_keep = ["qb_name", "draft_year", "draft_round", "draft_pick", "nfl_team",
               "college", "nfl_g", "nfl_gs", "has_advanced_stats"] + outcome_cols

# Keep id cols + predictors from features
features_keep = ["qb_name"] + predictor_cols

model_table = cohort[cohort_keep].merge(
    features[features_keep],
    on="qb_name",
    how="left"
)

# ---------------------------------------------------------------------------
# Step 4: Summary and save
# ---------------------------------------------------------------------------
print(f"\n{'='*60}")
print(f"Model table shape: {model_table.shape}")
print(f"\nOutcome variable coverage:")
for col in outcome_cols:
    n = model_table[col].notna().sum()
    print(f"  {col:<20} {n:>3}/{len(model_table)} non-null")

print(f"\nPredictor coverage:")
for col in predictor_cols:
    n = model_table[col].notna().sum()
    flag = " **MISSING**" if n < len(model_table) else ""
    print(f"  {col:<25} {n:>3}/{len(model_table)} non-null{flag}")

model_table.to_csv(OUTPUT_PATH, index=False)
print(f"\nSaved → {OUTPUT_PATH}")
print(f"\nPreview:")
print(model_table[["qb_name", "draft_year", "col_cmp_pct", "col_sack_rate",
                    "nfl_prss_pct", "nfl_badth_pct"]].to_string(index=False))
