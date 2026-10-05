import pytest

from shgrag.evaluation import binary_metrics, mcnemar, per_type_metrics, stability, summarize


def rec(cid, gt, gt_type, pred, ptype=None, cond="graph", run=0, error=None):
    return dict(case_id=cid, gt_label=gt, gt_type=gt_type, pred_conflict=pred, pred_type=ptype, condition=cond,
                run=run, error=error, key_nodes=[], explanation="", evidence=[])


def test_binary_metrics():
    rs = [rec("a", "conflict", "logical", True, "logical"), rec("b", "conflict", "physical", False),
          rec("c", "clean", None, True, "semantic"), rec("d", "clean", None, False)]
    m = binary_metrics(rs)
    assert (m["tp"], m["fn"], m["fp"], m["tn"]) == (1, 1, 1, 1)
    assert m["precision"] == m["recall"] == m["f1"] == m["accuracy"] == 0.5


def test_error_counts_as_clean():
    m = binary_metrics([rec("a", "conflict", "logical", None, error="refusal")])
    assert m["fn"] == 1 and m["n_errors"] == 1


def test_per_type():
    rs = [rec("a", "conflict", "physical", True, "semantic"), rec("b", "conflict", "physical", True, "physical"),
          rec("c", "clean", None, True, "physical")]
    t = per_type_metrics(rs)["physical"]
    assert t["detection_recall"] == 1.0
    assert t["typed_recall"] == 0.5
    assert t["typed_precision"] == 0.5


def test_summary_and_stability():
    rs = [rec("a", "conflict", "logical", True, "logical", run=0), rec("a", "conflict", "logical", False, run=1),
          rec("b", "clean", None, False, run=0), rec("b", "clean", None, False, run=1)]
    s = summarize(rs)["graph"]
    assert s["runs"] == 2
    assert s["aggregate"]["recall"]["mean"] == pytest.approx(0.5)
    assert stability(rs)["flipping_cases"] == ["a"]


def test_mcnemar():
    rs = []
    for i in range(10):
        rs.append(rec(f"c{i}", "conflict", "physical", False, cond="text"))
        rs.append(rec(f"c{i}", "conflict", "physical", True, "physical", cond="graph"))
    m = mcnemar(rs, "text", "graph")
    assert m["b_correct_only"] == 10 and m["a_correct_only"] == 0
    assert m["p_value"] < 0.01
