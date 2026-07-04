#!/usr/bin/env python3
"""Produce a deterministic structural and reproducibility audit of a v2 study."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
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
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            value = json.loads(line)
            if isinstance(value, dict):
                records.append(value)
    return records


def finding(
    severity: str, code: str, message: str, evidence: list[str], remediation: str
) -> dict[str, object]:
    return {
        "severity": severity,
        "code": code,
        "message": message,
        "evidence": evidence,
        "remediation": remediation,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=pathlib.Path, required=True)
    args = parser.parse_args()
    science = args.root.expanduser().resolve() / ".science"
    required = {
        "study": science / "study.json",
        "sources": science / "evidence/sources.jsonl",
        "paper_cards": science / "evidence/paper-cards",
        "claims": science / "evidence/claims.jsonl",
        "datasets": science / "datasets/registry.jsonl",
        "experiments": science / "experiments/registry.jsonl",
        "compute": science / "compute/jobs.jsonl",
        "artifacts": science / "artifacts/manifest.jsonl",
        "review": science / "reviews/REVIEW.md",
    }
    missing = [
        str(path)
        for name, path in required.items()
        if not (path.is_dir() if name == "paper_cards" else path.is_file())
    ]
    if missing:
        print("ERROR: missing project files: " + ", ".join(missing), file=sys.stderr)
        return 2
    try:
        study = json.loads(required["study"].read_text(encoding="utf-8"))
        sources = read_jsonl(required["sources"])
        paper_cards = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(required["paper_cards"].glob("*.json"))
        ]
        claims = read_jsonl(required["claims"])
        datasets = read_jsonl(required["datasets"])
        experiments = read_jsonl(required["experiments"])
        compute = read_jsonl(required["compute"])
        artifacts = read_jsonl(required["artifacts"])
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    findings: list[dict[str, object]] = []
    source_ids = {str(item.get("id")) for item in sources if item.get("id")}
    card_source_ids = {
        str(item.get("source_id")) for item in paper_cards if item.get("source_id")
    }
    referenced_sources: set[str] = set()
    for claim in claims:
        refs = claim.get("sources", [])
        if isinstance(refs, list):
            referenced_sources.update(str(source_id) for source_id in refs)
    for source_id in sorted(source_ids - referenced_sources):
        findings.append(
            finding(
                "note",
                "SOURCE_UNREFERENCED",
                f"Source {source_id} is not referenced by a claim.",
                [source_id],
                "Link it to a claim, mark it excluded/background, or remove it from the active synthesis.",
            )
        )
    for source in sources:
        if source.get("type") in ("paper", "preprint", "review") and str(source.get("id")) not in card_source_ids:
            findings.append(
                finding(
                    "note",
                    "PAPER_CARD_MISSING",
                    f"Literature source {source.get('id')} has no structured paper card.",
                    [str(source.get("id"))],
                    "Create a paper card for core evidence or mark the source as background/excluded.",
                )
            )

    for claim in claims:
        claim_id = str(claim.get("id", "<unknown>"))
        refs = claim.get("sources", [])
        experiments_refs = claim.get("experiments", [])
        if claim.get("status") not in ("hypothesis", "unsupported") and not refs and not experiments_refs:
            findings.append(
                finding(
                    "critical",
                    "CLAIM_WITHOUT_EVIDENCE",
                    f"Claim {claim_id} has no evidence reference.",
                    [claim_id],
                    "Attach source or experiment IDs, soften to a hypothesis, or mark unsupported.",
                )
            )
        if claim.get("status") == "conflicted":
            findings.append(
                finding(
                    "note",
                    "CLAIM_CONFLICTED",
                    f"Claim {claim_id} remains conflicted.",
                    [claim_id],
                    "Preserve both evidence lanes and define the next discriminating test.",
                )
            )

    dataset_ids = {str(item.get("id")) for item in datasets if item.get("id")}
    for dataset in datasets:
        if dataset.get("record_type") == "derived":
            missing_parents = [
                str(parent) for parent in dataset.get("parents", []) if str(parent) not in dataset_ids
            ]
            if missing_parents:
                findings.append(
                    finding(
                        "critical",
                        "DATASET_LINEAGE_BROKEN",
                        f"Dataset {dataset.get('id')} has unknown parents.",
                        missing_parents,
                        "Register every parent dataset and preserve transformation lineage.",
                    )
                )

    plan_ids = {
        str(item.get("id")) for item in experiments if item.get("record_type") == "plan"
    }
    result_parents = {
        str(item.get("parent_id")) for item in experiments if item.get("record_type") == "result"
    }
    for plan_id in sorted(plan_ids - result_parents):
        findings.append(
            finding(
                "note",
                "EXPERIMENT_PLAN_OPEN",
                f"Experiment plan {plan_id} has no result event.",
                [plan_id],
                "Run it, cancel it explicitly, or state why it remains open.",
            )
        )

    compute_plans = {
        str(item.get("id")): item for item in compute if item.get("record_type") == "plan"
    }
    approvals = {
        str(item.get("parent_id")) for item in compute if item.get("record_type") == "approval"
    }
    results = [item for item in compute if item.get("record_type") == "result"]
    for result in results:
        parent = str(result.get("parent_id"))
        if compute_plans.get(parent, {}).get("requires_approval") and parent not in approvals:
            findings.append(
                finding(
                    "critical",
                    "COMPUTE_APPROVAL_MISSING",
                    f"Compute result {result.get('id')} has no required approval event.",
                    [parent, str(result.get("id"))],
                    "Do not rely on the run; document authorization and governance review.",
                )
            )

    for artifact in artifacts:
        path_value = artifact.get("path")
        expected = artifact.get("sha256")
        artifact_id = str(artifact.get("id", "<unknown>"))
        if not isinstance(path_value, str) or not pathlib.Path(path_value).is_file():
            findings.append(
                finding(
                    "major",
                    "ARTIFACT_UNAVAILABLE",
                    f"Artifact {artifact_id} cannot be read locally.",
                    [str(path_value)],
                    "Restore the artifact or validate on the system that owns it.",
                )
            )
        elif digest(pathlib.Path(path_value)) != expected:
            findings.append(
                finding(
                    "critical",
                    "ARTIFACT_HASH_MISMATCH",
                    f"Artifact {artifact_id} changed after registration.",
                    [path_value],
                    "Regenerate or register a new immutable artifact event; do not rewrite history.",
                )
            )

    review_text = required["review"].read_text(encoding="utf-8")
    if study.get("status") == "complete" and len(review_text.split()) < 25:
        findings.append(
            finding(
                "major",
                "REVIEW_INCOMPLETE",
                "Study is marked complete but independent review is effectively empty.",
                [str(required["review"])],
                "Complete an adversarial review and preserve unresolved findings.",
            )
        )

    counts = {severity: 0 for severity in ("critical", "major", "minor", "note")}
    for item in findings:
        counts[str(item["severity"])] += 1
    status = "fail" if counts["critical"] else "warn" if counts["major"] else "pass"
    captured_at = dt.datetime.now(dt.timezone.utc).isoformat()
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report = {
        "schema": "codex-science.audit.v1",
        "captured_at": captured_at,
        "study_id": study.get("id"),
        "status": status,
        "counts": counts,
        "findings": findings,
        "boundary": "Deterministic audit only; scientific correctness requires expert review and reproduction.",
    }
    report_path = science / "reviews" / f"audit-{stamp}-{uuid.uuid4().hex[:8]}.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "counts": counts, "report": str(report_path)}))
    return 1 if counts["critical"] or counts["major"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
