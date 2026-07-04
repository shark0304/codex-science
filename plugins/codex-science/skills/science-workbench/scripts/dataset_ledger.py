#!/usr/bin/env python3
"""Register source and derived datasets with immutable lineage and SHA-256 identity."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import sys


ACCESS = ("public", "internal", "restricted", "unknown")


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def file_digest(path: pathlib.Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def path_identity(path: pathlib.Path) -> dict[str, object]:
    path = path.expanduser().resolve()
    if path.is_file():
        return {"path": str(path), "kind": "file", "sha256": file_digest(path), "bytes": path.stat().st_size}
    if not path.is_dir():
        raise ValueError(f"dataset path does not exist: {path}")
    digest = hashlib.sha256()
    files = 0
    total = 0
    for item in sorted(candidate for candidate in path.rglob("*") if candidate.is_file()):
        relative = item.relative_to(path).as_posix()
        item_hash = file_digest(item)
        size = item.stat().st_size
        digest.update(relative.encode("utf-8"))
        digest.update(item_hash.encode("ascii"))
        digest.update(str(size).encode("ascii"))
        files += 1
        total += size
    return {
        "path": str(path),
        "kind": "directory",
        "sha256": digest.hexdigest(),
        "bytes": total,
        "files": files,
    }


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
    source = sub.add_parser("register")
    source.add_argument("--id", required=True)
    source.add_argument("--location", default="")
    source.add_argument("--path", type=pathlib.Path)
    source.add_argument("--description", required=True)
    source.add_argument("--version", default="")
    source.add_argument("--license", default="unknown")
    source.add_argument("--access", choices=ACCESS, default="unknown")
    source.add_argument("--notes", default="")

    derived = sub.add_parser("derive")
    derived.add_argument("--id", required=True)
    derived.add_argument("--parent", action="append", required=True)
    derived.add_argument("--path", type=pathlib.Path, required=True)
    derived.add_argument("--description", required=True)
    derived.add_argument("--transformation", required=True)
    derived.add_argument("--command", required=True)
    derived.add_argument("--license", default="unknown")
    derived.add_argument("--access", choices=ACCESS, default="unknown")
    derived.add_argument("--notes", default="")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    ledger = args.root.expanduser().resolve() / ".science/datasets/registry.jsonl"
    try:
        if not ledger.is_file():
            raise FileNotFoundError(f"missing dataset ledger: {ledger}")
        records = read(ledger)
        ids = {record.get("id") for record in records}
        if args.id in ids:
            raise ValueError(f"duplicate dataset id: {args.id}")
        record: dict[str, object] = {
            "id": args.id,
            "record_type": "source" if args.command_name == "register" else "derived",
            "created_at": utc_now(),
            "description": args.description,
            "license": args.license,
            "access_class": args.access,
            "notes": args.notes,
        }
        if args.command_name == "register":
            if not args.location and not args.path:
                raise ValueError("register requires --location or --path")
            record["location"] = args.location or str(args.path.expanduser().resolve())
            record["version"] = args.version
            record["identity"] = path_identity(args.path) if args.path else None
        else:
            missing = [parent for parent in args.parent if parent not in ids]
            if missing:
                raise ValueError(f"unknown parent datasets: {', '.join(missing)}")
            record["parents"] = args.parent
            record["identity"] = path_identity(args.path)
            record["transformation"] = args.transformation
            record["command"] = args.command
        with ledger.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"Registered dataset {args.id} ({record['record_type']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
