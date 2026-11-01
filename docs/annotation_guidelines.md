# Expert annotation guidelines (explanations and repairs)

A correct node name in an explanation does not show that the causal explanation is right. Each sampled output is therefore scored on separate criteria. Use `1` (yes), `0` (no) or `NA` (does not apply). Use the `notes` column for anything a reviewer should know.

Build the sheets with `python -m shgrag rubric-sheet` and score them with `python -m shgrag rubric-score <csv>`. If two people annotate copies of the same sheet, `python -m shgrag rubric-kappa a.csv b.csv` reports Cohen's κ per criterion.

## Which outputs are sampled

The sample deliberately contains failures, not only successes. For each LLM condition (`text`, `text_deps`, `graph`) it uses run 0:

| Stratum | What it is | How many |
|---|---|---|
| TP | conflict found | 2 per conflict type |
| FP / FP-hard | clean case flagged as a conflict (hard = near-miss clean case) | all |
| FN | conflict missed | all |
| TN-hard | near-miss clean case correctly judged clean | 3 |

Rows are shuffled, so the condition order is hidden. The condition is still visible in its column; cover that column if you want a blind review. The repair sheet has one row per repair case: the final structured edit of the `graph` condition, plus the automatic verifier verdict.

## Explanation criteria

| Criterion | Score 1 when … | Typical 0 |
|---|---|---|
| **E1 direction** | every causal link points the right way: A's action → changed state/variable → B. | "the camera turns off the plug"; reversed trigger and action |
| **E2 steps** | no intermediate step is missing or invented. Multi-hop chains (plug → router → camera) name every hop. | skips the router; invents a relay that is not in the home |
| **E3 timing** | the stated situation can really occur: the time windows overlap, the modes and thresholds are compatible, the triggers can co-occur. | claims a 07:30 and a 22:00 rule fire together; ignores a mutually exclusive condition |
| **E4 no assumption** | every fact the explanation relies on is in the home description (rules, devices, dependencies). | "the heater probably shares the circuit" when no such dependency exists |
| **E5 outcome** | the undesired outcome matches the ground truth (`gt_outcome`). For a "no conflict" answer: the reason given is the right one. | right rules, wrong hazard; "clean because different rooms" when they share a device |

For a **false positive**, E1–E4 still apply to the mechanism the model claims. E5 is normally 0. For a **false negative**, score E5 on the stated reason and mark the other criteria NA unless the text describes a mechanism.

## Repair criteria

| Criterion | Score 1 when … |
|---|---|
| **R1 applicable** | the repair can be written as a rule edit using devices and variables that exist in the home. Free-text repairs count only if they are concrete enough to implement. |
| **R2 resolves** | it removes the conflict in the stated situation (`gt_situation`). |
| **R3 preserves** | each involved rule still does what it is for outside that situation. Example: turning the energy-saving plug rule off entirely does **not** preserve it. |
| **R4 safe** | no safety function is disabled and no new hazard is introduced. Example: unlocking on any motion at night is not safe. |

For the structured repairs the automatic verifier already checks R1–R3 on a small simulation. The expert judges whether the simulation's notion of "purpose" is adequate. Note disagreements in `notes`.

## What the automatic proxy does and does not show

`explanation_proxy` in `results.md` only checks that all ground-truth key nodes are mentioned. It cannot detect wrong direction, missing hops, impossible timing or invented facts. It must not be reported as explanation correctness.
