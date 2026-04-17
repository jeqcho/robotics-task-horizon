"""Filter classifications to manual tasks and draw a seeded sample of 100.

Inputs:
    outputs/classifications.tsv
Outputs:
    outputs/manual_tasks.tsv          — all manual tasks
    outputs/manual_tasks_sample100.tsv — seeded sample of 100
"""

from __future__ import annotations

import csv
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLASSIFICATIONS = ROOT / "outputs" / "classifications.tsv"
MANUAL_ALL = ROOT / "outputs" / "manual_tasks.tsv"
MANUAL_SAMPLE = ROOT / "outputs" / "manual_tasks_sample100.tsv"
SEED = 42
SAMPLE_SIZE = 100


def main() -> None:
    with CLASSIFICATIONS.open(encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        rows = list(reader)

    fieldnames = reader.fieldnames
    manual = [r for r in rows if r["is_manual"].strip().lower() == "true"]
    print(f"total={len(rows)} manual={len(manual)} text_based={len(rows) - len(manual)}")

    manual.sort(key=lambda r: r["task_id"])

    with MANUAL_ALL.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(manual)
    print(f"wrote {MANUAL_ALL.relative_to(ROOT)} rows={len(manual)}")

    if len(manual) < SAMPLE_SIZE:
        raise SystemExit(f"need {SAMPLE_SIZE} manual tasks, only have {len(manual)}")

    rng = random.Random(SEED)
    sample = rng.sample(manual, SAMPLE_SIZE)
    sample.sort(key=lambda r: r["task_id"])

    with MANUAL_SAMPLE.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(sample)
    print(f"wrote {MANUAL_SAMPLE.relative_to(ROOT)} rows={SAMPLE_SIZE} seed={SEED}")


if __name__ == "__main__":
    main()
