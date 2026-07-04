#!/usr/bin/env python3
"""Build and register a timestamped Markdown research handoff packet."""

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


def read_jsonl(path: pathlib.Path) -> list[dict[str, object]]:
    records = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{number}: record must be an object")
        records.append(value)
    return records


def cell(value: object) -> str:
    if isinstance(value, list):
        value = ", ".join(str(item) for item in value)
    if isinstance(value, dict):
        value = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value or "").replace("|", "\\|").replace("\n", " ")


def table(headers: list[str], rows: list[list[object]]) -> str:
    output = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    output.extend("| " + " | ".join(cell(item) for item in row) + " |" for row in rows)
    return "\n".join(output)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=pathlib.Path, required=True)
    args = parser.parse_args()
    root = args.root.expanduser().resolve()
    science = root / ".science"
    paths = {
        "study": science / "study.json",
        "question": science / "QUESTION.md",
        "plan": science / "PLAN.md",
        "governance": science / "GOVERNANCE.md",
        "notes": science / "LAB_NOTES.md",
        "capabilities": science / "capabilities.json",
        "sources": science / "evidence/sources.jsonl",
        "paper_cards": science / "evidence/paper-cards",
        "claims": science / "evidence/claims.jsonl",
        "searches": science / "evidence/searches.jsonl",
        "datasets": science / "datasets/registry.jsonl",
        "experiments": science / "experiments/registry.jsonl",
        "compute": science / "compute/jobs.jsonl",
        "manifest": science / "artifacts/manifest.jsonl",
        "review": science / "reviews/REVIEW.md",
        "forks": science / "forks.jsonl",
    }
    missing = [
        str(path)
        for name, path in paths.items()
        if not (path.is_dir() if name == "paper_cards" else path.is_file())
    ]
    if missing:
        print("ERROR: missing project files: " + ", ".join(missing), file=sys.stderr)
        return 2
    try:
        study = json.loads(paths["study"].read_text(encoding="utf-8"))
        capabilities = json.loads(paths["capabilities"].read_text(encoding="utf-8"))
        if not isinstance(study, dict) or not isinstance(capabilities, dict):
            raise ValueError("study and capabilities roots must be objects")
        sources = read_jsonl(paths["sources"])
        paper_card_paths = sorted(paths["paper_cards"].glob("*.json"))
        paper_cards = [json.loads(path.read_text(encoding="utf-8")) for path in paper_card_paths]
        claims = read_jsonl(paths["claims"])
        searches = read_jsonl(paths["searches"])
        datasets = read_jsonl(paths["datasets"])
        experiments = read_jsonl(paths["experiments"])
        compute = read_jsonl(paths["compute"])
        artifacts = read_jsonl(paths["manifest"])
        forks = read_jsonl(paths["forks"])
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    generated_at = dt.datetime.now(dt.timezone.utc).isoformat()
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = science / "artifacts" / f"research-packet-{stamp}-{uuid.uuid4().hex[:8]}.md"
    capability_rows = [
        [name, value.get("status"), value.get("evidence", []), value.get("note", "")]
        for name, value in capabilities.get("capabilities", {}).items()
        if isinstance(value, dict)
    ]
    sections = [
        f"# {study.get('title', 'Research packet')}",
        f"Generated: `{generated_at}`  \nStudy status: `{study.get('status', 'unknown')}`  \nStudy ID: `{study.get('id', 'unknown')}`",
        "## Research question and scope",
        paths["question"].read_text(encoding="utf-8"),
        "## Study plan",
        paths["plan"].read_text(encoding="utf-8"),
        "## Governance and safety",
        paths["governance"].read_text(encoding="utf-8"),
        "## Capability inventory",
        table(["Capability", "Status", "Evidence", "Note"], capability_rows),
        "## Search log",
        table(
            ["ID", "Database", "Query", "Selected", "Rejected"],
            [[item.get("id"), item.get("database"), item.get("query"), item.get("selected_sources"), item.get("rejected_sources")] for item in searches],
        ),
        "## Evidence sources",
        table(
            ["ID", "Title", "Location", "Retrieved"],
            [[item.get("id"), item.get("title"), item.get("location"), item.get("retrieved_at")] for item in sources],
        ),
        "## Claims",
        table(
            ["ID", "Status", "Claim", "Evidence"],
            [[item.get("id"), item.get("status"), item.get("text"), list(item.get("sources") or []) + list(item.get("experiments") or [])] for item in claims],
        ),
        "## Paper cards",
        table(
            ["ID", "Source", "Question", "Method", "Limitations"],
            [[item.get("id"), item.get("source_id"), item.get("question"), item.get("method"), item.get("limitations")] for item in paper_cards],
        ),
        "## Datasets and lineage",
        table(
            ["ID", "Type", "Description", "Parents", "Access", "Identity"],
            [[item.get("id"), item.get("record_type"), item.get("description"), item.get("parents", []), item.get("access_class"), item.get("identity")] for item in datasets],
        ),
        "## Experiment events",
        table(
            ["ID", "Type", "Parent", "Status or oracle"],
            [[item.get("id"), item.get("record_type"), item.get("parent_id"), item.get("status") or item.get("test_oracle")] for item in experiments],
        ),
        "## Compute events",
        table(
            ["ID", "Type", "Parent", "Backend", "Status", "Target"],
            [[item.get("id"), item.get("record_type"), item.get("parent_id"), item.get("backend"), item.get("status"), item.get("target")] for item in compute],
        ),
        "## Registered artifacts",
        table(
            ["ID", "Kind", "Path", "SHA-256"],
            [[item.get("id"), item.get("kind"), item.get("path"), item.get("sha256")] for item in artifacts],
        ),
        "## Fork history",
        table(
            ["ID", "Source", "Destination", "Reason"],
            [[item.get("id"), item.get("source_study_id"), item.get("destination_root"), item.get("reason")] for item in forks],
        ),
        "## Independent review",
        paths["review"].read_text(encoding="utf-8"),
        "## Lab notes",
        paths["notes"].read_text(encoding="utf-8"),
        "## Interpretation boundary",
        "This packet assembles recorded evidence and provenance. It does not independently establish scientific correctness, novelty, safety, peer review, or external validity.",
    ]
    output.write_text("\n\n".join(sections) + "\n", encoding="utf-8")

    # Exclude the mutable artifact manifest from input hashes to avoid a self-reference cycle.
    input_paths = [
        path for name, path in paths.items()
        if name not in ("manifest", "paper_cards")
    ] + paper_card_paths
    record = {
        "id": "A-" + uuid.uuid4().hex[:12],
        "created_at": generated_at,
        "path": str(output),
        "kind": "research-packet",
        "sha256": digest(output),
        "bytes": output.stat().st_size,
        "command": "build_research_packet.py",
        "inputs": [
            {
                "path": str(path),
                "sha256": digest(path),
                "bytes": path.stat().st_size,
                "mutable": True,
            }
            for path in input_paths
        ],
        "environment": {"platform": platform.platform(), "python": platform.python_version()},
    }
    with paths["manifest"].open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"Built research packet at {output}")
    print(f"Registered {record['id']} sha256={record['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
