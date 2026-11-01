"""Negative controls for the repair verifier.

For every repair case, two degenerate "repairs" are applied and must be
rejected:
  disable_<rule>  - restrict each case rule to a one-minute window at 04:44,
                    which effectively disables it (must fail the intent check
                    or leave the hazard in place);
  noop            - add a condition that is always true (must leave the hazard).
Writes results/repair/negative_controls.md.
"""

from pathlib import Path

from shgrag.loader import load_scenarios
from shgrag.repair import RepairProposal, apply_edit, load_specs, verify

by = {c.id: (s, c) for s in load_scenarios() for c in s.cases}
rows, passed_wrongly = [], 0
for sp in load_specs():
    s, c = by[sp["case"]]
    edits = {f"disable_{rid}": RepairProposal(target_rule=rid, operation="add_condition",
                                              condition=dict(type="time_range", start="04:44", end="04:45"),
                                              graph_path=[], rationale="negative control") for rid in c.rules}
    edits["noop"] = RepairProposal(target_rule=c.rules[0], operation="add_condition",
                                   condition=dict(type="time_range", start="00:00", end="23:59"), graph_path=[], rationale="negative control")
    for name, p in edits.items():
        v = verify(s, apply_edit(s, p), sp, c.rules)
        ok = v["resolved"] and v["intent"] and v["no_new"]
        passed_wrongly += ok
        rows.append(f"| {c.id} | {name} | {'ACCEPTED (bad)' if ok else 'rejected'} | {'resolved' if v['resolved'] else 'hazard remains'} | {'kept' if v['intent'] else 'intent lost'} |")
out = ["# Verifier negative controls", "", f"Degenerate edits accepted: {passed_wrongly} of {len(rows)}", "",
       "| Case | Edit | Verdict | Hazard | Intent |", "|---|---|---|---|---|", *rows]
Path("results/repair/negative_controls.md").write_text("\n".join(out) + "\n")
print(out[2])
