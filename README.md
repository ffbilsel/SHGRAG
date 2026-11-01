# SHGRAG — Graph-Assisted Detection of Conflicting Smart-Home Automation Rules

This is a capstone research prototype (Boğaziçi University, CMPE 492). SHGRAG turns smart-home automation rules into a knowledge graph. For each candidate rule set it retrieves the relevant devices, states and causal/physical effects. It then asks an LLM (Claude) to detect, classify and explain conflicts and to suggest a repair. The same LLM without the graph (text-only) is the baseline.

**Research question:** does graph-grounded context improve conflict detection and explanation over an LLM-only baseline when both see the same automation rules?

## Conflict types

| Type | Meaning | Example in the benchmark |
|---|---|---|
| **logical** | Two rules issue incompatible actions on the same state | night mode locks the door, hallway motion unlocks it (`s01_c2`) |
| **semantic** | An action changes an environment/context variable that makes another rule fire (or not) | the robot vacuum triggers the motion sensor, which triggers "unlock on presence" (`s03_c1`) |
| **physical** | An action affects another device through a dependency that is not in the rule text | the energy-saving plug-off cuts power to the security camera (`s01_c1`) |

Full definitions and labelling guidelines: [`docs/conflict_definitions.md`](docs/conflict_definitions.md).

## Repository layout

```
data/scenarios/        dev split: 20 hand-curated homes (YAML): devices, env vars, effects, rules, cases, full conflict list
data/test_scenarios/   held-out split: 8 homes, rules adapted from SmartThings / Home Assistant examples with sources,
                       frozen in MANIFEST.json before any LLM run; sources_check.json = last source verification
data/repair/           repair benchmark: 15 conflict cases with hazard / intent simulation runs
shgrag/
  schema.py            typed scenario schema + referential-integrity validation
  loader.py            YAML loading (YAML 1.2 booleans: on/off stay strings)
  graph_builder.py     Scenario -> NetworkX MultiDiGraph (HAS_DEVICE, HAS_STATE, HAS_ENV, TRIGGERED_BY,
                       CONDITIONED_ON, TARGETS, AFFECTS)
  retriever.py         rule-set neighbourhood + multi-hop AFFECTS causal chains -> compact text context
  prompts.py           shared system prompt, output schema (Verdict), text-only and graph prompts
  llm.py               Claude client (structured output, disk cache, repeat-run sampling)
  reasoners.py         text / graph / graph_noaffects (LLM) and symbolic (deterministic) reasoners
  evaluation.py        P/R/F1/Acc, per-type recall/F1, FP/FN, stability, McNemar, explanation proxy
  experiment.py        experiment runner + report (results.md, metrics.json, plots, annotation sheet)
  scan.py              whole-home scan: find all conflicting rule sets of a home (no candidate set given)
  simulate.py          minute-step execution simulator of rules + effects (used to verify repairs)
  repair.py            repair-verify loop: structured edit -> approval -> apply to copy -> verify -> retry
  annotation.py        stratified expert rubric sheets, scoring, Cohen's kappa, optional LLM-judge pilot
  provenance.py        source checking of adapted rules, dev/test leakage report
  freeze.py            test-set manifest (content hash + prompt fingerprint)
  visualize.py         graph drawings and result plots
  cli.py               command line interface
app/streamlit_app.py   demo UI
tests/                 functional, direct-conflict, hidden-dependency, clean-case, ablation, pipeline tests
docs/                  graph schema, conflict definitions, report outline, task plan
figures/               sample home graphs and retrieved subgraphs
results/symbolic/      reference results of the deterministic checker (no LLM)
```

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[demo,dev]"
export ANTHROPIC_API_KEY=...            # needed only for the LLM conditions with --backend api
# or: no API key, run the LLM through the logged-in Claude Code CLI with --backend claude_code
```

## Usage

```bash
python -m shgrag validate                              # dataset statistics + graph totals
python -m shgrag retrieve s05_c1                       # graph context the LLM sees for a case
python -m shgrag retrieve s05_c1 --no-affects          # same, ablation graph
python -m shgrag graph s05_router_dependency --case s05_c1 --out figures/s05_c1.png

# smoke test (2 cases, 1 run) before the full experiment
python -m shgrag run --limit 2 --runs 1 --out results/smoke
python -m shgrag run --backend claude_code --limit 2 --runs 1 --out results/smoke   # same, without an API key

