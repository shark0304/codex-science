#!/usr/bin/env python3
"""Migrate a Codex Science v1 project to the append-only v2 layout."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import shutil
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=pathlib.Path, required=True)
    args = parser.parse_args()

    science = args.root.expanduser().resolve() / ".science"
    study_path = science / "study.json"
    if not study_path.is_file():
        print(f"ERROR: missing study file: {study_path}", file=sys.stderr)
        return 2
    try:
        study = json.loads(study_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"ERROR: invalid study.json: {exc}", file=sys.stderr)
        return 2
    if not isinstance(study, dict):
        print("ERROR: study.json must contain an object", file=sys.stderr)
        return 2
    schema = study.get("schema")
    if schema == "codex-science.study.v2":
        print("Project already uses codex-science.study.v2")
        return 0
    if schema != "codex-science.study.v1":
        print(f"ERROR: unsupported source schema: {schema!r}", file=sys.stderr)
        return 2

    backup = science / "study.v1.backup.json"
    if backup.exists():
        print(f"ERROR: migration backup already exists: {backup}", file=sys.stderr)
        return 2
    shutil.copy2(study_path, backup)
    for relative in (
        "evidence/paper-cards",
        "evidence/snapshots",
        "datasets",
        "compute",
        "artifacts",
        "reviews",
        "runs",
    ):
        (science / relative).mkdir(parents=True, exist_ok=True)
    for relative in (
        "evidence/searches.jsonl",
        "datasets/registry.jsonl",
        "compute/jobs.jsonl",
        "forks.jsonl",
    ):
        path = science / relative
        if not path.exists():
            path.write_text("", encoding="utf-8")
    governance = science / "GOVERNANCE.md"
    if not governance.exists():
        governance.write_text(
            "# Governance and safety\n\n## Data classification and licenses\n\n"
            "## Human-subjects, clinical, wet-lab, or dual-use review\n\n"
            "## Compute budget and authorized targets\n\n## External actions requiring approval\n\n"
            "## Release and publication owner\n",
            encoding="utf-8",
        )
    capabilities = science / "capabilities.json"
    if not capabilities.exists():
        capabilities.write_text(
            json.dumps(
                {
                    "schema": "codex-science.capabilities.v1",
                    "captured_at": None,
                    "capabilities": {},
                    "note": "Run capability_report.py before relying on optional tools.",
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    study["schema"] = "codex-science.study.v2"
    study["migrated_from"] = "codex-science.study.v1"
    study["migrated_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    study_path.write_text(json.dumps(study, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Migrated project to v2; backup preserved at {backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
