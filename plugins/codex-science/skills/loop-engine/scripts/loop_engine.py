#!/usr/bin/env python3
"""Manage a bounded Codex Science plan-trace-eval-decision loop."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import Any

from _loop_common import (
    LoopError,
    append_jsonl,
    atomic_json,
    ensure_new,
    file_identity,
    latest_gate_evaluations,
    load_contract,
    load_lock,
    read_jsonl,
    require_loop,
    require_study,
    utc_now,
    validate_id,
)


TRACE_STATUSES = {"completed", "failed", "blocked", "cancelled"}
VERDICTS = {"pass", "fail", "error", "not-run"}
DECISIONS = {"continue", "succeed", "stop"}


def gate(value: str) -> tuple[str, str]:
    if ":" in value:
        identifier, description = value.split(":", 1)
    else:
        identifier, description = value, value
    identifier = re.sub(r"[^a-z0-9]+", "-", identifier.lower()).strip("-")
    if not identifier or not description.strip():
        raise argparse.ArgumentTypeError("gate must be ID:description")
    try:
        validate_id(identifier, "gate id")
    except LoopError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc
    return identifier, description.strip()


def paths(loop: pathlib.Path) -> dict[str, pathlib.Path]:
    return {
        "iterations": loop / "iterations.jsonl",
        "traces": loop / "traces.jsonl",
        "evaluations": loop / "evaluations.jsonl",
        "decisions": loop / "decisions.jsonl",
    }


def records(loop: pathlib.Path) -> dict[str, list[dict[str, Any]]]:
    return {name: read_jsonl(path) for name, path in paths(loop).items()}


def terminal_decision(decisions: list[dict[str, Any]]) -> dict[str, Any] | None:
    return next(
        (item for item in decisions if item.get("decision") in ("succeed", "stop")),
        None,
    )


def command_init(args: argparse.Namespace) -> None:
    science = require_study(args.root)
    loop = science / "loop"
    if loop.exists():
        raise LoopError(f"loop already exists; refusing to overwrite: {loop}")
    if args.max_iterations < 1:
        raise LoopError("max iterations must be at least 1")
    if args.stall_limit < 1:
        raise LoopError("stall limit must be at least 1")
    if not 0 <= args.min_progress <= 1:
        raise LoopError("minimum progress must be between 0 and 1")
    if args.budget_limit is not None and args.budget_limit <= 0:
        raise LoopError("budget limit must be positive")
    if args.budget_limit is not None and not args.budget_unit:
        raise LoopError("budget unit is required when budget limit is set")
    seen: set[str] = set()
    gates = []
    for identifier, description in args.gate:
        if identifier in seen:
            raise LoopError(f"duplicate gate id: {identifier}")
        seen.add(identifier)
        gates.append({"id": identifier, "description": description})
    loop.mkdir(parents=True)
    objective_slug = re.sub(r"[^a-z0-9]+", "-", args.objective.lower()).strip("-")
    contract: dict[str, object] = {
        "schema": "codex-science.loop-contract.v1",
        "id": "loop-" + (objective_slug[:48] or "study"),
        "objective": args.objective,
        "created_at": utc_now(),
        "required_gates": gates,
        "limits": {
            "max_iterations": args.max_iterations,
            "stall_limit": args.stall_limit,
            "min_progress": args.min_progress,
            "budget": {
                "unit": args.budget_unit,
                "limit": args.budget_limit,
            },
        },
        "authority": "Runtime permissions and external-action approvals remain separate.",
    }
    atomic_json(loop / "contract.json", contract)
    atomic_json(
        loop / "capability-lock.json",
        {
            "schema": "codex-science.capability-lock.v1",
            "updated_at": utc_now(),
            "capabilities": [],
        },
    )
    for name in (
        "capabilities.jsonl",
        "iterations.jsonl",
        "traces.jsonl",
        "evaluations.jsonl",
        "decisions.jsonl",
    ):
        (loop / name).write_text("", encoding="utf-8")
    (loop / "NEXT.md").write_text(
        "# Loop handoff\n\n"
        f"Status: `active`\n\nObjective: {args.objective}\n\n"
        "Next action: register any required capabilities, then plan iteration 1.\n",
        encoding="utf-8",
    )
    print(f"Initialized bounded loop at {loop}")


def command_plan(args: argparse.Namespace) -> None:
    loop = require_loop(args.root)
    contract = load_contract(loop)
    state = records(loop)
    validate_id(args.id, "iteration id")
    ensure_new(state["iterations"], args.id, "iteration")
    terminal = terminal_decision(state["decisions"])
    if terminal:
        raise LoopError(f"loop is closed by decision {terminal.get('id')}")
    if state["iterations"]:
        previous = state["iterations"][-1]
        previous_decision = next(
            (
                item
                for item in state["decisions"]
                if item.get("iteration_id") == previous.get("id")
            ),
            None,
        )
        if not previous_decision or previous_decision.get("decision") != "continue":
            raise LoopError("previous iteration must have a continue decision")
    sequence = len(state["iterations"]) + 1
    maximum = int(contract.get("limits", {}).get("max_iterations", 0))
    if sequence > maximum:
        raise LoopError(f"maximum iteration count reached: {maximum}")
    lock = load_lock(loop)
    for capability_id in args.capability:
        capability = lock.get(capability_id)
        if not capability:
            raise LoopError(f"capability is not locked: {capability_id}")
        if capability.get("trust") != "approved":
            raise LoopError(f"capability is not approved: {capability_id}")
    record = {
        "schema": "codex-science.loop-iteration.v1",
        "id": args.id,
        "sequence": sequence,
        "objective": args.objective,
        "capability_ids": args.capability,
        "inputs": [file_identity(value) for value in args.input],
        "created_at": utc_now(),
    }
    append_jsonl(paths(loop)["iterations"], record)
    print(f"Planned iteration {args.id} (sequence {sequence}/{maximum})")


def command_trace(args: argparse.Namespace) -> None:
    loop = require_loop(args.root)
    state = records(loop)
    validate_id(args.id, "trace id")
    ensure_new(state["traces"], args.id, "trace")
    if args.status not in TRACE_STATUSES:
        raise LoopError(f"invalid trace status: {args.status}")
    iteration = next(
        (item for item in state["iterations"] if item.get("id") == args.iteration), None
    )
    if not iteration:
        raise LoopError(f"unknown iteration: {args.iteration}")
    if any(item.get("iteration_id") == args.iteration for item in state["decisions"]):
        raise LoopError(f"iteration is already decided: {args.iteration}")
    planned = set(iteration.get("capability_ids", []))
    unexpected = sorted(set(args.capability) - planned)
    if unexpected:
        raise LoopError("trace used unplanned capabilities: " + ", ".join(unexpected))
    if args.cost < 0 or args.duration_seconds < 0:
        raise LoopError("cost and duration must be non-negative")
    record = {
        "schema": "codex-science.loop-trace.v1",
        "id": args.id,
        "iteration_id": args.iteration,
        "status": args.status,
        "summary": args.summary,
        "capability_ids": args.capability,
        "outputs": [file_identity(value) for value in args.output],
        "cost": args.cost,
        "duration_seconds": args.duration_seconds,
        "created_at": utc_now(),
    }
    append_jsonl(paths(loop)["traces"], record)
    print(f"Recorded trace {args.id} for {args.iteration}: {args.status}")


def command_evaluate(args: argparse.Namespace) -> None:
    loop = require_loop(args.root)
    contract = load_contract(loop)
    state = records(loop)
    validate_id(args.id, "evaluation id")
    ensure_new(state["evaluations"], args.id, "evaluation")
    if args.verdict not in VERDICTS:
        raise LoopError(f"invalid verdict: {args.verdict}")
    if args.score is not None and not 0 <= args.score <= 1:
        raise LoopError("evaluation score must be between 0 and 1")
    gates = {str(item.get("id")) for item in contract.get("required_gates", [])}
    if args.gate not in gates:
        raise LoopError(f"unknown required gate: {args.gate}")
    if not any(item.get("id") == args.iteration for item in state["iterations"]):
        raise LoopError(f"unknown iteration: {args.iteration}")
    if not any(item.get("iteration_id") == args.iteration for item in state["traces"]):
        raise LoopError("record at least one trace before evaluation")
    if any(item.get("iteration_id") == args.iteration for item in state["decisions"]):
        raise LoopError(f"iteration is already decided: {args.iteration}")
    record = {
        "schema": "codex-science.loop-evaluation.v1",
        "id": args.id,
        "iteration_id": args.iteration,
        "gate_id": args.gate,
        "verdict": args.verdict,
        "score": args.score,
        "summary": args.summary,
        "evidence": [file_identity(value) for value in args.evidence],
        "created_at": utc_now(),
    }
    append_jsonl(paths(loop)["evaluations"], record)
    print(f"Recorded {args.gate} evaluation {args.id}: {args.verdict}")


def total_cost(traces: list[dict[str, Any]]) -> float:
    return sum(float(item.get("cost", 0)) for item in traces)


def write_handoff(
    loop: pathlib.Path,
    contract: dict[str, Any],
    iteration: dict[str, Any],
    decision: dict[str, Any],
    evaluations: list[dict[str, Any]],
) -> None:
    latest = latest_gate_evaluations(evaluations, str(iteration["id"]))
    rows = []
    for item in contract.get("required_gates", []):
        identifier = str(item.get("id"))
        evaluation = latest.get(identifier, {})
        rows.append(
            f"- `{identifier}`: `{evaluation.get('verdict', 'not-evaluated')}` — "
            f"{evaluation.get('summary', '')}"
        )
    status = decision["decision"]
    next_action = decision.get("next_action") or "No further action recorded."
    text = (
        "# Loop handoff\n\n"
        f"Status: `{status}`  \nIteration: `{iteration['id']}`  \n"
        f"Objective: {contract.get('objective')}\n\n"
        "## Latest gate results\n\n"
        + "\n".join(rows)
        + "\n\n## Decision\n\n"
        + str(decision.get("reason"))
        + "\n\n## Next falsifiable action\n\n"
        + str(next_action)
        + "\n"
    )
    (loop / "NEXT.md").write_text(text, encoding="utf-8")


def command_decide(args: argparse.Namespace) -> None:
    loop = require_loop(args.root)
    contract = load_contract(loop)
    state = records(loop)
    validate_id(args.id, "decision id")
    ensure_new(state["decisions"], args.id, "decision")
    if args.decision not in DECISIONS:
        raise LoopError(f"invalid decision: {args.decision}")
    if not 0 <= args.progress <= 1:
        raise LoopError("progress must be between 0 and 1")
    iteration = next(
        (item for item in state["iterations"] if item.get("id") == args.iteration), None
    )
    if not iteration:
        raise LoopError(f"unknown iteration: {args.iteration}")
    if any(item.get("iteration_id") == args.iteration for item in state["decisions"]):
        raise LoopError(f"iteration is already decided: {args.iteration}")
    iteration_traces = [
        item for item in state["traces"] if item.get("iteration_id") == args.iteration
    ]
    if args.decision in ("continue", "succeed") and not iteration_traces:
        raise LoopError("continue and succeed require at least one trace")
    gates = [str(item.get("id")) for item in contract.get("required_gates", [])]
    latest = latest_gate_evaluations(state["evaluations"], args.iteration)
    if args.decision in ("continue", "succeed"):
        missing = [gate_id for gate_id in gates if gate_id not in latest]
        if missing:
            raise LoopError(
                "cannot decide without evaluations for gates: " + ", ".join(missing)
            )
    if args.decision == "succeed":
        failed = [gate_id for gate_id in gates if latest.get(gate_id, {}).get("verdict") != "pass"]
        if failed:
            raise LoopError("cannot succeed; gates are not passing: " + ", ".join(failed))
    limits = contract.get("limits", {})
    if args.decision == "continue":
        if not args.next_action:
            raise LoopError("continue requires a next action")
        maximum = int(limits.get("max_iterations", 0))
        if int(iteration.get("sequence", 0)) >= maximum:
            raise LoopError("cannot continue: maximum iteration count reached; record stop")
        budget = limits.get("budget", {})
        budget_limit = budget.get("limit") if isinstance(budget, dict) else None
        if budget_limit is not None and total_cost(state["traces"]) >= float(budget_limit):
            raise LoopError("cannot continue: budget limit reached; record stop")
        minimum = float(limits.get("min_progress", 0))
        stall_limit = int(limits.get("stall_limit", 1))
        stalled = 1 if args.progress < minimum else 0
        for previous in reversed(state["decisions"]):
            if previous.get("decision") != "continue":
                break
            if float(previous.get("progress", 0)) < minimum:
                stalled += 1
            else:
                break
        if stalled >= stall_limit:
            raise LoopError("cannot continue: consecutive low-progress limit reached; record stop")
    record = {
        "schema": "codex-science.loop-decision.v1",
        "id": args.id,
        "iteration_id": args.iteration,
        "decision": args.decision,
        "progress": args.progress,
        "reason": args.reason,
        "next_action": args.next_action,
        "created_at": utc_now(),
    }
    append_jsonl(paths(loop)["decisions"], record)
    write_handoff(loop, contract, iteration, record, state["evaluations"])
    print(f"Recorded decision {args.id}: {args.decision}")


def command_status(args: argparse.Namespace) -> None:
    loop = require_loop(args.root)
    contract = load_contract(loop)
    state = records(loop)
    terminal = terminal_decision(state["decisions"])
    current = state["iterations"][-1] if state["iterations"] else None
    latest = (
        latest_gate_evaluations(state["evaluations"], str(current["id"]))
        if current
        else {}
    )
    status = terminal.get("decision") if terminal else "active"
    summary = {
        "schema": "codex-science.loop-status.v1",
        "loop_id": contract.get("id"),
        "objective": contract.get("objective"),
        "status": status,
        "iterations": len(state["iterations"]),
        "current_iteration": current.get("id") if current else None,
        "total_cost": total_cost(state["traces"]),
        "gates": {
            identifier: evaluation.get("verdict") for identifier, evaluation in latest.items()
        },
        "terminal_decision": terminal.get("id") if terminal else None,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--root", type=pathlib.Path, required=True)
    sub = value.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="initialize a bounded loop")
    init.add_argument("--objective", required=True)
    init.add_argument("--gate", action="append", type=gate, required=True)
    init.add_argument("--max-iterations", type=int, default=8)
    init.add_argument("--stall-limit", type=int, default=2)
    init.add_argument("--min-progress", type=float, default=0.01)
    init.add_argument("--budget-unit")
    init.add_argument("--budget-limit", type=float)
    init.set_defaults(func=command_init)

    plan = sub.add_parser("plan", help="append an iteration plan")
    plan.add_argument("--id", required=True)
    plan.add_argument("--objective", required=True)
    plan.add_argument("--capability", action="append", default=[])
    plan.add_argument("--input", action="append", default=[])
    plan.set_defaults(func=command_plan)

    trace = sub.add_parser("trace", help="append an execution trace")
    trace.add_argument("--id", required=True)
    trace.add_argument("--iteration", required=True)
    trace.add_argument("--status", choices=sorted(TRACE_STATUSES), required=True)
    trace.add_argument("--summary", required=True)
    trace.add_argument("--capability", action="append", default=[])
    trace.add_argument("--output", action="append", default=[])
    trace.add_argument("--cost", type=float, default=0.0)
    trace.add_argument("--duration-seconds", type=float, default=0.0)
    trace.set_defaults(func=command_trace)

    evaluate = sub.add_parser("evaluate", help="append a gate evaluation")
    evaluate.add_argument("--id", required=True)
    evaluate.add_argument("--iteration", required=True)
    evaluate.add_argument("--gate", required=True)
    evaluate.add_argument("--verdict", choices=sorted(VERDICTS), required=True)
    evaluate.add_argument("--score", type=float)
    evaluate.add_argument("--summary", required=True)
    evaluate.add_argument("--evidence", action="append", default=[])
    evaluate.set_defaults(func=command_evaluate)

    decide = sub.add_parser("decide", help="append a loop decision")
    decide.add_argument("--id", required=True)
    decide.add_argument("--iteration", required=True)
    decide.add_argument("--decision", choices=sorted(DECISIONS), required=True)
    decide.add_argument("--progress", type=float, default=0.0)
    decide.add_argument("--reason", required=True)
    decide.add_argument("--next-action")
    decide.set_defaults(func=command_decide)

    status = sub.add_parser("status", help="print derived loop status")
    status.set_defaults(func=command_status)
    return value


def main() -> int:
    args = parser().parse_args()
    try:
        args.func(args)
    except LoopError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
