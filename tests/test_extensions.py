"""Tests for the extensions requested in the Nov 2026 review: text_deps
condition, held-out split and provenance, whole-home scan scoring,
simulator / repair verification and home-level statistics."""

import pytest

from shgrag.evaluation import cluster_bootstrap, paired_case_table
from shgrag.freeze import check_manifest
from shgrag.loader import TEST_DATA_DIR, load_scenarios
from shgrag.prompts import text_deps_prompt, text_only_prompt
from shgrag.provenance import family_overlap, name_overlap
from shgrag.repair import RepairProposal, apply_edit, check_path, load_specs, sanity_check, verify
from shgrag.scan import match, scan_gold, score_home
from shgrag.simulate import Simulator


@pytest.fixture(scope="module")
def test_homes():
    return {s.id: s for s in load_scenarios(TEST_DATA_DIR)}


# ---- text_deps -------------------------------------------------------------

def test_text_deps_adds_all_dependencies_as_plain_text(scenarios):
    s = scenarios["s05_router_dependency"]
    p = text_deps_prompt(s, ["R1", "R2"])
    assert p.startswith(text_only_prompt(s, ["R1", "R2"]).rsplit("\n\nAnalyse", 1)[0])
    for ef in s.effects:  # every effect of the home, not only the retrieved ones
        assert f"When {ef.source} is" in p
    assert "AFFECTS" not in p and "reaches" not in p and "->" not in p  # no graph notation or chains
    assert "monitor_office" in p  # unrelated devices are not filtered out


# ---- held-out split ----------------------------------------------------------

def test_test_split_is_separate_and_frozen(scenarios, test_homes):
    dev, test = list(scenarios.values()), list(test_homes.values())
    assert all(s.split == "dev" for s in dev) and all(s.split == "test" for s in test)
    assert all(s.family for s in dev + test)
    assert not family_overlap(dev, test)
    assert not name_overlap(dev, test)
    assert not check_manifest(TEST_DATA_DIR)


def test_test_rules_record_their_source(test_homes):
    for s in test_homes.values():
        for r in s.rules:
            assert r.source is not None, (s.id, r.id)
            if r.source.kind == "adapted":
                assert r.source.url.startswith("https://github.com/")
                assert r.source.excerpt and r.source.adaptation


def test_test_home_names_are_neutral(test_homes):
    for s in test_homes.values():
        words = set(s.name.lower().replace("-", " ").split())
        ids = {p for d in s.devices for p in d.id.split("_")} | {p for e in s.environment for p in e.id.split("_")}
        assert not words & (set(s.id.split("_")[1:]) | ids), s.name


def test_conflict_labels_state_situation_and_outcome(scenarios, test_homes):
    for s in list(scenarios.values()) + list(test_homes.values()):
        for c in s.cases:
            if c.label == "conflict":
                assert c.situation and c.undesired_outcome, c.id
        for h in s.home_conflicts:
            assert h.situation and h.undesired_outcome


# ---- whole-home scan -----------------------------------------------------------

def test_scan_matching_and_minimal_gold(scenarios):
    s = scenarios["s20_greenhouse"]
    gold = scan_gold(s)
    assert frozenset({"R1", "R2", "R3"}) not in {g for g, _ in gold}  # superset of R1+R3 is dropped
    perfect = [dict(rules=sorted(g), conflict_type=t) for g, t in gold]
    sc = score_home(s, perfect)
    assert sc["tp"] == sc["n_gold"] == sc["n_pred"] and not sc["false_positives"]
    sc = score_home(s, perfect + [dict(rules=["R2", "R5"], conflict_type="logical")])
    assert sc["false_positives"] == [["R2", "R5"]] and sc["fp_on_labelled_clean"] == 1
    assert match([frozenset({"R1", "R2"})], [frozenset({"R1", "R2", "R3"})]) == [(0, 0)]


# ---- simulator and repair ---------------------------------------------------------

def test_simulator_propagates_dependencies_and_restores(scenarios):
    s = scenarios["s05_router_dependency"]
    tr = Simulator(s).run("00:25", 10, init={"home_mode": "night"})
    end = tr.states[-1]
    assert end["plug_office.power"] == "off" and end["router.power"] == "off"
    assert end["camera_garden.cloud_upload"] == "off"  # two-hop dependency


def test_repair_specs_hold_on_original_rules(cases):
    for spec in load_specs():
        s, c = cases[spec["case"]]
        assert c.label == "conflict"
        assert not sanity_check(s, spec, c.rules)
    types = [cases[sp["case"]][1].type for sp in load_specs()]
    assert {t: types.count(t) for t in set(types)} == {"logical": 5, "semantic": 5, "physical": 5}


def _spec(case_id):
    return next(sp for sp in load_specs() if sp["case"] == case_id)


def test_good_repair_passes_and_bad_repair_fails(cases):
    s, c = cases["s01_c1"]
    good = RepairProposal(target_rule="R1", operation="add_condition",
                          condition=dict(type="env", ref="home_mode", op="!=", value="away"),
                          graph_path=["R1", "plug_hall.power", "camera_hall.power", "camera_hall", "camera_hall.recording", "R2"],
                          rationale="x")
    v = verify(s, apply_edit(s, good), _spec("s01_c1"), c.rules)
    assert v["resolved"] and v["intent"] and v["no_new"]
    assert check_path(s, good.graph_path)[0]
    s3, c3 = cases["s03_c1"]  # stopping the vacuum while away breaks the vacuum's purpose
    bad = RepairProposal(target_rule="R1", operation="add_condition",
                         condition=dict(type="env", ref="home_mode", op="==", value="home"), graph_path=["R1"], rationale="x")
    v = verify(s3, apply_edit(s3, bad), _spec("s03_c1"), c3.rules)
    assert v["resolved"] and not v["intent"]


def test_invalid_edits_are_rejected(cases):
    s, _ = cases["s01_c1"]
    with pytest.raises(ValueError):
        apply_edit(s, RepairProposal(target_rule="R1", operation="add_condition",
                                     condition=dict(type="env", ref="no_such_var", op="==", value="x"), graph_path=[], rationale="x"))
    with pytest.raises(ValueError):  # removing the only action would delete the rule
        apply_edit(s, RepairProposal(target_rule="R1", operation="remove_action",
                                     action=dict(ref="plug_hall.power", value="off"), graph_path=[], rationale="x"))


# ---- home-level statistics ----------------------------------------------------------

def _rec(case, home, cond, run, gt, pred):
    return dict(case_id=case, scenario_id=home, condition=cond, run=run, gt_label="conflict" if gt else "clean", pred_conflict=pred)


def test_cluster_bootstrap_resamples_homes():
    recs = []
    for h in range(6):
        for k in range(3):
            cid, gt = f"h{h}_c{k}", k != 2
            for run in range(3):
                recs.append(_rec(cid, f"h{h}", "a", run, gt, gt if h % 2 else not gt))
                recs.append(_rec(cid, f"h{h}", "b", run, gt, gt))
    out = cluster_bootstrap(recs, [("a", "b")], n_boot=500)
    assert out["n_homes"] == 6
    assert out["conditions"]["b"]["f1"]["lo"] == out["conditions"]["b"]["f1"]["hi"] == 1.0
    d = out["differences"]["b-a"]["accuracy"]
    assert d["lo"] <= d["value"] <= d["hi"] and d["value"] == pytest.approx(0.5)
    assert paired_case_table(recs, "a", "b") == dict(both_correct=9, only_a=0, only_b=9, both_wrong=0)
