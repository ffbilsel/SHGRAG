"""Conflict reasoners evaluated in the experiments.

  text            LLM sees only the raw rules                (baseline A)
  graph           LLM sees the retrieved subgraph            (system B)
  graph_noaffects LLM sees a subgraph built without AFFECTS  (ablation)
  symbolic        deterministic graph checker, no LLM        (rule-based reference)
"""

from __future__ import annotations

from dataclasses import dataclass, field

import networkx as nx

from .graph_builder import build_graph, node_label, rule_node
from .llm import LLMClient
from .prompts import graph_prompt, text_only_prompt
from .retriever import Retrieval, _causal_paths, _device_of, retrieve
from .schema import Scenario

CONDITIONS = ("text", "graph", "graph_noaffects", "symbolic")
LLM_CONDITIONS = ("text", "graph", "graph_noaffects")


@dataclass
class Prediction:
    conflict: bool | None  # None = no valid answer (error)
    conflict_type: str | None
    explanation: str = ""
    evidence: list[str] = field(default_factory=list)
    repair: str = ""
    involved_rules: list[str] = field(default_factory=list)
    error: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    latency_s: float = 0.0
    context_nodes: int = 0
    context_edges: int = 0


# Graph cache: one graph per (scenario, with/without effects)
_GRAPHS: dict[tuple[str, bool], nx.MultiDiGraph] = {}


def get_graph(scenario: Scenario, include_effects: bool = True) -> nx.MultiDiGraph:
    key = (scenario.id, include_effects)
    if key not in _GRAPHS:
        _GRAPHS[key] = build_graph(scenario, include_effects=include_effects)
    return _GRAPHS[key]


def get_retrieval(scenario: Scenario, rule_ids: list[str], include_effects: bool = True) -> Retrieval:
    return retrieve(scenario, get_graph(scenario, include_effects), rule_ids)


def _from_llm(res, retrieval: Retrieval | None = None) -> Prediction:
    ctx = dict(
        context_nodes=retrieval.num_nodes if retrieval else 0,
        context_edges=retrieval.num_edges if retrieval else 0,
    )
    usage = dict(input_tokens=res.input_tokens, output_tokens=res.output_tokens, latency_s=res.latency_s)
    if res.verdict is None:
        return Prediction(None, None, error=res.error, **usage, **ctx)
    v = res.verdict
    ctype = v.conflict_type if v.conflict else None
    if v.conflict and ctype == "none":
        ctype = None
    return Prediction(
        conflict=v.conflict,
        conflict_type=ctype,
        explanation=v.explanation,
        evidence=list(v.evidence),
        repair=v.repair,
        involved_rules=list(v.involved_rules),
        **usage,
        **ctx,
    )


class TextOnlyReasoner:
    name = "text"

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def prompt(self, scenario: Scenario, rule_ids: list[str]) -> str:
        return text_only_prompt(scenario, rule_ids)

    def predict(self, scenario: Scenario, rule_ids: list[str], run: int = 0) -> Prediction:
        return _from_llm(self.llm.verdict(self.prompt(scenario, rule_ids), run))


class GraphReasoner:
    def __init__(self, llm: LLMClient, include_effects: bool = True):
        self.llm = llm
        self.include_effects = include_effects
        self.name = "graph" if include_effects else "graph_noaffects"

    def prompt(self, scenario: Scenario, rule_ids: list[str]) -> tuple[str, Retrieval]:
        r = get_retrieval(scenario, rule_ids, self.include_effects)
        return graph_prompt(scenario, rule_ids, r.text), r

    def predict(self, scenario: Scenario, rule_ids: list[str], run: int = 0) -> Prediction:
        prompt, r = self.prompt(scenario, rule_ids)
        return _from_llm(self.llm.verdict(prompt, run), r)


# --------------------------------------------------------------------------
# Deterministic symbolic checker
# --------------------------------------------------------------------------

_DISABLING = {"off", "false", "closed", "0", "stopped", "disabled"}


def _s(v: object) -> str:
    return str(v).lower()


def _minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _in_range(t: int, start: int, end: int) -> bool:
    return start <= t <= end if start <= end else (t >= start or t <= end)


