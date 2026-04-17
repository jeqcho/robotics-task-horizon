"""Seeded sample of rated manual tasks below a human-time threshold.

Env vars (defaults in parens):
    SAMPLE_MAX_MIN   upper bound on human_time_minutes, exclusive (5)
    SAMPLE_SIZE      number of rows (25)
    SAMPLE_SEED      PRNG seed (42)
    SAMPLE_INPUT     input TSV (outputs/manual_tasks_rated_sonnet_4_6.tsv)

Output: outputs/manual_tasks_sample{N}_under_{MAX}min.tsv
"""

from __future__ import annotations

import csv
import os
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

MAX_MIN = float(os.environ.get("SAMPLE_MAX_MIN", 5))
SIZE = int(os.environ.get("SAMPLE_SIZE", 25))
SEED = int(os.environ.get("SAMPLE_SEED", 42))
INPUT = Path(os.environ.get("SAMPLE_INPUT", ROOT / "outputs" / "manual_tasks_rated_sonnet_4_6.tsv"))

max_tag = f"{MAX_MIN:g}"
OUTPUT = ROOT / "outputs" / f"manual_tasks_sample{SIZE}_under_{max_tag}min.tsv"


def main() -> None:
    with INPUT.open(encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        rows = list(reader)
        fieldnames = reader.fieldnames

    eligible = [r for r in rows if float(r["human_time_minutes"]) < MAX_MIN]
    print(f"total={len(rows)} eligible_under_{max_tag}min={len(eligible)}")

    if len(eligible) < SIZE:
        raise SystemExit(f"need {SIZE} eligible tasks, only {len(eligible)}")

    rng = random.Random(SEED)
    sample = rng.sample(eligible, SIZE)
    sample.sort(key=lambda r: (float(r["human_time_minutes"]), r["task_id"]))

    with OUTPUT.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(sample)
    print(f"wrote {OUTPUT.relative_to(ROOT)} rows={SIZE} seed={SEED}")
    print()
    print(f"{'t(min)':>7} {'p(%)':>5}  task")
    for r in sample:
        t = float(r["human_time_minutes"])
        p = float(r["robot_success_prob"])
        print(f"  {t:>5.2f} {p:>5.0f}  {r['task'][:110]}")


if __name__ == "__main__":
    main()
