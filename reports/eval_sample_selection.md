# Picking a sample seed for robotics evals

**TL;DR — recommend `seed44`.** It has the widest difficulty spread (2–62%, std 15.4pp) of the five candidates, a reasonable category mix (6 distinct), and a clear list of tasks that should be dropped (≈4 of 25). The three other non-trivial options are seed46 (second-widest spread but heavier on security/service tasks), seed45 (safest but narrowest; only 4 categories), and seed43 (good range but contains a blocking task — assisting in live surgery).

## Selection criteria

A good eval sample at this size (n=25) needs to:

1. **Differentiate capability.** The robot-success-probability distribution should span a wide range so we can tell strong and weak robot stacks apart. Mean 9% and median 5% on the full 6,841-task corpus means most tasks are hard — we need the sample to *include* the middle-to-high range, not just cluster at floor.
2. **Cover manual-task modalities.** Manipulation dominates short tasks, but a sample that is 80% manipulation wastes bandwidth. We want inspection, food prep, assembly, locomotion, and at least one "hard" case (e.g. caregiving, heavy machinery).
3. **Be physically runnable.** Tasks must be concretely specifiable for a benchtop rig or staged environment. Tasks that require a live person, live animal, fire, security-sensitive content, or heavy field vehicles are non-starters for a lab eval.
4. **Be ethically runnable.** No tasks on real patients / mourners / law-enforcement subjects. No tasting food (robots have no taste sense).

## Per-seed scorecard

| Seed | n cats | Mean p | Median p | Min–Max p | Std p | Mean t | Problematic tasks (count) | Eval-ready tasks |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 42 | 7 | 16.3 | 12 | 2–35 | 9.7 | 2.5 min | 3 (CPR check, hydraulic tractor, carcass cuts) | 22 |
| 43 | 6 | 24.0 | 25 | 3–45 | 11.5 | 2.6 min | 2 (**pass surgical instruments**, verify patient ID) | 23 |
| **44** | **6** | **17.9** | **12** | **2–62** | **15.4** | **2.3 min** | **4 (taste food, dismount garbage truck, assist mourners, meat inspection)** | **21** |
| 45 | 4 | 19.2 | 18 | 4–35 | 9.9 | 2.7 min | 1 (ignite torches) | 24 |
| 46 | 6 | 23.6 | 20 | 6–55 | 11.3 | 2.5 min | 3 (security: baggage tampering, mail contraband; bath clients) | 22 |

Full per-task listings in `outputs/25sample_under_5min/seed{42..46}.tsv`.

## Why seed44 wins

**Difficulty spread is the biggest differentiator of an eval set**, and seed44 is the clear winner. It reaches the single highest-probability task in any sample (`Place products in equipment or on work surfaces ...`, p=62%) *and* still covers hard tasks (`Test cooked food by tasting and smelling`, p=2%; `Adjust apertures, shutter speeds, and camera focus`, p=4%). A 60-pp range is ~50% larger than seeds 42 and 45, which bottom out at 35%. With only 25 data points per eval run, a wider range gives more statistical leverage when comparing two robot stacks.

Seed44's category mix is acceptable: 13 manipulation + 5 inspection + 4 food prep + 1 caregiving + 1 vehicle + 1 locomotion. Seed45 is more concentrated (11 manipulation, 8 inspection) and only spans 4 categories.

Seed44's problem list is the longest (4 tasks), but three of those are easily identified and replaceable, and the fourth — "dismount garbage trucks" — is borderline (a humanoid could physically step off a stationary truck). If we need exactly 25 eval-ready tasks, the clean recovery is:

> Drop the 4 problematic tasks from seed44 and top up with the first 4 non-overlapping replacements from seed45. Seed45 has the safest residual pool and the lowest mean robot_prob, so the top-up biases us slightly toward harder tasks — the direction we want for capability headroom.

## Problematic tasks per seed (to drop or replace)

Flagged when the task requires (a) a live person in a vulnerable state, (b) security-sensitive handling, (c) a capability the robot physically cannot have (taste, smell), or (d) heavy field equipment a benchtop rig cannot simulate.

**seed42** — drop:
- `Check victims for signs of life, such as breathing and pulse.` *(live emergency patient)*
- `Control hydraulic tractors equipped with tree clamps and booms to lift, swing, and bunch sheared trees.` *(heavy field equipment)*
- `Tend assembly lines, performing a few of the many cuts needed to process a carcass.` *(slaughterhouse; BSL-2 sanitation)*

**seed43** — drop:
- `Pass instruments or supplies to surgeon during procedure.` *(live surgery — blocking)*
- `Verify the identity of patient or operative site.` *(live patient)*

**seed44** — drop:
- `Test cooked food by tasting and smelling it to ensure palatability and flavor conformity.` *(robots have no gustation/olfaction)*
- `Offer assistance to mourners as they enter or exit limousines.` *(live bereaved persons)*
- `Dismount garbage trucks to collect garbage and remount trucks to ride to the next collection point.` *(heavy vehicle, outdoor route)*
- `Inspect meat products for defects, bruises or blemishes and remove them along with any excess fat.` *(meat plant; sanitation)*

**seed45** — drop:
- `Ignite torches or start power supplies and strike arcs by touching electrodes to metals being welded.` *(open flame / arc welding; facility constraint, not blocking if we have a welding bay)*

**seed46** — drop:
- `Inspect checked baggage for signs of tampering.` *(security-sensitive; typically restricted to cleared personnel)*
- `Inspect mail for the presence of contraband.` *(same)*
- `Provide towels and sheets to clients in public baths, steam rooms, and restrooms.` *(unclothed members of the public)*

## Runner-up: seed45 if safety-first

If the eval setup cannot tolerate *any* problematic tasks and you want the absolute safest bench, **seed45** is the pick:
- Only 1 task flagged (`ignite torches`), and that one just needs a welding bay.
- Residual 24 tasks are almost all benign factory / warehouse inspection and manipulation.
- Cost: narrower difficulty spread (std 9.9 vs 15.4) → less discriminating between robot stacks.

## Concrete recommendation

1. **Use seed44 as the base sample.**
2. **Drop the 4 tasks listed above** to land at 21 eval-ready tasks.
3. **Top up to 25** by taking the first 4 non-overlapping, non-flagged tasks from seed45 (in task_id order to preserve reproducibility). This is deterministic and trivially scripted.
4. Commit the final curated list to `outputs/25sample_under_5min/eval_curated.tsv` with a note in its header comment about the drop-and-top-up provenance.

If later eval data suggests we're bumping into sample-size limits, expand to seeds 44+46 merged-and-deduped (≈48 unique tasks after dropping problematic ones in both).
