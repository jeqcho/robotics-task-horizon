# robotics-task-horizon

A seed dataset and methodology for measuring **current-robot success rates vs. human task duration** on manual O\*NET occupational tasks — a robotics-side companion to Mertens et al. (2026) *Crashing Waves vs. Rising Tides*, which studied the LLM side.

## Motivation

Mertens et al. (2026) asked: across text-based labor-market tasks, how does LLM success scale with the time a human would need? They screened O\*NET tasks with GPT-4 for ≥10% LLM time-savings potential and found an approximately "rising tide" (flat-slope) success–duration curve.

Their screen was a **usefulness** criterion on text-based tasks. This project asks a parallel question on a different axis: for O\*NET tasks whose primary execution is **physical / manual** (the domain robots, not LLMs, must tackle), how do frontier humanoid/mobile-manipulator robots perform vs. human task duration?

This is not the logical inverse of the reference paper — their filter is time-savings-based, ours is modality-based — but it uses the same O\*NET task universe and is designed to let a similar analysis be run on the robotics side.

## Data

Source: O\*NET Task Statements (`data/onet/Task Statements.txt`, 18,796 tasks across 923 SOC codes).

## Pipeline

1. **Classify** every O\*NET task as *manual* (physical execution required) vs. *text-based* (cognitive / verbal / written / planning / supervisory). Claude Haiku 4.5, 200-way async, tool-forced structured output, prompt-cached system prompt, resumable.
   - Script: `src/classify_manual.py`
   - Output: `outputs/classifications.tsv`

2. **Filter and sample.** Keep only `is_manual=True` rows → `outputs/manual_tasks.tsv`. Draw a seeded sample of 100 (`seed=42`) → `outputs/manual_tasks_sample100.tsv`.
   - Script: `src/filter_and_sample.py`

3. **Rate.** For each of the 100 sampled tasks, Claude Sonnet 4.6 assigns:
   - `task_category` — short label (manipulation, locomotion, vehicle operation, assembly, food prep, cleaning, caregiving, inspection, heavy machinery, …).
   - `human_time_minutes` — median time for a competent human to complete one instance, with rationale.
   - `robot_success_prob` (0–100) — probability a best-available 2026 general-purpose mobile manipulator / humanoid could complete one instance autonomously at acceptable quality, with rationale.
   - Script: `src/rate.py`
   - Output: `outputs/manual_tasks_sample100_rated.tsv`

## Reproduce

```bash
uv sync
uv run python src/classify_manual.py    # ~3–5 min, ~$5–8 Anthropic spend
uv run python src/filter_and_sample.py  # instant
uv run python src/rate.py               # ~1 min, <$1 Anthropic spend
```

Requires `ANTHROPIC_API_KEY` in `.env` (note: `python-dotenv` is called with `override=True` because shell env may hold a stale key).

## Methodology notes

**Definition of "manual"** (modality, not LLM time-savings):
> A task is **manual** iff its primary execution requires physical manipulation of tangible objects, operation of physical tools/machinery/vehicles, bodily movement, or on-site physical presence to interact with the physical world.

Supervisory, planning, and communicative tasks are classified as **text-based** even when they occur in traditionally "blue-collar" SOC families (e.g. "Supervise construction workers" → text-based; "Load cargo onto trucks" → manual). Full definition with edge cases in `src/classify_manual.py`.

**Definition of "current robot"** (for success-probability ratings):
> Best-available 2026 general-purpose mobile manipulator / humanoid — e.g. Figure 02, 1X Neo Gamma, Tesla Optimus Gen 3, Boston Dynamics Atlas (electric), Unitree H1/G1, Agility Digit, Apptronik Apollo — deployed commercially or in advanced pilots. **Excludes**: task-specific research demos, teleoperation, narrow industrial arms on fixed fixtures.

Capability anchors used to calibrate the rater are in `src/rate.py`.

**Sample seed**: `42` (Python `random.Random`).

**Models**:
- Classification: `claude-haiku-4-5`
- Rating: `claude-sonnet-4-6`

## Output schemas

`outputs/classifications.tsv`:
| column | type | description |
| --- | --- | --- |
| task_id | str | O\*NET Task ID |
| soc_code | str | O\*NET-SOC code |
| task | str | task statement |
| is_manual | bool | classification outcome |
| rationale | str | ≤25-word justification |

`outputs/manual_tasks.tsv`: same columns, filtered to `is_manual=true`.

`outputs/manual_tasks_sample100.tsv`: same columns, seeded sample of 100.

`outputs/manual_tasks_sample100_rated.tsv`:
| column | type | description |
| --- | --- | --- |
| task_id | str | |
| soc_code | str | |
| task | str | |
| task_category | str | |
| human_time_minutes | float | |
| human_time_rationale | str | |
| robot_success_prob | float | 0–100 |
| robot_success_rationale | str | |

## Relationship to the reference paper

| | Mertens et al. 2026 | This project |
| --- | --- | --- |
| Domain | LLM automation | Robot automation |
| Filter axis | Time-savings ≥10% (GPT-4 screen) | Modality = physical (Haiku 4.5 screen) |
| Rater | Human workers (40+ LLMs evaluated) | Claude Sonnet 4.6 (seed dataset; human eval is future work) |
| Task source | O\*NET | O\*NET |
| Outcome | Manager-acceptable completion | Autonomous completion at acceptable quality |

The two filters overlap but are not complementary: some text-based tasks have <10% LLM time savings; some manual tasks also have text components. This dataset targets the **physical** slice specifically.

## Reference

Mertens, M., Kuzee, A., Harris, B. S., Lyu, H., Li, W., Rosenfeld, J., Anto, M., Fleming, M., Thompson, N. (2026). *Crashing Waves vs. Rising Tides: Preliminary Findings on AI Automation from Thousands of Worker Evaluations of Labor Market Tasks.* arXiv:2604.01363. PDF in `reference/`.