# main experiment: 75 cases x 3 runs x {text, graph, graph_noaffects} + symbolic
python -m shgrag run --runs 3 --out results/main
python -m shgrag report results/main                   # re-score from cached predictions


# information control: rules + every device/variable/dependency as flat text (no retrieval, no chains)
python -m shgrag run --backend claude_code --conditions text text_deps graph graph_noaffects symbolic --out results/main

# held-out test homes (frozen; check first)
python -m shgrag --data data/test_scenarios check-sources        # fetch every source URL, check the excerpt
python -m shgrag leakage                                         # dev/test family, name and similarity report
python -m shgrag --data data/test_scenarios run --backend claude_code --conditions text text_deps graph graph_noaffects symbolic --out results/test

# whole-home scan: all rules of a home, find every conflicting rule set + type
python -m shgrag scan --backend claude_code --out results/scan_dev
python -m shgrag scan-report results/scan_dev --adjudicate       # list unmatched predictions for pooled adjudication

# repair-verify loop (interactive approval; --yes approves automatically)
python -m shgrag repair --backend claude_code --runs 3 --yes --out results/repair

# expert rubric (direction, steps, timing, assumptions, outcome; repair applicability/function/safety)
python -m shgrag rubric-sheet results/main --out results/annotation/rubric_dev.csv --repairs results/repair
python -m shgrag rubric-score results/annotation/rubric_dev.csv
python -m shgrag rubric-kappa a.csv b.csv

