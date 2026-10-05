"""Typed schema for smart-home scenario files (YAML).

A scenario describes one home: rooms, devices with their state attributes,
environmental/context variables, physical/causal effects between them,
Trigger-Condition-Action rules, and ground-truth evaluation cases.

Reference conventions used throughout:
  * device state      -> "<device_id>.<attribute>"   e.g. "lock_front.lock"
  * environment var   -> "<env_id>"                  e.g. "temp_living"
"""

from __future__ import annotations

from typing import Literal, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

ConflictType = Literal["logical", "semantic", "physical"]
Label = Literal["conflict", "clean"]
Scalar = Union[str, int, float, bool]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Device(_Strict):
    id: str
    type: str
    room: str
    description: str = ""
    # attribute -> allowed values (empty list = numeric / free value)
    states: dict[str, list[Scalar]]


class EnvVar(_Strict):
    id: str
    room: str
    kind: Literal["numeric", "boolean", "categorical"] = "numeric"
    description: str = ""
    values: list[Scalar] = Field(default_factory=list)


class Effect(_Strict):
    """A physical or environmental causal relation: when `source` takes
    `when`, `target` changes according to `effect` (and `value`)."""

    source: str  # device state ref
    when: Scalar
    target: str  # device state ref or env var
    effect: Literal["set", "increase", "decrease"]
    value: Scalar | None = None
    kind: Literal["physical", "environmental"]
    description: str = ""


class Trigger(_Strict):
    type: Literal["time", "state", "env"]
    at: str | None = None  # time trigger "HH:MM"
    ref: str | None = None
    op: Literal["==", "!=", ">", "<", ">=", "<="] = "=="
    value: Scalar | None = None

    @model_validator(mode="after")
    def _check(self) -> "Trigger":
        if self.type == "time" and not self.at:
            raise ValueError("time trigger requires 'at'")
        if self.type in ("state", "env") and (self.ref is None or self.value is None):
            raise ValueError(f"{self.type} trigger requires 'ref' and 'value'")
        return self


class Condition(_Strict):
    type: Literal["time_range", "state", "env"]
    start: str | None = None  # time_range
    end: str | None = None
    ref: str | None = None
    op: Literal["==", "!=", ">", "<", ">=", "<="] = "=="
    value: Scalar | None = None

    @model_validator(mode="after")
    def _check(self) -> "Condition":
        if self.type == "time_range" and not (self.start and self.end):
            raise ValueError("time_range condition requires 'start' and 'end'")
        if self.type in ("state", "env") and (self.ref is None or self.value is None):
            raise ValueError(f"{self.type} condition requires 'ref' and 'value'")
        return self


class Action(_Strict):
    ref: str  # device state ref
    value: Scalar


class Rule(_Strict):
    id: str
    text: str
    trigger: Trigger
    conditions: list[Condition] = Field(default_factory=list)
    actions: list[Action]


class Case(_Strict):
    id: str
    rules: list[str]
    label: Label
    type: ConflictType | None = None
    justification: str
    # graph nodes a correct explanation should mention (used as an automatic proxy check)
    key_nodes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check(self) -> "Case":
        if self.label == "conflict" and self.type is None:
            raise ValueError(f"case {self.id}: conflict cases need a 'type'")
        if self.label == "clean" and self.type is not None:
            raise ValueError(f"case {self.id}: clean cases must not have a 'type'")
        return self


class Scenario(_Strict):
    id: str
    name: str
    description: str = ""
    rooms: list[str]
    devices: list[Device]
    environment: list[EnvVar] = Field(default_factory=list)
    effects: list[Effect] = Field(default_factory=list)
    rules: list[Rule]
    cases: list[Case]

    # ---- lookups -------------------------------------------------------
    def rule(self, rule_id: str) -> Rule:
        for r in self.rules:
            if r.id == rule_id:
                return r
        raise KeyError(f"{self.id}: unknown rule {rule_id}")

    def device(self, device_id: str) -> Device:
        for d in self.devices:
            if d.id == device_id:
                return d
        raise KeyError(f"{self.id}: unknown device {device_id}")

    def state_refs(self) -> set[str]:
        return {f"{d.id}.{a}" for d in self.devices for a in d.states}

    def env_refs(self) -> set[str]:
        return {e.id for e in self.environment}

    # ---- referential integrity ----------------------------------------
    @model_validator(mode="after")
    def _check_refs(self) -> "Scenario":
        rooms = set(self.rooms)
        states = self.state_refs()
        envs = self.env_refs()
        anyref = states | envs
        errors: list[str] = []

        for d in self.devices:
            if d.room not in rooms:
                errors.append(f"device {d.id}: unknown room {d.room}")
        for e in self.environment:
            if e.room not in rooms:
                errors.append(f"env {e.id}: unknown room {e.room}")
        for ef in self.effects:
            if ef.source not in states:
                errors.append(f"effect source {ef.source} is not a device state")
            if ef.target not in anyref:
                errors.append(f"effect target {ef.target} unknown")
        rule_ids = [r.id for r in self.rules]
        if len(rule_ids) != len(set(rule_ids)):
            errors.append("duplicate rule ids")
        for r in self.rules:
            refs = [r.trigger.ref] + [c.ref for c in r.conditions]
            for ref in refs:
                if ref is not None and ref not in anyref:
                    errors.append(f"rule {r.id}: unknown ref {ref}")
            for a in r.actions:
                if a.ref not in states:
                    errors.append(f"rule {r.id}: action ref {a.ref} is not a device state")
        for c in self.cases:
            for rid in c.rules:
                if rid not in rule_ids:
                    errors.append(f"case {c.id}: unknown rule {rid}")
        if errors:
            raise ValueError(f"scenario {self.id}: " + "; ".join(errors))
        return self
