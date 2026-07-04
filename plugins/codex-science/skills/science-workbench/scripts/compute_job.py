#!/usr/bin/env python3
"""Record compute plans, user approvals, and results without executing jobs."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import sys


BACKENDS = ("local", "ssh", "slurm", "modal", "other")
RESULTS = ("completed", "failed", "cancelled", "timeout", "unknown")
DATA_CLASSES = ("public", "internal", "restricted", "unknown")


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def digest(path: pathlib.Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def file_record(value: pathlib.Path) -> dict[str, object]:
    path = value.expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"not a file: {path}")
    return {"path": str(path), "sha256": digest(path), "bytes": path.stat().st_size}


def parse_pairs(values: list[str]) -> dict[str, str]:
    result = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"resource must use key=value: {value}")
        key, item = value.split("=", 1)
        if not key.strip():
            raise ValueError(f"empty resource key: {value}")
        result[key.strip()] = item
    return result


def read(path: pathlib.Path) -> list[dict[str, object]]:
    records = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{number}: invalid JSON: {exc}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{number}: record must be an object")
        records.append(value)
    return records


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=pathlib.Path, required=True)
    sub = parser.add_subparsers(dest="command_name", required=True)

    plan = sub.add_parser("plan")
    plan.add_argument("--id", required=True)
    plan.add_argument("--backend", choices=BACKENDS, required=True)
    plan.add_argument("--target", required=True)
    plan.add_argument("--command", required=True)
    plan.add_argument("--resource", action="append", default=[])
    plan.add_argument("--data-class", choices=DATA_CLASSES, default="unknown")
    plan.add_argument("--cost-limit", default="")
    plan.add_argument("--time-limit", required=True)
    plan.add_argument("--stop-condition", required=True)
    plan.add_argument("--output-location", required=True)
    plan.add_argument("--requires-approval", action="store_true")
    plan.add_argument("--no-approval-required", action="store_true")
    plan.add_argument("--notes", default="")

    approval = sub.add_parser("approve")
    approval.add_argument("--id", required=True)
    approval.add_argument("--parent", required=True)
    approval.add_argument("--approved-by", required=True)
    approval.add_argument("--scope", required=True)
    approval.add_argument("--expires", default="")
    approval.add_argument("--notes", default="")

    result = sub.add_parser("result")
    result.add_argument("--id", required=True)
    result.add_argument("--parent", required=True)
    result.add_argument("--status", choices=RESULTS, required=True)
    result.add_argument("--exit-code", type=int)
    result.add_argument("--job-id", default="")
    result.add_argument("--log", type=pathlib.Path, action="append", default=[])
    result.add_argument("--output", type=pathlib.Path, action="append", default=[])
    result.add_argument("--notes", default="")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    path = args.root.expanduser().resolve() / ".science/compute/jobs.jsonl"
    try:
        if not path.is_file():
            raise FileNotFoundError(f"missing compute ledger: {path}")
        records = read(path)
        ids = {record.get("id") for record in records}
        if args.id in ids:
            raise ValueError(f"duplicate compute event id: {args.id}")
        plans = {
            str(record["id"]): record
            for record in records
            if record.get("record_type") == "plan" and isinstance(record.get("id"), str)
        }
        if args.command_name == "plan":
            if args.requires_approval and args.no_approval_required:
                raise ValueError("choose only one approval flag")
            default_approval = args.backend != "local" or args.data_class == "restricted"
            requires_approval = (
                True if args.requires_approval else False if args.no_approval_required else default_approval
            )
            record: dict[str, object] = {
                "id": args.id,
                "record_type": "plan",
                "created_at": utc_now(),
                "backend": args.backend,
                "target": args.target,
                "command": args.command,
                "resources": parse_pairs(args.resource),
                "data_class": args.data_class,
                "cost_limit": args.cost_limit,
                "time_limit": args.time_limit,
                "stop_condition": args.stop_condition,
                "output_location": args.output_location,
                "requires_approval": requires_approval,
            }
        elif args.command_name == "approve":
            if args.parent not in plans:
                raise ValueError(f"unknown compute plan: {args.parent}")
            record = {
                "id": args.id,
                "record_type": "approval",
                "parent_id": args.parent,
                "created_at": utc_now(),
                "approved_by": args.approved_by,
                "scope": args.scope,
                "expires": args.expires,
            }
        else:
            if args.parent not in plans:
                raise ValueError(f"unknown compute plan: {args.parent}")
            approvals = [
                item for item in records
                if item.get("record_type") == "approval" and item.get("parent_id") == args.parent
            ]
            if plans[args.parent].get("requires_approval") and not approvals:
                raise ValueError(f"compute plan {args.parent} requires an approval event")
            record = {
                "id": args.id,
                "record_type": "result",
                "parent_id": args.parent,
                "created_at": utc_now(),
                "status": args.status,
                "exit_code": args.exit_code,
                "job_id": args.job_id,
                "logs": [file_record(item) for item in args.log],
                "outputs": [file_record(item) for item in args.output],
            }
        if args.notes:
            record["notes"] = args.notes
        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"Appended compute {record['record_type']} event {record['id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