streamlit run app/streamlit_app.py                     # demo
pytest                                                 # tests (no network)
```

## Experimental design

| Condition | Context given to the LLM |
|---|---|
| `text` (baseline A) | rule text + structured trigger/condition/action only |
| `text_deps` (information control) | `text` + every device, variable and dependency of the home as flat sentences (no retrieval, no chains, no graph notation) |
| `graph` (system B) | retrieved subgraph: rules, devices/states/rooms, AFFECTS edges and causal chains |
| `graph_noaffects` (ablation) | the same subgraph built **without** AFFECTS/dependency edges |
| `symbolic` (reference) | no LLM; a deterministic pairwise checker over the full graph |

- **Controlled settings.** All LLM conditions share the model (`claude-opus-5-5` by default), effort level, system prompt and output schema. Claude Opus 5.5 does not accept a `temperature` parameter, so the remaining sampling variation is measured with repeat runs instead. `--temperature` is passed through for models that accept it.
- **Repeatability.** Each run index is an independent, cached sample. The report gives mean ± std across runs, run-to-run agreement, and the cases whose verdict flips between runs.
- **Metrics:**
  - precision, recall, F1 and accuracy for conflict vs. clean;
  - recall and F1 per conflict type, both type-agnostic and type-aware;
  - FP and FN counts;
  - the ablation delta;
  - an exact McNemar test (text vs. graph, ablation vs. graph);
  - an automatic grounding proxy for explanations (do they mention the ground-truth key nodes?);
  - home-level cluster-bootstrap CIs and paired differences;
  - a criterion-level expert rubric (direction, steps, timing, assumptions, outcome; repair applicability, function, safety) on a sample that includes errors and hard clean cases.
- **Benchmark.** Dev split: 20 homes, 98 rules, 75 cases (15 logical, 14 semantic, 13 physical, 33 clean, of which 21 are hard near-misses). Held-out test split: 8 homes, 51 rules, 40 cases (5 / 4 / 5 / 26 clean, of which 15 are hard). 44 test rules are adapted from 24 public SmartThings and Home Assistant examples, each with a URL and a verbatim excerpt; `check-sources` verifies all 44. Every conflict label states its `situation` and `undesired_outcome`. Each home also lists its complete conflict set for the scan.
- **Candidate rule sets.** In the main experiment each case hands the reasoner the rule set to judge, usually a pair chosen by the annotator, so the task is pair classification. The whole-home scan removes this help.

### Reference result (symbolic checker, no LLM)

| | Precision | Recall | F1 | Logical / semantic / physical recall |
|---|---|---|---|---|
| full graph | 91.3 | 100 | 95.5 | 100 / 100 / 100 |
| without AFFECTS | 88.2 | 35.7 | 50.8 | 100 / 0 / 0 |

This sanity check shows that the semantic and physical conflicts in the benchmark can only be found through the causal/dependency edges. The checker's 4 false positives are intended feedback loops it cannot tell apart from conflicts: the sprinkler stopping when soil is wet, the backup heating a closet that is then cooled. 

### Main result (Claude Opus 5.5, effort medium, 3 runs per case)

Full tables: [`results/main/results.md`](results/main/results.md) (dev), [`results/test/results.md`](results/test/results.md) (held-out test), [`results/test_errata/results.md`](results/test_errata/results.md) (test with the two post-freeze label corrections). F1 intervals are home-level 95% cluster-bootstrap CIs: homes are resampled with all their cases and runs, so the runs of a case and the cases of a home are not treated as independent samples.

| Condition | Dev F1 [95% CI] (75 cases) | Dev L / S / P recall | Test F1 [95% CI] (40 cases, pre-registered) | Test F1 with errata |
|---|---|---|---|---|
| text | 85.8 [77.1, 92.4] | 100 / 78.6 / 64.1 | 82.7 [69.0, 96.3] | 90.2 |
| text_deps | 97.7 [93.8, 100] | 100 / 100 / 100 | 91.3 [84.0, 97.8] | 95.9 |
| graph | 98.1 [95.3, 100] | 100 / 100 / 100 | 91.3 [84.0, 97.8] | 95.9 |
| graph_noaffects | 84.3 [75.2, 91.4] | 100 / 73.8 / 46.2 | 90.3* | 97.0* |
| symbolic | 95.5 [90.9, 98.9] | 100 / 100 / 100 | 85.7 [75.0, 96.3] | 86.7 |

\* The test homes' device descriptions mention their dependencies, so the ablation is not informative on the test split.

- **API/format errors: 0** in every run (1500 detection calls). This means every call returned a valid structured answer. It does not mean every answer was right: misclassifications are the FP/FN columns of the results tables.
- **The gain comes from the dependency facts, not from the graph format.** `text_deps` (the same facts as flat sentences, no retrieval, no chains) matches `graph`: Δ F1 = +0.4 [−1.0, +2.5] on dev and 0.0 on test. The graph is useful as the structured store behind the text, the symbolic check, the simulator and the repair path check. It is not shown to be a better prompt format for homes of this size.
- **text → graph:** +12.2 F1 [+5.6, +20.8] on dev; +8.5 [+2.2, +16.1] on test with the pre-registered labels; +5.6 [−1.3, +12.6] on test with the errata.
- **Whole-home scan** (all rules of a home; find every conflicting rule set and its type; [`results/scan_dev`](results/scan_dev/scan_results.md), [`results/scan_test`](results/scan_test/scan_results.md)): after adjudication, F1 is 81.1 (text), 97.4 (text_deps), 97.8 (graph) and 90.0 (symbolic) on dev; 76.5, 92.7, 92.2 and 85.7 on test. Scores before adjudication are kept in `scan_results_before_adjudication.md`.
- **Repair–verify loop** (15 cases, 5 per type, 3 runs, ≤3 attempts; [`results/repair`](results/repair/repair_results.md)): 91% verified success for every condition (78–84% first try); the cited graph path is valid in 100% (graph) / 91% (text_deps) / 71% (text) of runs. All 45 degenerate edits in the negative controls are rejected. The two failing cases come from intent runs added after the rubric pilot: `s19` needs a higher crying threshold (found in 6/9 runs); `s15` cannot be repaired by a rule edit because the rain sensor cannot tell sprinkler water from rain.
- **Expert rubric:** sheets in `results/annotation/` (44 dev + 38 test explanation items, 15 repair items). Expert scores are still pending. `*_llmjudge_pilot.csv` holds a Claude Sonnet 5.5 pilot, which is not an expert result.
- Home names are neutral (e.g. "Two-bedroom flat"); `tests/test_loader.py` checks this. An earlier run used descriptive names such as "Home office - network dependency chain". Those names leaked the hidden dependency to the text baseline and inflated it to F1 92.7 with physical recall 92.3. The graph condition was unaffected (F1 98.1). That run is kept locally in `results/main_named_homes/`.

## Deliverables (proposal §9)

| # | Deliverable | Where |
|---|---|---|
| 1 | Source code | `shgrag/`, `app/` |
| 2 | Benchmark with ground truth | `data/scenarios/` |
| 3 | Graph schema and sample visualizations | `docs/graph_schema.md`, `figures/` |
| 4 | Result tables and plots | `python -m shgrag run` → `results/main/` |
| 5 | Short demo | `streamlit run app/streamlit_app.py` |
| 6 | Final report | outline in `docs/report_outline.md` |

Remaining work and the research roadmap (PhD extensions, related-work positioning) are in [`docs/TASK_PLAN.md`](docs/TASK_PLAN.md).
