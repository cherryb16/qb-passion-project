"""
Step 5: Parse NFL advanced rushing stat files and add to cohort.

Files cover 2017–2025 (sportsref_download 41–49, descending from 2025).
Columns include: Att, Yds, 1D, YBC, YBC/Att, YAC, YAC/Att, BrkTkl, Att/Br

Input:  data/raw/rushing/*.xls
        data/processed/qb_cohort.csv
Output: data/raw/nfl_rushing_all.csv
        data/processed/qb_cohort.csv  (updated with rushing columns)
"""

import glob
import pandas as pd

RUSHING_DIR = "data/raw/rushing"
COHORT_PATH = "data/processed/qb_cohort.csv"
RUSHING_OUT = "data/raw/nfl_rushing_all.csv"

# File 41 = 2025, 42 = 2024, ..., 49 = 2017
RUSHING_FILES = {
    "sportsref_download (41).xls": 2025,
    "sportsref_download (42).xls": 2024,
    "sportsref_download (43).xls": 2023,
    "sportsref_download (44).xls": 2022,
    "sportsref_download (45).xls": 2021,
    "sportsref_download (46).xls": 2020,
    "sportsref_download (47).xls": 2019,
    "sportsref_download (48).xls": 2018,
    "sportsref_download (49).xls": 2017,
}


def parse_rushing_file(path: str, year: int) -> pd.DataFrame:
    df = pd.read_html(path)[0]
    df.columns = [b if "Unnamed" in str(a) else f"{a}_{b}" for a, b in df.columns]
    df = df[df["Player"] != "Player"].dropna(subset=["Player"]).copy()

    rename = {
        "Rushing_Att":     "rush_att",
        "Rushing_Yds":     "rush_yds",
        "Rushing_1D":      "rush_1d",
        "Rushing_YBC":     "rush_ybc",
        "Rushing_YBC/Att": "rush_ybc_per_att",
        "Rushing_YAC":     "rush_yac",
        "Rushing_YAC/Att": "rush_yac_per_att",
        "Rushing_BrkTkl":  "rush_brk_tkl",
        "Rushing_Att/Br":  "rush_att_per_brk",
    }
    df = df.rename(columns=rename)

    keep = ["Player", "Age", "Team", "Pos", "G", "GS"] + list(rename.values())
    keep = [c for c in keep if c in df.columns]
    df = df[keep].copy()

    for col in df.columns.difference(["Player", "Team", "Pos"]):
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["season"] = year
    return df


def main():
    # --- Parse all rushing files ---
    frames = []
    for fname, year in RUSHING_FILES.items():
        path = f"{RUSHING_DIR}/{fname}"
        try:
            df = parse_rushing_file(path, year)
            print(f"  {year}: {len(df)} players")
            frames.append(df)
        except Exception as e:
            print(f"  ERROR {fname}: {e}")

    rushing_all = pd.concat(frames, ignore_index=True, sort=False)
    rushing_all.to_csv(RUSHING_OUT, index=False)
    print(f"\nSaved {len(rushing_all)} player-seasons to {RUSHING_OUT}")
    print(f"Columns: {rushing_all.columns.tolist()}")

    # --- Join to cohort ---
    cohort = pd.read_csv(COHORT_PATH)

    def normalize(s):
        return (str(s).strip()
                .replace(" Jr.", "").replace(" Sr.", "")
                .replace(" III", "").replace(" II", "").replace(" IV", ""))

    rushing_all["_name"] = rushing_all["Player"].apply(normalize)
    cohort["_name"] = cohort["qb_name"].apply(normalize)

    results = []
    for _, qb in cohort.iterrows():
        name = qb["_name"]
        draft_year = int(qb["draft_year"])
        seasons_needed = [draft_year, draft_year + 1]

        matches = rushing_all[
            (rushing_all["_name"] == name) &
            (rushing_all["season"].isin(seasons_needed))
        ]

        if matches.empty:
            print(f"  {qb['qb_name']}: no rushing match")
            results.append({"qb_name": qb["qb_name"], "draft_year": draft_year})
            continue

        # Sum counting stats, average rate stats (weighted by attempts)
        att = pd.to_numeric(matches["rush_att"], errors="coerce")
        total_att = att.sum()

        row = {"qb_name": qb["qb_name"], "draft_year": draft_year}

        for col in ["rush_att", "rush_yds", "rush_1d", "rush_ybc", "rush_yac", "rush_brk_tkl"]:
            if col in matches.columns:
                row[f"nfl_{col}"] = pd.to_numeric(matches[col], errors="coerce").sum()

        # Rate stats — attempt-weighted
        for col in ["rush_ybc_per_att", "rush_yac_per_att", "rush_att_per_brk"]:
            if col in matches.columns:
                vals = pd.to_numeric(matches[col], errors="coerce")
                if total_att > 0 and att.notna().any():
                    row[f"nfl_{col}"] = (vals * att).sum() / total_att
                else:
                    row[f"nfl_{col}"] = vals.mean()

        # Derived: rushing yards per attempt
        if row.get("nfl_rush_att", 0) > 0:
            row["nfl_rush_yds_per_att"] = round(row["nfl_rush_yds"] / row["nfl_rush_att"], 2)

        seasons_found = len(matches)
        row["nfl_rush_seasons_found"] = seasons_found
        print(f"  {qb['qb_name']}: {seasons_found} seasons — "
              f"att={row.get('nfl_rush_att')}, yds={row.get('nfl_rush_yds')}, "
              f"ybc/att={row.get('nfl_rush_ybc_per_att', 'N/A'):.2f}" if seasons_found else
              f"  {qb['qb_name']}: no data")
        results.append(row)

    rush_df = pd.DataFrame(results)
    cohort_updated = cohort.drop(columns=["_name"]).merge(
        rush_df.drop(columns=["draft_year"]), on="qb_name", how="left"
    )

    cohort_updated.to_csv(COHORT_PATH, index=False)
    matched = rush_df["nfl_rush_att"].notna().sum()
    print(f"\nMatched rushing data for {matched}/{len(cohort)} QBs")
    print(f"Updated cohort saved to {COHORT_PATH}")


if __name__ == "__main__":
    main()
