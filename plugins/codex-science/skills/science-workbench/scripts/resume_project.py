#!/usr/bin/env python3
"""Build a compact, cross-session research resume capsule."""

from __future__ import annotations

import argparse
import pathlib
import sys

from science import ScienceError, atomic_text, compute_status, read_json, read_jsonl, science_root


def tail_markdown(path: pathlib.Path, limit: int = 60) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    return "\n".join(lines[-limit:]).strip()


def build_resume(root: pathlib.Path) -> pathlib.Path:
    root = root.expanduser().resolve()
    science = science_root(root)
    status = compute_status(root, write=True)
    study = read_json(science / "study.json")
    counts = {
        "sources": len(read_jsonl(science / "evidence/sources.jsonl")),
        "searches": len(read_jsonl(science / "evidence/searches.jsonl")),
        "claims": len(read_jsonl(science / "evidence/claims.jsonl")),
        "datasets": len(read_jsonl(science / "datasets/registry.jsonl")),
        "experiment_events": len(read_jsonl(science / "experiments/registry.jsonl")),
        "compute_events": len(read_jsonl(science / "compute/jobs.jsonl")),
        "artifacts": len(read_jsonl(science / "artifacts/manifest.jsonl")),
    }
    actions = status.get("next_actions", [])
    action_lines = [
        f"- **{item.get('stage')}**: {item.get('action')}"
        for item in actions
        if isinstance(item, dict)
    ]
    loop_handoff = science / "loop/NEXT.md"
    loop_section = ""
    if loop_handoff.is_file():
        loop_section = "\n\n## Active loop handoff\n\n" + loop_handoff.read_text(encoding="utf-8").strip()
    audit_paths = sorted((science / "reviews").glob("audit-*.json"))
    latest_audit = str(audit_paths[-1]) if audit_paths else "not recorded"
    prompt = (
        "Use $science-workbench to resume the Codex Science study at "
        f"`{root}`. Read `.science/RESUME.md`, validate current project state, "
        "then continue the highest-value required action without claiming work that did not run."
    )
    content = (
        f"# Resume research: {study.get('title', 'Untitled study')}\n\n"
        f"Study ID: `{study.get('id', '')}`  \n"
        f"Profile: `{status.get('profile', '')}`  \n"
        f"Domain: `{status.get('domain', '')}`  \n"
        f"Recorded required coverage: **{status.get('required_ready', 0)}/{status.get('required_total', 0)} ({status.get('coverage_percent', 0)}%)**\n\n"
        "## Research question\n\n"
        f"{study.get('question', '')}\n\n"
        "## Recorded state\n\n"
        + "\n".join(f"- {name.replace('_', ' ')}: {value}" for name, value in counts.items())
        + f"\n- latest structural audit: `{latest_audit}`\n\n"
        "## Next required actions\n\n"
        + ("\n".join(action_lines) or "- No required coverage gap is recorded. Revalidate and obtain appropriate expert review before release.")
        + loop_section
        + "\n\n## Recent lab notes\n\n"
        + tail_markdown(science / "LAB_NOTES.md")
        + "\n\n## New-thread prompt\n\n"
        + prompt
        + "\n\n## Interpretation boundary\n\n"
        + str(status.get("boundary", ""))
        + "\n"
    )
    output = science / "RESUME.md"
    atomic_text(output, content)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        output = build_resume(args.root)
    except (ScienceError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"Built research resume at {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
