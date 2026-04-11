"""
Step 3: Join draft list to NFL passing stats, filter to cohort, and compute
        base-level NFL outcome metrics for each QB's first two seasons.

Cohort filters:
  - nfl_games_played_yrs1_2 >= 16  (got a real NFL opportunity)
  - [college filter TBD once college stats are sourced]

For each QB in the cohort, compute NFL outcomes aggregated across seasons 1-2:
  - Games played / started
  - Standard stats: ANY/A, passer rating, TD%, Int%, Y/A, sack rate
  - Advanced stats (2018+ draftees only): pressure %, on-target %, bad throw %,
    intended air yards per attempt, pocket time

Input:  data/raw/qbs_drafted.csv
        data/raw/nfl_passing_all.csv
Output: data/processed/qb_cohort.csv
"""

import pandas as pd

DRAFTED_PATH = "data/raw/qbs_drafted.csv"
PASSING_PATH = "data/raw/nfl_passing_all.csv"
OUT_PATH = "data/processed/qb_cohort.csv"

MIN_NFL_GAMES = 16
MIN_NFL_STARTS = 8


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def weighted_avg(df, stat_col, weight_col):
    """Attempt-weighted average of a rate stat across multiple seasons."""
    mask = df[stat_col].notna() & df[weight_col].notna()
    d = df[mask]
    if d.empty or d[weight_col].sum() == 0:
        return None
    return (d[stat_col] * d[weight_col]).sum() / d[weight_col].sum()


def aggregate_nfl_seasons(seasons_df):
    """
    Given 1-2 rows of a QB's NFL seasons, return a single aggregated record.
    Counting stats are summed; rate stats are attempt-weighted.
    """
    out = {}

    seasons_df = seasons_df.copy()
    seasons_df["_att"] = pd.to_numeric(seasons_df.get("Att"), errors="coerce")

    # Counting stats — sum across seasons
    count_cols = [
        "G", "GS", "Cmp", "Att",
        "IAY", "CAY", "YAC",
        "Bats", "ThAwy", "Spikes", "Drops", "BadTh", "OnTgt",
        "Bltz", "Hrry", "Hits", "Prss", "Scrm",
        "RPO_Plays", "RPO_Yds", "RPO_PassAtt", "RPO_PassYds",
        "RPO_RushAtt", "RPO_RushYds",
        "PA_PassAtt", "PA_PassYds",
    ]
    for col in count_cols:
        if col in seasons_df.columns:
            out[f"nfl_{col.lower()}"] = pd.to_numeric(seasons_df[col], errors="coerce").sum()

    # Rate stats — attempt-weighted average
    rate_cols = [
        "IAY_per_att", "CAY_per_cmp", "CAY_per_att", "YAC_per_cmp",
        "Drop_pct", "BadTh_pct", "OnTgt_pct",
        "PktTime", "Prss_pct", "Yds_per_scr",
    ]
    for col in rate_cols:
        if col in seasons_df.columns:
            out[f"nfl_{col.lower()}"] = weighted_avg(seasons_df, col, "_att")

    # Track which seasons were found
    out["nfl_seasons_found"] = len(seasons_df)
    out["nfl_seasons"] = ",".join(str(int(s)) for s in sorted(
        pd.to_numeric(seasons_df.get("season", pd.Series([])), errors="coerce").dropna()
    ))
    out["has_advanced_stats"] = seasons_df.get("stats_type", pd.Series([])).eq("advanced").any()

    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    drafted = pd.read_csv(DRAFTED_PATH)
    passing = pd.read_csv(PASSING_PATH)

    print(f"Drafted QBs: {len(drafted)}")
    print(f"NFL passing player-seasons: {len(passing)}")

    # Normalize player names for joining (strip whitespace, drop suffixes)
    def normalize(s):
        return (str(s).strip()
                .replace(" Jr.", "").replace(" Sr.", "")
                .replace(" III", "").replace(" II", "").replace(" IV", ""))

    drafted["_name"] = drafted["qb_name"].apply(normalize)
    passing["_name"] = passing["Player"].apply(normalize)

    results = []
    unmatched = []

    for _, qb in drafted.iterrows():
        name = qb["_name"]
        draft_year = int(qb["draft_year"])
        seasons_needed = [draft_year, draft_year + 1]

        # Look up this QB's passing rows in their first two NFL seasons
        matches = passing[
            (passing["_name"] == name) &
            (passing["season"].isin(seasons_needed))
        ]

        if matches.empty:
            unmatched.append(name)
            continue

        agg = aggregate_nfl_seasons(matches)
        games_played = agg.get("nfl_g", 0) or 0

        row = {
            "qb_name": qb["qb_name"],
            "draft_year": draft_year,
            "draft_round": qb["draft_round"],
            "draft_pick": qb["draft_pick"],
            "nfl_team": qb["nfl_team"],
            "college": qb["college"],
        }
        row.update(agg)
        results.append(row)

    df = pd.DataFrame(results)

    print(f"\nMatched {len(df)} QBs to NFL passing data")
    print(f"Unmatched ({len(unmatched)}): {unmatched[:10]}")

    # Apply cohort filter
    cohort = df[
        (pd.to_numeric(df["nfl_g"], errors="coerce").fillna(0) >= MIN_NFL_GAMES) &
        (pd.to_numeric(df["nfl_gs"], errors="coerce").fillna(0) >= MIN_NFL_STARTS) &
        (df["has_advanced_stats"] == True)
    ].copy()
    cohort = cohort.sort_values(["draft_year", "draft_pick"]).reset_index(drop=True)

    print(f"\nAfter ≥{MIN_NFL_GAMES} NFL games and ≥{MIN_NFL_STARTS} starts filter: {len(cohort)} QBs")
    print(f"\nBy draft year:")
    print(cohort.groupby("draft_year").size().to_string())

    print(f"\nSample (name, year, G, ANY/A, passer rating):")
    sample_cols = ["qb_name", "draft_year", "nfl_g", "nfl_gs",
                   "nfl_any_per_a", "nfl_rate", "has_advanced_stats"]
    print(cohort[[c for c in sample_cols if c in cohort.columns]].head(15).to_string(index=False))

    cohort.to_csv(OUT_PATH, index=False)
    print(f"\nSaved {len(cohort)} QBs to {OUT_PATH}")


if __name__ == "__main__":
    main()
