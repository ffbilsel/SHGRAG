# Final report outline

1. **Introduction and motivation.** Hidden rule interactions in smart homes; the research question.
2. **Related work.** Position this work against:
   - TAP conflict detection: SIGFRID, IoTSafe, TAPFixer, PhysCheck, CAGE-TAP, InteractionShield;
   - LLMs for IoT: AutoIoT, "When LLMs Meet Rule Conflicts";
   - the KFUPM SHGRAG thesis.

   See `docs/chatgpt_conversation_summary.md` §3.
3. **Conflict definitions.** Taken from `docs/conflict_definitions.md`.
4. **System.** Graph schema, retrieval (causal chains, touch points), prompts, output schema, symbolic reference checker.
5. **Benchmark.** 20 homes, 98 rules, 75 cases; how the data was built; how the clean look-alike cases were designed.
6. **Experimental setup.** Conditions, model/effort, repeat runs, metrics, McNemar test.
7. **Results.** Tables and plots from `results/main/`:
   - overall P/R/F1/accuracy, graph-assisted vs. text-only;
   - per-type recall/F1;
   - FP/FN;
   - ablation, full graph vs. no AFFECTS;
   - explanation/repair validity (expert 0/1) and the grounding proxy;
   - run-to-run variation.
8. **Discussion.** Proposal §8 questions:
   - When does the graph help, and when is plain rule text already enough?
   - Are the remaining errors caused by missing graph relations or by LLM reasoning mistakes? Use the symbolic checker's results as a "graph is sufficient" reference.
   - Why are semantic and physical conflicts harder than logical ones?
   - Does grounding improve explanations even when the label does not change?
   - How sensitive are the results to graph quality, prompt wording and the choice of LLM?
   - What would real deployment need? Platform adapters, privacy, incremental graph updates, latency/cost control, and stronger repair validation.
9. **Threats to validity.**
   - The benchmark is hand-curated and small.
   - Ground truth was labelled by the authors.
   - The retrieval "reaches" lines partly encode symbolic reasoning.
   - Opus 5.5 has no temperature control.
10. **Conclusion and future work.** See `docs/TASK_PLAN.md`, milestones M2 and M3.
