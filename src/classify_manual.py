"""Classify every O*NET task as manual (physical) vs text-based using Claude Haiku 4.5.

Input:  data/onet/Task Statements.txt (tab-separated)
Output: outputs/classifications.tsv (resumable — skips task IDs already present)
Log:    logs/classify_<timestamp>.log
"""

from __future__ import annotations

import asyncio
import csv
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
INPUT_PATH = ROOT / "data" / "onet" / "Task Statements.txt"
OUTPUT_PATH = ROOT / "outputs" / "classifications.tsv"
LOG_DIR = ROOT / "logs"

MODEL = "claude-haiku-4-5"
CONCURRENCY = 200
MAX_RETRIES = 5

SYSTEM_PROMPT = """You classify O*NET occupational tasks as MANUAL or TEXT-BASED.

DEFINITION — A task is MANUAL if its primary execution requires one or more of:
- Physical manipulation of tangible objects (lifting, carrying, assembling, cutting, cooking, cleaning, repairing).
- Operation of physical tools, machinery, or vehicles (driving, welding, operating a forklift, using a drill).
- Bodily movement or physical presence at a work site to interact with the physical world (patrolling, escorting, physically restraining, hands-on caregiving).
- Physical inspection that requires being there and touching/seeing objects (not a desk review of photos).

A task is TEXT-BASED (i.e. NOT MANUAL) if its primary execution is:
- Cognitive / analytical / planning / scheduling.
- Verbal or written communication (meetings, emails, reports, instruction, counseling, negotiating).
- Supervision or management without hands-on physical execution.
- Computer-based work (data entry, coding, design on a screen).
- Teaching or presenting (even if in person) when the work product is knowledge transfer, not physical action.

EDGE CASES:
- "Supervise construction workers" → TEXT-BASED (supervision is communication/planning).
- "Direct the loading of cargo" → TEXT-BASED (directing, not loading).
- "Load cargo onto trucks" → MANUAL.
- "Demonstrate equipment to students" → MANUAL (physical demo is the work).
- "Teach mathematics" → TEXT-BASED.
- "Inspect patient for injuries" (nurse) → MANUAL (physical exam).
- "Review medical records" → TEXT-BASED.
- "Drive a truck" → MANUAL.
- "Plan a delivery route" → TEXT-BASED.

Respond by calling the classify_task tool."""

CLASSIFY_TOOL = {
    "name": "classify_task",
    "description": "Classify an O*NET task as manual (physical) or text-based.",
    "input_schema": {
        "type": "object",
        "properties": {
            "is_manual": {
                "type": "boolean",
                "description": "True if the task's primary execution is physical/manual; False if text-based/cognitive/verbal.",
            },
            "rationale": {
                "type": "string",
                "description": "Brief justification, 25 words or fewer.",
            },
        },
        "required": ["is_manual", "rationale"],
    },
}


def setup_logging() -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = LOG_DIR / f"classify_{ts}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(log_path), logging.StreamHandler(sys.stderr)],
    )
    return log_path


def load_tasks() -> list[dict]:
    with INPUT_PATH.open(encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        return [
            {
                "soc_code": r["O*NET-SOC Code"],
                "task_id": r["Task ID"],
                "task": r["Task"],
            }
            for r in reader
        ]


def load_done_task_ids() -> set[str]:
    if not OUTPUT_PATH.exists():
        return set()
    done: set[str] = set()
    with OUTPUT_PATH.open(encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for r in reader:
            done.add(r["task_id"])
    return done


async def classify_one(
    client: AsyncAnthropic,
    semaphore: asyncio.Semaphore,
    task: dict,
) -> dict | None:
    async with semaphore:
        for attempt in range(MAX_RETRIES):
            try:
                resp = await client.messages.create(
                    model=MODEL,
                    max_tokens=256,
                    system=[
                        {
                            "type": "text",
                            "text": SYSTEM_PROMPT,
                            "cache_control": {"type": "ephemeral"},
                        }
                    ],
                    tools=[CLASSIFY_TOOL],
                    tool_choice={"type": "tool", "name": "classify_task"},
                    messages=[{"role": "user", "content": task["task"]}],
                )
                for block in resp.content:
                    if block.type == "tool_use" and block.name == "classify_task":
                        return {
                            "task_id": task["task_id"],
                            "soc_code": task["soc_code"],
                            "task": task["task"],
                            "is_manual": bool(block.input["is_manual"]),
                            "rationale": str(block.input["rationale"]).replace("\t", " ").replace("\n", " "),
                        }
                logging.warning("task_id=%s no tool_use in response", task["task_id"])
                return None
            except (RateLimitError, APIStatusError) as e:
                status = getattr(e, "status_code", None)
                if status in (429, 529, 500, 502, 503, 504) and attempt < MAX_RETRIES - 1:
                    backoff = 2**attempt
                    logging.warning(
                        "task_id=%s retry %d after %ds (status=%s)",
                        task["task_id"],
                        attempt + 1,
                        backoff,
                        status,
                    )
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

    all_tasks = load_tasks()
    done = load_done_task_ids()
    pending = [t for t in all_tasks if t["task_id"] not in done]
    logging.info("total=%d done=%d pending=%d", len(all_tasks), len(done), len(pending))

    if not pending:
        logging.info("nothing to do")
        return

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    new_file = not OUTPUT_PATH.exists()
    out = OUTPUT_PATH.open("a", encoding="utf-8", newline="")
    writer = csv.DictWriter(
        out,
        delimiter="\t",
        fieldnames=["task_id", "soc_code", "task", "is_manual", "rationale"],
        quoting=csv.QUOTE_MINIMAL,
    )
    if new_file:
        writer.writeheader()
        out.flush()

    client = AsyncAnthropic()
    semaphore = asyncio.Semaphore(CONCURRENCY)

    start = time.time()
    ok = 0
    fail = 0
    write_lock = asyncio.Lock()

    async def worker(task: dict) -> None:
        nonlocal ok, fail
        result = await classify_one(client, semaphore, task)
        if result is None:
            fail += 1
            return
        async with write_lock:
            writer.writerow(result)
            out.flush()
        ok += 1

    coros = [worker(t) for t in pending]
    await tqdm.gather(*coros, desc="classify", unit="task")

    out.close()
    elapsed = time.time() - start
    logging.info(
        "done ok=%d fail=%d elapsed=%.1fs rate=%.1f/s",
        ok,
        fail,
        elapsed,
        ok / elapsed if elapsed > 0 else 0,
    )


if __name__ == "__main__":
    asyncio.run(main())
