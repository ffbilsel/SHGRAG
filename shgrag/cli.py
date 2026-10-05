"""Command line interface.

  python -m shgrag validate
  python -m shgrag retrieve s01_c1 [--no-affects]
  python -m shgrag graph s01_hallway_security [--case s01_c1] [--out figures/s01.png]
  python -m shgrag run --conditions text graph graph_noaffects symbolic --runs 3 --out results/main
  python -m shgrag report results/main
  python -m shgrag score-annotations results/main/annotations.csv
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

    scenarios = load_scenarios(args.data)
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

    s, c = _find_case(load_scenarios(args.data), args.case)
    r = get_retrieval(s, c.rules, include_effects=not args.no_affects)
    print(r.text)
    print(f"\n[{r.num_nodes} nodes, {r.num_edges} edges] ground truth: {c.label} {c.type or ''}")


def cmd_graph(args) -> None:
    from .reasoners import get_graph, get_retrieval
    from .visualize import draw_graph

    scenarios = {s.id: s for s in load_scenarios(args.data)}
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

    scenarios = load_scenarios(args.data)
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
    if args.temperature is not None:
        cfg.temperature = args.temperature
    n_cases = sum(len(s.cases) for s in scenarios)
    n_llm = n_cases * args.runs * sum(c != "symbolic" for c in args.conditions)
    print(f"{n_cases} cases x {args.runs} runs x {args.conditions} -> {n_llm} LLM calls (model {cfg.model}, effort {cfg.effort})")
    run_experiment(scenarios, args.conditions, args.runs, Path(args.out), llm=LLMClient(cfg), workers=args.workers)
    print((Path(args.out) / "results.md").read_text())


def cmd_report(args) -> None:
    from .experiment import load_records, write_report

    out = Path(args.results)
    write_report(load_records(out), out)
    print((out / "results.md").read_text())


def cmd_score(args) -> None:
    from .experiment import score_annotations

    print(json.dumps(score_annotations(Path(args.csv)), indent=2))


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="shgrag", description="Graph-assisted smart-home rule conflict detection")
    p.add_argument("--data", default=str(DEFAULT_DATA_DIR), help="scenario directory")
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
                     choices=["text", "graph", "graph_noaffects", "symbolic", "symbolic_noaffects"])
    run.add_argument("--runs", type=int, default=3)
    run.add_argument("--out", default="results/main")
    run.add_argument("--workers", type=int, default=8)
    run.add_argument("--model")
    run.add_argument("--effort", choices=["low", "medium", "high", "xhigh", "max"])
    run.add_argument("--temperature", type=float, help="only for models that accept sampling parameters")
    run.add_argument("--scenarios", nargs="+", help="restrict to these scenario ids")
    run.add_argument("--limit", type=int, help="use only the first N cases (smoke test)")
    run.add_argument("--no-cache", action="store_true")
    run.set_defaults(fn=cmd_run)

    rep = sub.add_parser("report", help="recompute metrics, tables and plots from predictions.jsonl")
    rep.add_argument("results")
    rep.set_defaults(fn=cmd_report)

    sc = sub.add_parser("score-annotations", help="score the expert 0/1 explanation/repair sheet")
    sc.add_argument("csv")
    sc.set_defaults(fn=cmd_score)

    args = p.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
