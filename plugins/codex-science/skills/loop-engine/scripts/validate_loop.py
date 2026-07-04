#!/usr/bin/env python3
"""Validate a Codex Science loop state, references, limits, and file identities."""

from __future__ import annotations

import argparse
import pathlib
import sys
from typing import Any

from _loop_common import (
    LoopError,
    latest_gate_evaluations,
    load_contract,
    read_json,
    read_jsonl,
    require_loop,
    validate_identity,
)
from scan_capability import inventory as scan_inventory
from scan_capability import tree_digest
from capability_registry import build_lock


def unique(records: list[dict[str, Any]], label: str, errors: list[str]) -> set[str]:
    identifiers: set[str] = set()
    for record in records:
        identifier = record.get("id")
        if not isinstance(identifier, str) or not identifier:
            errors.append(f"{label}: record missing id")
        elif identifier in identifiers:
            errors.append(f"{label}: duplicate id {identifier}")
        else:
            identifiers.add(identifier)
    return identifiers


def identities(values: object, label: str, errors: list[str]) -> None:
    if not isinstance(values, list):
        errors.append(f"{label}: identities must be a list")
        return
    for index, value in enumerate(values):
        validate_identity(value, f"{label}[{index}]", errors)


def require_text(record: dict[str, Any], key: str, label: str, errors: list[str]) -> None:
    if not isinstance(record.get(key), str) or not str(record[key]).strip():
        errors.append(f"{label}: missing non-empty {key}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        loop = require_loop(args.root)
        required = {
            "capabilities": loop / "capabilities.jsonl",
            "lock": loop / "capability-lock.json",
            "iterations": loop / "iterations.jsonl",
            "traces": loop / "traces.jsonl",
            "evaluations": loop / "evaluations.jsonl",
            "decisions": loop / "decisions.jsonl",
            "handoff": loop / "NEXT.md",
        }
        missing = [str(path) for path in required.values() if not path.is_file()]
        if missing:
            raise LoopError("missing loop files: " + ", ".join(missing))
        contract = load_contract(loop)
        capability_events = read_jsonl(required["capabilities"])
        lock_value = read_json(required["lock"])
        iterations = read_jsonl(required["iterations"])
        traces = read_jsonl(required["traces"])
        evaluations = read_jsonl(required["evaluations"])
        decisions = read_jsonl(required["decisions"])
    except LoopError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    errors: list[str] = []
    gates = contract.get("required_gates")
    if not isinstance(gates, list) or not gates:
        errors.append("contract: at least one required gate is needed")
        gates = []
    gate_ids = [str(item.get("id")) for item in gates if isinstance(item, dict)]
    if len(set(gate_ids)) != len(gate_ids):
        errors.append("contract: duplicate gate ids")
    limits = contract.get("limits")
    if not isinstance(limits, dict):
        errors.append("contract: limits must be an object")
        limits = {}
    maximum = int(limits.get("max_iterations", 0) or 0)
    stall_limit = int(limits.get("stall_limit", 0) or 0)
    minimum = float(limits.get("min_progress", 0) or 0)
    if maximum < 1 or stall_limit < 1 or not 0 <= minimum <= 1:
        errors.append("contract: invalid loop limits")

    unique(capability_events, "capability events", errors)
    iteration_ids = unique(iterations, "iterations", errors)
    unique(traces, "traces", errors)
    unique(evaluations, "evaluations", errors)
    unique(decisions, "decisions", errors)

    if lock_value.get("schema") != "codex-science.capability-lock.v1":
        errors.append("capability lock: invalid schema")
    lock_items = lock_value.get("capabilities")
    if not isinstance(lock_items, list):
        errors.append("capability lock: capabilities must be a list")
        lock_items = []
    locked: dict[str, dict[str, Any]] = {}
    if lock_items != build_lock(capability_events):
        errors.append("capability lock: entries do not match the append-only registry")
    for event in capability_events:
        identifier = str(event.get("id", "<unknown>"))
        if event.get("schema") != "codex-science.capability-event.v1":
            errors.append(f"capability event {identifier}: invalid schema")
        for key in ("capability_id", "kind", "source", "revision", "license", "invocation", "trust", "created_at"):
            require_text(event, key, f"capability event {identifier}", errors)
    for item in lock_items:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            errors.append("capability lock: invalid entry")
            continue
        identifier = str(item["id"])
        if identifier in locked:
            errors.append(f"capability lock: duplicate id {identifier}")
        locked[identifier] = item
        if item.get("trust") == "approved":
            if not item.get("reviewed_by"):
                errors.append(f"capability {identifier}: approved without reviewer")
            validate_identity(item.get("scan_report"), f"capability {identifier} scan", errors)
            if item.get("scan_status") not in ("pass", "review"):
                errors.append(f"capability {identifier}: approved with invalid scan status")
            if item.get("scan_status") == "review" and not item.get("accepted_risk"):
                errors.append(f"capability {identifier}: warnings were not accepted")
            report_identity = item.get("scan_report")
            if isinstance(report_identity, dict) and isinstance(report_identity.get("path"), str):
                try:
                    report_path = pathlib.Path(str(report_identity["path"]))
                    report = read_json(report_path)
                    if report.get("schema") != "codex-science.capability-scan.v1":
                        errors.append(f"capability {identifier}: invalid scan report schema")
                        continue
                    if report.get("status") != item.get("scan_status"):
                        errors.append(f"capability {identifier}: scan status differs from lock")
                    if report.get("tree_sha256") != item.get("scan_tree_sha256"):
                        errors.append(f"capability {identifier}: scan tree differs from lock")
                    scan_root = pathlib.Path(str(report.get("root", "")))
                    if not scan_root.is_dir():
                        errors.append(f"capability {identifier}: scanned checkout is unavailable")
                    else:
                        current_files, _ = scan_inventory(scan_root, report_path)
                        if tree_digest(current_files) != item.get("scan_tree_sha256"):
                            errors.append(f"capability {identifier}: scanned checkout changed after approval")
                except LoopError as exc:
                    errors.append(f"capability {identifier}: cannot verify scan report: {exc}")

    expected_sequences = list(range(1, len(iterations) + 1))
    actual_sequences = [item.get("sequence") for item in iterations]
    if actual_sequences != expected_sequences:
        errors.append("iterations: sequence numbers must be contiguous and ordered")
    if len(iterations) > maximum:
        errors.append("iterations: maximum count exceeded")
    for iteration in iterations:
        identifier = str(iteration.get("id"))
        if iteration.get("schema") != "codex-science.loop-iteration.v1":
            errors.append(f"iteration {identifier}: invalid schema")
        for key in ("objective", "created_at"):
            require_text(iteration, key, f"iteration {identifier}", errors)
        capabilities = iteration.get("capability_ids")
        if not isinstance(capabilities, list) or not all(
            isinstance(item, str) for item in capabilities
        ):
            errors.append(f"iteration {identifier}: capability_ids must be a list")
            capabilities = []
        for capability_id in capabilities:
            item = locked.get(str(capability_id))
            if not item:
                errors.append(f"iteration {identifier}: unknown capability {capability_id}")
            elif item.get("trust") != "approved":
                errors.append(f"iteration {identifier}: unapproved capability {capability_id}")
        identities(iteration.get("inputs"), f"iteration {identifier} inputs", errors)

    trace_iterations: set[str] = set()
    total_cost = 0.0
    for trace in traces:
        identifier = str(trace.get("id"))
        iteration_id = str(trace.get("iteration_id"))
        if trace.get("schema") != "codex-science.loop-trace.v1":
            errors.append(f"trace {identifier}: invalid schema")
        for key in ("summary", "created_at"):
            require_text(trace, key, f"trace {identifier}", errors)
        if iteration_id not in iteration_ids:
            errors.append(f"trace {identifier}: unknown iteration {iteration_id}")
        trace_iterations.add(iteration_id)
        used = trace.get("capability_ids")
        if not isinstance(used, list) or not all(isinstance(item, str) for item in used):
            errors.append(f"trace {identifier}: capability_ids must be a list")
            used = []
        iteration = next(
            (item for item in iterations if item.get("id") == iteration_id), {}
        )
        planned_values = iteration.get("capability_ids", []) if isinstance(iteration, dict) else []
        planned = (
            set(planned_values)
            if isinstance(planned_values, list)
            and all(isinstance(item, str) for item in planned_values)
            else set()
        )
        unexpected = sorted(str(item) for item in set(used) - planned)
        if unexpected:
            errors.append(f"trace {identifier}: unplanned capabilities {unexpected}")
        if trace.get("status") not in ("completed", "failed", "blocked", "cancelled"):
            errors.append(f"trace {identifier}: invalid status")
        cost = trace.get("cost")
        if not isinstance(cost, (int, float)) or cost < 0:
            errors.append(f"trace {identifier}: invalid cost")
        else:
            total_cost += float(cost)
        identities(trace.get("outputs"), f"trace {identifier} outputs", errors)

    for evaluation in evaluations:
        identifier = str(evaluation.get("id"))
        iteration_id = str(evaluation.get("iteration_id"))
        if evaluation.get("schema") != "codex-science.loop-evaluation.v1":
            errors.append(f"evaluation {identifier}: invalid schema")
        for key in ("summary", "created_at"):
            require_text(evaluation, key, f"evaluation {identifier}", errors)
        if iteration_id not in iteration_ids:
            errors.append(f"evaluation {identifier}: unknown iteration {iteration_id}")
        if iteration_id not in trace_iterations:
            errors.append(f"evaluation {identifier}: iteration has no trace")
        if evaluation.get("gate_id") not in gate_ids:
            errors.append(f"evaluation {identifier}: unknown gate")
        if evaluation.get("verdict") not in ("pass", "fail", "error", "not-run"):
            errors.append(f"evaluation {identifier}: invalid verdict")
        score = evaluation.get("score")
        if score is not None and (not isinstance(score, (int, float)) or not 0 <= score <= 1):
            errors.append(f"evaluation {identifier}: invalid score")
        identities(evaluation.get("evidence"), f"evaluation {identifier} evidence", errors)

    decisions_by_iteration: dict[str, dict[str, Any]] = {}
    terminal_sequence: int | None = None
    stalled = 0
    for decision in decisions:
        identifier = str(decision.get("id"))
        iteration_id = str(decision.get("iteration_id"))
        if decision.get("schema") != "codex-science.loop-decision.v1":
            errors.append(f"decision {identifier}: invalid schema")
        for key in ("reason", "created_at"):
            require_text(decision, key, f"decision {identifier}", errors)
        if iteration_id not in iteration_ids:
            errors.append(f"decision {identifier}: unknown iteration {iteration_id}")
            continue
        if iteration_id in decisions_by_iteration:
            errors.append(f"iteration {iteration_id}: multiple decisions")
        decisions_by_iteration[iteration_id] = decision
        action = decision.get("decision")
        if action not in ("continue", "succeed", "stop"):
            errors.append(f"decision {identifier}: invalid action")
        progress = decision.get("progress")
        if not isinstance(progress, (int, float)) or not 0 <= progress <= 1:
            errors.append(f"decision {identifier}: invalid progress")
            progress = 0
        iteration = next(item for item in iterations if item.get("id") == iteration_id)
        sequence = int(iteration.get("sequence", 0))
        if action in ("continue", "succeed") and iteration_id not in trace_iterations:
            errors.append(f"decision {identifier}: {action} requires a trace")
        latest = latest_gate_evaluations(evaluations, iteration_id)
        if action in ("continue", "succeed"):
            missing = [gate_id for gate_id in gate_ids if gate_id not in latest]
            if missing:
                errors.append(f"decision {identifier}: gates were not evaluated {missing}")
        if action == "continue":
            require_text(decision, "next_action", f"decision {identifier}", errors)
            if sequence >= maximum:
                errors.append(f"decision {identifier}: continues past maximum")
            stalled = stalled + 1 if float(progress) < minimum else 0
            if stalled >= stall_limit:
                errors.append(f"decision {identifier}: continues after stall limit")
        else:
            stalled = 0
        if action == "succeed":
            failed = [gate_id for gate_id in gate_ids if latest.get(gate_id, {}).get("verdict") != "pass"]
            if failed:
                errors.append(f"decision {identifier}: success with failing gates {failed}")
        if action in ("succeed", "stop"):
            if terminal_sequence is not None:
                errors.append("decisions: multiple terminal actions")
            terminal_sequence = sequence

    for index, iteration in enumerate(iterations[:-1]):
        decision = decisions_by_iteration.get(str(iteration.get("id")))
        if not decision or decision.get("decision") != "continue":
            errors.append(f"iteration {iteration.get('id')}: later work requires continue")
    if terminal_sequence is not None and any(
        int(item.get("sequence", 0)) > terminal_sequence for item in iterations
    ):
        errors.append("iterations: work exists after terminal decision")
    budget = limits.get("budget")
    if isinstance(budget, dict) and budget.get("limit") is not None:
        if total_cost > float(budget["limit"]):
            errors.append("traces: budget limit exceeded")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(
        "Codex Science loop validation: PASS "
        f"({len(locked)} capabilities, {len(iterations)} iterations, {len(traces)} traces, "
        f"{len(evaluations)} evaluations, {len(decisions)} decisions, cost={total_cost:g})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
