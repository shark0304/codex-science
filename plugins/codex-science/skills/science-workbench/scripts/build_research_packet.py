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
    connector_snapshot_paths = sorted((science / "evidence/snapshots").glob("*.json"))
    eval_score_paths = sorted((science / "evals").glob("*/scores.json"))
    workflow_path = science / "workflow.json"
    status_path = science / "STATUS.json"
    parity_path = science / "PARITY.json"
    resume_path = science / "RESUME.md"
    portal_path = science / "PORTAL.html"
    loop_paths: dict[str, pathlib.Path] = {}
    if (science / "loop/contract.json").is_file():
        loop_paths = {
            "loop_contract": science / "loop/contract.json",
            "loop_registry": science / "loop/capabilities.jsonl",
            "loop_capabilities": science / "loop/capability-lock.json",
            "loop_iterations": science / "loop/iterations.jsonl",
            "loop_traces": science / "loop/traces.jsonl",
            "loop_evaluations": science / "loop/evaluations.jsonl",
            "loop_decisions": science / "loop/decisions.jsonl",
            "loop_handoff": science / "loop/NEXT.md",
        }
    missing = [
        str(path)
        for name, path in paths.items()
        if not (path.is_dir() if name == "paper_cards" else path.is_file())
    ]
    if missing:
        print("ERROR: missing project files: " + ", ".join(missing), file=sys.stderr)
        return 2
    loop_missing = [str(path) for path in loop_paths.values() if not path.is_file()]
    if loop_missing:
        print("ERROR: incomplete loop state: " + ", ".join(loop_missing), file=sys.stderr)
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
        for search in searches:
            snapshot = search.get("snapshot")
            if isinstance(snapshot, dict) and isinstance(snapshot.get("path"), str):
                path = pathlib.Path(snapshot["path"])
                if path.is_file() and path not in connector_snapshot_paths:
                    connector_snapshot_paths.append(path)
        loop_contract = (
            json.loads(loop_paths["loop_contract"].read_text(encoding="utf-8"))
            if loop_paths
            else {}
        )
        loop_capabilities = (
            json.loads(loop_paths["loop_capabilities"].read_text(encoding="utf-8"))
            if loop_paths
            else {}
        )
        loop_iterations = read_jsonl(loop_paths["loop_iterations"]) if loop_paths else []
        loop_traces = read_jsonl(loop_paths["loop_traces"]) if loop_paths else []
        loop_evaluations = read_jsonl(loop_paths["loop_evaluations"]) if loop_paths else []
        loop_decisions = read_jsonl(loop_paths["loop_decisions"]) if loop_paths else []
        eval_summaries = [json.loads(path.read_text(encoding="utf-8")) for path in eval_score_paths]
        workflow = json.loads(workflow_path.read_text(encoding="utf-8")) if workflow_path.is_file() else {}
        workflow_status = json.loads(status_path.read_text(encoding="utf-8")) if status_path.is_file() else {}
        parity = json.loads(parity_path.read_text(encoding="utf-8")) if parity_path.is_file() else {}
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
    loop_sections = []
    if loop_paths:
        locked = loop_capabilities.get("capabilities", [])
        if not isinstance(locked, list):
            locked = []
        loop_sections = [
            "## Closed-loop improvement",
            f"Objective: {loop_contract.get('objective', '')}\n\n"
            + "Current handoff:\n\n"
            + loop_paths["loop_handoff"].read_text(encoding="utf-8"),
            "### Locked external capabilities",
            table(
                ["ID", "Kind", "Revision", "Trust", "Scan", "Invocation"],
                [
                    [item.get("id"), item.get("kind"), item.get("revision"), item.get("trust"), item.get("scan_status"), item.get("invocation")]
                    for item in locked
                    if isinstance(item, dict)
                ],
            ),
            "### Loop iterations and decisions",
            table(
                ["Iteration", "Sequence", "Objective", "Decision ID", "Decision", "Progress"],
                [
                    [
                        item.get("id"),
                        item.get("sequence"),
                        item.get("objective"),
                        next(
                            (decision.get("id") for decision in loop_decisions if decision.get("iteration_id") == item.get("id")),
                            "",
                        ),
                        next(
                            (decision.get("decision") for decision in loop_decisions if decision.get("iteration_id") == item.get("id")),
                            "open",
                        ),
                        next(
                            (decision.get("progress") for decision in loop_decisions if decision.get("iteration_id") == item.get("id")),
                            "",
                        ),
                    ]
                    for item in loop_iterations
                ],
            ),
            "### Loop traces",
            table(
                ["ID", "Iteration", "Status", "Capabilities", "Cost", "Summary"],
                [
                    [item.get("id"), item.get("iteration_id"), item.get("status"), item.get("capability_ids"), item.get("cost"), item.get("summary")]
                    for item in loop_traces
                ],
            ),
            "### Loop evaluations",
            table(
                ["ID", "Iteration", "Gate", "Verdict", "Score", "Summary"],
                [
                    [item.get("id"), item.get("iteration_id"), item.get("gate_id"), item.get("verdict"), item.get("score"), item.get("summary")]
                    for item in loop_evaluations
                ],
            ),
        ]
    eval_sections = []
    if eval_summaries:
        eval_sections = [
            "## Scientific-agent evaluations",
            table(
                ["System", "Model", "Suite", "Structural mean", "Pass rate", "Coverage"],
                [
                    [
                        item.get("system"),
                        item.get("model"),
                        item.get("suite_id"),
                        item.get("structural_mean"),
                        item.get("strict_pass_rate"),
                        f"{item.get('recorded_attempts')}/{item.get('expected_attempts')}",
                    ]
                    for item in eval_summaries
                    if isinstance(item, dict)
                ],
            ),
            "These transparent benchmark summaries measure research-process discipline; they do not establish overall scientific intelligence or product parity.",
        ]
    workflow_sections = []
    if workflow_status:
        workflow_sections = [
            "## Research workflow dashboard",
            f"Profile: `{workflow_status.get('profile', workflow.get('profile', ''))}`  \n"
            f"Domain: `{workflow_status.get('domain', workflow.get('domain', ''))}`  \n"
            f"Recorded required coverage: `{workflow_status.get('required_ready', 0)}/{workflow_status.get('required_total', 0)}`",
            table(
                ["Stage", "Requirement", "Status", "Recorded evidence", "Next action"],
                [
                    [item.get("label"), item.get("requirement"), item.get("status"), item.get("evidence"), item.get("next_action")]
                    for item in workflow_status.get("stages", [])
                    if isinstance(item, dict)
                ],
            ),
            str(workflow_status.get("boundary", "")),
        ]
    parity_sections = []
    if parity:
        parity_sections = [
            "## Public capability conformance",
            table(
                ["Capability", "Status", "Local evidence", "Remaining gap"],
                [
                    [item.get("label"), item.get("status"), item.get("evidence"), item.get("gap")]
                    for item in parity.get("capabilities", [])
                    if isinstance(item, dict)
                ],
            ),
            str(parity.get("boundary", "")),
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
        *workflow_sections,
        *parity_sections,
        "## Continuity and workspace views",
        f"Resume capsule: `{resume_path if resume_path.is_file() else 'not generated'}`  \n"
        f"Research portal: `{portal_path if portal_path.is_file() else 'not generated'}`",
        "## Search log",
        table(
            ["ID", "Database", "Query", "Selected", "Rejected", "Snapshot"],
            [[item.get("id"), item.get("database"), item.get("query"), item.get("selected_sources"), item.get("rejected_sources"), item.get("snapshot")] for item in searches],
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
        *loop_sections,
        *eval_sections,
        "## Independent review",
        paths["review"].read_text(encoding="utf-8"),
        "## Lab notes",
        paths["notes"].read_text(encoding="utf-8"),
        "## Interpretation boundary",
        "This packet assembles recorded evidence and provenance. It does not independently establish scientific correctness, novelty, safety, peer review, or external validity.",
    ]
    output.write_text("\n\n".join(sections) + "\n", encoding="utf-8")

    # Exclude the mutable artifact manifest from input hashes to avoid a self-reference cycle.
    loop_scan_paths = []
    if loop_paths:
        for item in loop_capabilities.get("capabilities", []):
            if not isinstance(item, dict):
                continue
            scan = item.get("scan_report")
            if isinstance(scan, dict) and isinstance(scan.get("path"), str):
                path = pathlib.Path(scan["path"])
                if path.is_file():
                    loop_scan_paths.append(path)
    eval_input_paths = []
    for scores_path in eval_score_paths:
        for name in ("run.json", "suite.json", "results.jsonl", "scores.json", "report.md"):
            path = scores_path.parent / name
            if path.is_file():
                eval_input_paths.append(path)
    workflow_input_paths = [
        path
        for path in (workflow_path, status_path, parity_path, resume_path, portal_path)
        if path.is_file()
    ]
    input_paths = [
        path for name, path in paths.items()
        if name not in ("manifest", "paper_cards")
    ] + workflow_input_paths + paper_card_paths + connector_snapshot_paths + list(loop_paths.values()) + loop_scan_paths + eval_input_paths
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
