"""
Step 2: Parse all downloaded PFR passing stat files into a single NFL passing table.

File structure:
  data/raw/passing/sportsref_download (16-26, even).xls  -> 2018-2023 advanced stats
  data/raw/passing/sportsref_download (28-36).xls        -> 2009-2017 standard stats
  (odd files 17-27 are small subsets of the same year — skipped)
  (file 37 = 2001, out of range — skipped)

Output: data/raw/nfl_passing_all.csv
"""

import glob
import os
import pandas as pd

PASSING_DIR = "data/raw/passing"
OUT_PATH = "data/raw/nfl_passing_all.csv"

# --- File-to-year mapping ---
ADVANCED_FILES = {
    "2018-advanced.xls": 2018,
    "2019-advanced.xls": 2019,
    "2020-advanced.xls": 2020,
    "2021-advanced.xls": 2021,
    "2022-advanced.xls": 2022,
    "2023-advanced.xls": 2023,
    "2024-advanced.xls": 2024,
    "2025-advanced.xls": 2025,   # drop file here when available
}

STANDARD_FILES = {
    "2018-standard.xls": 2018,
    "2019-standard.xls": 2019,
    "2020-standard.xls": 2020,
    "2021-standard.xls": 2021,
    "2022-standard.xls": 2022,
    "2023-standard.xls": 2023,
    "2024-standard.xls": 2024,
    "2025-standard.xls": 2025,   # drop file here when available
}


def flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    new_cols = []
    for top, bottom in df.columns:
        if "Unnamed" in str(top):
            new_cols.append(bottom)
        else:
            new_cols.append(f"{top}_{bottom}")
    df.columns = new_cols
    return df


def clean_numeric(series):
    return pd.to_numeric(series, errors="coerce")


def parse_advanced(path: str, year: int) -> pd.DataFrame:
    dfs = pd.read_html(path)
    df = flatten_columns(dfs[0])
    df = df[df["Player"] != "Player"].dropna(subset=["Player"]).copy()

    # Rename all advanced columns to clean, consistent names
    rename = {
        "Passing_Cmp":           "Cmp",
        "Passing_Att":           "Att",
        # Air Yards
        "Air Yards_IAY":         "IAY",
        "Air Yards_IAY/PA":      "IAY_per_att",
        "Air Yards_CAY":         "CAY",
        "Air Yards_CAY/Cmp":     "CAY_per_cmp",
        "Air Yards_CAY/PA":      "CAY_per_att",
        "Air Yards_YAC":         "YAC",
        "Air Yards_YAC/Cmp":     "YAC_per_cmp",
        # Accuracy
        "Accuracy_Bats":         "Bats",
        "Accuracy_ThAwy":        "ThAwy",
        "Accuracy_Spikes":       "Spikes",
        "Accuracy_Drops":        "Drops",
        "Accuracy_Drop%":        "Drop_pct",
        "Accuracy_BadTh":        "BadTh",
        "Accuracy_Bad%":         "BadTh_pct",
        "Accuracy_OnTgt":        "OnTgt",
        "Accuracy_OnTgt%":       "OnTgt_pct",
        # Pressure
        "Pressure_PktTime":      "PktTime",
        "Pressure_Bltz":         "Bltz",
        "Pressure_Hrry":         "Hrry",
        "Pressure_Hits":         "Hits",
        "Pressure_Prss":         "Prss",
        "Pressure_Prss%":        "Prss_pct",
        "Pressure_Scrm":         "Scrm",
        "Pressure_Yds/Scr":      "Yds_per_scr",
        # RPO
        "RPO_Plays":             "RPO_Plays",
        "RPO_Yds":               "RPO_Yds",
        "RPO_PassAtt":           "RPO_PassAtt",
        "RPO_PassYds":           "RPO_PassYds",
        "RPO_RushAtt":           "RPO_RushAtt",
        "RPO_RushYds":           "RPO_RushYds",
        # Play Action
        "PlayAction_PassAtt":    "PA_PassAtt",
        "PlayAction_PassYds":    "PA_PassYds",
    }
    df = df.rename(columns=rename)

    keep = [
        "Player", "Age", "Team", "G", "GS",
        # Passing volume
        "Cmp", "Att",
        # Air yards
        "IAY", "IAY_per_att", "CAY", "CAY_per_cmp", "CAY_per_att",
        "YAC", "YAC_per_cmp",
        # Accuracy
        "Bats", "ThAwy", "Spikes", "Drops", "Drop_pct",
        "BadTh", "BadTh_pct", "OnTgt", "OnTgt_pct",
        # Pressure
        "PktTime", "Bltz", "Hrry", "Hits", "Prss", "Prss_pct",
        "Scrm", "Yds_per_scr",
        # RPO
        "RPO_Plays", "RPO_Yds", "RPO_PassAtt", "RPO_PassYds",
        "RPO_RushAtt", "RPO_RushYds",
        # Play action
        "PA_PassAtt", "PA_PassYds",
    ]
    keep = [c for c in keep if c in df.columns]
    df = df[keep].copy()
    df["season"] = year
    df["stats_type"] = "advanced"
    return df


def parse_standard(path: str, year: int) -> pd.DataFrame:
    dfs = pd.read_html(path)
    df = dfs[0].copy()
    # Single-level columns already
    df = df[df["Player"] != "Player"].dropna(subset=["Player"]).copy()

    keep = [
        "Player", "Age", "Team", "G", "GS",
        "Cmp", "Att", "Cmp%", "Yds", "TD", "TD%", "Int", "Int%",
        "Y/A", "AY/A", "NY/A", "ANY/A", "Rate", "QBR",
        "Sk", "Sk%",
    ]
    keep = [c for c in keep if c in df.columns]
    df = df[keep].copy()
    df["season"] = year
    df["stats_type"] = "standard"
    return df


def main():
    frames = []

    print("Parsing advanced stat files...")
    for fname, year in ADVANCED_FILES.items():
        path = f"{PASSING_DIR}/{fname}"
        if not os.path.exists(path):
            print(f"  {year}: SKIPPED (file not found — drop {fname} to include)")
            continue
        try:
            df = parse_advanced(path, year)
            print(f"  {year}: {len(df)} QBs")
            frames.append(df)
        except Exception as e:
            print(f"  ERROR {fname}: {e}")

    print("\nParsing standard stat files...")
    for fname, year in STANDARD_FILES.items():
        path = f"{PASSING_DIR}/{fname}"
        if not os.path.exists(path):
            print(f"  {year}: SKIPPED (file not found — drop {fname} to include)")
            continue
        try:
            df = parse_standard(path, year)
            print(f"  {year}: {len(df)} QBs")
            frames.append(df)
        except Exception as e:
            print(f"  ERROR {fname}: {e}")

    combined = pd.concat(frames, ignore_index=True, sort=False)

    # Normalize numeric columns
    numeric_cols = combined.columns.difference(["Player", "Team", "stats_type"])
    for col in numeric_cols:
        combined[col] = clean_numeric(combined[col])

    combined = combined.sort_values(["season", "Player"]).reset_index(drop=True)
    combined.to_csv(OUT_PATH, index=False)

    print(f"\nSaved {len(combined)} player-seasons to {OUT_PATH}")
    print(f"Season range: {int(combined['season'].min())}–{int(combined['season'].max())}")
    print(f"Columns: {combined.columns.tolist()}")


if __name__ == "__main__":
    main()
