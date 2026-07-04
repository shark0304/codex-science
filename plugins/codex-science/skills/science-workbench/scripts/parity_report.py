#!/usr/bin/env python3
"""Compare local capabilities with the public Claude Science feature boundary."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import shutil
import sys
import tempfile
from typing import Any


HERE = pathlib.Path(__file__).resolve().parent
WORKBENCH = HERE.parent
SKILLS = WORKBENCH.parent
SPEC_PATH = WORKBENCH / "assets/public-parity-v1.json"


class ParityError(ValueError):
    """A parity specification or project error."""


def read_json(path: pathlib.Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ParityError(f"invalid JSON at {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ParityError(f"JSON root must be an object: {path}")
    return value


def atomic_json(path: pathlib.Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        temporary = pathlib.Path(stream.name)
    temporary.replace(path)


def capability(
    source: dict[str, Any], status: str, evidence: list[str], gap: str
) -> dict[str, object]:
    return {
        "id": source["id"],
        "label": source["label"],
        "status": status,
        "public_description": source["public_description"],
        "evidence": evidence,
        "gap": gap,
    }


def build_report(root: pathlib.Path) -> dict[str, object]:
    root = root.expanduser().resolve()
    science = root / ".science"
    if not (science / "study.json").is_file():
        raise ParityError(f"initialize a Codex Science project first: {science}")
    spec = read_json(SPEC_PATH)
    if spec.get("schema") != "codex-science.public-parity.v1":
        raise ParityError("unsupported public parity specification")
    sources = {
        item["id"]: item
        for item in spec.get("capabilities", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    expected = {
        "single-research-environment",
        "auditable-artifact-history",
        "local-and-remote-access",
        "curated-scientific-ecosystem",
        "specialist-and-reviewer-agents",
        "native-rich-scientific-rendering",
        "managed-elastic-compute",
        "session-forking-and-memory",
        "custom-tools-and-pipelines",
    }
    if set(sources) != expected:
        raise ParityError("public parity specification has an incomplete capability set")
    bundled_skills = sorted(path.parent.name for path in SKILLS.glob("*/SKILL.md"))
    connectors = ("crossref", "pubmed", "openalex")
    ssh = shutil.which("ssh")
    slurm = shutil.which("sbatch")
    modal = shutil.which("modal")
    gpu = shutil.which("nvidia-smi")
    items = [
        capability(
            sources["single-research-environment"],
            "ready",
            ["unified science.py control entry", "profile-aware status and handoff", "self-contained research portal"],
            "Codex Science uses Codex plus local project files rather than Claude Science's proprietary application shell.",
        ),
        capability(
            sources["auditable-artifact-history"],
            "ready",
            ["SHA-256 artifact identities", "input and environment lineage", "append-oriented ledgers and validation"],
            "Scientific validity and exact reproduction still require the underlying code, environment, data access, and expert review.",
        ),
        capability(
            sources["local-and-remote-access"],
            "degraded",
            [f"ssh={'available' if ssh else 'unavailable'}", f"slurm={'available' if slurm else 'unavailable'}", "approval-aware compute ledger"],
            "The plugin records and validates remote work but does not itself provision, authenticate, or own an SSH/HPC session.",
        ),
        capability(
            sources["curated-scientific-ecosystem"],
            "degraded",
            [f"bundled_skills={len(bundled_skills)}", f"metadata_connectors={len(connectors)}", "pinned external capability registry"],
            "The public Claude Science description covers more than 60 curated skills/connectors and many domain databases; this plugin bundles a smaller general core.",
        ),
        capability(
            sources["specialist-and-reviewer-agents"],
            "degraded",
            ["specialist skill routing", "deterministic integrity audit", "adversarial reviewer protocol"],
            "Independent reviewer-agent status requires a fresh authorized context; it is not inferred from the current session.",
        ),
        capability(
            sources["native-rich-scientific-rendering"],
            "unavailable",
            ["static artifact lineage and visual-QA protocol", "HTML research portal"],
            "The plugin does not ship native molecular, protein, genome-track, or structure viewers; installed renderers and static fallbacks are required.",
        ),
        capability(
            sources["managed-elastic-compute"],
            "degraded",
            [f"modal={'available' if modal else 'unavailable'}", f"gpu={'available' if gpu else 'unavailable'}", "plan/approval/result event model"],
            "Job submission, monitoring, spend, credentials, and recovery remain controlled by authorized tools in the user's environment.",
        ),
        capability(
            sources["session-forking-and-memory"],
            "ready",
            ["LAB_NOTES.md", "RESUME.md context capsule", "provenance-preserving study forks", "Codex thread history"],
            "Thread-level memory and remote handoff depend on the active Codex deployment and user settings.",
        ),
        capability(
            sources["custom-tools-and-pipelines"],
            "ready",
            ["Codex skills and plugin packaging", "scanned pinned capability registry", "MCP/app connector compatibility"],
            "Every external capability still requires license, security, data-boundary, authentication, and scientific validation review.",
        ),
    ]
    counts = {status: sum(item["status"] == status for item in items) for status in ("ready", "degraded", "unavailable")}
    return {
        "schema": "codex-science.parity-report.v1",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "study_root": str(root),
        "source": spec["source"],
        "source_retrieved_at": spec["retrieved_at"],
        "counts": counts,
        "capabilities": items,
        "boundary": (
            "Public-feature conformance only. This report does not establish model-quality parity, "
            "benchmark parity, access to proprietary services, or complete product equivalence."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=pathlib.Path, required=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()
    try:
        report = build_report(args.root)
    except (ParityError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if args.save:
        atomic_json(args.root.expanduser().resolve() / ".science/PARITY.json", report)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        counts = report["counts"]
        print(f"Public parity: ready={counts['ready']} degraded={counts['degraded']} unavailable={counts['unavailable']}")
        for item in report["capabilities"]:
            print(f"{item['status']:11} {item['label']}")
        print(f"\nBoundary: {report['boundary']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
