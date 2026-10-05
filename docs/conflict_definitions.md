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
- `key_nodes`: the devices or variables that a correct explanation must mention. These drive the automatic grounding proxy.

## Expert check (0/1)

For each LLM output flagged as a conflict (`annotations.csv`):
- `explanation_supported = 1` if the explanation is consistent with the scenario facts and names the actual mechanism;
- `repair_safe = 1` if the suggested repair resolves the conflict without disabling a safety function or creating a new hazard.
