#!/usr/bin/env python3
"""Append preregistered plans and immutable result events to an experiment ledger."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import sys


RESULT_STATUSES = ("passed", "failed", "error", "inconclusive")


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def digest(path: pathlib.Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def registry(root: pathlib.Path) -> pathlib.Path:
    path = root.expanduser().resolve() / ".science" / "experiments" / "registry.jsonl"
    if not path.is_file():
        raise FileNotFoundError(f"missing experiment registry: {path}")
    return path


def load(path: pathlib.Path) -> list[dict[str, object]]:
    records = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{number}: invalid JSON: {exc}") from exc
        if not isinstance(record, dict):
            raise ValueError(f"{path}:{number}: record must be a JSON object")
        records.append(record)
    return records


def parse_pairs(values: list[str]) -> dict[str, str]:
    result = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"parameter must use key=value: {value}")
        key, item = value.split("=", 1)
        if not key.strip():
            raise ValueError(f"parameter key is empty: {value}")
        result[key.strip()] = item
    return result


def file_records(values: list[pathlib.Path]) -> list[dict[str, object]]:
    result = []
    for value in values:
        path = value.expanduser().resolve()
        if not path.is_file():
            raise ValueError(f"not a file: {path}")
        result.append({"path": str(path), "sha256": digest(path), "bytes": path.stat().st_size})
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=pathlib.Path, required=True)
    sub = parser.add_subparsers(dest="command_name", required=True)

    plan = sub.add_parser("plan")
    plan.add_argument("--id", required=True)
    plan.add_argument("--objective", required=True)
    plan.add_argument("--oracle", required=True)
    plan.add_argument("--threshold", required=True)
    plan.add_argument("--command", default="")
    plan.add_argument("--input", type=pathlib.Path, action="append", default=[])
    plan.add_argument("--dataset", action="append", default=[])
    plan.add_argument("--parameter", action="append", default=[])
    plan.add_argument("--seed", action="append", default=[])
    plan.add_argument("--notes", default="")

    result = sub.add_parser("result")
    result.add_argument("--id", required=True)
    result.add_argument("--parent", required=True)
    result.add_argument("--status", choices=RESULT_STATUSES, required=True)
    result.add_argument("--exit-code", type=int)
    result.add_argument("--output", type=pathlib.Path, action="append", default=[])
    result.add_argument("--notes", default="")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        path = registry(args.root)
        records = load(path)
        ids = {record.get("id") for record in records}
        if args.id in ids:
            raise ValueError(f"duplicate experiment event id: {args.id}")

        if args.command_name == "plan":
            dataset_ledger = path.parent.parent / "datasets" / "registry.jsonl"
            dataset_ids = {
                record.get("id") for record in load(dataset_ledger)
            } if dataset_ledger.is_file() else set()
            missing_datasets = [item for item in args.dataset if item not in dataset_ids]
            if missing_datasets:
                raise ValueError(f"unknown datasets: {', '.join(missing_datasets)}")
            record: dict[str, object] = {
                "id": args.id,
                "record_type": "plan",
                "created_at": utc_now(),
                "objective": args.objective,
                "test_oracle": args.oracle,
                "acceptance_threshold": args.threshold,
                "command": args.command,
                "inputs": file_records(args.input),
                "datasets": args.dataset,
                "parameters": parse_pairs(args.parameter),
                "seeds": args.seed,
            }
        else:
            plans = {
                record.get("id") for record in records if record.get("record_type") == "plan"
            }
            if args.parent not in plans:
                raise ValueError(f"unknown parent plan: {args.parent}")
            record = {
                "id": args.id,
                "record_type": "result",
                "parent_id": args.parent,
                "created_at": utc_now(),
                "status": args.status,
                "exit_code": args.exit_code,
                "outputs": file_records(args.output),
            }
        if args.notes:
            record["notes"] = args.notes
        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"Appended experiment {record['record_type']} event {record['id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
