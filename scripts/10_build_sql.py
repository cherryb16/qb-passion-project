"""
10_build_sql.py

Loads processed CSVs into a SQLite database and runs the analytical queries
defined in scripts/10_build_sql.sql.

No server or installation required — the database is a single file.

Usage:
    python scripts/10_build_sql.py

Database: data/qb_analysis.db
SQL file: scripts/10_build_sql.sql
"""

import os
import re
import sqlite3

import pandas as pd

DB_PATH  = "data/qb_analysis.db"
SQL_PATH = "scripts/10_build_sql.sql"

CSV_MAP = {
    "qb_cohort":        "data/processed/qb_cohort.csv",
    "college_features": "data/processed/qb_college_features.csv",
    "composite_scores": "data/processed/qb_composite_scores.csv",
    "model_table":      "data/processed/qb_model_table.csv",
    "qb_clusters":      "data/processed/qb_clusters.csv",
}


def load_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    return df


def load_tables(conn: sqlite3.Connection) -> None:
    for table_name, csv_path in CSV_MAP.items():
        if not os.path.exists(csv_path):
            print(f"  WARNING: {csv_path} not found — skipping '{table_name}'")
            continue
        df = load_csv(csv_path)
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        print(f"  {table_name:<22} {len(df)} rows x {len(df.columns)} cols")


def run_queries(conn: sqlite3.Connection) -> None:
    with open(SQL_PATH) as f:
        sql_text = f.read()

    # Split on the numbered section headers
    sections = re.split(
        r"--\s*-{5,}\n--\s*(\d+\. .+?)\n--\s*-{5,}",
        sql_text,
    )

    print("\n" + "=" * 70)
    print("ANALYTICAL SQL QUERIES")
    print("=" * 70)

    i = 1
    while i < len(sections):
        title = sections[i].strip()
        body  = sections[i + 1] if i + 1 < len(sections) else ""
        i += 2

        match = re.search(r"(SELECT[\s\S]+?);", body, re.IGNORECASE)
        if not match:
            continue

        stmt = match.group(1).strip()
        print(f"\n--- {title} ---")
        try:
            df = pd.read_sql_query(stmt, conn)
            print(df.to_string(index=False))
        except Exception as e:
            print(f"  ERROR: {e}")


def main():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"Removed existing database: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)

    print("\nLoading tables:")
    load_tables(conn)
    conn.commit()

    run_queries(conn)

    conn.close()
    print(f"\nDone. Database saved to {DB_PATH}")


if __name__ == "__main__":
    main()
