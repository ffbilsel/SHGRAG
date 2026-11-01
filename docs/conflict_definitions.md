# Conflict definitions and labelling guidelines

A **case** is a set of 2–3 rules from one home. Its label is `conflict` if the rules can produce an unsafe, contradictory or clearly unintended outcome when they are active together in that home. Otherwise the label is `clean`.

## Types

**Logical.** Two rules issue incompatible actions on the *same* device state, and there is a realistic situation in which both fire.
- Conflict: lock vs. unlock when smoke appears while switching to away mode (`s04_c1`).
- Clean: the same device at non-overlapping times (blinds open 07:30 / close 22:00, `s08_c2`). Also clean: opposite actions under mutually exclusive conditions or thresholds (heater on below 24 °C, off above 28 °C, `s06_c3`).

**Semantic.** An action of rule A changes an environmental or context variable, which makes rule B fire unexpectedly or keeps it from firing.
- Conflict: heater raises temperature → ventilation opens the window (`s02_c1`). Sprinkler wets the rain sensor → skylight closes (`s15_c2`).
- Clean: the effect is on a different room or variable (`s02_c2`). Also clean: a designed feedback loop, such as backup load heating the closet → cooling fan (`s16_c3`).

**Physical (dependency).** Rule A's action affects another device through a dependency that is not stated in the rule. Examples are power, network, water and wiring.
- Conflict: office plug off → router off → garden camera cannot upload (`s05_c1`, two hops).
- Clean: the plug that is switched off powers something unrelated (`s05_c3`, `s14_c3`).

When several types apply, the case is labelled with the most safety-relevant mechanism; `s20_c5` documents this.

## Fields

- `justification`: one or two sentences that a reviewer can check against the scenario.
- `situation` (required for conflicts): the concrete situation in which the conflict shows up, such as times, modes and sensor values. For a clean near-miss case it names what makes the case look like a conflict.
- `undesired_outcome` (required for conflicts): what goes wrong in that situation. A label is therefore more than a dependency path. It says *when* the path matters and *what* the harm is.
- `key_nodes`: the devices or variables that a correct explanation must mention. These drive the automatic grounding proxy, which is a weak signal only (see `annotation_guidelines.md`).
- `hard: true`: a clean case built to look like a conflict. Examples: opposite actions under non-overlapping thresholds, or a plug that powers something unrelated.

## Whole-home ground truth

The evaluation cases are chosen rule sets, usually pairs: the "candidate rule set" of the main experiment. The whole-home scan instead asks for every conflicting rule set in a home, so each home also lists:

- `home_conflicts`: conflicts that are not evaluation cases, with the same fields as a conflict case. Entries added after the pooled review of scan outputs carry `added_by: adjudication`, and the report gives scan scores before and after adjudication.
- `home_clean_notes`: rule pairs reviewed and judged clean, with the reason. Labelled clean cases count as reviewed automatically.

The scan's ground truth uses the minimal conflicting sets: a triple whose hazard is already one of its pairs is dropped.

## Provenance and splits

- `split: dev | test`: the 20 `dev` homes were used while building the prompts and the retriever. The 8 `test` homes (`data/test_scenarios/`) were written afterwards and frozen in `MANIFEST.json` (content hash + prompt fingerprint) before any LLM saw them.
- `family`: the scenario family. Dev and test families must not overlap, so small variants of one scenario never sit on both sides of the split. `python -m shgrag leakage` also reports content similarity.
- `source` on a rule: `original` (written by the author), or `adapted` with `platform`, `app`, `url`, a verbatim `excerpt` and the `adaptation` made. `python -m shgrag --data data/test_scenarios check-sources` fetches each URL and checks the excerpt; the last check is saved in `data/test_scenarios/sources_check.json`. Dev rules without a `source` are original.

## Expert check

The old 0/1 sheet (`annotations.csv`) is replaced by a criterion-level rubric: direction, intermediate steps, timing/condition consistency, unsupported assumptions and outcome for explanations; applicability, resolution, function preservation and safety for repairs. Its sample also contains false positives, false negatives and hard clean cases. See [`annotation_guidelines.md`](annotation_guidelines.md).
