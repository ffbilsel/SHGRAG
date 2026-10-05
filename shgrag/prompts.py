"""Prompt templates shared by the text-only baseline and the graph-assisted
pipeline. Both conditions use the same system prompt and output schema so the
only difference is the context block (raw rules vs. retrieved subgraph)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .schema import Rule, Scenario

SYSTEM_PROMPT = """\
You are a safety analyst for smart-home automation. You are given a set of \
Trigger-Condition-Action automation rules from one home. Decide whether these \
rules, when active together in this home, can lead to a conflict.

Conflict categories:
- logical: two rules issue incompatible actions on the same device state \
(e.g. lock vs. unlock, on vs. off) in situations where both can fire.
- semantic: an action of one rule changes an environmental or context variable \
(temperature, humidity, light level, motion, presence, ...) so that another rule \
fires unexpectedly or is prevented from firing.
- physical: an action affects another device through a physical dependency that \
is not stated in the rule itself (e.g. cutting power to a device that another \
rule relies on).

Rules that act on the same device at different, non-overlapping times or under \
mutually exclusive conditions are not a conflict. If there is no conflict, \
answer conflict=false and conflict_type="none".

When there is a conflict, explain it briefly in plain language for a home owner, \
list the concrete facts that support your verdict as evidence, and propose one \
safe repair (e.g. add a condition, change a time window, re-wire a dependency). \
Never propose disabling a safety device. If there is no conflict, set repair to "none".\
"""


class Verdict(BaseModel):
    conflict: bool = Field(description="True if the rules can conflict in this home")
    conflict_type: Literal["logical", "semantic", "physical", "none"]
    involved_rules: list[str] = Field(description="Ids of the rules involved in the conflict")
    explanation: str = Field(description="Short, user-readable explanation (2-4 sentences)")
    evidence: list[str] = Field(description="Facts from the given context that support the verdict")
    repair: str = Field(description="One safe repair suggestion, or 'none'")


def _fmt_rule(r: Rule) -> str:
    t = r.trigger
    if t.type == "time":
        trig = f"time == {t.at}"
    else:
        trig = f"{t.ref} {t.op} {t.value}"
    conds = []
    for c in r.conditions:
        if c.type == "time_range":
            conds.append(f"time in [{c.start}, {c.end}]")
        else:
            conds.append(f"{c.ref} {c.op} {c.value}")
    acts = [f"{a.ref} := {a.value}" for a in r.actions]
    return (
        f'{r.id}: "{r.text}"\n'
        f"  trigger: {trig}\n"
        f"  conditions: {'; '.join(conds) if conds else 'none'}\n"
        f"  actions: {'; '.join(acts)}"
    )


def text_only_prompt(scenario: Scenario, rule_ids: list[str]) -> str:
    rules = "\n".join(_fmt_rule(scenario.rule(rid)) for rid in rule_ids)
    return (
        f"Home: {scenario.name}\n\n"
        f"# Automation rules\n{rules}\n\n"
        f"Analyse rules {', '.join(rule_ids)} for conflicts."
    )


def graph_prompt(scenario: Scenario, rule_ids: list[str], graph_context: str) -> str:
    return (
        f"Home: {scenario.name}\n\n"
        f"{graph_context}\n\n"
        "The context above was retrieved from the home's knowledge graph. AFFECTS edges "
        "describe physical/causal effects that are not visible in the rule text; "
        "'reaches' lines show where a rule's action propagates.\n\n"
        f"Analyse rules {', '.join(rule_ids)} for conflicts."
    )
