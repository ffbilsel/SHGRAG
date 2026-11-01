"""Whole-home scan: find the conflicting rule sets without being told which rules to look at.

In the main experiment every case hands the reasoner a candidate rule set (a
pair or triple chosen by the annotator), and the task is to say whether that
set conflicts. Here the reasoner gets *all* rules of a home and must return
every conflicting rule set and its type. The ground truth is the complete
conflict list of the home: the conflict cases plus `home_conflicts`
(`Scenario.all_conflicts`).

Conditions mirror the main experiment and share one system prompt and one output
schema:
  text            all rules
  text_deps       all rules + every device, variable and dependency as flat text
  graph           retrieved subgraph for all rules (chains + touch points)
  graph_noaffects the same without AFFECTS edges
  symbolic        deterministic pairwise checker over all rule pairs
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import combinations
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from .llm import LLMClient
from .prompts import _fmt_rule, home_facts_text
from .reasoners import SymbolicReasoner, get_graph, get_retrieval
from .schema import Scenario

SCAN_CONDITIONS = ("text", "text_deps", "graph", "graph_noaffects", "symbolic")

SCAN_SYSTEM_PROMPT = """\
You are a safety analyst for smart-home automation. You are given all \
Trigger-Condition-Action automation rules of one home. Find every set of rules \
(usually two, at most three) that, when active together in this home, can lead \
to a conflict.

Conflict categories:
- logical: two rules issue incompatible actions on the same device state \
(e.g. lock vs. unlock, on vs. off) in situations where both can fire.
- semantic: an action of one rule changes an environmental or context variable \
(temperature, humidity, light level, motion, presence, ...) so that another rule \
fires unexpectedly or is prevented from firing.
- physical: an action affects another device through a physical dependency that \
is not stated in the rule itself (e.g. cutting power to a device that another \
rule relies on).

Rules that act on the same device at different, non-overlapping times or under \
mutually exclusive conditions are not a conflict. Designed control loops \
(a heater on below one threshold and off above a higher one, a stop rule that \
reacts to the effect of a start rule) are not conflicts either.

