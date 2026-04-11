"""
09_regression.py

Linear regression: which college QB traits predict early NFL success?

For each NFL outcome variable, run:
  1. Pearson correlations with all college predictors
  2. OLS regression (standardized predictors) → coefficients + p-values
  3. Feature importance chart

Outcomes:
  nfl_prss_pct    — pressure rate %     (lower = better, QB avoids pressure)
  nfl_badth_pct   — bad throw %         (lower = better, accuracy)
  nfl_ontgt_pct   — on-target %         (higher = better, 27 QBs only)
  nfl_iay_per_att — intended air yards  (higher = deeper/more aggressive)
  nfl_pkttime     — pocket time         (higher = more patient in pocket)

Usage:
  python scripts/09_regression.py
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")  # non-interactive backend for file output
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from scipy import stats
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score
import warnings
warnings.filterwarnings("ignore")

df = pd.read_csv("data/processed/qb_model_table.csv")
print(f"Loaded model table: {df.shape[0]} QBs, {df.shape[1]} columns")

# ---------------------------------------------------------------------------
# Define predictors and outcomes
# ---------------------------------------------------------------------------
predictors = {
    "col_cmp_pct":           "College Comp%",
    "col_yds_per_att":       "College Yds/Att",
    "col_td_int_ratio":      "College TD/INT",
    "col_int_rate":          "College INT Rate",
    "col_rush_yds_per_att":  "College Rush Yds/Att",
    "col_ppa_overall":       "PPA Overall",
    "col_ppa_pass":          "PPA Pass",
    "col_ppa_rush":          "PPA Rush",
    "col_usage_overall":     "Usage Overall",
    "col_usage_pass":        "Usage Pass",
    "col_usage_third_down":  "Usage 3rd Down",
    "col_sack_rate":         "College Sack Rate",
    "recruit_rating":        "Recruit Rating",
}

outcomes = {
    "nfl_prss_pct":    ("NFL Pressure Rate %",    "lower"),
    "nfl_badth_pct":   ("NFL Bad Throw %",        "lower"),
    "nfl_ontgt_pct":   ("NFL On-Target %",        "higher"),
    "nfl_iay_per_att": ("NFL Air Yards/Att",      "higher"),
    "nfl_pkttime":     ("NFL Pocket Time",        "higher"),
}

pred_cols  = list(predictors.keys())
pred_labels = list(predictors.values())

# ---------------------------------------------------------------------------
# 1. Correlation heatmap: college predictors vs NFL outcomes
# ---------------------------------------------------------------------------
print("\n=== PEARSON CORRELATIONS ===")
corr_data = {}
for out_col, (out_label, direction) in outcomes.items():
    sub = df[[out_col] + pred_cols].dropna()
    corrs = {}
    for pc in pred_cols:
        r, p = stats.pearsonr(sub[pc], sub[out_col])
        corrs[pc] = r
    corr_data[out_label] = corrs
    print(f"\n{out_label} (n={len(sub)}):")
    ranked = sorted(corrs.items(), key=lambda x: abs(x[1]), reverse=True)
    for col, r in ranked[:5]:
        print(f"  {predictors[col]:<25} r={r:+.3f}")

corr_df = pd.DataFrame(corr_data, index=pred_cols)
corr_df.index = pred_labels

fig, ax = plt.subplots(figsize=(10, 8))
sns.heatmap(corr_df,
            annot=True, fmt=".2f", center=0,
            cmap="RdBu_r", vmin=-0.7, vmax=0.7,
            linewidths=0.5, ax=ax,
            annot_kws={"size": 9})
ax.set_title("College Traits vs Early NFL Outcomes\nPearson r", fontsize=13, fontweight="bold")
ax.set_xlabel("NFL Outcome", fontsize=11)
ax.set_ylabel("College Predictor", fontsize=11)
plt.xticks(rotation=20, ha="right")
plt.tight_layout()
plt.savefig("data/processed/corr_heatmap.png", dpi=150)
print("\nSaved: data/processed/corr_heatmap.png")

# ---------------------------------------------------------------------------
# 2. OLS regression per outcome (standardized predictors)
# ---------------------------------------------------------------------------
print("\n=== OLS REGRESSION RESULTS (standardized predictors) ===")

reg_results = {}

for out_col, (out_label, direction) in outcomes.items():
    sub = df[[out_col] + pred_cols].dropna()
    # Use all predictors available in the subset
    available_preds = [c for c in pred_cols if int(sub[c].isna().sum()) == 0]
    X_raw = sub[available_preds].values
    y     = sub[out_col].values

    scaler = StandardScaler()
    X_std  = scaler.fit_transform(X_raw)

    # sklearn for coefficients
    lr = LinearRegression().fit(X_std, y)
    y_pred = lr.predict(X_std)
    r2 = r2_score(y, y_pred)

    # scipy for p-values
    n, k = len(y), len(available_preds)
    residuals = y - y_pred
    se_res = np.sqrt(np.sum(residuals**2) / (n - k - 1))
    X_std_w_const = np.column_stack([np.ones(n), X_std])
    var_coef = se_res**2 * np.linalg.pinv(X_std_w_const.T @ X_std_w_const).diagonal()[1:]
    se_coef  = np.sqrt(np.abs(var_coef))
    t_stats  = lr.coef_ / (se_coef + 1e-12)
    p_vals   = [2 * (1 - stats.t.cdf(abs(t), df=n - k - 1)) for t in t_stats]

    coef_df = pd.DataFrame({
        "predictor": [predictors.get(c, c) for c in available_preds],
        "coef":      lr.coef_,
        "p_val":     p_vals,
    }).sort_values("coef", key=abs, ascending=False)

    reg_results[out_col] = {"label": out_label, "direction": direction,
                             "r2": r2, "n": n, "coefs": coef_df}

    print(f"\n{out_label}  (R²={r2:.3f}, n={n})")
    print(f"  {'Predictor':<25} {'Coef':>8}  {'p-val':>7}  Sig")
    for _, row in coef_df.iterrows():
        sig = "***" if row.p_val < 0.01 else "**" if row.p_val < 0.05 else "*" if row.p_val < 0.1 else ""
        print(f"  {row.predictor:<25} {row.coef:>+8.3f}  {row.p_val:>7.3f}  {sig}")

# ---------------------------------------------------------------------------
# 3. Coefficient bar charts (one per outcome)
# ---------------------------------------------------------------------------
fig, axes = plt.subplots(1, len(outcomes), figsize=(18, 7), sharey=False)

for ax, (out_col, (out_label, direction)) in zip(axes, outcomes.items()):
    res = reg_results[out_col]
    cd  = res["coefs"]

    colors = []
    for _, row in cd.iterrows():
        # Green = "good" direction, Red = "bad", grey = weak
        if row.p_val > 0.15:
            colors.append("#cccccc")
        elif (direction == "lower" and row.coef < 0) or (direction == "higher" and row.coef > 0):
            colors.append("#2ecc71")
        else:
            colors.append("#e74c3c")

    ax.barh(cd["predictor"], cd["coef"], color=colors)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_title(f"{out_label}\nR²={res['r2']:.2f}, n={res['n']}", fontsize=10, fontweight="bold")
    ax.set_xlabel("Standardized β", fontsize=9)
    ax.tick_params(axis="y", labelsize=8)

    # Significance markers
    for i, (_, row) in enumerate(cd.iterrows()):
        if row.p_val < 0.1:
            marker = "***" if row.p_val < 0.01 else "**" if row.p_val < 0.05 else "*"
            x_offset = row.coef + (0.02 if row.coef >= 0 else -0.02)
            ax.text(x_offset, i, marker, va="center", ha="left" if row.coef >= 0 else "right",
                    fontsize=8, color="black")

legend_handles = [
    mpatches.Patch(color="#2ecc71", label="Positive effect"),
    mpatches.Patch(color="#e74c3c", label="Negative effect"),
    mpatches.Patch(color="#cccccc", label="p > 0.15"),
]
fig.legend(handles=legend_handles, loc="lower center", ncol=3, fontsize=9,
           bbox_to_anchor=(0.5, -0.02))
plt.suptitle("Which College Traits Predict Early NFL Success?\n(Standardized OLS Coefficients — * p<0.1  ** p<0.05  *** p<0.01)",
             fontsize=12, fontweight="bold")
plt.tight_layout(rect=[0, 0.05, 1, 1])
plt.savefig("data/processed/regression_coefficients.png", dpi=150, bbox_inches="tight")
print("\nSaved: data/processed/regression_coefficients.png")

# ---------------------------------------------------------------------------
# 4. Top scatter plots: strongest single-predictor relationships
# ---------------------------------------------------------------------------
# Find top 2 correlations across all outcomes
top_pairs = []
for out_col, (out_label, direction) in outcomes.items():
    sub = df[[out_col] + pred_cols].dropna()
    for pc in pred_cols:
        r, p = stats.pearsonr(sub[pc], sub[out_col])
        top_pairs.append((abs(r), r, pc, out_col, out_label, direction, p, len(sub)))

top_pairs.sort(reverse=True)
seen = set()
unique_top = []
for item in top_pairs:
    key = (item[2], item[3])
    if key not in seen:
        seen.add(key)
        unique_top.append(item)
    if len(unique_top) == 6:
        break

fig, axes = plt.subplots(2, 3, figsize=(14, 9))
axes = axes.flatten()

for ax, (abs_r, r, pc, out_col, out_label, direction, p, n) in zip(axes, unique_top):
    sub = df[[out_col, pc, "qb_name"]].dropna()
    ax.scatter(sub[pc], sub[out_col], alpha=0.7, s=60, color="#2980b9")

    # Add QB name labels for notable outliers
    q_hi = sub[pc].quantile(0.85)
    q_lo = sub[pc].quantile(0.15)
    for _, row in sub.iterrows():
        if row[pc] >= q_hi or row[pc] <= q_lo:
            ax.annotate(row["qb_name"].split()[-1],
                        (row[pc], row[out_col]),
                        textcoords="offset points", xytext=(4, 2),
                        fontsize=7, alpha=0.8)

    # Trendline
    m, b = np.polyfit(sub[pc], sub[out_col], 1)
    x_line = np.linspace(sub[pc].min(), sub[pc].max(), 100)
    ax.plot(x_line, m * x_line + b, "r--", linewidth=1.5, alpha=0.8)

    ax.set_xlabel(predictors.get(pc, pc), fontsize=10)
    ax.set_ylabel(out_label, fontsize=10)
    ax.set_title(f"r={r:+.3f}  p={p:.3f}  n={n}", fontsize=10)

plt.suptitle("Top College → NFL Predictor Relationships",
             fontsize=13, fontweight="bold")
plt.tight_layout()
plt.savefig("data/processed/top_scatter_plots.png", dpi=150)
print("Saved: data/processed/top_scatter_plots.png")

# ---------------------------------------------------------------------------
# 5. Print GM-facing summary
# ---------------------------------------------------------------------------
print("\n" + "="*60)
print("GM TAKEAWAYS: Which college stats matter most?")
print("="*60)

# Strongest correlations across all outcomes
print("\nStrongest single-predictor correlations (|r| > 0.25):")
for abs_r, r, pc, out_col, out_label, direction, p, n in unique_top[:10]:
    if abs_r > 0.25:
        sign_word = "↑" if r > 0 else "↓"
        print(f"  {predictors.get(pc,'?'):<25} {sign_word} {out_label:<22}  r={r:+.3f}  p={p:.3f}")

print("\nDone. Outputs in data/processed/")
