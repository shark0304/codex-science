#!/usr/bin/env python3
"""Initialize a non-destructive .science research control directory."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import re
import sys


PROFILE_STAGES = {
    "quick": {
        "framing": "required",
        "governance": "adaptive",
        "evidence": "required",
        "data": "adaptive",
        "protocol": "adaptive",
        "compute": "adaptive",
        "artifacts": "adaptive",
        "review": "adaptive",
        "iteration": "adaptive",
        "evaluation": "adaptive",
        "handoff": "required",
    },
    "standard": {
        "framing": "required",
        "governance": "required",
        "evidence": "required",
        "data": "required",
        "protocol": "required",
        "compute": "adaptive",
        "artifacts": "required",
        "review": "required",
        "iteration": "adaptive",
        "evaluation": "adaptive",
        "handoff": "required",
    },
    "deep": {
        "framing": "required",
        "governance": "required",
        "evidence": "required",
        "data": "required",
        "protocol": "required",
        "compute": "adaptive",
        "artifacts": "required",
        "review": "required",
        "iteration": "required",
        "evaluation": "adaptive",
        "handoff": "required",
    },
}


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:64] or "study"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=pathlib.Path, required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--question", required=True)
    parser.add_argument("--profile", choices=sorted(PROFILE_STAGES), default="standard")
    parser.add_argument("--domain", default="general")
    args = parser.parse_args()

    root = args.root.expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    science = root / ".science"
    if science.exists():
        print(f"ERROR: {science} already exists; refusing to overwrite", file=sys.stderr)
        return 2

    for relative in (
        "evidence/paper-cards",
        "evidence/snapshots",
        "datasets",
        "experiments",
        "compute",
        "artifacts",
        "reviews",
        "runs",
    ):
        (science / relative).mkdir(parents=True)

    created_at = utc_now()
    study = {
        "schema": "codex-science.study.v2",
        "id": slugify(args.title),
        "title": args.title,
        "question": args.question,
        "status": "draft",
        "created_at": created_at,
    }
    (science / "study.json").write_text(
        json.dumps(study, indent=2) + "\n", encoding="utf-8"
    )
    workflow = {
        "schema": "codex-science.workflow.v1",
        "profile": args.profile,
        "domain": args.domain.strip() or "general",
        "created_at": created_at,
        "updated_at": created_at,
        "stages": PROFILE_STAGES[args.profile],
        "boundary": (
            "Workflow coverage is navigation metadata; stage readiness does not establish "
            "scientific correctness, ethics approval, safety, novelty, or publication readiness."
        ),
    }
    (science / "workflow.json").write_text(
        json.dumps(workflow, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (science / "QUESTION.md").write_text(
        f"# Research question\n\n{args.question}\n\n"
        "## Scope\n\n- Population or system:\n- Intervention or exposure:\n"
        "- Comparator:\n- Outcomes:\n- Decision this informs:\n\n"
        "## Hypotheses and falsifiers\n\n- Confirmatory hypothesis:\n"
        "- Exploratory questions:\n- Evidence that would falsify the hypothesis:\n",
        encoding="utf-8",
    )
    (science / "PLAN.md").write_text(
        "# Study plan\n\n## Success criteria and test oracle\n\n"
        "## Data and evidence\n\n## Method\n\n## Controls and sensitivity checks\n\n"
        "## Compute and safety boundaries\n\n## Planned artifacts\n",
        encoding="utf-8",
    )
    (science / "GOVERNANCE.md").write_text(
        "# Governance and safety\n\n## Data classification and licenses\n\n"
        "## Human-subjects, clinical, wet-lab, or dual-use review\n\n"
        "## Compute budget and authorized targets\n\n## External actions requiring approval\n\n"
        "## Release and publication owner\n",
        encoding="utf-8",
    )
    (science / "LAB_NOTES.md").write_text(
        f"# Lab notes\n\n## {created_at}\n\n- Initialized study.\n"
        "- Next falsifiable action: define the success criterion and evidence plan.\n",
        encoding="utf-8",
    )
    for path in (
        science / "evidence/sources.jsonl",
        science / "evidence/claims.jsonl",
        science / "evidence/searches.jsonl",
        science / "datasets/registry.jsonl",
        science / "experiments/registry.jsonl",
        science / "compute/jobs.jsonl",
        science / "artifacts/manifest.jsonl",
        science / "forks.jsonl",
    ):
        path.write_text("", encoding="utf-8")
    (science / "capabilities.json").write_text(
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
    (science / "reviews/REVIEW.md").write_text(
        "# Independent review\n\n## Critical findings\n\n## Major findings\n\n"
        "## Minor findings\n\n## Reproduction status\n\n## Unresolved claims\n",
        encoding="utf-8",
    )
    print(f"Initialized Codex Science study at {science}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
