"""Retrieve the small, relevant neighbourhood of a candidate rule set.

Steps
  1. seeds: the rule nodes of the case
  2. one hop: TRIGGERED_BY / CONDITIONED_ON / TARGETS nodes of each rule
  3. causal closure: from every TARGETS state follow AFFECTS edges forward
     (up to `max_hops`), only along effects whose `when` value matches the
     value produced by the previous step (so e.g. "plug=on" does not pull in
     effects that only happen when "plug=off")
  4. context: owning device of each state (+ its sibling states) and room
  5. touch points: causal chains of rule A that reach a node rule B
     triggers on / is conditioned on / targets / whose device B uses

The result is serialised to compact, line-oriented text for the LLM prompt.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import networkx as nx

from .graph_builder import node_label, rule_node, state_node
from .schema import Scenario


@dataclass
class CausalStep:
    source: str
    target: str
    when: object
    effect: str
    value: object
    kind: str
    description: str


@dataclass
class CausalPath:
    rule: str  # rule id that starts the chain
    action: str  # "ref = value"
    steps: list[CausalStep]
    touches: list[str] = field(default_factory=list)  # human-readable touch-point notes


@dataclass
class Retrieval:
    rule_ids: list[str]
    subgraph: nx.MultiDiGraph
    paths: list[CausalPath]
    text: str

    @property
    def num_nodes(self) -> int:
        return self.subgraph.number_of_nodes()

    @property
    def num_edges(self) -> int:
        return self.subgraph.number_of_edges()


def _fmt(v: object) -> str:
    if isinstance(v, bool):
        return str(v).lower()
    return str(v)


def _effect_applies(edge: dict, incoming_value: object) -> bool:
    if incoming_value is None:  # value unknown after an increase/decrease
        return True
    return _fmt(edge["when"]) == _fmt(incoming_value)


def _causal_paths(g: nx.MultiDiGraph, start: str, value: object, max_hops: int) -> list[list[CausalStep]]:
    """All maximal AFFECTS chains starting at `start` given it was set to `value`."""
    out: list[list[CausalStep]] = []

    def walk(node: str, val: object, path: list[CausalStep], seen: set[str]) -> None:
        extended = False
        if len(path) < max_hops:
            for _, tgt, d in g.out_edges(node, data=True):
                if d["type"] != "AFFECTS" or tgt in seen or not _effect_applies(d, val):
                    continue
                step = CausalStep(node, tgt, d["when"], d["effect"], d.get("value"), d["kind"], d.get("description", ""))
                next_val = d.get("value") if d["effect"] == "set" else None
                walk(tgt, next_val, path + [step], seen | {tgt})
                extended = True
        if not extended and path:
            out.append(path)

    walk(start, value, [], {start})
    return out


def _device_of(g: nx.MultiDiGraph, node: str) -> str | None:
    for u, _, d in g.in_edges(node, data=True):
        if d["type"] == "HAS_STATE":
            return u
    return None


def _room_of(g: nx.MultiDiGraph, node: str) -> str | None:
    for u, _, d in g.in_edges(node, data=True):
        if d["type"] in ("HAS_DEVICE", "HAS_ENV"):
            return u
    return None


def _touch_notes(g: nx.MultiDiGraph, reached: str, other_rules: list[str]) -> list[str]:
    """How a node reached by a causal chain relates to the other rules."""
    notes: list[str] = []
    reached_dev = _device_of(g, reached)
    for rid in other_rules:
        rn = rule_node(rid)
        for _, tgt, d in g.out_edges(rn, data=True):
            rel = d["type"]
            if rel not in ("TRIGGERED_BY", "CONDITIONED_ON", "TARGETS"):
                continue
            if tgt == reached:
                cmp = f"{d.get('op', '=')} {_fmt(d['value'])}" if rel != "TARGETS" else f"= {_fmt(d['value'])}"
                notes.append(f"{node_label(reached)} is {rel} of {rid} ({node_label(tgt)} {cmp})")
            elif reached_dev is not None and _device_of(g, tgt) == reached_dev:
                notes.append(
                    f"{node_label(reached)} belongs to device {node_label(reached_dev)}, "
                    f"whose state {node_label(tgt)} is {rel} of {rid}"
                )
    return notes


def retrieve(
    scenario: Scenario,
    g: nx.MultiDiGraph,
    rule_ids: list[str],
    max_hops: int = 3,
) -> Retrieval:
    keep: set[str] = set()
    for rid in rule_ids:
        rn = rule_node(rid)
        if rn not in g:
            raise KeyError(f"{scenario.id}: rule {rid} not in graph")
        keep.add(rn)
        keep.update(v for _, v in g.out_edges(rn))

    # causal closure from each action
    paths: list[CausalPath] = []
    for rid in rule_ids:
        others = [r for r in rule_ids if r != rid]
        for a in scenario.rule(rid).actions:
            for steps in _causal_paths(g, state_node(a.ref), a.value, max_hops):
                cp = CausalPath(rule=rid, action=f"{a.ref} = {_fmt(a.value)}", steps=steps)
                for s in steps:
                    keep.add(s.target)
                    cp.touches.extend(_touch_notes(g, s.target, others))
                paths.append(cp)

    # context: devices (with all their states) and rooms
    for n in list(keep):
        if g.nodes[n]["type"] in ("State", "EnvVar"):
            dev = _device_of(g, n)
            if dev:
                keep.add(dev)
                keep.update(v for _, v, d in g.out_edges(dev, data=True) if d["type"] == "HAS_STATE")
    for n in list(keep):
        if g.nodes[n]["type"] in ("Device", "EnvVar"):
            room = _room_of(g, n)
            if room:
                keep.add(room)

    sub = g.subgraph(keep).copy()
    # Only AFFECTS edges that lie on a retrieved causal path are kept as evidence.
    on_path = {(s.source, s.target) for p in paths for s in p.steps}
    drop = [(u, v, k) for u, v, k, d in sub.edges(keys=True, data=True) if d["type"] == "AFFECTS" and (u, v) not in on_path]
    sub.remove_edges_from(drop)

    text = serialize(scenario, sub, rule_ids, paths)
    return Retrieval(rule_ids=list(rule_ids), subgraph=sub, paths=paths, text=text)


# Serialisation -----------------------------------------------------------


def _fmt_rule_edges(g: nx.MultiDiGraph, rid: str) -> list[str]:
    rn = rule_node(rid)
    attrs = g.nodes[rn]
    lines = []
    if attrs.get("trigger_time"):
        lines.append(f"  TRIGGERED_BY time == {attrs['trigger_time']}")
    for start, end in attrs.get("time_ranges", []):
        lines.append(f"  CONDITIONED_ON time in [{start}, {end}]")
    order = {"TRIGGERED_BY": 0, "CONDITIONED_ON": 1, "TARGETS": 2}
    edges = sorted(
        ((d["type"], v, d) for _, v, d in g.out_edges(rn, data=True) if d["type"] in order),
        key=lambda e: (order[e[0]], e[1]),
    )
    for rel, v, d in edges:
        if rel == "TARGETS":
            lines.append(f"  TARGETS {node_label(v)} := {_fmt(d['value'])}")
        else:
            lines.append(f"  {rel} {node_label(v)} {d['op']} {_fmt(d['value'])}")
    return lines


def serialize(scenario: Scenario, sub: nx.MultiDiGraph, rule_ids: list[str], paths: list[CausalPath]) -> str:
    lines: list[str] = ["# Retrieved knowledge-graph context", "", "## Rules (TRIGGERED_BY / CONDITIONED_ON / TARGETS)"]
    for rid in rule_ids:
        lines.append(f'{rid}: "{sub.nodes[rule_node(rid)]["text"]}"')
        lines.extend(_fmt_rule_edges(sub, rid))

    lines += ["", "## Devices, states and environment (HAS_DEVICE / HAS_STATE / HAS_ENV)"]
    for n, d in sorted(sub.nodes(data=True)):
        if d["type"] == "Device":
            room = _room_of(sub, n)
            states = sorted(node_label(v) for _, v, e in sub.out_edges(n, data=True) if e["type"] == "HAS_STATE")
            desc = f' - "{d["description"]}"' if d.get("description") else ""
            lines.append(f"{node_label(room) if room else '?'} HAS_DEVICE {node_label(n)} [{d['device_type']}]{desc}")
            for s in states:
                vals = sub.nodes[state_node(s)].get("values") or []
                lines.append(f"  HAS_STATE {s}" + (f" in {{{', '.join(_fmt(x) for x in vals)}}}" if vals else ""))
        elif d["type"] == "EnvVar":
            room = _room_of(sub, n)
            desc = f' - "{d["description"]}"' if d.get("description") else ""
            lines.append(f"{node_label(room) if room else '?'} HAS_ENV {node_label(n)} [{d['kind']}]{desc}")

    affects = sorted(
        {(u, v, _fmt(d["when"]), d["effect"], _fmt(d.get("value")), d["kind"], d.get("description", ""))
         for u, v, d in sub.edges(data=True) if d["type"] == "AFFECTS"}
    )
    lines += ["", "## Physical / causal effects (AFFECTS)"]
    if not affects:
        lines.append("(none retrieved)")
    for u, v, when, effect, value, kind, desc in affects:
        tgt = f"{effect} {value}" if effect == "set" else effect
        note = f'  - "{desc}"' if desc else ""
        lines.append(f"{node_label(u)} == {when} --AFFECTS[{kind}]--> {node_label(v)} {tgt}{note}")

    lines += ["", "## Causal chains from rule actions"]
    if not paths:
        lines.append("(none)")
    for p in paths:
        chain = " -> ".join(
            [f"{p.rule}: {p.action}"]
            + [f"{node_label(s.target)} {('set ' + _fmt(s.value)) if s.effect == 'set' else s.effect}" for s in p.steps]
        )
        lines.append(chain)
        for t in dict.fromkeys(p.touches):
            lines.append(f"  reaches: {t}")
    return "\n".join(lines)
