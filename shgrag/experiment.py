"""Experiment runner: every case x condition x run, then metrics/tables/plots."""

from __future__ import annotations

import csv
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from pathlib import Path

from .evaluation import TYPES, error_cases, mcnemar, summarize
from .llm import LLMClient
from .reasoners import LLM_CONDITIONS, make_reasoner
from .schema import Case, Scenario


def iter_cases(scenarios: list[Scenario]):
    for s in scenarios:
        for c in s.cases:
            yield s, c


def _record(scenario: Scenario, case: Case, condition: str, run: int, pred) -> dict:
    return dict(
        case_id=case.id,
        scenario_id=scenario.id,
        rules=case.rules,
        gt_label=case.label,
        gt_type=case.type,
        key_nodes=case.key_nodes,
        condition=condition,
        run=run,
        pred_conflict=pred.conflict,
        pred_type=pred.conflict_type,
        **{k: v for k, v in asdict(pred).items() if k not in ("conflict", "conflict_type")},
    )


def run_experiment(
    scenarios: list[Scenario],
    conditions: list[str],
    runs: int,
    out_dir: Path,
    llm: LLMClient | None = None,
    workers: int = 8,
    progress: bool = True,
) -> list[dict]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if any(c in LLM_CONDITIONS for c in conditions) and llm is None:
        llm = LLMClient()
    reasoners = {c: make_reasoner(c, llm) for c in conditions}
    jobs = [(s, c, cond, run) for s, c in iter_cases(scenarios) for cond in conditions for run in range(runs)]

    records: list[dict] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(reasoners[cond].predict, s, c.rules, run): (s, c, cond, run) for s, c, cond, run in jobs}
        for i, fut in enumerate(as_completed(futures), 1):
            s, c, cond, run = futures[fut]
            records.append(_record(s, c, cond, run, fut.result()))
            if progress and (i % 25 == 0 or i == len(jobs)):
                print(f"  {i}/{len(jobs)} predictions", flush=True)

    records.sort(key=lambda r: (r["condition"], r["run"], r["case_id"]))
    with open(out_dir / "predictions.jsonl", "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    meta = dict(
        conditions=conditions, runs=runs, n_cases=sum(len(s.cases) for s in scenarios),
        model=llm.config.model if llm else None, effort=llm.config.effort if llm else None,
    )
    (out_dir / "run_config.json").write_text(json.dumps(meta, indent=2))
    write_report(records, out_dir, meta)
    return records


def load_records(out_dir: Path) -> list[dict]:
    with open(Path(out_dir) / "predictions.jsonl") as f:
        return [json.loads(line) for line in f if line.strip()]


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------


def _pm(agg: dict, key: str, pct: bool = True) -> str:
    m, s = agg[key]["mean"], agg[key]["std"]
    return f"{100 * m:.1f} ± {100 * s:.1f}" if pct else f"{m:.1f} ± {s:.1f}"


