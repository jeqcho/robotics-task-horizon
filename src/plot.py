"""Slide-quality scatter of human time (log) vs current-robot success probability.

Input:  outputs/manual_tasks_rated_sonnet_4_6.tsv (or RATE_OUTPUT)
Output: plots/human_time_vs_robot_prob.png
"""

from __future__ import annotations

import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
INPUT_PATH = Path(
    os.environ.get("PLOT_INPUT", ROOT / "outputs" / "manual_tasks_rated_sonnet_4_6.tsv")
)
PLOTS_DIR = ROOT / "plots"
PLOTS_DIR.mkdir(exist_ok=True)
OUT_PATH = PLOTS_DIR / "human_time_vs_robot_prob.png"


def main() -> None:
    df = pd.read_csv(INPUT_PATH, sep="\t")
    df["human_time_minutes"] = df["human_time_minutes"].astype(float)
    df["robot_success_prob"] = df["robot_success_prob"].astype(float)

    top_cats = df["task_category"].value_counts().head(8).index.tolist()
    df["cat_plot"] = df["task_category"].where(df["task_category"].isin(top_cats), "other")

    cats = top_cats + ["other"]
    cmap = plt.get_cmap("tab10")
    colors = {c: cmap(i) for i, c in enumerate(cats)}

    fig, ax = plt.subplots(figsize=(14, 9))
    for c in cats:
        sub = df[df["cat_plot"] == c]
        if sub.empty:
            continue
        ax.scatter(
            sub["human_time_minutes"],
            sub["robot_success_prob"],
            s=28,
            alpha=0.55,
            color=colors[c],
            edgecolor="white",
            linewidth=0.4,
            label=f"{c} (n={len(sub)})",
        )

    bins = np.logspace(np.log10(max(df["human_time_minutes"].min(), 0.5)), np.log10(df["human_time_minutes"].max() * 1.01), 11)
    df["bin"] = pd.cut(df["human_time_minutes"], bins=bins, include_lowest=True)
    per_bin = df.groupby("bin", observed=True).agg(
        x=("human_time_minutes", "median"),
        y_median=("robot_success_prob", "median"),
        y_mean=("robot_success_prob", "mean"),
        n=("robot_success_prob", "size"),
    ).dropna()
    ax.plot(per_bin["x"], per_bin["y_mean"], color="black", linewidth=2.5, label="binned mean", zorder=5)

    ax.set_xscale("log")
    ax.set_xlabel("Human completion time per instance (minutes, log scale)", fontsize=16)
    ax.set_ylabel("Current-robot success probability (%)", fontsize=16)
    ax.set_title(
        f"Robot success vs. human task duration on {len(df):,} manual O*NET tasks\n"
        "(rated by Claude Sonnet 4.6; frontier humanoids as of April 2026)",
        fontsize=17,
    )
    ax.set_ylim(-2, 102)
    ax.grid(True, which="both", alpha=0.3)
    ax.tick_params(axis="both", labelsize=13)
    ax.legend(fontsize=11, loc="upper right", framealpha=0.9)

    ax.axhline(50, color="gray", linestyle="--", linewidth=0.8, alpha=0.5)
    ax.text(df["human_time_minutes"].min() * 1.1, 51.5, "50%", fontsize=10, color="gray")

    fig.tight_layout()
    fig.savefig(OUT_PATH, dpi=160, bbox_inches="tight")
    print(f"wrote {OUT_PATH.relative_to(ROOT)} rows={len(df)}")
    print("\nbinned mean robot-success by human-time bin:")
    print(per_bin.to_string())


if __name__ == "__main__":
    main()
