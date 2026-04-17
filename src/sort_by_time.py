"""Sort the rated tasks by human time and emit a compact view.

Input:  outputs/manual_tasks_rated_sonnet_4_6.tsv
Output: outputs/manual_tasks_rated_by_time.tsv
"""

from __future__ import annotations

import csv
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INPUT_PATH = Path(
    os.environ.get("SORT_INPUT", ROOT / "outputs" / "manual_tasks_rated_sonnet_4_6.tsv")
)
OUTPUT_PATH = ROOT / "outputs" / "manual_tasks_rated_by_time.tsv"


def main() -> None:
    with INPUT_PATH.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))

    rows.sort(key=lambda r: (float(r["human_time_minutes"]), -float(r["robot_success_prob"])))
    fieldnames = list(rows[0].keys())

    with OUTPUT_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {OUTPUT_PATH.relative_to(ROOT)} rows={len(rows)}")


if __name__ == "__main__":
    main()