List each conflict once, with the smallest set of rule ids that produces it, \
its type, the situation in which it happens and the undesired outcome. If the \
home has no conflict, return an empty list.\
"""


class ScanConflict(BaseModel):
    rules: list[str] = Field(description="Ids of the rules that together produce the conflict (2-3)")
    conflict_type: Literal["logical", "semantic", "physical"]
    situation: str = Field(description="When the conflict happens (time, mode, sensor values)")
    undesired_outcome: str = Field(description="What goes wrong")
    explanation: str = Field(description="Short causal explanation (1-3 sentences)")


class ScanVerdict(BaseModel):
    conflicts: list[ScanConflict]


def _rules_text(scenario: Scenario) -> str:
    return "\n".join(_fmt_rule(r) for r in scenario.rules)


def scan_prompt(scenario: Scenario, condition: str) -> str:
    ids = [r.id for r in scenario.rules]
    tail = f"Find all conflicting rule sets among rules {', '.join(ids)}."
    if condition == "text":
        return f"Home: {scenario.name}\n\n# Automation rules\n{_rules_text(scenario)}\n\n{tail}"
    if condition == "text_deps":
        return f"Home: {scenario.name}\n\n# Automation rules\n{_rules_text(scenario)}\n\n{home_facts_text(scenario)}\n\n{tail}"
    if condition in ("graph", "graph_noaffects"):
        r = get_retrieval(scenario, ids, include_effects=condition == "graph")
        return (
            f"Home: {scenario.name}\n\n{r.text}\n\n"
            "The context above was retrieved from the home's knowledge graph. AFFECTS edges "
            "describe physical/causal effects that are not visible in the rule text; "
            "'reaches' lines show where a rule's action propagates.\n\n" + tail
        )
    raise ValueError(condition)


def symbolic_scan(scenario: Scenario) -> list[dict]:
    sym = SymbolicReasoner(True)
    g = get_graph(scenario, True)
    out = []
    for a, b in combinations([r.id for r in scenario.rules], 2):
        f = sym._pair(scenario, g, a, b) + sym._pair(scenario, g, b, a)
        if f:
            order = {"logical": 0, "physical": 1, "semantic": 2}
            f.sort(key=lambda x: order[x[0]])
            out.append(dict(rules=[a, b], conflict_type=f[0][0], situation="", undesired_outcome="", explanation=f[0][1]))
    return out


# --------------------------------------------------------------------------
# Matching and metrics
# --------------------------------------------------------------------------


def match(pred: list[frozenset], gold: list[frozenset]) -> list[tuple[int, int]]:
    """One-to-one matching of predicted to gold rule sets.

    Exact set equality first. Then containment for sets larger than a pair:
    a predicted pair inside a gold triple, or a predicted triple that contains
    a gold pair, still localises the conflict to the right rules."""
    pairs: list[tuple[int, int]] = []
    used_p: set[int] = set()
    used_g: set[int] = set()
    for i, p in enumerate(pred):
        for j, g in enumerate(gold):
            if j not in used_g and i not in used_p and p == g:
                pairs.append((i, j))
                used_p.add(i)
                used_g.add(j)
    for i, p in enumerate(pred):
        if i in used_p or len(p) < 2:
            continue
        for j, g in enumerate(gold):
            if j in used_g:
                continue
            if (len(g) > 2 and p < g) or (len(p) > 2 and g < p):
                pairs.append((i, j))
                used_p.add(i)
                used_g.add(j)
                break
    return pairs


def scan_gold(scenario: Scenario) -> list[tuple[frozenset[str], str]]:
    """Minimal conflicting rule sets: a gold set that contains another gold set
    (e.g. the triple s20_c5, whose hazard is already the pair s20_c2) is dropped,
    because the scan asks for the smallest set that produces each conflict."""
    allc = scenario.all_conflicts()
    return [(g, t) for g, t in allc if not any(h < g for h, _ in allc)]


def score_home(scenario: Scenario, conflicts: list[dict]) -> dict:
    gold = scan_gold(scenario)
    gold_sets = [g for g, _ in gold]
    pred_sets = [frozenset(c["rules"]) for c in conflicts]
    m = match(pred_sets, gold_sets)
    clean_cases = {frozenset(c.rules) for c in scenario.cases if c.label == "clean"}
    unmatched = [i for i in range(len(pred_sets)) if i not in {a for a, _ in m}]
    return dict(
        n_gold=len(gold),
        n_pred=len(pred_sets),
        tp=len(m),
        typed_tp=sum(conflicts[i]["conflict_type"] == gold[j][1] for i, j in m),
        per_type_gold={t: sum(tt == t for _, tt in gold) for t in ("logical", "semantic", "physical")},
        per_type_found={t: sum(gold[j][1] == t for _, j in m) for t in ("logical", "semantic", "physical")},
        missed=[sorted(gold_sets[j]) for j in range(len(gold)) if j not in {b for _, b in m}],
        false_positives=[sorted(pred_sets[i]) for i in unmatched],
        fp_on_labelled_clean=sum(pred_sets[i] in clean_cases for i in unmatched),
    )


def aggregate(scores: list[dict]) -> dict:
    tp = sum(s["tp"] for s in scores)
    n_pred = sum(s["n_pred"] for s in scores)
    n_gold = sum(s["n_gold"] for s in scores)
    p = tp / n_pred if n_pred else 0.0
    r = tp / n_gold if n_gold else 0.0
    out = dict(
        precision=p, recall=r, f1=2 * p * r / (p + r) if p + r else 0.0,
        typed_recall=sum(s["typed_tp"] for s in scores) / n_gold if n_gold else 0.0,
        n_pred=n_pred, n_gold=n_gold, tp=tp, fp=n_pred - tp,
        fp_on_labelled_clean=sum(s["fp_on_labelled_clean"] for s in scores),
    )
    for t in ("logical", "semantic", "physical"):
        g = sum(s["per_type_gold"][t] for s in scores)
        out[f"{t}_recall"] = sum(s["per_type_found"][t] for s in scores) / g if g else 0.0
    return out


def bootstrap_scan(rows: list[dict], cond: str, n_boot: int = 5000, seed: int = 0) -> dict:
    """Home-level CI of scan F1 / recall / precision (homes resampled, runs pooled)."""
    import random

    by_home: dict[str, list[dict]] = {}
    for r in rows:
        if r["condition"] == cond:
            by_home.setdefault(r["scenario_id"], []).append(r["score"])
    homes = sorted(by_home)
    rng = random.Random(seed)
    samp = {k: [] for k in ("precision", "recall", "f1")}
    for _ in range(n_boot):
        sc = [s for h in (rng.choice(homes) for _ in homes) for s in by_home[h]]
        a = aggregate(sc)
        for k in samp:
            samp[k].append(a[k])
    out = {}
    for k, v in samp.items():
        v.sort()
        out[k] = (v[int(0.025 * n_boot)], v[min(n_boot - 1, int(0.975 * n_boot))])
    return out


# --------------------------------------------------------------------------
# Runner
# --------------------------------------------------------------------------


def run_scan(scenarios: list[Scenario], conditions: list[str], runs: int, out_dir: Path, llm: LLMClient | None, workers: int = 6) -> list[dict]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    jobs = []
    for s in scenarios:
        for cond in conditions:
            for run in range(1 if cond == "symbolic" else runs):
                jobs.append((s, cond, run))

    def one(s: Scenario, cond: str, run: int) -> dict:
        if cond == "symbolic":
            conflicts, err, usage = symbolic_scan(s), None, {}
        else:
            res = llm.structured(scan_prompt(s, cond), run, SCAN_SYSTEM_PROMPT, ScanVerdict)
            conflicts = [c.model_dump() for c in res.verdict.conflicts] if res.verdict else []
            err = res.error
            usage = dict(input_tokens=res.input_tokens, output_tokens=res.output_tokens)
        return dict(scenario_id=s.id, split=s.split, condition=cond, run=run, n_rules=len(s.rules),
                    conflicts=conflicts, error=err, **usage)

    rows = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(one, *j): j for j in jobs}
        for i, f in enumerate(as_completed(futs), 1):
            rows.append(f.result())
            if i % 10 == 0 or i == len(jobs):
                print(f"  {i}/{len(jobs)} scans", flush=True)
    rows.sort(key=lambda r: (r["condition"], r["run"], r["scenario_id"]))
    with open(out_dir / "scan_predictions.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    write_scan_report(scenarios, rows, out_dir)
    return rows


def write_scan_report(scenarios: list[Scenario], rows: list[dict], out_dir: Path) -> dict:
    sc = {s.id: s for s in scenarios}
    for r in rows:
        r["score"] = score_home(sc[r["scenario_id"]], r["conflicts"])
    conds = [c for c in SCAN_CONDITIONS if any(r["condition"] == c for r in rows)]
    summary = {}
    lines = [
        "# Whole-home scan results",
        "",
        "Each reasoner sees all rules of a home and must list every conflicting rule set and its type. "
        "A prediction counts as correct when it names the same rule set as a ground-truth conflict "
        "(a pair inside a ground-truth triple also counts). Ground truth = conflict cases + `home_conflicts`. "
        "LLM runs are pooled; CIs resample homes.",
        "",
        f"Homes: {len(scenarios)} · ground-truth conflicts (minimal sets): {sum(len(scan_gold(s)) for s in scenarios)} · "
        f"rule pairs in these homes: {sum(len(s.rules) * (len(s.rules) - 1) // 2 for s in scenarios)}",
        "",
        "| Condition | Precision | Recall | F1 | Typed recall | Logical / semantic / physical recall | FP per home | FP on labelled clean pairs | API/format errors |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for c in conds:
        rr = [r for r in rows if r["condition"] == c]
        a = aggregate([r["score"] for r in rr])
        ci = bootstrap_scan(rows, c)
        a["ci"] = ci
        a["n_errors"] = sum(r["error"] is not None for r in rr)
        summary[c] = a
        lines.append(
            f"| {c} | {100*a['precision']:.1f} [{100*ci['precision'][0]:.0f}, {100*ci['precision'][1]:.0f}] | "
            f"{100*a['recall']:.1f} [{100*ci['recall'][0]:.0f}, {100*ci['recall'][1]:.0f}] | "
            f"{100*a['f1']:.1f} [{100*ci['f1'][0]:.0f}, {100*ci['f1'][1]:.0f}] | {100*a['typed_recall']:.1f} | "
            f"{100*a['logical_recall']:.0f} / {100*a['semantic_recall']:.0f} / {100*a['physical_recall']:.0f} | "
            f"{a['fp'] / len(rr):.2f} | {a['fp_on_labelled_clean']} | {a['n_errors']} |"
        )
    lines += ["", "## Misses and false positives per home (all runs)", ""]
    for c in conds:
        lines.append(f"### {c}")
        for s in scenarios:
            rr = [r for r in rows if r["condition"] == c and r["scenario_id"] == s.id]
            miss = sorted({"+".join(m) for r in rr for m in r["score"]["missed"]})
            fps = sorted({"+".join(m) for r in rr for m in r["score"]["false_positives"]})
            if miss or fps:
                lines.append(f"- {s.id}: missed {', '.join(miss) or '–'}; FP {', '.join(fps) or '–'}")
        lines.append("")
    (out_dir / "scan_results.md").write_text("\n".join(lines) + "\n")
    (out_dir / "scan_metrics.json").write_text(json.dumps(summary, indent=2))
    return summary


def unmatched_for_adjudication(scenarios: list[Scenario], rows: list[dict]) -> list[dict]:
    """Predicted rule sets that match no ground-truth conflict, pooled over all
    conditions and runs, for manual adjudication (pooling as in IR evaluation)."""
    sc = {s.id: s for s in scenarios}
    seen: dict[tuple, dict] = {}
    for r in rows:
        s = sc[r["scenario_id"]]
        gold = [g for g, _ in s.all_conflicts()]  # supersets count as matched here too
        for c in r["conflicts"]:
            p = frozenset(c["rules"])
            if match([p], gold):
                continue
            key = (s.id, tuple(sorted(p)))
            e = seen.setdefault(key, dict(scenario_id=s.id, rules=sorted(p), votes=0, conditions=set(), example=c))
            e["votes"] += 1
            e["conditions"].add(r["condition"])
    out = sorted(seen.values(), key=lambda e: (e["scenario_id"], e["rules"]))
    for e in out:
        e["conditions"] = sorted(e["conditions"])
        scen = sc[e["scenario_id"]]
        labelled = {frozenset(c.rules): c for c in scen.cases if c.label == "clean"}
        case = labelled.get(frozenset(e["rules"]))
        note = scen.home_clean_notes.get("+".join(e["rules"])) or (f"clean case {case.id}: {case.justification}" if case else None)
        e["already_reviewed_clean"] = note
    return out
