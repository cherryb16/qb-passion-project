"""
10_build_sql.py

Build a SQLite database from the processed CSV files.

Tables created:
  qb_cohort         -- NFL stats + identifiers for all 40 cohort QBs
  college_features  -- College stats + recruiting data per QB
  composite_scores  -- Composite NFL success scores + recruit bias
  model_table       -- Merged feature table used for modeling
  qb_clusters       -- PCA + K-Means cluster assignments

Database: data/qb_analysis.db

Also runs and prints a set of analytical SQL queries to demonstrate the
findings from the project (draft round vs. score, recruit bias, cluster
summaries, top college predictors, conference breakdowns).
"""

import sqlite3
import pandas as pd
import os

DB_PATH = "data/qb_analysis.db"

CSV_MAP = {
    "qb_cohort":        "data/processed/qb_cohort.csv",
    "college_features": "data/processed/qb_college_features.csv",
    "composite_scores": "data/processed/qb_composite_scores.csv",
    "model_table":      "data/processed/qb_model_table.csv",
    "qb_clusters":      "data/processed/qb_clusters.csv",
}

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def load_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    # Normalize column names: lowercase, spaces → underscores
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    return df


def create_db(db_path: str) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"Removed existing database at {db_path}")
    conn = sqlite3.connect(db_path)
    return conn


def load_tables(conn: sqlite3.Connection) -> None:
    for table_name, csv_path in CSV_MAP.items():
        if not os.path.exists(csv_path):
            print(f"  WARNING: {csv_path} not found — skipping table '{table_name}'")
            continue
        df = load_csv(csv_path)
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        print(f"  Loaded '{table_name}': {len(df)} rows × {len(df.columns)} cols")


# ---------------------------------------------------------------------------
# Analytical queries
# ---------------------------------------------------------------------------

