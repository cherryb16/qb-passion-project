"""
08_clustering.py

PCA + K-Means clustering on college QB profiles to identify archetypes.

Inputs:  data/processed/qb_model_table.csv
         data/processed/qb_composite_scores.csv
Output:  data/processed/qb_clusters.csv
"""

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.impute import SimpleImputer

MODEL_PATH   = "data/processed/qb_model_table.csv"
SCORES_PATH  = "data/processed/qb_composite_scores.csv"
OUTPUT_PATH  = "data/processed/qb_clusters.csv"

FEATURES = [
    "col_cmp_pct",
    "col_yds_per_att",
    "col_td_int_ratio",
    "col_int_rate",
    "col_ppa_overall",
    "col_ppa_pass",
    "col_usage_overall",
    "col_usage_pass",
    "col_usage_third_down",
    "col_rush_yds_per_att",
    "col_team_win_pct",
    "col_sack_rate",
]

CLUSTER_LABELS = {
    0: "Pure Pocket Passers",
    1: "Efficient Passers",
    2: "Raw Dual-Threats",
    3: "Elite Multi-Dimensional",
}


def main():
    model  = pd.read_csv(MODEL_PATH)
    scores = pd.read_csv(SCORES_PATH)

    # -----------------------------------------------------------------------
    # Prep feature matrix
    # -----------------------------------------------------------------------
    available_features = [feature for feature in FEATURES if feature in model.columns]
    dropped_features = [
        feature for feature in available_features
        if model[feature].dropna().empty
    ]
    clustering_features = [
        feature for feature in available_features
        if feature not in dropped_features
    ]

    if not clustering_features:
        raise ValueError("No non-null clustering features are available.")

    if dropped_features:
        print("Dropping all-null clustering features:")
        for feature in dropped_features:
            print(f"  - {feature}")

    X_raw = model[clustering_features].copy()
    imputer = SimpleImputer(strategy="median")
    X = imputer.fit_transform(X_raw)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # -----------------------------------------------------------------------
    # PCA — 3 components explain ~79% of variance
    # -----------------------------------------------------------------------
    pca = PCA(n_components=3, random_state=42)
    X_pca = pca.fit_transform(X_scaled)

    evr = pca.explained_variance_ratio_
    print("PCA explained variance:")
    for i, v in enumerate(evr):
        print(f"  PC{i+1}: {v:.1%}  (cumulative: {sum(evr[:i+1]):.1%})")

    loadings = pd.DataFrame(
        pca.components_.T,
        index=clustering_features,
        columns=[f"PC{i+1}" for i in range(3)]
    )
    print("\nPC1 — Passing Efficiency axis (top drivers):")
    print(loadings["PC1"].abs().sort_values(ascending=False).head(5).to_string())
    print("\nPC2 — Volume/Usage axis (top drivers):")
    print(loadings["PC2"].abs().sort_values(ascending=False).head(5).to_string())
    print("\nPC3 — Rushing axis (top drivers):")
    print(loadings["PC3"].abs().sort_values(ascending=False).head(5).to_string())

    # -----------------------------------------------------------------------
    # Elbow method to confirm k=4
    # -----------------------------------------------------------------------
    print("\nElbow method (inertia by k):")
    for k in range(2, 7):
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        km.fit(X_pca)
        print(f"  k={k}: {km.inertia_:.1f}")

    # -----------------------------------------------------------------------
    # K-Means with k=4
    # -----------------------------------------------------------------------
    km4 = KMeans(n_clusters=4, random_state=42, n_init=10)
    clusters = km4.fit_predict(X_pca)

    # -----------------------------------------------------------------------
    # Build output dataframe
    # -----------------------------------------------------------------------
    df = model[["qb_name", "draft_year", "draft_round", "college",
                "col_cmp_pct", "col_ppa_pass", "col_rush_yds_per_att",
                "col_usage_overall", "col_int_rate", "col_team_win_pct"]].copy()
    df["cluster_id"]    = clusters
    df["cluster_label"] = df["cluster_id"].map(CLUSTER_LABELS)
    df["pc1"] = X_pca[:, 0].round(4)
    df["pc2"] = X_pca[:, 1].round(4)
    df["pc3"] = X_pca[:, 2].round(4)
    df = df.merge(scores[["qb_name", "composite_nfl_score", "recruit_rating_scaled"]], on="qb_name")

    # -----------------------------------------------------------------------
    # Cluster summaries
    # -----------------------------------------------------------------------
    print("\n" + "=" * 65)
    print("CLUSTER PROFILES")
    print("=" * 65)

    summary_rows = []
    for cid in sorted(df["cluster_id"].unique()):
        sub = df[df["cluster_id"] == cid]
        label = CLUSTER_LABELS[cid]
        avg_score    = sub["composite_nfl_score"].mean()
        avg_cmp      = sub["col_cmp_pct"].mean()
        avg_ppa      = sub["col_ppa_pass"].mean()
        avg_rush     = sub["col_rush_yds_per_att"].mean()
        avg_usage    = sub["col_usage_overall"].mean()
        avg_int_rate = sub["col_int_rate"].mean()
        avg_recruit  = sub["recruit_rating_scaled"].mean()
        n = len(sub)

        print(f"\n[{cid}] {label}  (n={n})")
        print(f"  Avg NFL composite score : {avg_score:.1f}")
        print(f"  College completion %    : {avg_cmp:.1f}%")
        print(f"  College PPA (passing)   : {avg_ppa:.3f}")
        print(f"  College rush yds/att    : {avg_rush:.2f}")
        print(f"  College usage rate      : {avg_usage:.3f}")
        print(f"  College INT rate        : {avg_int_rate:.4f}")
        print(f"  Avg recruit rating      : {avg_recruit:.1f}")
        print(f"  QBs: {sorted(sub['qb_name'].tolist())}")

        summary_rows.append({
            "cluster_id": cid, "cluster_label": label, "n": n,
            "avg_nfl_score": round(avg_score, 1),
            "avg_col_cmp_pct": round(avg_cmp, 1),
            "avg_col_ppa_pass": round(avg_ppa, 3),
            "avg_col_rush_yds_per_att": round(avg_rush, 2),
            "avg_col_usage": round(avg_usage, 3),
            "avg_col_int_rate": round(avg_int_rate, 4),
            "avg_recruit_rating": round(avg_recruit, 1),
        })

    # -----------------------------------------------------------------------
    # Save
    # -----------------------------------------------------------------------
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"\nSaved {len(df)} QBs to {OUTPUT_PATH}")

    summary = pd.DataFrame(summary_rows).sort_values("avg_nfl_score", ascending=False)
    print("\nCluster summary (sorted by avg NFL score):")
    print(summary[["cluster_label", "n", "avg_nfl_score", "avg_col_cmp_pct",
                   "avg_col_ppa_pass", "avg_col_rush_yds_per_att", "avg_recruit_rating"]].to_string(index=False))


if __name__ == "__main__":
    main()
