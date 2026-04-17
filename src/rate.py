"""Rate each of the 100 sampled manual tasks on human time and robot success probability.

Input:  outputs/manual_tasks_sample100.tsv
Output: outputs/manual_tasks_sample100_rated.tsv
Log:    logs/rate_<timestamp>.log

Model: claude-sonnet-4-6 with tool-forced structured output.
"""

from __future__ import annotations

import asyncio
import csv
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from anthropic import AsyncAnthropic, APIStatusError, RateLimitError
from dotenv import load_dotenv
from tqdm.asyncio import tqdm

ROOT = Path(__file__).resolve().parent.parent
INPUT_PATH = Path(os.environ.get("RATE_INPUT", ROOT / "outputs" / "manual_tasks_sample100.tsv"))
LOG_DIR = ROOT / "logs"

MODEL = os.environ.get("RATE_MODEL", "claude-sonnet-4-6")
_tag = MODEL.replace("claude-", "").replace("-", "_")
_stem = INPUT_PATH.stem
OUTPUT_PATH = Path(os.environ.get("RATE_OUTPUT", ROOT / "outputs" / f"{_stem}_rated_{_tag}.tsv"))
CONCURRENCY = 200
MAX_RETRIES = 5

SYSTEM_PROMPT = """You rate O*NET manual/physical tasks on two axes:

(1) HUMAN COMPLETION TIME — median time for a competent human worker to complete ONE instance of this task, in minutes. Think about what a single "instance" means (e.g. "clean a room" = one room; "drive passengers" = one trip of typical length). For recurring/ongoing tasks, estimate the unit that a manager would measure.

(2) CURRENT ROBOT SUCCESS PROBABILITY — probability (0–100) that a best-available 2026 general-purpose mobile manipulator / humanoid robot could complete ONE instance of this task successfully, autonomously, without teleoperation or human intervention, at a quality that a reasonable human supervisor would accept.

"CURRENT ROBOT" means the frontier as of April 2026, e.g. Figure 02, 1X Neo Gamma, Tesla Optimus Gen 3, Boston Dynamics Atlas (electric), Unitree H1/G1, Agility Digit, Apptronik Apollo — deployed commercially or in advanced pilots. Exclude: task-specific research demos, teleoperation, narrow industrial arms bolted to a fixture. Include: dexterity, locomotion, perception, generalization, safety limits.

Capability anchors (April 2026):
- Pick-and-place of common objects in a tidy bin: ~70–90%.
- Folding laundry, unloading a dishwasher: ~30–60% (improving fast).
- Walking over flat indoor terrain: ~85%; rough/outdoor terrain: ~30–60%.
- Opening arbitrary doors, using handles: ~40–70%.
- Fine dexterous work (surgery, jewelry, hand-sewing): <5%.
- Driving passenger vehicles on public roads: <5% (humanoids cannot drive; L4 AVs are different systems and only on mapped routes).
- Operating heavy construction/farm machinery: <5%.
- Unstructured caregiving (bathing, feeding elderly): ~5–15%.
- Cooking from a recipe in a typical kitchen: ~5–20%.
- Cleaning (sweeping, mopping, wiping surfaces): ~40–70%.
- Assembly of standardized parts on a jig: ~40–80%.
- Loading/unloading trucks with varied items: ~20–50%.

Tasks that require vehicles, heavy equipment, or highly specialized tools that a humanoid cannot operate should score low (<15%) unless the task can be redefined as "physically present but operating through built-in controls" — but be strict: a humanoid cannot actually drive a truck in traffic.

Use the rate_task tool. Be consistent. Calibrate across tasks."""

RATE_TOOL = {
    "name": "rate_task",
    "description": "Rate a manual O*NET task on human time and current-robot success probability.",
    "input_schema": {
        "type": "object",
        "properties": {
            "task_category": {
                "type": "string",
                "description": "Short category label (e.g. 'manipulation', 'locomotion', 'vehicle operation', 'assembly', 'food prep', 'cleaning', 'caregiving', 'inspection', 'heavy machinery').",
            },
            "human_time_minutes": {
                "type": "number",
                "description": "Estimated median time in minutes for a competent human to complete one instance.",
            },
            "human_time_rationale": {
                "type": "string",
                "description": "Brief justification, 30 words or fewer. Define what 'one instance' means.",
            },
            "robot_success_prob": {
                "type": "number",
                "description": "Probability 0-100 that a current (2026) frontier general-purpose robot could complete one instance autonomously.",
            },
            "robot_success_rationale": {
                "type": "string",
                "description": "Brief justification citing capability/limitation drivers (dexterity, perception, mobility, tool-use, generalization), 40 words or fewer.",
            },
        },
        "required": [
            "task_category",
            "human_time_minutes",
            "human_time_rationale",
            "robot_success_prob",
            "robot_success_rationale",
        ],
    },
}


def setup_logging() -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = LOG_DIR / f"rate_{ts}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(log_path), logging.StreamHandler(sys.stderr)],
        force=True,
    )
    return log_path


