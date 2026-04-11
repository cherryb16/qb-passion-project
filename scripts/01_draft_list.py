"""
Step 1: Parse locally downloaded PFR draft XLS files into a clean QB list.

Files in data/raw/draft/ are HTML tables exported from PFR with a .xls extension.
They cover 2008–2023 in order: sportsref_download.xls = 2008,
sportsref_download (1).xls = 2009, ..., sportsref_download (15).xls = 2023.

Output: data/raw/qbs_drafted.csv
Columns: qb_name, draft_year, draft_round, draft_pick, nfl_team, college
"""

import glob
import pandas as pd

DRAFT_DIR = "data/raw/draft"
OUT_PATH = "data/raw/qbs_drafted.csv"

# Maps file sort-order index (0-based) to draft year
START_YEAR = 2008


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
    files = sorted(glob.glob(f"{DRAFT_DIR}/*.xls"), key=lambda x: (len(x), x))

    if not files:
        print(f"No .xls files found in {DRAFT_DIR}/")
        return

    all_rows = []
    for i, path in enumerate(files):
        year = START_YEAR + i
        rows = parse_file(path, year)
        print(f"{year}: {len(rows)} QBs — {[r['qb_name'] for r in rows[:3]]}")
        all_rows.extend(rows)

    df = pd.DataFrame(all_rows)
    df.to_csv(OUT_PATH, index=False)
    print(f"\nSaved {len(df)} total QBs to {OUT_PATH}")


if __name__ == "__main__":
    main()
