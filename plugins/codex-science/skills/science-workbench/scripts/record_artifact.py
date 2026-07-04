#!/usr/bin/env python3
"""Hash and record a generated scientific artifact and its local inputs."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import platform
import sys
import uuid


def digest(path: pathlib.Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=pathlib.Path, required=True)
    parser.add_argument("--file", type=pathlib.Path, required=True)
    parser.add_argument("--kind", required=True)
    parser.add_argument("--command", default="")
    parser.add_argument("--input", type=pathlib.Path, action="append", default=[])
    parser.add_argument("--notes", default="")
    args = parser.parse_args()

    root = args.root.expanduser().resolve()
    manifest = root / ".science" / "artifacts" / "manifest.jsonl"
    artifact = args.file.expanduser().resolve()
    if not manifest.is_file():
        print(f"ERROR: missing manifest: {manifest}", file=sys.stderr)
        return 2
    if not artifact.is_file():
        print(f"ERROR: artifact is not a file: {artifact}", file=sys.stderr)
        return 2

    inputs = []
    for input_arg in args.input:
        path = input_arg.expanduser().resolve()
        if not path.is_file():
            print(f"ERROR: input is not a file: {path}", file=sys.stderr)
            return 2
        inputs.append({"path": str(path), "sha256": digest(path), "bytes": path.stat().st_size})

    record = {
        "id": "A-" + uuid.uuid4().hex[:12],
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "path": str(artifact),
        "kind": args.kind,
        "sha256": digest(artifact),
        "bytes": artifact.stat().st_size,
        "command": args.command,
        "inputs": inputs,
        "environment": {
            "platform": platform.platform(),
            "python": platform.python_version(),
        },
    }
    if args.notes:
        record["notes"] = args.notes
    with manifest.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"Recorded {record['id']} sha256={record['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
