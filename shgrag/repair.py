"""Repair–verify loop.

  1. propose  the LLM returns one structured edit (RepairProposal): target rule,
              operation, new condition / trigger / action, and the graph path
              that justifies it;
  2. approve  the edit and the resulting rule diff are shown to the user, who
              approves it (`--yes` approves automatically, for experiments);
  3. apply    the edit is applied to a *copy* of the scenario (the YAML on disk
              is never touched) and the copy is re-validated;
  4. verify   deterministic checks on the copy:
                a. applicable  - the edit is well formed and the home still validates
                b. resolved    - every hazard simulation of the case is now false
                c. intent      - every intent simulation of the case still passes
                d. no_new      - a whole-home symbolic re-check flags no rule pair
                                 that was not flagged before
                e. path_valid  - the cited graph path exists in the home graph
  5. retry    if a check fails, the verifier's messages are sent back and the
              LLM proposes again (up to `max_attempts`).

Success = a + b + c + d. The path check is reported separately: it measures the
grounding of the justification, not whether the repair works.
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import combinations
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, ValidationError

from .graph_builder import build_graph
from .llm import LLMClient
from .prompts import _fmt_rule, home_facts_text
from .reasoners import SymbolicReasoner, get_retrieval
from .schema import Scenario
from .simulate import check, summarize_trace

REPAIR_CONDITIONS = ("text", "text_deps", "graph")
DEFAULT_SPEC = Path(__file__).resolve().parent.parent / "data" / "repair" / "repair_cases.yaml"

REPAIR_SYSTEM_PROMPT = """\
You repair conflicts between smart-home Trigger-Condition-Action rules. You are \
given the rules of a home, context about its devices and dependencies, and a \
conflict that the home owner has confirmed. Propose exactly one edit to one \
rule that removes the conflict.

Allowed operations:
- add_condition: add a condition (time_range, or a state/env comparison) to the rule
- replace_condition: replace the rule's condition on `old_ref` ("time" for a time range)
- remove_condition: remove the rule's condition on `old_ref`
- change_trigger: replace the rule's trigger
- add_action: add an action to the rule
- change_action: change the value written by the rule's action on `action.ref`
- remove_action: remove the rule's action on `action.ref` (the rule must keep at least one action)

