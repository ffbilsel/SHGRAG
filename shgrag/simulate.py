"""Small deterministic execution simulator for a home's rules and effects.

Used to verify repairs: a hazard scenario must show the undesired outcome on
the original rules and must no longer show it after the repair, and intent
scenarios (what each rule is for) must still pass.

Semantics (one tick = one minute):
  * external events set variables at given clock times;
  * time-triggered rules fire when the clock equals `at`;
  * state/env-triggered rules are edge-triggered: they fire when their
    trigger predicate turns from false to true;
  * a rule fires only if its conditions hold at that moment;
  * `set` effects hold while their source has the `when` value. While one is
    active its target is forced to the effect value and rule writes to the
    target are deferred (they apply when the effect ends, e.g. a camera
    commanded to record while unpowered starts when power returns);
  * `increase`/`decrease` effects change a numeric target by a rate per tick,
    bounded by the scenario's dynamics (`rate`, `max`, `min`);
  * changes are propagated to a fixpoint within the tick (at most
    `MAX_FIRINGS_PER_TICK` rule firings, beyond which the tick is marked as
    oscillating).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .schema import Condition, Rule, Scenario, Trigger

MAX_FIRINGS_PER_TICK = 50


def _norm(v: object) -> object:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().lower()
    if s in ("true", "false"):
        return s == "true"
    try:
        return float(s)
    except ValueError:
        return s


def _minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _in_range(t: int, start: int, end: int) -> bool:
    return start <= t <= end if start <= end else (t >= start or t <= end)


def compare(a: object, op: str, b: object) -> bool:
    a, b = _norm(a), _norm(b)
    if op == "==":
        return a == b
    if op == "!=":
        return a != b
    if not (isinstance(a, float) and isinstance(b, float)):
        return False
    return {"<": a < b, ">": a > b, "<=": a <= b, ">=": a >= b}[op]


@dataclass
class Firing:
    tick: int
    clock: str
    rule: str
    writes: list[tuple[str, object]]
    cause: str  # "time", "event:<ref>", "rule:<id>", "effect:<src>", "dynamics:<ref>"


@dataclass
class Trace:
    states: list[dict]  # end-of-tick snapshot
    firings: list[Firing]
    writes: list[tuple[int, str, str, object]]  # (tick, rule, ref, value)
    blocked: list[tuple[int, str, str, object]]  # writes deferred by an active set effect
    oscillating_ticks: list[int] = field(default_factory=list)

    def ever(self, preds: list[dict]) -> bool:
        return any(all(_pred(st, p) for p in preds) for st in self.states)

    def at_end(self, preds: list[dict]) -> bool:
        return all(_pred(self.states[-1], p) for p in preds)

    def fired(self, rule_id: str) -> bool:
        return any(f.rule == rule_id for f in self.firings)

    def write_conflicts(self, ref: str | None = None, window: int = 2) -> list[tuple]:
        """Different rules writing different values to the same ref within `window` ticks."""
        out = []
        ws = [w for w in self.writes if ref is None or w[2] == ref]
        for i, (t1, r1, ref1, v1) in enumerate(ws):
            for t2, r2, ref2, v2 in ws[i + 1:]:
                if ref1 == ref2 and r1 != r2 and _norm(v1) != _norm(v2) and abs(t2 - t1) <= window:
                    out.append((t1, r1, t2, r2, ref1))
        return out


def _pred(state: dict, p: dict) -> bool:
    return compare(state.get(p["ref"]), p.get("op", "=="), p["value"])


class Simulator:
    def __init__(self, scenario: Scenario, dynamics: dict | None = None):
        self.s = scenario
        self.dynamics = dynamics or {}

    def _initial(self, init: dict) -> dict:
        st: dict = {}
        for d in self.s.devices:
            for a, vals in d.states.items():
                st[f"{d.id}.{a}"] = _norm(vals[0]) if vals else 0.0
        for e in self.s.environment:
            if e.kind == "boolean":
                st[e.id] = False
            elif e.kind == "categorical":
                st[e.id] = _norm(e.values[0]) if e.values else ""
            else:
                st[e.id] = 0.0
        for k, v in (init or {}).items():
            if k not in st:
                raise KeyError(f"{self.s.id}: unknown ref {k} in simulation init")
            st[k] = _norm(v)
        return st

    def _trig(self, t: Trigger, st: dict) -> bool:
        return compare(st.get(t.ref), t.op, t.value)

    def _conds(self, r: Rule, st: dict, clock: int) -> bool:
        for c in r.conditions:
            if c.type == "time_range":
                if not _in_range(clock, _minutes(c.start), _minutes(c.end)):
                    return False
            elif not compare(st.get(c.ref), c.op, c.value):
                return False
        return True

    def run(self, start: str, minutes: int, init: dict | None = None, events: list[dict] | None = None) -> Trace:
        st = self._initial(init or {})
        t0 = _minutes(start)
        events = events or []
        forced: dict[str, dict] = {}  # target -> {"effect": ef, "saved": value}
        trace = Trace(states=[], firings=[], writes=[], blocked=[])

        # effects active in the initial state hold from the start
        for ef in self.s.effects:
            if ef.effect == "set" and compare(st[ef.source], "==", ef.when):
                forced[ef.target] = {"effect": ef, "saved": st[ef.target]}
                st[ef.target] = _norm(ef.value)

        def set_var(ref: str, val: object, changes: list, who: str, tick: int, from_rule: str | None) -> None:
            val = _norm(val)
            if from_rule is not None:
                trace.writes.append((tick, from_rule, ref, val))
                if ref in forced:
                    forced[ref]["saved"] = val
                    trace.blocked.append((tick, from_rule, ref, val))
                    return
            if st.get(ref) != val:
                old = st.get(ref)
                st[ref] = val
                changes.append((ref, old, who))

        def propagate(changes: list, tick: int, clock: int) -> None:
            fired = 0
            while changes:
                ref, old, who = changes.pop(0)
                # set effects whose source changed
                for ef in self.s.effects:
                    if ef.effect != "set" or ef.source != ref:
                        continue
                    active = compare(st[ref], "==", ef.when)
                    if active and ef.target not in forced:
                        forced[ef.target] = {"effect": ef, "saved": st[ef.target]}
                        set_var(ef.target, ef.value, changes, f"effect:{ref}", tick, None)
                    elif not active and ef.target in forced and forced[ef.target]["effect"] is ef:
                        saved = forced.pop(ef.target)["saved"]
                        set_var(ef.target, saved, changes, f"effect:{ref}", tick, None)
                # edge-triggered rules
                prev = dict(st)
                prev[ref] = old
                for r in self.s.rules:
                    t = r.trigger
                    if t.type == "time" or t.ref != ref:
                        continue
                    if self._trig(t, st) and not self._trig(t, prev) and self._conds(r, st, clock):
                        fired += 1
                        if fired > MAX_FIRINGS_PER_TICK:
                            trace.oscillating_ticks.append(tick)
                            changes.clear()
                            return
                        self._fire(r, tick, clock, f"{who}", changes, set_var, trace)

        for m in range(minutes + 1):
            clock = (t0 + m) % 1440
            hhmm = f"{clock // 60:02d}:{clock % 60:02d}"
            changes: list = []
            for ev in events:
                if _minutes(ev["at"]) == clock and ev.get("tick", m) == m:
                    for k, v in ev["set"].items():
                        if k not in st:
                            raise KeyError(f"{self.s.id}: unknown ref {k} in simulation event")
                        set_var(k, v, changes, f"event:{k}", m, None)
            propagate(changes, m, clock)
            for r in self.s.rules:
                if r.trigger.type == "time" and _minutes(r.trigger.at) == clock and self._conds(r, st, clock):
                    self._fire(r, m, clock, "time", changes, set_var, trace)
            propagate(changes, m, clock)
            # continuous effects
            for ef in self.s.effects:
                if ef.effect in ("increase", "decrease") and compare(st[ef.source], "==", ef.when):
                    dyn = self.dynamics.get(ef.target, {})
                    rate = float(dyn.get("rate", 1.0))
                    cur = float(st[ef.target])
                    if ef.effect == "increase":
                        new = min(cur + rate, float(dyn["max"])) if "max" in dyn else cur + rate
                        new = max(new, cur)
                    else:
                        new = max(cur - rate, float(dyn["min"])) if "min" in dyn else cur - rate
                        new = min(new, cur)
                    set_var(ef.target, new, changes, f"dynamics:{ef.source}", m, None)
            propagate(changes, m, clock)
            snap = dict(st)
            snap["_clock"] = hhmm
            trace.states.append(snap)
        return trace

    def _fire(self, r: Rule, tick: int, clock: int, cause: str, changes: list, set_var, trace: Trace) -> None:
        hhmm = f"{clock // 60:02d}:{clock % 60:02d}"
        trace.firings.append(Firing(tick, hhmm, r.id, [(a.ref, a.value) for a in r.actions], cause))
        for a in r.actions:
            set_var(a.ref, a.value, changes, f"rule:{r.id}", tick, r.id)


# --------------------------------------------------------------------------
# Checks used by the repair verifier
# --------------------------------------------------------------------------


def check(scenario: Scenario, spec: dict, dynamics: dict | None = None) -> tuple[bool, str, Trace]:
    """Run one scenario spec and evaluate its expectation.

    spec keys: name, start, minutes, init, events, and one of
      ever: [preds]          some tick satisfies all predicates
      at_end: [preds]        the last tick satisfies all predicates
      write_conflict: ref    two rules write different values to ref within 2 ticks
      fires: rule_id         the rule fires at least once
    Returns (holds, description, trace)."""
    tr = Simulator(scenario, dynamics).run(spec["start"], spec["minutes"], spec.get("init"), spec.get("events"))
    if "ever" in spec:
        ok = tr.ever(spec["ever"])
        what = "ever " + " & ".join(f"{p['ref']} {p.get('op', '==')} {p['value']}" for p in spec["ever"])
    elif "at_end" in spec:
        ok = tr.at_end(spec["at_end"])
        what = "at end " + " & ".join(f"{p['ref']} {p.get('op', '==')} {p['value']}" for p in spec["at_end"])
    elif "write_conflict" in spec:
        ok = bool(tr.write_conflicts(spec["write_conflict"])) or bool(tr.oscillating_ticks)
        what = f"conflicting writes on {spec['write_conflict']}"
    elif "fires" in spec:
        ok = tr.fired(spec["fires"])
        what = f"{spec['fires']} fires"
    else:
        raise ValueError(f"spec {spec.get('name')} has no expectation")
    return ok, what, tr


def summarize_trace(tr: Trace, limit: int = 12) -> str:
    lines = [f"{f.clock} {f.rule} ({f.cause}) -> " + ", ".join(f"{r}={v}" for r, v in f.writes) for f in tr.firings[:limit]]
    if len(tr.firings) > limit:
        lines.append(f"... {len(tr.firings) - limit} more firings")
    if tr.blocked:
        lines.append("deferred by an active dependency: " + ", ".join(f"{r} {ref}={v}" for _, r, ref, v in tr.blocked[:5]))
    if tr.oscillating_ticks:
        lines.append(f"oscillation at ticks {tr.oscillating_ticks[:5]}")
    return "\n".join(lines)
