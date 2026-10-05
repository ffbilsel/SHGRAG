"""Functional tests: graph construction for manually inspected examples."""

import pytest

from shgrag.graph_builder import build_graph, edges_of_type, graph_summary


def _edges(g, etype):
    return {(u, v) for u, v, _ in edges_of_type(g, etype)}


def test_s01_nodes_and_edges(scenarios):
    g = build_graph(scenarios["s01_hallway_security"])
    s = graph_summary(g)
    assert s["Room"] == 3 and s["Device"] == 4 and s["EnvVar"] == 2 and s["Rule"] == 5
    assert s["State"] == 5  # lock, plug power, camera power+recording, lamp power
    assert ("room:hallway", "device:camera_hall") in _edges(g, "HAS_DEVICE")
    assert ("device:camera_hall", "state:camera_hall.recording") in _edges(g, "HAS_STATE")
    assert ("rule:R1", "state:plug_hall.power") in _edges(g, "TARGETS")
    assert ("rule:R2", "env:home_mode") in _edges(g, "TRIGGERED_BY")
    assert ("rule:R4", "env:motion_hall") in _edges(g, "TRIGGERED_BY")
    assert _edges(g, "AFFECTS") == {("state:plug_hall.power", "state:camera_hall.power")}
    assert g.nodes["rule:R1"]["trigger_time"] == "23:00"
    assert g.nodes["rule:R4"]["time_ranges"] == [("22:00", "06:00")]


def test_s05_two_hop_dependency_edges(scenarios):
    g = build_graph(scenarios["s05_router_dependency"])
    affects = _edges(g, "AFFECTS")
    assert ("state:plug_office.power", "state:router.power") in affects
    assert ("state:router.power", "state:camera_garden.cloud_upload") in affects
    assert ("state:router.power", "state:doorbell.notifications") in affects


def test_s02_environmental_edges(scenarios):
    g = build_graph(scenarios["s02_bedroom_climate"])
    data = {(u, v): d for u, v, d in edges_of_type(g, "AFFECTS")}
    assert data[("state:heater_living.power", "env:temp_living")]["effect"] == "increase"
    assert data[("state:window_living.position", "env:temp_living")]["effect"] == "decrease"
    assert ("rule:R2", "env:temp_living") in _edges(g, "TRIGGERED_BY")


def test_conditions_become_edges(scenarios):
    g = build_graph(scenarios["s03_robot_vacuum"])
    assert ("rule:R3", "env:home_mode") in _edges(g, "CONDITIONED_ON")
    assert ("rule:R3", "env:motion_living") in _edges(g, "TRIGGERED_BY")


def test_state_trigger(scenarios):
    g = build_graph(scenarios["s04_kitchen_safety"])
    assert ("rule:R3", "state:oven.power") in _edges(g, "TRIGGERED_BY")


@pytest.mark.parametrize("sid", ["s01_hallway_security", "s05_router_dependency", "s12_garage_ev", "s20_greenhouse"])
def test_ablation_removes_only_affects(scenarios, sid):
    full = graph_summary(build_graph(scenarios[sid]))
    abl = graph_summary(build_graph(scenarios[sid], include_effects=False))
    assert "AFFECTS" in full and "AFFECTS" not in abl
    assert {k: v for k, v in full.items() if k != "AFFECTS"} == abl


def test_every_scenario_builds(scenarios):
    for s in scenarios.values():
        g = build_graph(s)
        assert len(edges_of_type(g, "AFFECTS")) == len(s.effects)
        assert sum(1 for _, d in g.nodes(data=True) if d["type"] == "Rule") == len(s.rules)
