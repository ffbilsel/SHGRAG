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
data/scenarios/        20 hand-curated homes (YAML): devices, env vars, effects, rules, ground-truth cases
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
export ANTHROPIC_API_KEY=...            # needed only for the LLM conditions
```

## Usage

```bash
python -m shgrag validate                              # dataset statistics + graph totals
python -m shgrag retrieve s05_c1                       # graph context the LLM sees for a case
python -m shgrag retrieve s05_c1 --no-affects          # same, ablation graph
python -m shgrag graph s05_router_dependency --case s05_c1 --out figures/s05_c1.png

# smoke test (2 cases, 1 run) before the full experiment
python -m shgrag run --limit 2 --runs 1 --out results/smoke

# main experiment: 75 cases x 3 runs x {text, graph, graph_noaffects} + symbolic
python -m shgrag run --runs 3 --out results/main
python -m shgrag report results/main                   # re-score from cached predictions

# expert check: fill explanation_supported / repair_safe (0/1) in results/main/annotations.csv
python -m shgrag score-annotations results/main/annotations.csv

streamlit run app/streamlit_app.py                     # demo
pytest                                                 # tests (no network)
```

## Experimental design

| Condition | Context given to the LLM |
|---|---|
| `text` (baseline A) | rule text + structured trigger/condition/action only |
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
  - the 0/1 expert sheet for explanation support and repair safety.
- **Benchmark.** 20 homes, 98 rules, 75 cases: 15 logical, 14 semantic, 13 physical and 33 clean. Clean cases are deliberately similar-looking to conflicts, e.g. a plug-off whose plug does *not* power the camera, or hysteresis thermostat pairs.

### Reference result (symbolic checker, no LLM)

| | Precision | Recall | F1 | Logical / semantic / physical recall |
|---|---|---|---|---|
| full graph | 91.3 | 100 | 95.5 | 100 / 100 / 100 |
| without AFFECTS | 88.2 | 35.7 | 50.8 | 100 / 0 / 0 |

This sanity check shows that the semantic and physical conflicts in the benchmark can only be found through the causal/dependency edges. The checker's 4 false positives are intended feedback loops it cannot tell apart from conflicts: the sprinkler stopping when soil is wet, the backup heating a closet that is then cooled. LLM results go in `results/main/` after running the experiment.

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
