"""Draw N disjoint (distinct-seed) samples of K rated manual tasks below a human-time threshold.

Env vars (defaults in parens):
    SAMPLE_MAX_MIN   upper bound on human_time_minutes, exclusive (5)
    SAMPLE_SIZE      rows per sample (25)
    SAMPLE_SEEDS     comma-separated PRNG seeds (42,43,44,45,46)
    SAMPLE_INPUT     input TSV (outputs/manual_tasks_rated_sonnet_4_6.tsv)
    SAMPLE_OUT_DIR   directory for one TSV per seed (outputs/25sample_under_5min)

Each sample is drawn independently (with its own seed) from the same eligible pool;
samples may overlap — they are not a partition.
"""

from __future__ import annotations

import csv
import os
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

MAX_MIN = float(os.environ.get("SAMPLE_MAX_MIN", 5))
SIZE = int(os.environ.get("SAMPLE_SIZE", 25))
SEEDS = [int(s) for s in os.environ.get("SAMPLE_SEEDS", "42,43,44,45,46").split(",")]
INPUT = Path(os.environ.get("SAMPLE_INPUT", ROOT / "outputs" / "manual_tasks_rated_sonnet_4_6.tsv"))
OUT_DIR = Path(os.environ.get("SAMPLE_OUT_DIR", ROOT / "outputs" / "25sample_under_5min"))


def main() -> None:
    with INPUT.open(encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        rows = list(reader)
        fieldnames = reader.fieldnames

    max_tag = f"{MAX_MIN:g}"
    eligible = [r for r in rows if float(r["human_time_minutes"]) < MAX_MIN]
    print(f"total={len(rows)} eligible_under_{max_tag}min={len(eligible)}")

    if len(eligible) < SIZE:
        raise SystemExit(f"need {SIZE} eligible tasks, only {len(eligible)}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for seed in SEEDS:
        rng = random.Random(seed)
        sample = rng.sample(eligible, SIZE)
        sample.sort(key=lambda r: (float(r["human_time_minutes"]), r["task_id"]))
        path = OUT_DIR / f"seed{seed}.tsv"
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
            writer.writeheader()
            writer.writerows(sample)
        print(f"wrote {path.relative_to(ROOT)} rows={SIZE} seed={seed}")


if __name__ == "__main__":
    main()
