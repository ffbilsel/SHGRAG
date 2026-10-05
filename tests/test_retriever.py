from shgrag.reasoners import get_retrieval


def test_hidden_dependency_is_retrieved(cases):
    s, c = cases["s05_c1"]
    r = get_retrieval(s, c.rules)
    assert any(len(p.steps) == 2 and p.steps[-1].target == "state:camera_garden.cloud_upload" for p in r.paths)
    assert "plug_office.power == off --AFFECTS[physical]--> router.power" in r.text
    assert "reaches: camera_garden.cloud_upload is TARGETS of R2" in r.text


def test_ablation_hides_dependency(cases):
    s, c = cases["s05_c1"]
    r = get_retrieval(s, c.rules, include_effects=False)
    assert r.paths == []
    assert "(none retrieved)" in r.text
    assert "router" not in r.text  # router is only reachable through AFFECTS


def test_effect_value_must_match(cases):
    # thermostat.mode affects temperature only when set to "heat": R1 sets heat, R5 sets eco
    s, c = cases["s11_c3"]
    r = get_retrieval(s, c.rules)
    assert {p.rule for p in r.paths} == {"R1"}


def test_clean_case_has_no_cross_rule_touch(cases):
    s, c = cases["s05_c3"]
    r = get_retrieval(s, c.rules)
    assert not any(p.touches for p in r.paths)


def test_semantic_chain_reaches_trigger(cases):
    s, c = cases["s03_c1"]
    r = get_retrieval(s, c.rules)
    assert any("motion_living is TRIGGERED_BY of R2" in t for p in r.paths for t in p.touches)


def test_retrieval_is_small(cases):
    for s, c in cases.values():
        r = get_retrieval(s, c.rules)
        assert r.num_nodes <= 30, c.id
