#!/usr/bin/env python3
"""Register pinned external capabilities and rebuild the loop capability lock."""

from __future__ import annotations

import argparse
import pathlib
import sys
import uuid
from typing import Any

from _loop_common import (
    LoopError,
    append_jsonl,
    atomic_json,
    file_identity,
    read_json,
    read_jsonl,
    require_loop,
    utc_now,
    validate_id,
)


KINDS = {"skill", "plugin", "mcp", "command", "service"}
TRUST = {"unreviewed", "reviewed", "approved", "blocked"}
FLOATING_REVISIONS = {"head", "main", "master", "latest", "stable", "develop", "development"}


def build_lock(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for event in events:
        identifier = event.get("capability_id")
        if isinstance(identifier, str):
            latest[identifier] = {
                "id": identifier,
                "kind": event.get("kind"),
                "source": event.get("source"),
                "revision": event.get("revision"),
                "license": event.get("license"),
                "invocation": event.get("invocation"),
                "input_contract": event.get("input_contract"),
                "output_contract": event.get("output_contract"),
                "trust": event.get("trust"),
                "reviewed_by": event.get("reviewed_by"),
                "accepted_risk": event.get("accepted_risk", False),
                "scan_status": event.get("scan_status"),
                "scan_tree_sha256": event.get("scan_tree_sha256"),
                "scan_report": event.get("scan_report"),
                "event_id": event.get("id"),
            }
    return [latest[key] for key in sorted(latest)]


def write_lock(loop: pathlib.Path, events: list[dict[str, Any]]) -> None:
    atomic_json(
        loop / "capability-lock.json",
        {
            "schema": "codex-science.capability-lock.v1",
            "updated_at": utc_now(),
            "capabilities": build_lock(events),
        },
    )


def command_register(args: argparse.Namespace) -> None:
    loop = require_loop(args.root)
    validate_id(args.id, "capability id")
    if args.kind not in KINDS:
        raise LoopError(f"unsupported capability kind: {args.kind}")
    if args.trust not in TRUST:
        raise LoopError(f"unsupported trust level: {args.trust}")
    revision = args.revision.strip()
    if not revision or revision.lower() in FLOATING_REVISIONS or "*" in revision:
        raise LoopError("revision must be immutable; floating branch names and wildcards are rejected")

    report_identity = None
    scan_status = None
    tree_sha = None
    if args.scan_report:
        report_path = args.scan_report.expanduser().resolve()
        report = read_json(report_path)
        if report.get("schema") != "codex-science.capability-scan.v1":
            raise LoopError("unsupported capability scan schema")
        scan_status = report.get("status")
        tree_sha = report.get("tree_sha256")
        report_identity = file_identity(report_path)
    if args.trust == "approved":
        if not args.reviewed_by:
            raise LoopError("approved capabilities require --reviewed-by")
        if scan_status not in ("pass", "review"):
            raise LoopError("approved capabilities require a non-blocked scan report")
        if scan_status == "review" and not args.accept_risk:
            raise LoopError("scan has warnings; approval requires --accept-risk")
    if scan_status == "block" and args.trust != "blocked":
        raise LoopError("a blocked scan may only be registered with trust=blocked")

    event = {
        "schema": "codex-science.capability-event.v1",
        "id": "CAPEV-" + uuid.uuid4().hex[:12],
        "capability_id": args.id,
        "kind": args.kind,
        "source": args.source,
        "revision": revision,
        "license": args.license,
        "invocation": args.invocation,
        "input_contract": args.input_contract,
        "output_contract": args.output_contract,
        "trust": args.trust,
        "reviewed_by": args.reviewed_by,
        "accepted_risk": bool(args.accept_risk),
        "scan_status": scan_status,
        "scan_tree_sha256": tree_sha,
        "scan_report": report_identity,
        "notes": args.notes,
        "created_at": utc_now(),
    }
    ledger = loop / "capabilities.jsonl"
    append_jsonl(ledger, event)
    events = read_jsonl(ledger)
    write_lock(loop, events)
    print(f"Registered capability {args.id}@{revision} trust={args.trust}")


def command_list(args: argparse.Namespace) -> None:
    loop = require_loop(args.root)
    lock = read_json(loop / "capability-lock.json")
    for item in lock.get("capabilities", []):
        if isinstance(item, dict):
            print(
                f"{item.get('id')}\t{item.get('kind')}\t{item.get('trust')}\t"
                f"{item.get('revision')}\t{item.get('invocation')}"
            )


def command_rebuild(args: argparse.Namespace) -> None:
    loop = require_loop(args.root)
    events = read_jsonl(loop / "capabilities.jsonl")
    write_lock(loop, events)
    print(f"Rebuilt capability lock from {len(events)} registry events")


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--root", type=pathlib.Path, required=True)
    sub = value.add_subparsers(dest="command", required=True)
    register = sub.add_parser("register")
    register.add_argument("--id", required=True)
    register.add_argument("--kind", choices=sorted(KINDS), required=True)
    register.add_argument("--source", required=True)
    register.add_argument("--revision", required=True)
    register.add_argument("--license", required=True)
    register.add_argument("--invocation", required=True)
    register.add_argument("--input-contract", default="Task-scoped inputs declared by the iteration plan")
    register.add_argument("--output-contract", default="Traceable files or structured output with explicit failure semantics")
    register.add_argument("--trust", choices=sorted(TRUST), default="unreviewed")
    register.add_argument("--scan-report", type=pathlib.Path)
    register.add_argument("--reviewed-by")
    register.add_argument("--accept-risk", action="store_true")
    register.add_argument("--notes", default="")
    register.set_defaults(func=command_register)
    listing = sub.add_parser("list")
    listing.set_defaults(func=command_list)
    rebuild = sub.add_parser("rebuild-lock")
    rebuild.set_defaults(func=command_rebuild)
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
