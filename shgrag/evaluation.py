"""Metrics for conflict detection experiments.

Every prediction record is a dict with at least:
  case_id, condition, run, gt_label ("conflict"/"clean"), gt_type,
  pred_conflict (bool|None), pred_type (str|None), error (str|None)

A prediction with an error (refusal, invalid output, ...) counts as "clean"
for the metrics - i.e. a missed hazard - and is reported in `n_errors`.
"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from statistics import mean, pstdev

TYPES = ("logical", "semantic", "physical")


def _safe_div(a: float, b: float) -> float:
    return a / b if b else 0.0


def _f1(p: float, r: float) -> float:
    return _safe_div(2 * p * r, p + r)


def binary_metrics(records: list[dict]) -> dict:
    tp = fp = fn = tn = errors = 0
    for r in records:
        gt = r["gt_label"] == "conflict"
        pred = bool(r["pred_conflict"])
        errors += r.get("error") is not None
        if gt and pred:
            tp += 1
        elif gt:
            fn += 1
        elif pred:
            fp += 1
        else:
            tn += 1
    p, rec = _safe_div(tp, tp + fp), _safe_div(tp, tp + fn)
    return dict(
        n=len(records), tp=tp, fp=fp, fn=fn, tn=tn, n_errors=errors,
        precision=p, recall=rec, f1=_f1(p, rec), accuracy=_safe_div(tp + tn, len(records)),
    )


def per_type_metrics(records: list[dict]) -> dict:
    """For each conflict type:
    detection_recall : gt cases of this type flagged as *any* conflict
    typed_precision/recall/f1 : one-vs-rest on the predicted type label
    """
    out = {}
    for t in TYPES:
        gt_t = [r for r in records if r["gt_type"] == t]
        pred_t = [r for r in records if r["pred_conflict"] and r["pred_type"] == t]
        hit_any = sum(bool(r["pred_conflict"]) for r in gt_t)
        hit_typed = sum(bool(r["pred_conflict"]) and r["pred_type"] == t for r in gt_t)
        tp_typed = sum(r["gt_type"] == t for r in pred_t)
        p = _safe_div(tp_typed, len(pred_t))
        rec = _safe_div(hit_typed, len(gt_t))
        det = _safe_div(hit_any, len(gt_t))
        out[t] = dict(
            n=len(gt_t),
            detection_recall=det,
            detection_f1=_f1(_safe_div(hit_any, hit_any + _fp_for_type(records, t)), det),
            typed_precision=p,
            typed_recall=rec,
            typed_f1=_f1(p, rec),
        )
    return out


def _fp_for_type(records: list[dict], t: str) -> int:
    """False positives attributed to type t: clean cases predicted as type t."""
    return sum(r["gt_label"] == "clean" and r["pred_conflict"] and r["pred_type"] == t for r in records)


_TOKEN = re.compile(r"[a-z0-9]+")


def _mentions(text: str, node: str) -> bool:
    """Loose match: every word of the node id (split on _ . -) starts a word in
    the text, so "camera_hall" matches "hallway camera"."""
    words = [w for w in _TOKEN.findall(node.lower()) if len(w) > 1]
    t = set(_TOKEN.findall(text.lower()))
    return bool(words) and all(any(tw.startswith(w) for tw in t) for w in words)


def explanation_proxy(records: list[dict]) -> dict:
    """Automatic proxy for explanation grounding: share of correctly flagged
    conflicts whose explanation+evidence mention all ground-truth key nodes.
    This does not replace the 0/1 expert check (see annotation sheet)."""
    eligible = [r for r in records if r["gt_label"] == "conflict" and r["pred_conflict"] and r.get("key_nodes")]
    ok = 0
    for r in eligible:
        text = " ".join([r.get("explanation", "")] + list(r.get("evidence", [])))
        ok += all(_mentions(text, k) for k in r["key_nodes"])
    return dict(n=len(eligible), grounded=ok, rate=_safe_div(ok, len(eligible)))


def group_by(records: list[dict], *keys: str) -> dict[tuple, list[dict]]:
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for r in records:
        groups[tuple(r[k] for k in keys)].append(r)
    return dict(groups)


def _agg(values: list[float]) -> dict:
    return dict(mean=mean(values), std=pstdev(values) if len(values) > 1 else 0.0, min=min(values), max=max(values))


def summarize(records: list[dict]) -> dict:
    """Per condition: metrics per run, then mean/std across runs."""
    summary = {}
    for (cond,), recs in sorted(group_by(records, "condition").items()):
        runs = group_by(recs, "run")
        per_run = {}
        for (run,), rr in sorted(runs.items()):
            per_run[run] = dict(binary=binary_metrics(rr), per_type=per_type_metrics(rr), explanation_proxy=explanation_proxy(rr))
        agg = {}
        for m in ("precision", "recall", "f1", "accuracy", "fp", "fn", "n_errors"):
            agg[m] = _agg([v["binary"][m] for v in per_run.values()])
        for t in TYPES:
            for m in ("detection_recall", "detection_f1", "typed_f1"):
                agg[f"{t}_{m}"] = _agg([v["per_type"][t][m] for v in per_run.values()])
        agg["explanation_proxy"] = _agg([v["explanation_proxy"]["rate"] for v in per_run.values()])
        agg["input_tokens"] = _agg([sum(r.get("input_tokens", 0) for r in rr) / len(rr) for (_,), rr in runs.items()])
        summary[cond] = dict(runs=len(per_run), per_run=per_run, aggregate=agg, stability=stability(recs))
    return summary


def stability(records: list[dict]) -> dict:
    """Run-to-run agreement: share of cases whose binary prediction is identical across runs."""
    by_case = group_by(records, "case_id")
    if not by_case:
        return dict(n_cases=0, agreement=0.0, flipping_cases=[])
    flipping = [cid for (cid,), rr in by_case.items() if len({bool(r["pred_conflict"]) for r in rr}) > 1]
    return dict(n_cases=len(by_case), agreement=1 - len(flipping) / len(by_case), flipping_cases=sorted(flipping))


def majority_vote(records: list[dict]) -> dict[str, bool]:
    """case_id -> majority binary prediction across runs (ties -> conflict)."""
    out = {}
    for (cid,), rr in group_by(records, "case_id").items():
        votes = sum(bool(r["pred_conflict"]) for r in rr)
        out[cid] = votes * 2 >= len(rr)
    return out


def mcnemar(records: list[dict], cond_a: str, cond_b: str) -> dict:
    """Exact McNemar test on per-case correctness (majority vote over runs)."""
    gt = {r["case_id"]: r["gt_label"] == "conflict" for r in records}
    a = majority_vote([r for r in records if r["condition"] == cond_a])
    b = majority_vote([r for r in records if r["condition"] == cond_b])
    common = sorted(set(a) & set(b))
    a_only = sum((a[c] == gt[c]) and (b[c] != gt[c]) for c in common)
    b_only = sum((b[c] == gt[c]) and (a[c] != gt[c]) for c in common)
    n = a_only + b_only
    k = min(a_only, b_only)
    p = min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2**n) if n else 1.0
    return dict(a=cond_a, b=cond_b, n_cases=len(common), a_correct_only=a_only, b_correct_only=b_only, p_value=p)


def error_cases(records: list[dict], condition: str) -> dict[str, list[str]]:
    """Case ids that are wrong in the majority vote, split into FP and FN."""
    recs = [r for r in records if r["condition"] == condition]
    gt = {r["case_id"]: r["gt_label"] == "conflict" for r in recs}
    mv = majority_vote(recs)
    return dict(
        false_positives=sorted(c for c, p in mv.items() if p and not gt[c]),
        false_negatives=sorted(c for c, p in mv.items() if not p and gt[c]),
    )


# --------------------------------------------------------------------------
# Home-level (clustered) uncertainty and paired comparisons
# --------------------------------------------------------------------------
# Cases from the same home share devices and rules, and the runs of one case
# are repeated samples of the same item, not new items. The bootstrap therefore
# resamples whole homes; within a resampled home all its cases and all runs are
# kept, so run repeats only reduce sampling noise of the case, they do not add
# effective sample size.


def _case_votes(records: list[dict]) -> dict[str, dict[str, list[bool]]]:
    out: dict[str, dict[str, list[bool]]] = defaultdict(lambda: defaultdict(list))
    for r in records:
        out[r["condition"]][r["case_id"]].append(bool(r["pred_conflict"]))
    return out


def _f1_from(votes: dict[str, list[bool]], gt: dict[str, bool], cases: list[str]) -> dict:
    tp = fp = fn = tn = 0
    for c in cases:
        for p in votes[c]:
            g = gt[c]
            tp += g and p
            fp += (not g) and p
            fn += g and not p
            tn += (not g) and not p
    p_, r_ = _safe_div(tp, tp + fp), _safe_div(tp, tp + fn)
    return dict(precision=p_, recall=r_, f1=_f1(p_, r_), accuracy=_safe_div(tp + tn, tp + fp + fn + tn))


def cluster_bootstrap(records: list[dict], pairs: list[tuple[str, str]] = (), n_boot: int = 5000, seed: int = 0) -> dict:
    """95% percentile CIs with homes as the resampling unit.

    Returns {"conditions": {cond: {metric: {value, lo, hi}}},
             "differences": {"b-a": {metric: {value, lo, hi, p_le_0}}}}
    where a difference is b minus a, and p_le_0 is the bootstrap share of
    resamples in which b is not better than a (a one-sided bootstrap p-value)."""
    import random

    votes = _case_votes(records)
    gt = {r["case_id"]: r["gt_label"] == "conflict" for r in records}
    home = {r["case_id"]: r["scenario_id"] for r in records}
    by_home: dict[str, list[str]] = defaultdict(list)
    for c, h in sorted(home.items()):
        by_home[h].append(c)
    homes = sorted(by_home)
    conds = sorted(votes)
    all_cases = sorted(home)
    metrics = ("precision", "recall", "f1", "accuracy")
    point = {c: _f1_from(votes[c], gt, [x for x in all_cases if x in votes[c]]) for c in conds}
    rng = random.Random(seed)
    samples: dict[tuple, list[float]] = defaultdict(list)
    for _ in range(n_boot):
        cases = [c for h in (rng.choice(homes) for _ in homes) for c in by_home[h]]
        m = {c: _f1_from(votes[c], gt, [x for x in cases if x in votes[c]]) for c in conds}
        for c in conds:
            for k in metrics:
                samples[(c, k)].append(m[c][k])
        for a, b in pairs:
            if a in m and b in m:
                for k in metrics:
                    samples[(f"{b}-{a}", k)].append(m[b][k] - m[a][k])

    def ci(v: list[float]) -> tuple[float, float]:
        v = sorted(v)
        return v[int(0.025 * len(v))], v[min(len(v) - 1, int(0.975 * len(v)))]

    out = dict(n_homes=len(homes), n_boot=n_boot, conditions={}, differences={})
    for c in conds:
        out["conditions"][c] = {k: dict(value=point[c][k], lo=ci(samples[(c, k)])[0], hi=ci(samples[(c, k)])[1]) for k in metrics}
    for a, b in pairs:
        if a in point and b in point:
            key = f"{b}-{a}"
            out["differences"][key] = {
                k: dict(
                    value=point[b][k] - point[a][k],
                    lo=ci(samples[(key, k)])[0],
                    hi=ci(samples[(key, k)])[1],
                    p_le_0=sum(x <= 0 for x in samples[(key, k)]) / n_boot,
                )
                for k in metrics
            }
    return out


def paired_by_home(records: list[dict], a: str, b: str) -> list[dict]:
    """Per home: mean per-case accuracy (averaged over runs) for two conditions."""
    votes = _case_votes(records)
    gt = {r["case_id"]: r["gt_label"] == "conflict" for r in records}
    home = {r["case_id"]: r["scenario_id"] for r in records}
    rows = []
    for h in sorted(set(home.values())):
        cases = [c for c in sorted(home) if home[c] == h and c in votes[a] and c in votes[b]]
        if not cases:
            continue

        def acc(cond: str) -> float:
            return mean(mean(p == gt[c] for p in votes[cond][c]) for c in cases)

        rows.append(dict(home=h, n_cases=len(cases), a=acc(a), b=acc(b)))
    return rows


def paired_case_table(records: list[dict], a: str, b: str) -> dict:
    """2x2 table of per-case majority-vote correctness (the McNemar input)."""
    gt = {r["case_id"]: r["gt_label"] == "conflict" for r in records}
    va = majority_vote([r for r in records if r["condition"] == a])
    vb = majority_vote([r for r in records if r["condition"] == b])
    common = sorted(set(va) & set(vb))
    t = dict(both_correct=0, only_a=0, only_b=0, both_wrong=0)
    for c in common:
        ca, cb = va[c] == gt[c], vb[c] == gt[c]
        t["both_correct" if ca and cb else "only_a" if ca else "only_b" if cb else "both_wrong"] += 1
    return t