def tables_markdown(summary: dict, records: list[dict], meta: dict) -> str:
    conds = list(summary)
    lines = [
        "# SHGRAG experiment results",
        "",
        f"Model: `{meta.get('model')}` · effort: `{meta.get('effort')}` · runs: {meta.get('runs')} · cases: {meta.get('n_cases')}",
        "",
        "Values are mean ± std across runs (percent).",
        "",
        "## Overall conflict-vs-clean detection",
        "",
        "| Condition | Precision | Recall | F1 | Accuracy | FP | FN | Errors | Run agreement |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for c in conds:
        a = summary[c]["aggregate"]
        lines.append(
            f"| {c} | {_pm(a, 'precision')} | {_pm(a, 'recall')} | {_pm(a, 'f1')} | {_pm(a, 'accuracy')} | "
            f"{_pm(a, 'fp', False)} | {_pm(a, 'fn', False)} | {_pm(a, 'n_errors', False)} | "
            f"{100 * summary[c]['stability']['agreement']:.1f} |"
        )
    lines += ["", "## Per-type detection recall (flagged as any conflict)", "", "| Condition | " + " | ".join(TYPES) + " |", "|---|" + "---|" * len(TYPES)]
    for c in conds:
        a = summary[c]["aggregate"]
        lines.append(f"| {c} | " + " | ".join(_pm(a, f"{t}_detection_recall") for t in TYPES) + " |")
    lines += ["", "## Per-type F1 (detection; FP = clean cases labelled with that type)", "", "| Condition | " + " | ".join(TYPES) + " |", "|---|" + "---|" * len(TYPES)]
    for c in conds:
        a = summary[c]["aggregate"]
        lines.append(f"| {c} | " + " | ".join(_pm(a, f"{t}_detection_f1") for t in TYPES) + " |")
    lines += ["", "## Per-type F1 (type label must also be correct)", "", "| Condition | " + " | ".join(TYPES) + " |", "|---|" + "---|" * len(TYPES)]
    for c in conds:
        a = summary[c]["aggregate"]
        lines.append(f"| {c} | " + " | ".join(_pm(a, f"{t}_typed_f1") for t in TYPES) + " |")

    if "graph" in conds and "graph_noaffects" in conds:
        g, n = summary["graph"]["aggregate"], summary["graph_noaffects"]["aggregate"]
        lines += ["", "## Ablation: full graph vs. graph without AFFECTS edges", "", "| Metric | Full graph | No AFFECTS | Δ (pp) |", "|---|---|---|---|"]
        for key, label in [("f1", "Overall F1"), ("recall", "Overall recall")] + [
            (f"{t}_detection_recall", f"{t} recall") for t in TYPES
        ]:
            lines.append(f"| {label} | {_pm(g, key)} | {_pm(n, key)} | {100 * (g[key]['mean'] - n[key]['mean']):+.1f} |")

    lines += ["", "## Explanation grounding (automatic proxy)", "",
              "Share of correctly flagged conflicts whose explanation/evidence mentions all ground-truth key nodes. "
              "The required 0/1 expert check uses `annotations.csv`.", "", "| Condition | Grounded |", "|---|---|"]
    for c in conds:
        lines.append(f"| {c} | {_pm(summary[c]['aggregate'], 'explanation_proxy')} |")

    pairs = [(a, b) for a, b in [("text", "graph"), ("graph_noaffects", "graph"), ("text", "symbolic")] if a in conds and b in conds]
    if pairs:
        lines += ["", "## Significance (exact McNemar, majority vote over runs)", "", "| A | B | only A correct | only B correct | p-value |", "|---|---|---|---|---|"]
        for a, b in pairs:
            m = mcnemar(records, a, b)
            lines.append(f"| {a} | {b} | {m['a_correct_only']} | {m['b_correct_only']} | {m['p_value']:.4f} |")

    lines += ["", "## Error cases (majority vote)", ""]
    for c in conds:
        e = error_cases(records, c)
        lines.append(f"- **{c}** — FP: {', '.join(e['false_positives']) or '–'}; FN: {', '.join(e['false_negatives']) or '–'}")
        flips = summary[c]["stability"]["flipping_cases"]
        if flips:
            lines.append(f"  - unstable across runs: {', '.join(flips)}")
    return "\n".join(lines) + "\n"


def write_annotation_sheet(records: list[dict], path: Path) -> None:
    """One row per (condition, case) for run 0 of each LLM condition. Experts fill
    `explanation_supported` and `repair_safe` with 0/1."""
    rows = [r for r in records if r["run"] == 0 and r["condition"] in LLM_CONDITIONS and r["pred_conflict"]]
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["condition", "case_id", "gt_label", "gt_type", "pred_type", "explanation", "repair", "explanation_supported", "repair_safe"])
        for r in rows:
            w.writerow([r["condition"], r["case_id"], r["gt_label"], r["gt_type"] or "", r["pred_type"] or "", r["explanation"], r["repair"], "", ""])


def score_annotations(path: Path) -> dict:
    """Percentage of explanations judged supported and repairs judged safe, per condition."""
    out: dict[str, dict] = {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            c = out.setdefault(row["condition"], dict(n=0, explanation_supported=0, repair_safe=0, n_conflict_gt=0, supported_on_true_conflicts=0))
            if row["explanation_supported"].strip() == "" or row["repair_safe"].strip() == "":
                continue
            c["n"] += 1
            c["explanation_supported"] += int(row["explanation_supported"])
            c["repair_safe"] += int(row["repair_safe"])
            if row["gt_label"] == "conflict":
                c["n_conflict_gt"] += 1
                c["supported_on_true_conflicts"] += int(row["explanation_supported"])
    for c in out.values():
        c["explanation_supported_pct"] = 100 * c["explanation_supported"] / c["n"] if c["n"] else 0.0
        c["repair_safe_pct"] = 100 * c["repair_safe"] / c["n"] if c["n"] else 0.0
    return out


def write_report(records: list[dict], out_dir: Path, meta: dict | None = None) -> dict:
    out_dir = Path(out_dir)
    meta = meta or json.loads((out_dir / "run_config.json").read_text())
    summary = summarize(records)
    (out_dir / "metrics.json").write_text(json.dumps(summary, indent=2))
    (out_dir / "results.md").write_text(tables_markdown(summary, records, meta))
    if not (out_dir / "annotations.csv").exists():  # never overwrite expert labels
        write_annotation_sheet(records, out_dir / "annotations.csv")
    try:
        from .visualize import plot_results

        plot_results(summary, out_dir)
    except ImportError:
        pass
    return summary
