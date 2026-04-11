"""
Step 1: Parse locally downloaded PFR draft XLS files into a clean QB list.

Files in data/raw/draft/ are named {year}-draft.xls (e.g. 2008-draft.xls).
Add new years by dropping a {year}-draft.xls file in the directory.

Output: data/raw/qbs_drafted.csv
Columns: qb_name, draft_year, draft_round, draft_pick, nfl_team, college
"""

import glob
import re
import pandas as pd

DRAFT_DIR = "data/raw/draft"
OUT_PATH = "data/raw/qbs_drafted.csv"


def flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    """PFR exports use multi-level headers. Flatten to single level."""
    new_cols = []
    for top, bottom in df.columns:
        if "Unnamed" in str(top):
            new_cols.append(bottom)
        else:
            new_cols.append(f"{top}_{bottom}")
    df.columns = new_cols
    return df


def parse_file(path: str, year: int) -> list[dict]:
    dfs = pd.read_html(path)
    if not dfs:
        print(f"  No tables found in {path}")
        return []

    df = flatten_columns(dfs[0])

    # Drop repeated header rows PFR injects mid-table
    df = df[df["Pos"] != "Pos"].copy()

    # Filter to QBs only
    qbs = df[df["Pos"] == "QB"].copy()

    rows = []
    for _, row in qbs.iterrows():
        name = str(row.get("Player", "")).strip()
        if not name or name == "nan":
            continue
        rows.append({
            "qb_name": name,
            "draft_year": year,
            "draft_round": row.get("Rnd", ""),
            "draft_pick": row.get("Pick", ""),
            "nfl_team": row.get("Tm", ""),
            "college": row.get("College/Univ", ""),
        })

    return rows


def main():
    files = sorted(glob.glob(f"{DRAFT_DIR}/*.xls"))

    if not files:
        print(f"No .xls files found in {DRAFT_DIR}/")
        return

    all_rows = []
    for path in files:
        # Extract year from filename: {year}-draft.xls
        match = re.search(r"(\d{4})-draft", path)
        if not match:
            print(f"  Skipping unrecognized filename: {path}")
            continue
        year = int(match.group(1))
        rows = parse_file(path, year)
        print(f"{year}: {len(rows)} QBs — {[r['qb_name'] for r in rows[:3]]}")
        all_rows.extend(rows)

    df = pd.DataFrame(all_rows)
    df.to_csv(OUT_PATH, index=False)
    print(f"\nSaved {len(df)} total QBs to {OUT_PATH}")


if __name__ == "__main__":
    main()