async def rate_one(
    client: AsyncAnthropic,
    semaphore: asyncio.Semaphore,
    task: dict,
) -> dict | None:
    async with semaphore:
        for attempt in range(MAX_RETRIES):
            try:
                resp = await client.messages.create(
                    model=MODEL,
                    max_tokens=1024,
                    system=[
                        {
                            "type": "text",
                            "text": SYSTEM_PROMPT,
                            "cache_control": {"type": "ephemeral"},
                        }
                    ],
                    tools=[RATE_TOOL],
                    tool_choice={"type": "tool", "name": "rate_task"},
                    messages=[{"role": "user", "content": task["task"]}],
                )
                required = ("task_category", "human_time_minutes", "human_time_rationale",
                            "robot_success_prob", "robot_success_rationale")
                for block in resp.content:
                    if block.type == "tool_use" and block.name == "rate_task":
                        r = block.input
                        if not all(k in r for k in required):
                            logging.warning("task_id=%s incomplete tool input attempt=%d raw=%s",
                                            task["task_id"], attempt + 1, json.dumps(r))
                            if attempt < MAX_RETRIES - 1:
                                await asyncio.sleep(1 + attempt)
                                break  # retry outer loop
                            return None
                        logging.info("task_id=%s raw=%s", task["task_id"], json.dumps(r))
                        return {
                            "task_id": task["task_id"],
                            "soc_code": task["soc_code"],
                            "task": task["task"],
                            "task_category": str(r["task_category"]).replace("\t", " "),
                            "human_time_minutes": float(r["human_time_minutes"]),
                            "human_time_rationale": str(r["human_time_rationale"]).replace("\t", " ").replace("\n", " "),
                            "robot_success_prob": float(r["robot_success_prob"]),
                            "robot_success_rationale": str(r["robot_success_rationale"]).replace("\t", " ").replace("\n", " "),
                        }
                else:
                    logging.warning("task_id=%s no tool_use in response", task["task_id"])
                    return None
                continue  # retry after incomplete input
            except (RateLimitError, APIStatusError) as e:
                status = getattr(e, "status_code", None)
                if status in (429, 529, 500, 502, 503, 504) and attempt < MAX_RETRIES - 1:
                    backoff = min(2**attempt * 4, 60)  # 4,8,16,32,60s
                    logging.warning("task_id=%s retry %d sleep=%ds (status=%s)",
                                    task["task_id"], attempt + 1, backoff, status)
                    await asyncio.sleep(backoff)
                    continue
                logging.error("task_id=%s permanent error: %s", task["task_id"], e)
                return None
            except Exception as e:
                logging.error("task_id=%s unexpected error: %s", task["task_id"], e)
                return None
        return None


async def main() -> None:
    log_path = setup_logging()
    logging.info("log=%s model=%s concurrency=%d", log_path, MODEL, CONCURRENCY)

    load_dotenv(ROOT / ".env", override=True)
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY not set")

    with INPUT_PATH.open(encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        all_tasks = list(reader)

    done: set[str] = set()
    if OUTPUT_PATH.exists():
        with OUTPUT_PATH.open(encoding="utf-8") as f:
            for r in csv.DictReader(f, delimiter="\t"):
                done.add(r["task_id"])
    pending = [t for t in all_tasks if t["task_id"] not in done]
    logging.info("input=%s total=%d done=%d pending=%d", INPUT_PATH, len(all_tasks), len(done), len(pending))

    if not pending:
        print(f"nothing to do; {OUTPUT_PATH.relative_to(ROOT)} already has all {len(done)} rows")
        return

    fieldnames = [
        "task_id",
        "soc_code",
        "task",
        "task_category",
        "human_time_minutes",
        "human_time_rationale",
        "robot_success_prob",
        "robot_success_rationale",
    ]
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    new_file = not OUTPUT_PATH.exists()
    out = OUTPUT_PATH.open("a", encoding="utf-8", newline="")
    writer = csv.DictWriter(out, fieldnames=fieldnames, delimiter="\t")
    if new_file:
        writer.writeheader()
        out.flush()

    client = AsyncAnthropic()
    semaphore = asyncio.Semaphore(CONCURRENCY)
    write_lock = asyncio.Lock()
    ok = 0
    fail = 0

    async def worker(task: dict) -> None:
        nonlocal ok, fail
        result = await rate_one(client, semaphore, task)
        if result is None:
            fail += 1
            return
        async with write_lock:
            writer.writerow(result)
            out.flush()
        ok += 1

    start = time.time()
    coros = [worker(t) for t in pending]
    await tqdm.gather(*coros, desc="rate", unit="task")
    elapsed = time.time() - start

    out.close()
    logging.info("done ok=%d fail=%d elapsed=%.1fs", ok, fail, elapsed)
    print(f"wrote {OUTPUT_PATH.relative_to(ROOT)} new_rows={ok} fail={fail}")


if __name__ == "__main__":
    asyncio.run(main())