def _ranges_overlap(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return _in_range(a[0], *b) or _in_range(b[0], *a)


def _time_window(rule) -> tuple[int, int] | None:
    """Time window in which the rule can fire (None = any time)."""
    if rule.trigger.type == "time":
        t = _minutes(rule.trigger.at)
        window = (t, t)
    else:
        window = None
    for c in rule.conditions:
        if c.type == "time_range":
            rng = (_minutes(c.start), _minutes(c.end))
            if window is None:
                window = rng
            elif window[0] == window[1]:
                if not _in_range(window[0], *rng):
                    return (-1, -1)  # never fires
            else:
                window = rng  # keep it simple: last explicit range wins
    return window


def _equalities(rule) -> dict[str, str]:
    eq = {}
    if rule.trigger.type in ("state", "env") and rule.trigger.op == "==":
        eq[rule.trigger.ref] = _s(rule.trigger.value)
    for c in rule.conditions:
        if c.type in ("state", "env") and c.op == "==":
            eq[c.ref] = _s(c.value)
    return eq


def _can_co_occur(ra, rb) -> bool:
    wa, wb = _time_window(ra), _time_window(rb)
    if wa == (-1, -1) or wb == (-1, -1):
        return False
    if wa is not None and wb is not None and not _ranges_overlap(wa, wb):
        return False
    ea, eb = _equalities(ra), _equalities(rb)
    if any(ea[k] != eb[k] for k in ea.keys() & eb.keys()):
        return False
    return not _disjoint_thresholds(ra.trigger, rb.trigger)


def _disjoint_thresholds(ta, tb) -> bool:
    """Two numeric triggers on the same variable that cannot hold together,
    e.g. `temp < 24` and `temp > 28` (hysteresis band)."""
    if ta.type != "env" or tb.type != "env" or ta.ref != tb.ref:
        return False
    if not all(isinstance(t.value, (int, float)) and not isinstance(t.value, bool) for t in (ta, tb)):
        return False
    lo = {"<": False, "<=": False, ">": True, ">=": True}
    if ta.op not in lo or tb.op not in lo or lo[ta.op] == lo[tb.op]:
        return False
    upper, lower = (ta, tb) if not lo[ta.op] else (tb, ta)  # upper: x < u ; lower: x > l
    return upper.value <= lower.value


def _direction_matches(effect: str, value: object, op: str, threshold: object) -> bool:
    if effect == "increase":
        return op in (">", ">=")
    if effect == "decrease":
        return op in ("<", "<=")
    # set
    if op == "==":
        return _s(value) == _s(threshold)
    if op == "!=":
        return _s(value) != _s(threshold)
    return True


class SymbolicReasoner:
    """Pairwise checker over the full graph; a transparent rule-based reference."""

    def __init__(self, include_effects: bool = True, max_hops: int = 3):
        self.include_effects = include_effects
        self.max_hops = max_hops
        self.name = "symbolic" if include_effects else "symbolic_noaffects"

    def predict(self, scenario: Scenario, rule_ids: list[str], run: int = 0) -> Prediction:
        g = get_graph(scenario, self.include_effects)
        findings: list[tuple[str, str, list[str]]] = []  # (type, explanation, rules)
        for a in rule_ids:
            for b in rule_ids:
                if a != b:
                    findings.extend(self._pair(scenario, g, a, b))
        if not findings:
            return Prediction(False, None, explanation="No conflicting targets or causal paths found.", repair="none")
        order = {"logical": 0, "physical": 1, "semantic": 2}
        findings.sort(key=lambda f: order[f[0]])
        ctype, expl, rules = findings[0]
        return Prediction(
            True,
            ctype,
            explanation=expl,
            evidence=[f[1] for f in findings],
            involved_rules=rules,
            repair="Add mutually exclusive conditions or a priority between the involved rules.",
        )

    def _pair(self, scenario: Scenario, g: nx.MultiDiGraph, a: str, b: str) -> list[tuple[str, str, list[str]]]:
        ra, rb = scenario.rule(a), scenario.rule(b)
        out = []
        co = _can_co_occur(ra, rb)
        # logical: incompatible values on the same state
        if a < b and co:
            for aa in ra.actions:
                for ab in rb.actions:
                    if aa.ref == ab.ref and _s(aa.value) != _s(ab.value):
                        out.append(("logical", f"{a} sets {aa.ref}={aa.value} while {b} sets it to {ab.value}", [a, b]))

        # A pair that switches the same actuator at two thresholds of the same
        # variable is a designed control loop (hysteresis), not a semantic conflict.
        control_loop = (
            ra.trigger.type == rb.trigger.type == "env"
            and ra.trigger.ref == rb.trigger.ref
            and {x.ref for x in ra.actions} & {x.ref for x in rb.actions}
        )
        b_edges = [(d["type"], v, d) for _, v, d in g.out_edges(rule_node(b), data=True)]
        for act in ra.actions:
            for path in _causal_paths(g, f"state:{act.ref}", act.value, self.max_hops):
                for step in path:
                    tgt = step.target
                    is_env = g.nodes[tgt]["type"] == "EnvVar"
                    for rel, v, d in b_edges:
                        hit = None
                        if v == tgt and rel == "TRIGGERED_BY":
                            if _direction_matches(step.effect, step.value, d["op"], d["value"]):
                                hit = f"{a}'s action {act.ref}={act.value} {step.effect}s {node_label(tgt)}, which triggers {b}"
                        elif v == tgt and rel == "CONDITIONED_ON":
                            hit = f"{a}'s action {act.ref}={act.value} changes {node_label(tgt)}, a condition of {b}"
                        elif v == tgt and rel == "TARGETS" and co and step.effect == "set" and _s(step.value) != _s(d["value"]):
                            hit = f"{a} indirectly sets {node_label(tgt)}={step.value} while {b} sets it to {d['value']}"
                        elif (
                            rel == "TARGETS" and not is_env and v != tgt and co
                            and _device_of(g, v) is not None and _device_of(g, v) == _device_of(g, tgt)
                            and step.effect == "set" and _s(step.value) in _DISABLING
                        ):
                            hit = f"{a} indirectly sets {node_label(tgt)}={step.value}, disabling the device {b} controls"
                        if hit and not (is_env and control_loop):
                            out.append(("semantic" if is_env else "physical", hit, [a, b]))
        return out


def make_reasoner(name: str, llm: LLMClient | None = None):
    if name == "symbolic":
        return SymbolicReasoner(True)
    if name == "symbolic_noaffects":
        return SymbolicReasoner(False)
    if llm is None:
        raise ValueError(f"reasoner {name} needs an LLM client")
    if name == "text":
        return TextOnlyReasoner(llm)
    if name == "graph":
        return GraphReasoner(llm, include_effects=True)
    if name == "graph_noaffects":
        return GraphReasoner(llm, include_effects=False)
    raise ValueError(f"unknown reasoner {name}")
