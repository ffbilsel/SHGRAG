"""Direct-conflict, hidden-dependency, clean-case and ablation tests on the
deterministic checker (the LLM conditions are exercised in test_pipeline.py)."""

import pytest

from shgrag.reasoners import SymbolicReasoner

FULL = SymbolicReasoner(True)
ABL = SymbolicReasoner(False)


@pytest.mark.parametrize("cid", ["s01_c2", "s04_c1", "s11_c1", "s14_c2", "s17_c1", "s18_c4"])
def test_direct_conflicts(cases, cid):
    s, c = cases[cid]
    for r in (FULL, ABL):  # visible without the graph's causal edges
        p = r.predict(s, c.rules)
        assert p.conflict and p.conflict_type == "logical"


@pytest.mark.parametrize("cid", ["s01_c1", "s05_c1", "s06_c1", "s10_c1", "s14_c1", "s16_c1", "s20_c2"])
def test_hidden_dependency_conflicts(cases, cid):
    s, c = cases[cid]
    assert FULL.predict(s, c.rules).conflict_type == "physical"
    assert not ABL.predict(s, c.rules).conflict


@pytest.mark.parametrize("cid", ["s02_c1", "s03_c1", "s09_c1", "s13_c1", "s15_c2", "s19_c1"])
def test_semantic_conflicts(cases, cid):
    s, c = cases[cid]
    assert FULL.predict(s, c.rules).conflict_type == "semantic"
    assert not ABL.predict(s, c.rules).conflict


@pytest.mark.parametrize("cid", ["s01_c3", "s01_c4", "s02_c2", "s05_c3", "s06_c2", "s06_c3", "s08_c2", "s09_c2", "s15_c4", "s18_c2"])
def test_clean_lookalikes(cases, cid):
    s, c = cases[cid]
    assert not FULL.predict(s, c.rules).conflict


def test_overall_symbolic_quality(cases):
    wrong = [cid for cid, (s, c) in cases.items() if FULL.predict(s, c.rules).conflict != (c.label == "conflict")]
    assert len(wrong) <= 5, wrong
