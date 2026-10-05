"""Convert a Scenario into a typed knowledge graph (NetworkX MultiDiGraph).

Node types : Room, Device, State, EnvVar, Rule
Edge types :
  HAS_DEVICE     Room   -> Device
  HAS_STATE      Device -> State
  HAS_ENV        Room   -> EnvVar
  TRIGGERED_BY   Rule   -> State | EnvVar        (op, value)
  CONDITIONED_ON Rule   -> State | EnvVar        (op, value)
  TARGETS        Rule   -> State                 (value)
  AFFECTS        State  -> State | EnvVar        (when, effect, value, kind)

AFFECTS edges carry the physical/causal knowledge that is *not* visible in
rule text. `include_effects=False` drops them (ablation).
"""

from __future__ import annotations

import networkx as nx

from .schema import Scenario

# Node id helpers ---------------------------------------------------------


def room_node(room: str) -> str:
    return f"room:{room}"


def device_node(device_id: str) -> str:
    return f"device:{device_id}"


def state_node(ref: str) -> str:
    return f"state:{ref}"


def env_node(ref: str) -> str:
    return f"env:{ref}"


def rule_node(rule_id: str) -> str:
    return f"rule:{rule_id}"


def ref_node(scenario: Scenario, ref: str) -> str:
    """Map a scenario reference (device state or env var) to its node id."""
    if ref in scenario.env_refs():
        return env_node(ref)
    if ref in scenario.state_refs():
        return state_node(ref)
    raise KeyError(f"{scenario.id}: unknown ref {ref}")


def node_label(node: str) -> str:
    """Human-readable short label (drops the type prefix)."""
    return node.split(":", 1)[1]


# Builder -----------------------------------------------------------------

EDGE_TYPES = (
    "HAS_DEVICE",
    "HAS_STATE",
    "HAS_ENV",
    "TRIGGERED_BY",
    "CONDITIONED_ON",
    "TARGETS",
    "AFFECTS",
)


def build_graph(scenario: Scenario, include_effects: bool = True) -> nx.MultiDiGraph:
    g = nx.MultiDiGraph(scenario=scenario.id, name=scenario.name)

    for room in scenario.rooms:
        g.add_node(room_node(room), type="Room", name=room)

    for d in scenario.devices:
        dn = device_node(d.id)
        g.add_node(dn, type="Device", name=d.id, device_type=d.type, description=d.description)
        g.add_edge(room_node(d.room), dn, type="HAS_DEVICE")
        for attr, values in d.states.items():
            sn = state_node(f"{d.id}.{attr}")
            g.add_node(sn, type="State", name=f"{d.id}.{attr}", device=d.id, values=list(values))
            g.add_edge(dn, sn, type="HAS_STATE")

    for e in scenario.environment:
        en = env_node(e.id)
        g.add_node(en, type="EnvVar", name=e.id, kind=e.kind, description=e.description, values=list(e.values))
        g.add_edge(room_node(e.room), en, type="HAS_ENV")

    for r in scenario.rules:
        rn = rule_node(r.id)
        trig = r.trigger
        g.add_node(
            rn,
            type="Rule",
            name=r.id,
            text=r.text,
            trigger_time=trig.at if trig.type == "time" else None,
            time_ranges=[(c.start, c.end) for c in r.conditions if c.type == "time_range"],
        )
        if trig.type in ("state", "env"):
            g.add_edge(rn, ref_node(scenario, trig.ref), type="TRIGGERED_BY", op=trig.op, value=trig.value)
        for c in r.conditions:
            if c.type in ("state", "env"):
                g.add_edge(rn, ref_node(scenario, c.ref), type="CONDITIONED_ON", op=c.op, value=c.value)
        for a in r.actions:
            g.add_edge(rn, state_node(a.ref), type="TARGETS", value=a.value)

    if include_effects:
        for ef in scenario.effects:
            g.add_edge(
                state_node(ef.source),
                ref_node(scenario, ef.target),
                type="AFFECTS",
                when=ef.when,
                effect=ef.effect,
                value=ef.value,
                kind=ef.kind,
                description=ef.description,
            )
    return g


def edges_of_type(g: nx.MultiDiGraph, edge_type: str) -> list[tuple[str, str, dict]]:
    return [(u, v, d) for u, v, d in g.edges(data=True) if d["type"] == edge_type]


def graph_summary(g: nx.MultiDiGraph) -> dict[str, int]:
    """Counts of nodes per type and edges per type (used in tests/report)."""
    out: dict[str, int] = {}
    for _, d in g.nodes(data=True):
        out[d["type"]] = out.get(d["type"], 0) + 1
    for _, _, d in g.edges(data=True):
        out[d["type"]] = out.get(d["type"], 0) + 1
    return out
