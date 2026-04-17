"""Slide-quality histogram of human completion time across manual O*NET tasks.

Input:  outputs/manual_tasks_rated_sonnet_4_6.tsv (or PLOT_INPUT)
Output: plots/human_time_histogram.png
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
OUT_PATH = PLOTS_DIR / "human_time_histogram.png"


def main() -> None:
    df = pd.read_csv(INPUT_PATH, sep="\t")
    t = df["human_time_minutes"].astype(float)
    n = len(t)

    bins = np.logspace(np.log10(max(t.min(), 0.1)), np.log10(t.max() * 1.01), 26)

    fig, ax = plt.subplots(figsize=(14, 8))
    counts, edges, patches = ax.hist(
        t,
        bins=bins,
        color="#4a8cd8",
        edgecolor="white",
        linewidth=0.6,
    )

    share = counts / n * 100
    for i, p in enumerate(patches):
        if share[i] >= 1.5:
            cx = (edges[i] * edges[i + 1]) ** 0.5
            ax.text(cx, counts[i] + n * 0.004, f"{share[i]:.1f}%", ha="center", va="bottom", fontsize=10)

    median = float(t.median())
    mean = float(t.mean())
    ax.axvline(median, color="black", linestyle="--", linewidth=1.5, label=f"median = {median:g} min")
    ax.axvline(mean, color="firebrick", linestyle=":", linewidth=1.5, label=f"mean = {mean:.1f} min")

    ax.set_xscale("log")
    ax.set_xlabel("Human completion time per instance (minutes, log scale)", fontsize=16)
    ax.set_ylabel("Number of manual O*NET tasks", fontsize=16)
    ax.set_title(
        f"Human completion time across {n:,} manual O*NET tasks\n"
        "(rated by Claude Sonnet 4.6)",
        fontsize=17,
    )
    ax.tick_params(axis="both", labelsize=13)
    ax.grid(True, which="both", axis="y", alpha=0.3)

    tick_positions = [0.25, 1, 5, 15, 60, 240, 8 * 60, 24 * 60, 7 * 24 * 60]
    tick_labels = ["15s", "1m", "5m", "15m", "1h", "4h", "8h", "1d", "1w"]
    valid = [(p, lab) for p, lab in zip(tick_positions, tick_labels) if t.min() <= p <= t.max() * 1.01]
    ax.set_xticks([p for p, _ in valid])
    ax.set_xticklabels([lab for _, lab in valid])

    ax.legend(fontsize=12, loc="upper right", framealpha=0.9)

    fig.tight_layout()
    fig.savefig(OUT_PATH, dpi=160, bbox_inches="tight")
    print(f"wrote {OUT_PATH.relative_to(ROOT)} rows={n}")
    print(f"min={t.min()} p25={t.quantile(0.25)} median={median} p75={t.quantile(0.75)} max={t.max()} mean={mean:.1f}")


if __name__ == "__main__":
    main()
