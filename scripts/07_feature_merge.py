"""
07_feature_merge.py

Merge all data sources into one modelling table:
  1. Backfill col_sacks / col_sack_yds / col_sack_rate in college features
     using Sportradar profiles (last 2 meaningful college seasons)
  2. Join qb_cohort (NFL outcomes) + qb_college_features (college predictors)
  3. Save → data/processed/qb_model_table.csv

Usage:
  python scripts/07_feature_merge.py
"""

import json
import os
import pandas as pd
import numpy as np

PROFILES_PATH = "data/raw/sportradar_profiles.json"
FEATURES_PATH = "data/processed/qb_college_features.csv"
COHORT_PATH   = "data/processed/qb_cohort.csv"
OUTPUT_PATH   = "data/processed/qb_model_table.csv"


def main():
    cohort   = pd.read_csv(COHORT_PATH)
    features = pd.read_csv(FEATURES_PATH)

    # -----------------------------------------------------------------------
    # Step 1: Backfill sack stats from Sportradar profiles (if available)
    # -----------------------------------------------------------------------
    if os.path.exists(PROFILES_PATH):
        with open(PROFILES_PATH) as f:
            profiles = json.load(f)

        sack_rows = []
        for qb_name, profile in profiles.items():
            season_stats = []
            for s in profile.get("seasons", []):
                for t in s.get("teams", []):
                    p = t.get("statistics", {}).get("passing", {})
                    att   = p.get("attempts", 0) or 0
                    sacks = p.get("sacks", 0) or 0
                    syds  = p.get("sack_yards", 0) or 0
                    if att >= 20:
                        season_stats.append({
                            "year": s["year"], "attempts": att,
                            "sacks": sacks, "sack_yds": syds,
                        })

            last2 = sorted(season_stats, key=lambda x: x["year"])[-2:]
            total_att   = sum(r["attempts"] for r in last2)
            total_sacks = sum(r["sacks"]    for r in last2)
            total_syds  = sum(r["sack_yds"] for r in last2)
            sack_rate   = total_sacks / (total_att + total_sacks) if (total_att + total_sacks) > 0 else np.nan

            sack_rows.append({
                "qb_name":      qb_name,
                "sr_sacks":     total_sacks,
                "sr_sack_yds":  total_syds,
                "sr_sack_rate": round(sack_rate, 4) if not np.isnan(sack_rate) else np.nan,
            })

        sack_df = pd.DataFrame(sack_rows)
        print(f"Sportradar sack data: {len(sack_df)} QBs")

        features = features.merge(sack_df, on="qb_name", how="left")
        # Prefer Sportradar sack rate; fall back to CFBD col_sack_rate
        for col, src in [("col_sacks", "sr_sacks"), ("col_sack_yds", "sr_sack_yds"), ("col_sack_rate", "sr_sack_rate")]:
            if src in features.columns:
                features[col] = features[src].combine_first(features.get(col, pd.Series(dtype=float)))
                features.drop(columns=[src], inplace=True)
    else:
        print("No Sportradar profiles found — skipping sack backfill")

    # -----------------------------------------------------------------------
    # Step 2: Merge cohort (NFL outcomes) + college features
    # -----------------------------------------------------------------------

    # All NFL outcome columns present in cohort
    nfl_outcome_cols = [
        # Accuracy
        "nfl_ontgt_pct", "nfl_badth_pct", "nfl_cmp_pct",
        # Efficiency
        "nfl_any_a", "nfl_rate", "nfl_qbr", "nfl_td_pct", "nfl_int_pct",
        # Pressure
        "nfl_prss_pct",
        # Rushing
        "nfl_rush_yds_per_att", "nfl_rush_att", "nfl_rush_yds",
        # Volume
        "nfl_g", "nfl_gs", "nfl_att", "nfl_yds", "nfl_td", "nfl_int",
    ]

    # College predictor columns
    college_predictor_cols = [
        # Traditional passing
        "col_cmp_pct", "col_yds_per_att", "col_td_int_ratio",
        "col_int_rate", "col_sack_rate",
        # Rushing
        "col_rush_yds_per_att",
        # PPA (Predicted Points Added)
        "col_ppa_overall", "col_ppa_pass", "col_ppa_rush",
        # Usage & explosiveness
        "col_usage_overall", "col_usage_pass", "col_usage_rush",
        "col_usage_first_down", "col_usage_second_down", "col_usage_third_down",
        "col_explosiveness",
        # Team context
        "col_team_win_pct", "col_sos_rating",
        # Recruiting
        "recruit_rating", "recruit_stars",
        # Meta
        "col_conference", "col_team", "col_seasons_found",
    ]

    id_cols = ["qb_name", "draft_year", "draft_round", "draft_pick", "nfl_team", "college"]

    cohort_keep   = id_cols + [c for c in nfl_outcome_cols if c in cohort.columns] + ["has_advanced_stats"]
    features_keep = ["qb_name"] + [c for c in college_predictor_cols if c in features.columns]

    model_table = cohort[cohort_keep].merge(
        features[features_keep],
        on="qb_name",
        how="left"
    )

    # -----------------------------------------------------------------------
    # Step 3: Summary and save
    # -----------------------------------------------------------------------
    print(f"\n{'='*60}")
    print(f"Model table: {model_table.shape[0]} QBs × {model_table.shape[1]} columns")

    print(f"\nNFL outcome coverage:")
    for col in nfl_outcome_cols:
        if col in model_table.columns:
            n = model_table[col].notna().sum()
            print(f"  {col:<25} {n:>3}/{len(model_table)} non-null")

    print(f"\nCollege predictor coverage:")
    for col in college_predictor_cols:
        if col in model_table.columns:
            n = model_table[col].notna().sum()
            flag = " *** MISSING ***" if n == 0 else (" (partial)" if n < len(model_table) else "")
            print(f"  {col:<30} {n:>3}/{len(model_table)} non-null{flag}")

    model_table.to_csv(OUTPUT_PATH, index=False)
    print(f"\nSaved → {OUTPUT_PATH}")

    print(f"\nSample (first 5 QBs):")
    preview_cols = ["qb_name", "draft_year", "college", "col_cmp_pct",
                    "col_ppa_pass", "nfl_any_a", "nfl_rate", "nfl_ontgt_pct"]
    print(model_table[[c for c in preview_cols if c in model_table.columns]].head(5).to_string(index=False))


if __name__ == "__main__":
    main()