Requirements: the conflict must no longer occur; every rule must keep doing \
what it is for outside the conflict situation; do not create a new conflict \
with other rules of the home; never disable a safety function; do not delete \
rules. Use only device states and variables that exist in the home. \
`graph_path` lists the chain of nodes that justifies the edit, from the \
rule you edit through devices/states/variables to the other rule, using ids \
such as R1, plug_hall.power, camera_hall, home_mode.\
"""


class CondSpec(BaseModel):
    type: Literal["time_range", "state", "env"]
    ref: str | None = None
    op: Literal["==", "!=", ">", "<", ">=", "<="] | None = None
    value: str | None = Field(default=None, description="value as text, e.g. off, away, true, 24")
    start: str | None = Field(default=None, description="HH:MM for time_range")
    end: str | None = None


class TrigSpec(BaseModel):
    type: Literal["time", "state", "env"]
    at: str | None = None
    ref: str | None = None
    op: Literal["==", "!=", ">", "<", ">=", "<="] | None = None
    value: str | None = None


class ActSpec(BaseModel):
    ref: str
    value: str


class RepairProposal(BaseModel):
    target_rule: str = Field(description="Id of the rule to edit")
    operation: Literal["add_condition", "replace_condition", "remove_condition", "change_trigger", "add_action", "change_action", "remove_action"]
    condition: CondSpec | None = Field(default=None, description="New condition (add_condition / replace_condition)")
    old_ref: str | None = Field(default=None, description="Ref of the condition to replace/remove, or 'time'")
    trigger: TrigSpec | None = Field(default=None, description="New trigger (change_trigger)")
    action: ActSpec | None = Field(default=None, description="Action to add / change / remove")
    graph_path: list[str] = Field(description="Node ids from the edited rule to the other rule that justify the edit")
    rationale: str = Field(description="1-3 sentences: why this removes the conflict and keeps both rules' purposes")


# --------------------------------------------------------------------------
# Applying an edit
# --------------------------------------------------------------------------


def _val(v: str | None):
    if v is None:
        return None
    s = str(v).strip()
    if s.lower() in ("true", "false"):
        return s.lower() == "true"
    try:
        f = float(s)
        return int(f) if f.is_integer() and "." not in s else f
    except ValueError:
        return s


def _cond_dict(c: CondSpec) -> dict:
    if c.type == "time_range":
        return {"type": "time_range", "start": c.start, "end": c.end}
    return {"type": c.type, "ref": c.ref, "op": c.op or "==", "value": _val(c.value)}


def apply_edit(scenario: Scenario, p: RepairProposal) -> Scenario:
    """Return a validated copy of the scenario with the edit applied. Raises ValueError if not applicable."""
    raw = scenario.model_dump(mode="python", exclude_none=True)
    rules = {r["id"]: r for r in raw["rules"]}
    if p.target_rule not in rules:
        raise ValueError(f"unknown rule {p.target_rule}")
    r = rules[p.target_rule]
    r.setdefault("conditions", [])
    op = p.operation

    def cond_matches(c: dict, ref: str | None) -> bool:
        return (ref == "time" and c["type"] == "time_range") or c.get("ref") == ref

    if op == "add_condition":
        if p.condition is None:
            raise ValueError("add_condition needs `condition`")
        r["conditions"].append(_cond_dict(p.condition))
    elif op in ("replace_condition", "remove_condition"):
        idx = [i for i, c in enumerate(r["conditions"]) if cond_matches(c, p.old_ref)]
        if not idx:
            raise ValueError(f"{p.target_rule} has no condition on {p.old_ref}")
        if op == "remove_condition":
            del r["conditions"][idx[0]]
        else:
            if p.condition is None:
                raise ValueError("replace_condition needs `condition`")
            r["conditions"][idx[0]] = _cond_dict(p.condition)
    elif op == "change_trigger":
        t = p.trigger
        if t is None:
            raise ValueError("change_trigger needs `trigger`")
        r["trigger"] = {"type": "time", "at": t.at} if t.type == "time" else {"type": t.type, "ref": t.ref, "op": t.op or "==", "value": _val(t.value)}
    elif op in ("add_action", "change_action", "remove_action"):
        a = p.action
        if a is None:
            raise ValueError(f"{op} needs `action`")
        idx = [i for i, x in enumerate(r["actions"]) if x["ref"] == a.ref]
        if op == "add_action":
            r["actions"].append({"ref": a.ref, "value": _val(a.value)})
        elif not idx:
            raise ValueError(f"{p.target_rule} has no action on {a.ref}")
        elif op == "change_action":
            r["actions"][idx[0]]["value"] = _val(a.value)
        else:
            del r["actions"][idx[0]]
            if not r["actions"]:
                raise ValueError("remove_action would leave the rule without actions (rule deletion is not allowed)")
    try:
        return Scenario.model_validate(raw)
    except ValidationError as e:
        raise ValueError(f"edited home does not validate: {e.errors()[0]['msg']}") from None


def rule_diff(before: Scenario, after: Scenario, rule_id: str) -> str:
    return f"- {_fmt_rule(before.rule(rule_id))}\n+ {_fmt_rule(after.rule(rule_id))}"


# --------------------------------------------------------------------------
# Verification
# --------------------------------------------------------------------------


def _scoped(scenario: Scenario, rule_ids: list[str]) -> Scenario:
    return scenario.model_copy(update={"rules": [r for r in scenario.rules if r.id in rule_ids]})


def symbolic_pairs(scenario: Scenario, include_condition_links: bool = False) -> set[frozenset]:
    """Rule pairs the symbolic checker flags in the whole home.

    By default a pair flagged *only* because one rule's effect changes a
    variable in the other rule's conditions is left out: adding a guard
    condition (the most common repair) always creates such a link, and a
    condition alone cannot make a rule fire. These links are reported
    separately as warnings."""
    sym = SymbolicReasoner(True)
    g = build_graph(scenario)
    out = set()
    for a, b in combinations([r.id for r in scenario.rules], 2):
        f = sym._pair(scenario, g, a, b) + sym._pair(scenario, g, b, a)
        if not include_condition_links:
            f = [x for x in f if ", a condition of " not in x[1]]
        if f:
            out.add(frozenset((a, b)))
    return out


def _resolve(scenario: Scenario, item: str) -> str | None:
    x = item.strip()
    if ":" in x and x.split(":", 1)[0] in ("rule", "state", "env", "device", "room"):
        return x
    if any(r.id == x for r in scenario.rules):
        return f"rule:{x}"
    if x in scenario.state_refs():
        return f"state:{x}"
    if x in scenario.env_refs():
        return f"env:{x}"
    if any(d.id == x for d in scenario.devices):
        return f"device:{x}"
    if x in scenario.rooms:
        return f"room:{x}"
    return None


def check_path(scenario: Scenario, path: list[str]) -> tuple[bool, str]:
    """Every element must be a node of the home graph and consecutive elements
    must be joined by an edge (either direction)."""
    g = build_graph(scenario)
    nodes = [_resolve(scenario, p) for p in path]
    if len(nodes) < 2:
        return False, "path has fewer than two nodes"
    for raw, n in zip(path, nodes):
        if n is None or n not in g:
            return False, f"unknown node {raw}"
    for a, b in zip(nodes, nodes[1:]):
        if not (g.has_edge(a, b) or g.has_edge(b, a)):
            return False, f"no edge between {a} and {b}"
    return True, "ok"


def _runs(spec: dict, kind: str) -> list[dict]:
    """Hazard or intent runs with the case's `base_init` merged into each run's init."""
    base = spec.get("base_init") or {}
    return [{**r, "init": {**base, **(r.get("init") or {})}} for r in spec[kind]]


def verify(original: Scenario, repaired: Scenario, spec: dict, case_rules: list[str]) -> dict:
    dyn = spec.get("dynamics") or {}
    out = dict(resolved=True, intent=True, no_new=True, messages=[])
    scoped = _scoped(repaired, case_rules)
    for h in _runs(spec, "hazard"):
        holds, what, tr = check(scoped, h, dyn)
        if holds:
            out["resolved"] = False
            out["messages"].append(f"Conflict still occurs in situation '{h['name']}' ({what}). Trace:\n{summarize_trace(tr)}")
    for it in _runs(spec, "intent"):
        holds, what, tr = check(scoped, it, dyn)
        if not holds:
            out["intent"] = False
            out["messages"].append(f"Intended behaviour lost: '{it['name']}' expected {what}. Trace:\n{summarize_trace(tr)}")
    before, after = symbolic_pairs(original), symbolic_pairs(repaired)
    new = sorted(sorted(p) for p in after - before)
    out["new_pairs"] = new
    out["new_condition_links"] = sorted(
        sorted(p) for p in (symbolic_pairs(repaired, True) - symbolic_pairs(original, True)) if sorted(p) not in new
    )
    if new:
        out["no_new"] = False
        out["messages"].append("The edit creates new potential conflicts between rule pairs: " + ", ".join("+".join(p) for p in new))
    return out


def sanity_check(scenario: Scenario, spec: dict, case_rules: list[str]) -> list[str]:
    """On the original rules every hazard must hold and every intent must pass."""
    problems = []
    dyn = spec.get("dynamics") or {}
    scoped = _scoped(scenario, case_rules)
    # default initial values (first listed value) silently start effects, so
    # every effect source must be given explicitly in each run's init
    sources = {ef.source for ef in scenario.effects}
    for run in _runs(spec, "hazard") + _runs(spec, "intent"):
        missing = sorted(sources - set(run.get("init") or {}))
        if missing:
            problems.append(f"{spec['case']}: run '{run['name']}' does not set effect sources {missing} in init")
    for h in _runs(spec, "hazard"):
        if not check(scoped, h, dyn)[0]:
            problems.append(f"{spec['case']}: hazard '{h['name']}' does not occur on the original rules")
        # the hazard must come from the interaction: without any one rule of the case it must vanish
        for rid in spec.get("requires", case_rules):
            others = [r for r in case_rules if r != rid]
            if check(_scoped(scenario, others), h, dyn)[0]:
                problems.append(f"{spec['case']}: hazard '{h['name']}' occurs even without {rid} (spec does not isolate the conflict)")
    for it in _runs(spec, "intent"):
        if it.get("new_requirement"):
            try:
                ok = check(_scoped(apply_edit(scenario, RepairProposal.model_validate(it["witness"])), case_rules), it, dyn)[0]
            except (KeyError, ValueError) as e:
                ok = False
                problems.append(f"{spec['case']}: intent '{it['name']}' has no valid witness ({e})")
            if not ok:
                problems.append(f"{spec['case']}: new-requirement intent '{it['name']}' is not met by its witness edit")
        elif not check(scoped, it, dyn)[0]:
            problems.append(f"{spec['case']}: intent '{it['name']}' fails on the original rules")
    return problems


# --------------------------------------------------------------------------
# Prompting and the loop
# --------------------------------------------------------------------------


def repair_prompt(scenario: Scenario, case, condition: str, feedback: list[str]) -> str:
    rules = case.rules
    all_rules = "\n".join(_fmt_rule(r) for r in scenario.rules)
    if condition == "graph":
        ctx = get_retrieval(scenario, rules).text
    elif condition == "text_deps":
        ctx = home_facts_text(scenario)
    else:
        ctx = "(no device or dependency information)"
    conflict = (
        f"Rules {', '.join(rules)} conflict ({case.type}).\n"
        f"Situation: {case.situation}\nUndesired outcome: {case.undesired_outcome}"
    )
    parts = [f"Home: {scenario.name}", f"# All automation rules of the home\n{all_rules}", f"# Context\n{ctx}", f"# Confirmed conflict\n{conflict}"]
    if feedback:
        parts.append("# Your previous proposal was rejected by the verifier\n" + "\n\n".join(feedback) + "\n\nPropose a different edit.")
    parts.append("Propose one edit that repairs this conflict.")
    return "\n\n".join(parts)


def load_specs(path: Path = DEFAULT_SPEC) -> list[dict]:
    with open(path) as f:
        return yaml.safe_load(f)


def _approve(scenario: Scenario, repaired: Scenario, p: RepairProposal, auto: bool) -> bool:
    print(f"\nProposed edit ({p.operation}) on {p.target_rule}:\n{rule_diff(scenario, repaired, p.target_rule)}")
    print(f"Graph path: {' -> '.join(p.graph_path)}\nRationale: {p.rationale}")
    if auto:
        print("[auto-approved with --yes]")
        return True
    return input("Apply this edit to a copy of the home and verify it? [y/N] ").strip().lower() == "y"


def repair_case(scenario: Scenario, case, spec: dict, condition: str, llm: LLMClient, run: int = 0,
                max_attempts: int = 3, auto_approve: bool = True, out_dir: Path | None = None, verbose: bool = False) -> dict:
    feedback: list[str] = []
    attempts = []
    for k in range(max_attempts):
        res = llm.structured(repair_prompt(scenario, case, condition, feedback), run * 10 + k, REPAIR_SYSTEM_PROMPT, RepairProposal)
        if res.verdict is None:
            attempts.append(dict(attempt=k, error=res.error, applicable=False))
            feedback = [f"The previous answer was not a valid proposal ({res.error})."]
            continue
        p: RepairProposal = res.verdict
        rec = dict(attempt=k, proposal=p.model_dump(exclude_none=True))
        try:
            repaired = apply_edit(scenario, p)
        except ValueError as e:
            rec.update(applicable=False, messages=[f"Edit not applicable: {e}"])
            attempts.append(rec)
            feedback = rec["messages"]
            continue
        rec["applicable"] = True
        rec["diff"] = rule_diff(scenario, repaired, p.target_rule)
        rec["path_valid"], rec["path_msg"] = check_path(scenario, p.graph_path)
        rec["approved"] = _approve(scenario, repaired, p, auto_approve) if (verbose or not auto_approve) else True
        if not rec["approved"]:
            rec["messages"] = ["Rejected by the user."]
            attempts.append(rec)
            feedback = rec["messages"]
            continue
        v = verify(scenario, repaired, spec, case.rules)
        rec.update(v)
        rec["success"] = v["resolved"] and v["intent"] and v["no_new"]
        if out_dir is not None:
            d = Path(out_dir) / condition
            d.mkdir(parents=True, exist_ok=True)
            (d / f"{case.id}_run{run}_attempt{k}.yaml").write_text(
                yaml.safe_dump(repaired.model_dump(mode="json", exclude_none=True), sort_keys=False, allow_unicode=True))
        attempts.append(rec)
        if rec["success"]:
            break
        feedback = v["messages"]
    final = attempts[-1]
    return dict(
        case_id=case.id, scenario_id=scenario.id, type=case.type, condition=condition, run=run,
        success=bool(final.get("success")), first_try_success=bool(attempts[0].get("success")),
        n_attempts=len(attempts), applicable=bool(final.get("applicable")),
        resolved=bool(final.get("resolved")), intent=bool(final.get("intent")), no_new=bool(final.get("no_new")),
        path_valid=bool(final.get("path_valid")), attempts=attempts,
    )


def run_repairs(scenarios: list[Scenario], conditions: list[str], runs: int, out_dir: Path, llm: LLMClient,
                spec_path: Path = DEFAULT_SPEC, max_attempts: int = 3, workers: int = 6, auto_approve: bool = True) -> list[dict]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    specs = load_specs(spec_path)
    by_case = {c.id: (s, c) for s in scenarios for c in s.cases}
    problems = [p for sp in specs for p in sanity_check(by_case[sp["case"]][0], sp, by_case[sp["case"]][1].rules)]
    if problems:
        raise ValueError("repair specs fail on the original rules:\n" + "\n".join(problems))
    jobs = [(sp, cond, run) for sp in specs for cond in conditions for run in range(runs)]
    rows = []
    if not auto_approve:
        workers = 1
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(repair_case, *by_case[sp["case"]], sp, cond, llm, run, max_attempts, auto_approve, out_dir,
                            not auto_approve): (sp, cond, run) for sp, cond, run in jobs}
        for i, f in enumerate(as_completed(futs), 1):
            rows.append(f.result())
            if i % 10 == 0 or i == len(jobs):
                print(f"  {i}/{len(jobs)} repairs", flush=True)
    rows.sort(key=lambda r: (r["condition"], r["case_id"], r["run"]))
    with open(out_dir / "repair_results.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    write_repair_report(rows, out_dir, auto_approve)
    return rows


def write_repair_report(rows: list[dict], out_dir: Path, auto_approve: bool = True) -> None:
    conds = [c for c in REPAIR_CONDITIONS if any(r["condition"] == c for r in rows)]
    lines = [
        "# Repair–verify results",
        "",
        f"{len({r['case_id'] for r in rows})} conflict cases (5 per type) · runs: {max(r['run'] for r in rows) + 1} · "
        f"max attempts per run: {max(r['n_attempts'] for r in rows)} · approval: {'automatic (--yes)' if auto_approve else 'interactive'}",
        "",
        "Success = the edit applies, the hazard simulations no longer show the undesired outcome, the intent simulations "
        "still pass, and a whole-home symbolic re-check flags no new rule pair. `path valid` = the cited graph path exists.",
        "",
        "| Condition | Success (any attempt) | First-try success | Mean attempts | Applicable | Resolved | Intent kept | No new conflict | Path valid |",
        "|---|---|---|---|---|---|---|---|---|",
    ]

    def pct(rr, k):
        return f"{100 * sum(r[k] for r in rr) / len(rr):.0f}"

    for c in conds:
        rr = [r for r in rows if r["condition"] == c]
        lines.append(
            f"| {c} | {pct(rr, 'success')} | {pct(rr, 'first_try_success')} | {sum(r['n_attempts'] for r in rr) / len(rr):.2f} | "
            f"{pct(rr, 'applicable')} | {pct(rr, 'resolved')} | {pct(rr, 'intent')} | {pct(rr, 'no_new')} | {pct(rr, 'path_valid')} |"
        )
    lines += ["", "## Success by conflict type (any attempt)", "", "| Condition | logical | semantic | physical |", "|---|---|---|---|"]
    for c in conds:
        cells = []
        for t in ("logical", "semantic", "physical"):
            rr = [r for r in rows if r["condition"] == c and r["type"] == t]
            cells.append(pct(rr, "success") if rr else "–")
        lines.append(f"| {c} | " + " | ".join(cells) + " |")
    lines += ["", "## Per case (final attempt of run 0)", ""]
    for r in rows:
        if r["run"] != 0:
            continue
        fa = r["attempts"][-1]
        p = fa.get("proposal", {})
        why = "; ".join(m.split("\n")[0] for m in fa.get("messages", [])) if not r["success"] else ""
        lines.append(
            f"- **{r['condition']} / {r['case_id']}** ({r['type']}) — {'✅' if r['success'] else '❌'} after {r['n_attempts']} attempt(s): "
            f"`{p.get('operation', '?')}` on {p.get('target_rule', '?')}" + (f" — {why}" if why else "")
        )
        if fa.get("diff"):
            lines.append("  ```\n  " + fa["diff"].replace("\n", "\n  ") + "\n  ```")
    (out_dir / "repair_results.md").write_text("\n".join(lines) + "\n")
