#!/usr/bin/env python3
"""Unified entry point for the Codex Science research workbench."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import platform
import shutil
import subprocess
import sys
import tempfile
import uuid
from typing import Any


HERE = pathlib.Path(__file__).resolve().parent
WORKBENCH = HERE.parent
SKILLS = WORKBENCH.parent
CATALOG_PATH = WORKBENCH / "assets/service-catalog-v1.json"
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
STAGE_LABELS = {
    "framing": "Question and success criteria",
    "governance": "Governance and approval boundaries",
    "evidence": "Literature and claim evidence",
    "data": "Dataset identity and lineage",
    "protocol": "Preregistered protocol",
    "compute": "Bounded compute",
    "artifacts": "Reproducible artifacts",
    "review": "Audit and scientific review",
    "iteration": "Bounded improvement loop",
    "evaluation": "Scientific-agent evaluation",
    "handoff": "Research handoff packet",
}
NEXT_ACTIONS = {
    "framing": "Complete QUESTION.md scope/falsifier fields and PLAN.md success criteria.",
    "governance": "Record data classification, approvals, safety boundaries, and release ownership in GOVERNANCE.md.",
    "evidence": "Run a logged search, screen sources, and bind at least one claim to evidence.",
    "data": "Register the source dataset and preserve version, access, license, and identity.",
    "protocol": "Append an experiment plan with oracle, threshold, inputs, controls, and stop conditions before outcomes.",
    "compute": "Record a bounded compute plan and any required approval before recording results.",
    "artifacts": "Create and register a code-backed figure, table, notebook, report, or manuscript.",
    "review": "Run the deterministic audit and complete an adversarial review in reviews/REVIEW.md.",
    "iteration": "Initialize a bounded loop with frozen gates, then record a valid terminal decision.",
    "evaluation": "Initialize, record, grade, and validate a versioned scientific-agent eval run.",
    "handoff": "Run the handoff command to refresh status, validate, audit, and build a research packet.",
}
TOOL_EXECUTABLES = {
    "git": "git",
    "python": "python3",
    "jupyter": "jupyter",
    "r": "R",
    "julia": "julia",
    "pandoc": "pandoc",
    "quarto": "quarto",
    "latex": "latexmk",
    "docker": "docker",
    "ssh": "ssh",
    "slurm": "sbatch",
    "modal": "modal",
    "gpu": "nvidia-smi",
}
SECRET_ENVIRONMENT = (
    "CROSSREF_MAILTO",
    "NCBI_EMAIL",
    "NCBI_API_KEY",
    "OPENALEX_API_KEY",
)


class ScienceError(ValueError):
    """A unified-workbench input or project-state error."""


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def atomic_json(path: pathlib.Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        temporary = pathlib.Path(stream.name)
    temporary.replace(path)


def atomic_text(path: pathlib.Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as stream:
        stream.write(value)
        temporary = pathlib.Path(stream.name)
    temporary.replace(path)


def read_json(path: pathlib.Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ScienceError(f"invalid JSON at {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ScienceError(f"JSON root must be an object: {path}")
    return value


def read_jsonl(path: pathlib.Path) -> list[dict[str, Any]]:
    records = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ScienceError(f"cannot read {path}: {exc}") from exc
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ScienceError(f"{path}:{number}: invalid JSON: {exc}") from exc
        if not isinstance(value, dict):
            raise ScienceError(f"{path}:{number}: record must be an object")
        records.append(value)
    return records


def science_root(root: pathlib.Path) -> pathlib.Path:
    science = root.expanduser().resolve() / ".science"
    if not (science / "study.json").is_file():
        raise ScienceError(f"initialize a Codex Science project first: {science}")
    return science


def load_catalog() -> dict[str, Any]:
    catalog = read_json(CATALOG_PATH)
    if catalog.get("schema") != "codex-science.service-catalog.v1":
        raise ScienceError("unsupported service catalog schema")
    return catalog


def default_workflow(profile: str, domain: str, created_at: str | None = None) -> dict[str, object]:
    timestamp = created_at or utc_now()
    return {
        "schema": "codex-science.workflow.v1",
        "profile": profile,
        "domain": domain.strip() or "general",
        "created_at": timestamp,
        "updated_at": timestamp,
        "stages": dict(PROFILE_STAGES[profile]),
        "boundary": (
            "Workflow coverage is navigation metadata; stage readiness does not establish "
            "scientific correctness, ethics approval, safety, novelty, or publication readiness."
        ),
    }


def load_workflow(science: pathlib.Path) -> dict[str, Any]:
    path = science / "workflow.json"
    if not path.is_file():
        return default_workflow("standard", "general")
    workflow = read_json(path)
    if workflow.get("schema") != "codex-science.workflow.v1":
        raise ScienceError("unsupported workflow schema")
    return workflow


def section_has_content(path: pathlib.Path, heading: str) -> bool:
    lines = path.read_text(encoding="utf-8").splitlines()
    active = False
    for raw in lines:
        line = raw.strip()
        if line.startswith("## "):
            if active:
                return False
            active = line[3:].strip() == heading
            continue
        if not active or not line or line.startswith("#"):
            continue
        value = line.lstrip("-* ").strip()
        if not value:
            continue
        if ":" in value:
            if value.split(":", 1)[1].strip():
                return True
        elif value:
            return True
    return False


def document_has_content(path: pathlib.Path) -> bool:
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        value = line.lstrip("-* ").strip()
        if not value:
            continue
        if ":" not in value or value.split(":", 1)[1].strip():
            return True
    return False


def stage(
    identifier: str,
    requirement: str,
    ready: bool,
    started: bool,
    evidence: list[str],
) -> dict[str, object]:
    if ready:
        status = "ready"
    elif started:
        status = "in-progress"
    elif requirement == "not-requested":
        status = "not-requested"
    else:
        status = "not-started"
    return {
        "id": identifier,
        "label": STAGE_LABELS[identifier],
        "requirement": requirement,
        "status": status,
        "evidence": evidence,
        "next_action": "" if status in ("ready", "not-requested") else NEXT_ACTIONS[identifier],
    }


def compute_status(root: pathlib.Path, write: bool = True) -> dict[str, object]:
    science = science_root(root)
    study = read_json(science / "study.json")
    workflow = load_workflow(science)
    requirements = workflow.get("stages")
    if not isinstance(requirements, dict):
        raise ScienceError("workflow stages must be an object")
    sources = read_jsonl(science / "evidence/sources.jsonl")
    searches = read_jsonl(science / "evidence/searches.jsonl")
    claims = read_jsonl(science / "evidence/claims.jsonl")
    datasets = read_jsonl(science / "datasets/registry.jsonl")
    experiments = read_jsonl(science / "experiments/registry.jsonl")
    compute = read_jsonl(science / "compute/jobs.jsonl")
    artifacts = read_jsonl(science / "artifacts/manifest.jsonl")
    experiment_plans = [item for item in experiments if item.get("record_type") == "plan"]
    experiment_results = [item for item in experiments if item.get("record_type") == "result"]
    compute_plans = [item for item in compute if item.get("record_type") == "plan"]
    compute_results = [item for item in compute if item.get("record_type") == "result"]
    result_parents = {str(item.get("parent_id")) for item in compute_results}
    research_artifacts = [item for item in artifacts if item.get("kind") != "research-packet"]
    packets = [item for item in artifacts if item.get("kind") == "research-packet"]
    audits = sorted((science / "reviews").glob("audit-*.json"))
    evals = sorted((science / "evals").glob("*/scores.json"))
    decisions = (
        read_jsonl(science / "loop/decisions.jsonl")
        if (science / "loop/decisions.jsonl").is_file()
        else []
    )
    loop_ready = bool(decisions and decisions[-1].get("decision") in ("succeed", "stop"))
    framing_ready = section_has_content(science / "QUESTION.md", "Scope") and section_has_content(
        science / "PLAN.md", "Success criteria and test oracle"
    )
    governance_ready = section_has_content(
        science / "GOVERNANCE.md", "Data classification and licenses"
    ) and section_has_content(
        science / "GOVERNANCE.md", "External actions requiring approval"
    )
    evidence_ready = bool(sources and searches and claims)
    review_text_ready = document_has_content(science / "reviews/REVIEW.md")
    stages = [
        stage("framing", str(requirements.get("framing", "adaptive")), framing_ready, True, [f"question={bool(study.get('question'))}", f"framing_fields={framing_ready}"]),
        stage("governance", str(requirements.get("governance", "adaptive")), governance_ready, governance_ready, [f"governance_fields={governance_ready}"]),
        stage("evidence", str(requirements.get("evidence", "adaptive")), evidence_ready, bool(sources or searches or claims), [f"sources={len(sources)}", f"searches={len(searches)}", f"claims={len(claims)}"]),
        stage("data", str(requirements.get("data", "adaptive")), bool(datasets), bool(datasets), [f"datasets={len(datasets)}"]),
        stage("protocol", str(requirements.get("protocol", "adaptive")), bool(experiment_plans), bool(experiments), [f"plans={len(experiment_plans)}", f"results={len(experiment_results)}"]),
        stage("compute", str(requirements.get("compute", "adaptive")), bool(compute_plans) and all(str(item.get("id")) in result_parents for item in compute_plans), bool(compute), [f"plans={len(compute_plans)}", f"results={len(compute_results)}"]),
        stage("artifacts", str(requirements.get("artifacts", "adaptive")), bool(research_artifacts), bool(research_artifacts), [f"research_artifacts={len(research_artifacts)}"]),
        stage("review", str(requirements.get("review", "adaptive")), bool(audits) and review_text_ready, bool(audits) or review_text_ready, [f"audits={len(audits)}", f"review_content={review_text_ready}"]),
        stage("iteration", str(requirements.get("iteration", "adaptive")), loop_ready, (science / "loop/contract.json").is_file(), [f"terminal_decision={loop_ready}", f"decisions={len(decisions)}"]),
        stage("evaluation", str(requirements.get("evaluation", "adaptive")), bool(evals), bool(evals), [f"validated_score_files={len(evals)}"]),
        stage("handoff", str(requirements.get("handoff", "adaptive")), bool(packets), bool(packets), [f"research_packets={len(packets)}"]),
    ]
    required = [item for item in stages if item["requirement"] == "required"]
    required_ready = [item for item in required if item["status"] == "ready"]
    next_actions = [
        {"stage": item["id"], "action": item["next_action"]}
        for item in stages
        if item["requirement"] == "required" and item["status"] != "ready"
    ]
    report = {
        "schema": "codex-science.status.v1",
        "generated_at": utc_now(),
        "study_id": study.get("id"),
        "title": study.get("title"),
        "profile": workflow.get("profile", "standard"),
        "domain": workflow.get("domain", "general"),
        "required_ready": len(required_ready),
        "required_total": len(required),
        "coverage_percent": round(100 * len(required_ready) / len(required), 1) if required else 100.0,
        "stages": stages,
        "next_actions": next_actions,
        "boundary": (
            "Coverage reflects recorded workflow state only. It is not a scientific-quality score, "
            "ethics approval, safety determination, expert review, or publication decision."
        ),
    }
    if write:
        atomic_json(science / "STATUS.json", report)
        rows = [
            f"| {item['label']} | {item['requirement']} | {item['status']} | {', '.join(str(value) for value in item['evidence'])} |"
            for item in stages
        ]
        markdown = (
            f"# Research workflow status\n\nGenerated: `{report['generated_at']}`  \n"
            f"Profile: `{report['profile']}`  \nDomain: `{report['domain']}`  \n"
            f"Required coverage: **{report['required_ready']}/{report['required_total']} ({report['coverage_percent']}%)**\n\n"
            "| Stage | Requirement | Status | Recorded evidence |\n"
            "| --- | --- | --- | --- |\n"
            + "\n".join(rows)
            + "\n\n## Next required actions\n\n"
            + ("\n".join(f"- **{item['stage']}**: {item['action']}" for item in next_actions) or "- No required coverage gap is recorded. Run validation, audit, and expert review before release.")
            + f"\n\n## Interpretation boundary\n\n{report['boundary']}\n"
        )
        atomic_text(science / "STATUS.md", markdown)
    return report


def services_command(args: argparse.Namespace) -> int:
    catalog = load_catalog()
    if args.json:
        print(json.dumps(catalog, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        for service in catalog.get("services", []):
            if isinstance(service, dict):
                print(f"{service.get('id', ''):20} {service.get('availability', ''):24} {service.get('label', '')}")
        print(f"\nBoundary: {catalog.get('boundary')}")
    return 0


def doctor_command(args: argparse.Namespace) -> int:
    root = args.root.expanduser().resolve()
    science = root / ".science"
    tools = {
        name: {"status": "ready" if shutil.which(executable) else "unavailable", "path": shutil.which(executable) or ""}
        for name, executable in TOOL_EXECUTABLES.items()
    }
    credentials = {name: {"configured": bool(os.environ.get(name))} for name in SECRET_ENVIRONMENT}
    skills = sorted(path.parent.name for path in SKILLS.glob("*/SKILL.md"))
    report = {
        "schema": "codex-science.doctor.v1",
        "generated_at": utc_now(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "project": {"root": str(root), "initialized": (science / "study.json").is_file()},
        "skills": skills,
        "tools": tools,
        "providers": {
            "crossref": {"status": "ready", "authentication": "optional-contact"},
            "pubmed": {"status": "ready", "authentication": "optional-key"},
            "openalex": {
                "status": "ready" if credentials["OPENALEX_API_KEY"]["configured"] else "configuration-required",
                "authentication": "required-key",
            },
        },
        "credentials": credentials,
        "privacy": "Only credential presence booleans are recorded; values and environment contents are excluded.",
        "boundary": "Tool discovery does not prove authorization, compatibility, data governance, or successful execution.",
    }
    if args.save:
        if not science.is_dir():
            raise ScienceError("--save requires an initialized project")
        atomic_json(science / "DOCTOR.json", report)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"Codex Science doctor: project={'ready' if report['project']['initialized'] else 'not-initialized'} skills={len(skills)}")
        for name, value in report["providers"].items():
            print(f"provider {name:12} {value['status']}")
        for name, value in tools.items():
            print(f"tool     {name:12} {value['status']}")
        print(f"\nPrivacy: {report['privacy']}")
    return 0


def init_command(args: argparse.Namespace) -> int:
    code = run_delegate(
        HERE / "init_science_project.py",
        ["--root", str(args.root), "--title", args.title, "--question", args.question, "--profile", args.profile, "--domain", args.domain],
    )
    if code == 0:
        compute_status(args.root, write=True)
        for script, extra in (
            ("parity_report.py", ["--save"]),
            ("resume_project.py", []),
            ("build_research_portal.py", []),
        ):
            generated = run_delegate(HERE / script, ["--root", str(args.root), *extra])
            if generated != 0:
                return generated
        print("Next: edit .science/QUESTION.md, PLAN.md, and GOVERNANCE.md, then run `science.py next --root <root>`.")
    return code


def configure_command(args: argparse.Namespace) -> int:
    science = science_root(args.root)
    current = load_workflow(science)
    profile = args.profile or str(current.get("profile", "standard"))
    domain = args.domain or str(current.get("domain", "general"))
    workflow = default_workflow(profile, domain, str(current.get("created_at") or utc_now()))
    if not args.profile and isinstance(current.get("stages"), dict):
        workflow["stages"] = dict(current["stages"])
    stages = workflow["stages"]
    if not isinstance(stages, dict):
        raise ScienceError("workflow stages must be an object")
    for assignment in args.stage:
        if "=" not in assignment:
            raise ScienceError("--stage must use <stage>=<required|adaptive|not-requested>")
        identifier, requirement = assignment.split("=", 1)
        if identifier not in STAGE_LABELS:
            raise ScienceError(f"unknown workflow stage: {identifier}")
        if requirement not in ("required", "adaptive", "not-requested"):
            raise ScienceError(f"invalid stage requirement: {requirement}")
        stages[identifier] = requirement
    workflow["updated_at"] = utc_now()
    atomic_json(science / "workflow.json", workflow)
    report = compute_status(args.root, write=True)
    print(f"Configured profile={workflow['profile']} domain={workflow['domain']} coverage={report['required_ready']}/{report['required_total']}")
    return 0


def status_command(args: argparse.Namespace) -> int:
    report = compute_status(args.root, write=not args.no_write)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"{report['title']} [{report['profile']}/{report['domain']}] required coverage {report['required_ready']}/{report['required_total']} ({report['coverage_percent']}%)")
        for item in report["stages"]:
            print(f"{item['id']:12} {item['requirement']:13} {item['status']}")
        print(f"\nBoundary: {report['boundary']}")
    return 0


def next_command(args: argparse.Namespace) -> int:
    if not 1 <= args.limit <= len(STAGE_LABELS):
        raise ScienceError(f"--limit must be between 1 and {len(STAGE_LABELS)}")
    report = compute_status(args.root, write=True)
    actions = report["next_actions"]
    if args.json:
        print(json.dumps({"study_id": report["study_id"], "next_actions": actions, "boundary": report["boundary"]}, ensure_ascii=False, indent=2, sort_keys=True))
    elif actions:
        for number, item in enumerate(actions[: args.limit], 1):
            print(f"{number}. [{item['stage']}] {item['action']}")
    else:
        print("No required coverage gap is recorded. Run validation, audit, and expert review before release.")
    return 0


def run_delegate(script: pathlib.Path, arguments: list[str]) -> int:
    if not script.is_file():
        raise ScienceError(f"required service script is unavailable: {script}")
    process = subprocess.run([sys.executable, str(script), *arguments], check=False)
    return int(process.returncode)


def simple_delegate(args: argparse.Namespace, script: str, extra: list[str] | None = None) -> int:
    arguments = ["--root", str(args.root)]
    if extra:
        arguments.extend(extra)
    return run_delegate(HERE / script, arguments)


def search_command(args: argparse.Namespace) -> int:
    science = science_root(args.root)
    output = args.output
    if output is None:
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        output = science / "evidence/snapshots" / f"{args.provider}-{stamp}-{uuid.uuid4().hex[:8]}.json"
    connector = SKILLS / "scientific-connectors/scripts/literature_connectors.py"
    return run_delegate(
        connector,
        [args.provider, "--query", args.query, "--limit", str(args.limit), "--timeout", str(args.timeout), "--output", str(output)],
    )


def import_command(args: argparse.Namespace) -> int:
    connector = SKILLS / "scientific-connectors/scripts/literature_connectors.py"
    values = [
        "import", "--root", str(args.root), "--file", str(args.file), "--prefix", args.prefix,
        "--search-id", args.search_id, "--reason", args.reason, "--next-search", args.next_search,
    ]
    for index in args.select:
        values.extend(["--select", str(index)])
    return run_delegate(connector, values)


def remainder_command(args: argparse.Namespace, script: pathlib.Path, prefix: list[str] | None = None) -> int:
    remainder = list(args.arguments)
    if remainder and remainder[0] == "--":
        remainder = remainder[1:]
    return run_delegate(script, [*(prefix or []), *(remainder or ["--help"])])


def handoff_command(args: argparse.Namespace) -> int:
    compute_status(args.root, write=True)
    for script, extra in (
        ("parity_report.py", ["--save"]),
        ("resume_project.py", []),
        ("build_research_portal.py", []),
    ):
        code = simple_delegate(args, script, extra)
        if code != 0:
            print(f"Handoff stopped: {script} failed.", file=sys.stderr)
            return code
    validation = simple_delegate(args, "validate_science_project.py")
    if validation != 0:
        print("Handoff stopped: structural validation failed.", file=sys.stderr)
        return validation
    audit = simple_delegate(args, "audit_project.py")
    simple_delegate(args, "build_research_portal.py")
    packet = simple_delegate(args, "build_research_packet.py")
    if packet != 0:
        return packet
    final = compute_status(args.root, write=True)
    simple_delegate(args, "resume_project.py")
    simple_delegate(args, "parity_report.py", ["--save"])
    simple_delegate(args, "build_research_portal.py")
    gaps = [
        str(item["id"])
        for item in final["stages"]
        if item["requirement"] == "required" and item["status"] != "ready"
    ]
    if audit != 0 or gaps:
        reasons = []
        if audit != 0:
            reasons.append("audit findings")
        if gaps:
            reasons.append("required workflow gaps: " + ", ".join(gaps))
        print(
            "Draft research packet built, but milestone completion remains blocked by "
            + "; ".join(reasons)
            + ".",
            file=sys.stderr,
        )
        return audit if audit != 0 else 1
    print("Handoff complete. Expert review and external approvals remain separate human responsibilities.")
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    services = commands.add_parser("services", help="List the scientific service catalog")
    services.add_argument("--json", action="store_true")
    services.set_defaults(func=services_command)
    doctor = commands.add_parser("doctor", help="Inspect local tools and provider configuration without exposing secrets")
    doctor.add_argument("--root", type=pathlib.Path, default=pathlib.Path("."))
    doctor.add_argument("--json", action="store_true")
    doctor.add_argument("--save", action="store_true")
    doctor.set_defaults(func=doctor_command)
    initialize = commands.add_parser("init", help="Initialize a guided research workspace")
    initialize.add_argument("--root", type=pathlib.Path, required=True)
    initialize.add_argument("--title", required=True)
    initialize.add_argument("--question", required=True)
    initialize.add_argument("--profile", choices=sorted(PROFILE_STAGES), default="standard")
    initialize.add_argument("--domain", default="general")
    initialize.set_defaults(func=init_command)
    configure = commands.add_parser("configure", help="Tailor required stages to the study")
    configure.add_argument("--root", type=pathlib.Path, required=True)
    configure.add_argument("--profile", choices=sorted(PROFILE_STAGES))
    configure.add_argument("--domain")
    configure.add_argument("--stage", action="append", default=[])
    configure.set_defaults(func=configure_command)
    status = commands.add_parser("status", help="Build a workflow coverage dashboard")
    status.add_argument("--root", type=pathlib.Path, required=True)
    status.add_argument("--json", action="store_true")
    status.add_argument("--no-write", action="store_true")
    status.set_defaults(func=status_command)
    next_step = commands.add_parser("next", help="Show deterministic next required actions")
    next_step.add_argument("--root", type=pathlib.Path, required=True)
    next_step.add_argument("--json", action="store_true")
    next_step.add_argument("--limit", type=int, default=3)
    next_step.set_defaults(func=next_command)
    for name, script in (
        ("validate", "validate_science_project.py"),
        ("audit", "audit_project.py"),
        ("packet", "build_research_packet.py"),
        ("capabilities", "capability_report.py"),
        ("portal", "build_research_portal.py"),
        ("resume", "resume_project.py"),
    ):
        command = commands.add_parser(name)
        command.add_argument("--root", type=pathlib.Path, required=True)
        command.set_defaults(func=lambda args, selected=script: simple_delegate(args, selected))
    parity = commands.add_parser("parity", help="Audit public Claude Science feature conformance")
    parity.add_argument("--root", type=pathlib.Path, required=True)
    parity.add_argument("--json", action="store_true")
    parity.add_argument("--save", action="store_true")
    parity.set_defaults(
        func=lambda args: simple_delegate(
            args,
            "parity_report.py",
            (["--json"] if args.json else []) + (["--save"] if args.save else []),
        )
    )
    handoff = commands.add_parser("handoff", help="Refresh status, validate, audit, and build a packet")
    handoff.add_argument("--root", type=pathlib.Path, required=True)
    handoff.set_defaults(func=handoff_command)
    search = commands.add_parser("search", help="Query a bounded scientific metadata provider")
    search.add_argument("provider", choices=("crossref", "pubmed", "openalex"))
    search.add_argument("--root", type=pathlib.Path, required=True)
    search.add_argument("--query", required=True)
    search.add_argument("--limit", type=int, default=10)
    search.add_argument("--timeout", type=float, default=20.0)
    search.add_argument("--output", type=pathlib.Path)
    search.set_defaults(func=search_command)
    importing = commands.add_parser("import-sources", help="Import explicitly selected connector records")
    importing.add_argument("--root", type=pathlib.Path, required=True)
    importing.add_argument("--file", type=pathlib.Path, required=True)
    importing.add_argument("--prefix", required=True)
    importing.add_argument("--search-id", required=True)
    importing.add_argument("--reason", required=True)
    importing.add_argument("--select", type=int, action="append", default=[])
    importing.add_argument("--next-search", default="")
    importing.set_defaults(func=import_command)
    evaluation = commands.add_parser("eval", help="Pass through to the scientific-agent eval harness")
    evaluation.add_argument("arguments", nargs=argparse.REMAINDER)
    evaluation.set_defaults(func=lambda args: remainder_command(args, SKILLS / "science-evals/scripts/science_eval.py"))
    loop = commands.add_parser("loop", help="Pass through to the bounded improvement loop")
    loop.add_argument("--root", type=pathlib.Path, required=True)
    loop.add_argument("arguments", nargs=argparse.REMAINDER)
    loop.set_defaults(func=lambda args: remainder_command(args, SKILLS / "loop-engine/scripts/loop_engine.py", ["--root", str(args.root)]))
    fork = commands.add_parser("fork", help="Pass through to the provenance-preserving study fork")
    fork.add_argument("arguments", nargs=argparse.REMAINDER)
    fork.set_defaults(func=lambda args: remainder_command(args, HERE / "fork_study.py"))
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        return int(args.func(args))
    except (ScienceError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
