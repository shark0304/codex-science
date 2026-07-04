#!/usr/bin/env python3
"""Fork .science state into a new project root without overwriting data."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import shutil
import sys
import uuid


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=pathlib.Path, required=True)
    parser.add_argument("--destination", type=pathlib.Path, required=True)
    parser.add_argument("--reason", required=True)
    args = parser.parse_args()

    source_root = args.root.expanduser().resolve()
    source = source_root / ".science"
    destination_root = args.destination.expanduser().resolve()
    destination = destination_root / ".science"
    if not (source / "study.json").is_file():
        print(f"ERROR: source study is missing: {source}", file=sys.stderr)
        return 2
    if destination.exists():
        print(f"ERROR: destination study already exists: {destination}", file=sys.stderr)
        return 2
    destination_root.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination)

    created_at = dt.datetime.now(dt.timezone.utc).isoformat()
    source_study = json.loads((source / "study.json").read_text(encoding="utf-8"))
    fork_id = "F-" + uuid.uuid4().hex[:12]
    fork_record = {
        "id": fork_id,
        "created_at": created_at,
        "source_root": str(source_root),
        "destination_root": str(destination_root),
        "source_study_id": source_study.get("id"),
        "reason": args.reason,
        "scope": "Copied .science state only; project data and code must be versioned or copied separately.",
    }
    source_forks = source / "forks.jsonl"
    destination_forks = destination / "forks.jsonl"
    with source_forks.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(fork_record, ensure_ascii=False, sort_keys=True) + "\n")
    with destination_forks.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(fork_record, ensure_ascii=False, sort_keys=True) + "\n")

    source_id = str(source_study.get("id", "study"))
    source_study["id"] = f"{source_id}-fork-{fork_id[2:].lower()}"
    source_study["fork_of"] = source_id
    source_study["fork_record"] = fork_id
    source_study["forked_at"] = created_at
    (destination / "study.json").write_text(
        json.dumps(source_study, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with (destination / "LAB_NOTES.md").open("a", encoding="utf-8") as stream:
        stream.write(f"\n## {created_at}\n\n- Forked from `{source_id}`.\n- Reason: {args.reason}\n")
    print(f"Forked study state to {destination} ({fork_id})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