QUERIES = [
    (
        "Average composite NFL score by draft round",
        """
        SELECT
            draft_round,
            COUNT(*)                              AS n_qbs,
            ROUND(AVG(composite_nfl_score), 1)   AS avg_nfl_score,
            ROUND(MIN(composite_nfl_score), 1)   AS min_score,
            ROUND(MAX(composite_nfl_score), 1)   AS max_score
        FROM composite_scores
        GROUP BY draft_round
        ORDER BY draft_round
        """,
    ),
    (
        "Top 10 QBs by composite NFL success score",
        """
        SELECT
            qb_name,
            draft_year,
            draft_round,
            ROUND(composite_nfl_score, 1)         AS nfl_score,
            ROUND(recruit_rating_scaled, 1)        AS recruit_rating,
            ROUND(recruit_bias, 1)                 AS recruit_bias
        FROM composite_scores
        ORDER BY composite_nfl_score DESC
        LIMIT 10
        """,
    ),
    (
        "Most overvalued QBs (high recruit rating, low NFL output)",
        """
        SELECT
            qb_name,
            draft_year,
            draft_round,
            ROUND(recruit_rating_scaled, 1)        AS recruit_rating,
            ROUND(composite_nfl_score, 1)          AS nfl_score,
            ROUND(recruit_bias, 1)                 AS recruit_bias
        FROM composite_scores
        WHERE recruit_bias IS NOT NULL
        ORDER BY recruit_bias DESC
        LIMIT 10
        """,
    ),
    (
        "Most undervalued QBs (low recruit rating, high NFL output)",
        """
        SELECT
            qb_name,
            draft_year,
            draft_round,
            ROUND(recruit_rating_scaled, 1)        AS recruit_rating,
            ROUND(composite_nfl_score, 1)          AS nfl_score,
            ROUND(recruit_bias, 1)                 AS recruit_bias
        FROM composite_scores
        WHERE recruit_bias IS NOT NULL
        ORDER BY recruit_bias ASC
        LIMIT 10
        """,
    ),
    (
        "Cluster summary: avg NFL score, completion %, PPA, rushing by archetype",
        """
        SELECT
            cluster_label,
            COUNT(*)                               AS n_qbs,
            ROUND(AVG(composite_nfl_score), 1)    AS avg_nfl_score,
            ROUND(AVG(col_cmp_pct), 1)            AS avg_col_cmp_pct,
            ROUND(AVG(col_ppa_pass), 3)           AS avg_col_ppa_pass,
            ROUND(AVG(col_rush_yds_per_att), 2)   AS avg_rush_yds_per_att,
            ROUND(AVG(recruit_rating_scaled), 1)  AS avg_recruit_rating
        FROM qb_clusters
        GROUP BY cluster_label
        ORDER BY avg_nfl_score DESC
        """,
    ),
    (
        "College completion % vs NFL score (correlation proxy — decile buckets)",
        """
        SELECT
            CASE
                WHEN col_cmp_pct < 58  THEN '< 58%'
                WHEN col_cmp_pct < 62  THEN '58-62%'
                WHEN col_cmp_pct < 65  THEN '62-65%'
                WHEN col_cmp_pct < 68  THEN '65-68%'
                ELSE '68%+'
            END                                    AS col_cmp_bucket,
            COUNT(*)                               AS n_qbs,
            ROUND(AVG(cs.composite_nfl_score), 1) AS avg_nfl_score
        FROM model_table m
        JOIN composite_scores cs ON m.qb_name = cs.qb_name
        WHERE col_cmp_pct IS NOT NULL
        GROUP BY col_cmp_bucket
        ORDER BY col_cmp_bucket
        """,
    ),
    (
        "Average NFL score by conference (min 3 QBs)",
        """
        SELECT
            m.col_conference,
            COUNT(*)                               AS n_qbs,
            ROUND(AVG(cs.composite_nfl_score), 1) AS avg_nfl_score
        FROM model_table m
        JOIN composite_scores cs ON m.qb_name = cs.qb_name
        WHERE m.col_conference IS NOT NULL
        GROUP BY m.col_conference
        HAVING COUNT(*) >= 3
        ORDER BY avg_nfl_score DESC
        """,
    ),
    (
        "Round 1 busts: first-round picks scoring below 45",
        """
        SELECT
            qb_name,
            draft_year,
            draft_round,
            draft_pick,
            ROUND(composite_nfl_score, 1)          AS nfl_score,
            ROUND(recruit_rating_scaled, 1)        AS recruit_rating
        FROM composite_scores
        WHERE draft_round = 1
          AND composite_nfl_score < 45
        ORDER BY composite_nfl_score ASC
        """,
    ),
    (
        "Late-round overachievers: rounds 3–7 scoring above cohort mean (58)",
        """
        SELECT
            qb_name,
            draft_year,
            draft_round,
            draft_pick,
            ROUND(composite_nfl_score, 1)          AS nfl_score,
            ROUND(recruit_rating_scaled, 1)        AS recruit_rating
        FROM composite_scores
        WHERE draft_round >= 3
          AND composite_nfl_score > 58
        ORDER BY composite_nfl_score DESC
        """,
    ),
    (
        "College PPA vs NFL score (PPA quartile buckets)",
        """
        SELECT
            CASE
                WHEN col_ppa_overall < 0.2   THEN 'Q1: < 0.20'
                WHEN col_ppa_overall < 0.35  THEN 'Q2: 0.20–0.35'
                WHEN col_ppa_overall < 0.50  THEN 'Q3: 0.35–0.50'
                ELSE 'Q4: 0.50+'
            END                                    AS ppa_bucket,
            COUNT(*)                               AS n_qbs,
            ROUND(AVG(cs.composite_nfl_score), 1) AS avg_nfl_score
        FROM model_table m
        JOIN composite_scores cs ON m.qb_name = cs.qb_name
        WHERE col_ppa_overall IS NOT NULL
        GROUP BY ppa_bucket
        ORDER BY ppa_bucket
        """,
    ),
]


def run_queries(conn: sqlite3.Connection) -> None:
    print("\n" + "=" * 70)
    print("ANALYTICAL SQL QUERIES")
    print("=" * 70)

    for title, sql in QUERIES:
        print(f"\n--- {title} ---")
        try:
            df = pd.read_sql_query(sql, conn)
            print(df.to_string(index=False))
        except Exception as e:
            print(f"  ERROR: {e}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Building SQLite database...")
    conn = create_db(DB_PATH)

    print("\nLoading tables:")
    load_tables(conn)

    conn.commit()

    # Verify row counts
    print("\nRow counts in database:")
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    for t in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {t}")
        n = cursor.fetchone()[0]
        print(f"  {t:<22} {n} rows")

    run_queries(conn)

    conn.close()
    print(f"\nDatabase saved to {DB_PATH}")


if __name__ == "__main__":
    main()
