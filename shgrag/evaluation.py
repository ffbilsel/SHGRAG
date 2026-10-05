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
