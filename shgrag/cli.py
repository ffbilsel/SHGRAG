"""Command line interface.

  python -m shgrag validate
  python -m shgrag retrieve s01_c1 [--no-affects]
  python -m shgrag graph s01_hallway_security [--case s01_c1] [--out figures/s01.png]
  python -m shgrag run --conditions text graph graph_noaffects symbolic --runs 3 --out results/main
  python -m shgrag report results/main
  python -m shgrag scan --out results/scan_dev          (whole-home scan)
  python -m shgrag repair --yes --out results/repair    (repair-verify loop)
  python -m shgrag rubric-sheet results/main --out results/annotation/rubric_dev.csv
  python -m shgrag --data data/test_scenarios check-sources
  (score-annotations: legacy 0/1 sheet, superseded by the rubric)
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from .loader import DEFAULT_DATA_DIR, load_scenarios


def _find_case(scenarios, case_id):
    for s in scenarios:
        for c in s.cases:
            if c.id == case_id:
                return s, c
    sys.exit(f"unknown case {case_id}")


def cmd_validate(args) -> None:
    from .graph_builder import build_graph, graph_summary

    scenarios = load_scenarios(args.data, errata=args.errata)
    cases = [c for s in scenarios for c in s.cases]
    print(f"{len(scenarios)} scenarios, {sum(len(s.rules) for s in scenarios)} rules, {len(cases)} cases")
    counts = Counter(c.type or "clean" for c in cases)
    print("cases by type: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    totals: Counter = Counter()
    for s in scenarios:
        totals.update(graph_summary(build_graph(s)))
    print("graph totals: " + ", ".join(f"{k}={v}" for k, v in sorted(totals.items())))


def cmd_retrieve(args) -> None:
    from .reasoners import get_retrieval

    s, c = _find_case(load_scenarios(args.data, errata=args.errata), args.case)
    r = get_retrieval(s, c.rules, include_effects=not args.no_affects)
    print(r.text)
    print(f"\n[{r.num_nodes} nodes, {r.num_edges} edges] ground truth: {c.label} {c.type or ''}")


def cmd_graph(args) -> None:
    from .reasoners import get_graph, get_retrieval
    from .visualize import draw_graph

    scenarios = {s.id: s for s in load_scenarios(args.data, errata=args.errata)}
    if args.scenario not in scenarios:
        sys.exit(f"unknown scenario {args.scenario}")
    s = scenarios[args.scenario]
    if args.case:
        case = next((c for c in s.cases if c.id == args.case), None)
        if case is None:
            sys.exit(f"unknown case {args.case} in {s.id}")
        g = get_retrieval(s, case.rules).subgraph
        title = f"{s.name} - retrieved subgraph for {case.id}"
    else:
        g, title = get_graph(s), s.name
    out = Path(args.out or f"figures/{args.case or s.id}.png")
    print(draw_graph(g, out, title=title))


def cmd_run(args) -> None:
    from .experiment import run_experiment
    from .llm import LLMClient, LLMConfig

    scenarios = load_scenarios(args.data, errata=args.errata)
    if args.scenarios:
        scenarios = [s for s in scenarios if s.id in set(args.scenarios)]
    if args.limit:
        kept, n = [], 0
        for s in scenarios:
            if n >= args.limit:
                break
            s = s.model_copy(update={"cases": s.cases[: args.limit - n]})
            n += len(s.cases)
            kept.append(s)
        scenarios = kept
    cfg = LLMConfig(use_cache=not args.no_cache)
    if args.model:
        cfg.model = args.model
    if args.effort:
        cfg.effort = args.effort
    if args.backend:
        cfg.backend = args.backend
    if args.temperature is not None:
        cfg.temperature = args.temperature
    n_cases = sum(len(s.cases) for s in scenarios)
    n_llm = n_cases * args.runs * sum(c != "symbolic" for c in args.conditions)
    print(f"{n_cases} cases x {args.runs} runs x {args.conditions} -> {n_llm} LLM calls (model {cfg.model}, effort {cfg.effort}, backend {cfg.backend})")
    run_experiment(scenarios, args.conditions, args.runs, Path(args.out), llm=LLMClient(cfg), workers=args.workers)
    print((Path(args.out) / "results.md").read_text())


def cmd_report(args) -> None:
    from .experiment import load_records, write_report

    out = Path(args.results)
    records = load_records(out)
    if args.relabel_to:
        # re-score the same predictions against the (errata-corrected) labels of --data
        cases = {c.id: c for s in load_scenarios(args.data, errata=args.errata) for c in s.cases}
        for r in records:
            c = cases[r["case_id"]]
            r["gt_label"], r["gt_type"] = c.label, c.type
        dst = Path(args.relabel_to)
        dst.mkdir(parents=True, exist_ok=True)
        (dst / "run_config.json").write_text((out / "run_config.json").read_text())
        with open(dst / "predictions.jsonl", "w") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")
        out = dst
    write_report(records, out)
    print((out / "results.md").read_text())


def _llm_from_args(args):
    from .llm import LLMClient, LLMConfig

    cfg = LLMConfig(use_cache=not getattr(args, "no_cache", False))
    for k in ("model", "effort", "backend"):
        if getattr(args, k, None):
            setattr(cfg, k, getattr(args, k))
    return LLMClient(cfg)


def _load(args):
    scenarios = load_scenarios(args.data, errata=args.errata)
    if getattr(args, "scenarios", None):
        scenarios = [s for s in scenarios if s.id in set(args.scenarios)]
    return scenarios


def cmd_scan(args) -> None:
    from .scan import run_scan

    scenarios = _load(args)
    llm = _llm_from_args(args) if any(c != "symbolic" for c in args.conditions) else None
    n = len(scenarios) * args.runs * sum(c != "symbolic" for c in args.conditions)
    print(f"{len(scenarios)} homes x {args.runs} runs x {args.conditions} -> {n} LLM calls")
    run_scan(scenarios, args.conditions, args.runs, Path(args.out), llm, workers=args.workers)
    print((Path(args.out) / "scan_results.md").read_text())


def cmd_scan_report(args) -> None:
    from .scan import unmatched_for_adjudication, write_scan_report

    scenarios = _load(args)
    out = Path(args.results)
    rows = [json.loads(x) for x in open(out / "scan_predictions.jsonl")]
    write_scan_report(scenarios, rows, out)
    if args.adjudicate:
        items = unmatched_for_adjudication(scenarios, rows)
        (out / "scan_adjudication.json").write_text(json.dumps(items, indent=2, default=str))
        print(f"{len(items)} unmatched predicted rule sets -> {out / 'scan_adjudication.json'}")
    print((out / "scan_results.md").read_text())


def cmd_repair(args) -> None:
    from .repair import run_repairs

    scenarios = load_scenarios(args.data, errata=args.errata)
    llm = _llm_from_args(args)
    rows = run_repairs(scenarios, args.conditions, args.runs, Path(args.out), llm,
                       max_attempts=args.max_attempts, workers=args.workers, auto_approve=args.yes)
    print((Path(args.out) / "repair_results.md").read_text()[:4000])
    return rows


def cmd_repair_report(args) -> None:
    from .repair import write_repair_report

    out = Path(args.results)
    rows = [json.loads(x) for x in open(out / "repair_results.jsonl")]
    write_repair_report(rows, out)
    print((out / "repair_results.md").read_text())


def cmd_rubric_sheet(args) -> None:
    from .annotation import build_repair_sheet, build_sheet
    from .experiment import load_records

    scenarios = load_scenarios(args.data, errata=args.errata)
    rows = build_sheet(load_records(Path(args.results)), scenarios, Path(args.out), args.split)
    print(f"{len(rows)} explanation items -> {args.out}")
    if args.repairs:
        rr = [json.loads(x) for x in open(Path(args.repairs) / "repair_results.jsonl")]
        out = Path(args.out).with_name(Path(args.out).stem + "_repairs.csv")
        print(f"{len(build_repair_sheet(rr, scenarios, out))} repair items -> {out}")


def cmd_rubric_judge(args) -> None:
    from .annotation import judge_sheet

    llm = _llm_from_args(args)
    n = judge_sheet(Path(args.csv), load_scenarios(args.data, errata=args.errata), Path(args.out), llm, workers=args.workers)
    print(f"{n} items judged -> {args.out} (LLM-judge pilot, not an expert annotation)")


def cmd_rubric_score(args) -> None:
    from .annotation import score_sheet

    print(json.dumps(score_sheet(Path(args.csv)), indent=2))


def cmd_rubric_kappa(args) -> None:
    from .annotation import cohen_kappa

    print(json.dumps(cohen_kappa(Path(args.a), Path(args.b)), indent=2))


def cmd_check_sources(args) -> None:
    from .provenance import check_sources

    res = check_sources(load_scenarios(args.data, errata=args.errata))
    for r in res:
        print(f"{'OK ' if r['ok'] else 'BAD'} {r['scenario']} {r['rule']} {r['app']} {r['error'] or ''}")
    print(f"{sum(r['ok'] for r in res)}/{len(res)} adapted rules verified against their source")
    if args.out:
        Path(args.out).write_text(json.dumps(res, indent=2))
    if not all(r["ok"] for r in res):
        sys.exit(1)


def cmd_leakage(args) -> None:
    from .loader import TEST_DATA_DIR
    from .provenance import family_overlap, name_overlap, similarity_report

    dev, test = load_scenarios(args.data, errata=args.errata), load_scenarios(args.test_data or TEST_DATA_DIR)
    print("family overlap:", sorted(family_overlap(dev, test)) or "none")
    print("home-name overlap:", sorted(name_overlap(dev, test)) or "none")
    for r in similarity_report(dev, test):
        print(json.dumps(r))


def cmd_score(args) -> None:
    from .experiment import score_annotations

    print(json.dumps(score_annotations(Path(args.csv)), indent=2))


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="shgrag", description="Graph-assisted smart-home rule conflict detection")
    p.add_argument("--data", default=str(DEFAULT_DATA_DIR), help="scenario directory")
    p.add_argument("--errata", action="store_true", help="apply post-freeze label corrections (errata.yaml) when loading")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("validate", help="validate scenario files and print dataset statistics").set_defaults(fn=cmd_validate)

    r = sub.add_parser("retrieve", help="print the retrieved graph context for a case")
    r.add_argument("case")
    r.add_argument("--no-affects", action="store_true", help="ablation: graph without AFFECTS edges")
    r.set_defaults(fn=cmd_retrieve)

    g = sub.add_parser("graph", help="draw a home graph or a case's retrieved subgraph")
    g.add_argument("scenario")
    g.add_argument("--case")
    g.add_argument("--out")
    g.set_defaults(fn=cmd_graph)

    run = sub.add_parser("run", help="run the experiment")
    run.add_argument("--conditions", nargs="+", default=["text", "graph", "graph_noaffects", "symbolic"],
                     choices=["text", "text_deps", "graph", "graph_noaffects", "symbolic", "symbolic_noaffects"])
    run.add_argument("--runs", type=int, default=3)
    run.add_argument("--out", default="results/main")
    run.add_argument("--workers", type=int, default=8)
    run.add_argument("--model")
    run.add_argument("--effort", choices=["low", "medium", "high", "xhigh", "max"])
    run.add_argument("--backend", choices=["api", "claude_code"],
                     help="api: Anthropic API key; claude_code: logged-in Claude Code CLI, no API key")
    run.add_argument("--temperature", type=float, help="only for models that accept sampling parameters")
    run.add_argument("--scenarios", nargs="+", help="restrict to these scenario ids")
    run.add_argument("--limit", type=int, help="use only the first N cases (smoke test)")
    run.add_argument("--no-cache", action="store_true")
    run.set_defaults(fn=cmd_run)

    def llm_args(sp):
        sp.add_argument("--model")
        sp.add_argument("--effort", choices=["low", "medium", "high", "xhigh", "max"])
        sp.add_argument("--backend", choices=["api", "claude_code"])
        sp.add_argument("--no-cache", action="store_true")
        sp.add_argument("--workers", type=int, default=6)
        sp.add_argument("--scenarios", nargs="+", help="restrict to these scenario ids")

    scn = sub.add_parser("scan", help="whole-home scan: find all conflicting rule sets of each home")
    scn.add_argument("--conditions", nargs="+", default=["text", "text_deps", "graph", "graph_noaffects", "symbolic"],
                     choices=["text", "text_deps", "graph", "graph_noaffects", "symbolic"])
    scn.add_argument("--runs", type=int, default=3)
    scn.add_argument("--out", default="results/scan")
    llm_args(scn)
    scn.set_defaults(fn=cmd_scan)

    scr = sub.add_parser("scan-report", help="re-score a scan from scan_predictions.jsonl")
    scr.add_argument("results")
    scr.add_argument("--adjudicate", action="store_true", help="also list unmatched predictions for manual adjudication")
    scr.add_argument("--scenarios", nargs="+")
    scr.set_defaults(fn=cmd_scan_report)

    rp = sub.add_parser("repair", help="repair-verify loop on the cases in data/repair/repair_cases.yaml")
    rp.add_argument("--conditions", nargs="+", default=["text", "text_deps", "graph"], choices=["text", "text_deps", "graph"])
    rp.add_argument("--runs", type=int, default=3)
    rp.add_argument("--max-attempts", type=int, default=3)
    rp.add_argument("--out", default="results/repair")
    rp.add_argument("--yes", action="store_true", help="approve every proposed edit without asking (experiments)")
    llm_args(rp)
    rp.set_defaults(fn=cmd_repair)

    rpr = sub.add_parser("repair-report", help="re-write repair_results.md from repair_results.jsonl")
    rpr.add_argument("results")
    rpr.set_defaults(fn=cmd_repair_report)

    rs = sub.add_parser("rubric-sheet", help="stratified expert rubric sheet (explanations, optionally repairs)")
    rs.add_argument("results")
    rs.add_argument("--out", required=True)
    rs.add_argument("--split", default="dev")
    rs.add_argument("--repairs", help="results dir of a repair run, to add the repair sheet")
    rs.set_defaults(fn=cmd_rubric_sheet)
    rj = sub.add_parser("rubric-judge", help="pilot: fill a copy of a rubric sheet with an LLM judge")
    rj.add_argument("csv")
    rj.add_argument("--out", required=True)
    llm_args(rj)
    rj.set_defaults(fn=cmd_rubric_judge)
    rsc = sub.add_parser("rubric-score", help="score a filled rubric sheet")
    rsc.add_argument("csv")
    rsc.set_defaults(fn=cmd_rubric_score)
    rk = sub.add_parser("rubric-kappa", help="Cohen's kappa between two filled copies of a rubric sheet")
    rk.add_argument("a")
    rk.add_argument("b")
    rk.set_defaults(fn=cmd_rubric_kappa)
    cs = sub.add_parser("check-sources", help="fetch the source of every adapted rule and check its excerpt")
    cs.add_argument("--out")
    cs.set_defaults(fn=cmd_check_sources)
    lk = sub.add_parser("leakage", help="dev/test family, name and content-similarity report")
    lk.add_argument("--test-data")
    lk.set_defaults(fn=cmd_leakage)

    rep = sub.add_parser("report", help="recompute metrics, tables and plots from predictions.jsonl")
    rep.add_argument("results")
    rep.add_argument("--relabel-to", help="write a re-scored copy (labels from --data, e.g. with --errata) to this directory")
    rep.set_defaults(fn=cmd_report)

    sc = sub.add_parser("score-annotations", help="score the expert 0/1 explanation/repair sheet")
    sc.add_argument("csv")
    sc.set_defaults(fn=cmd_score)

    args = p.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
