from collections import Counter

import pytest
import yaml

from shgrag.loader import load_scenario
from shgrag.schema import Scenario


def test_dataset_size_matches_proposal(scenarios):
    rules = sum(len(s.rules) for s in scenarios.values())
    cases = [c for s in scenarios.values() for c in s.cases]
    assert 15 <= len(scenarios) <= 25
    assert 60 <= rules <= 100
    counts = Counter(c.type or "clean" for c in cases)
    for t in ("logical", "semantic", "physical"):
        assert counts[t] >= 10, counts
    assert counts["clean"] >= 20


def test_on_off_stay_strings(scenarios):
    s = scenarios["s01_hallway_security"]
    assert s.rule("R1").actions[0].value == "off"
    assert s.device("plug_hall").states["power"] == ["on", "off"]
    assert s.rule("R4").trigger.value is True  # real booleans still parse


def test_every_case_has_justification(scenarios):
    for s in scenarios.values():
        for c in s.cases:
            assert c.justification.strip()
            if c.label == "conflict":
                assert c.key_nodes, c.id


def test_invalid_reference_is_rejected(tmp_path):
    bad = {
        "id": "bad", "name": "bad", "rooms": ["r"],
        "devices": [{"id": "d", "type": "light", "room": "r", "states": {"power": ["on", "off"]}}],
        "rules": [{"id": "R1", "text": "t", "trigger": {"type": "time", "at": "10:00"},
                   "actions": [{"ref": "missing.power", "value": "on"}]}],
        "cases": [],
    }
    p = tmp_path / "bad.yaml"
    p.write_text(yaml.safe_dump(bad))
    with pytest.raises(ValueError, match="missing.power"):
        load_scenario(p)


def test_conflict_case_requires_type():
    with pytest.raises(ValueError):
        Scenario.model_validate({
            "id": "x", "name": "x", "rooms": ["r"],
            "devices": [{"id": "d", "type": "t", "room": "r", "states": {"p": ["a"]}}],
            "rules": [{"id": "R1", "text": "t", "trigger": {"type": "time", "at": "1:00"}, "actions": [{"ref": "d.p", "value": "a"}]}],
            "cases": [{"id": "c", "rules": ["R1"], "label": "conflict", "justification": "j"}],
        })
