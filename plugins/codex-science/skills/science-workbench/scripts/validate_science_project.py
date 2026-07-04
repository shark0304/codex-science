#!/usr/bin/env python3
"""Validate a Codex Science v2 project, references, events, and local hashes."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import sys


FILES = (
    "study.json",
    "QUESTION.md",
    "PLAN.md",
    "GOVERNANCE.md",
    "LAB_NOTES.md",
    "capabilities.json",
    "evidence/sources.jsonl",
    "evidence/claims.jsonl",
    "evidence/searches.jsonl",
    "datasets/registry.jsonl",
    "experiments/registry.jsonl",
    "compute/jobs.jsonl",
    "artifacts/manifest.jsonl",
    "reviews/REVIEW.md",
    "forks.jsonl",
)
DIRECTORIES = ("evidence/paper-cards", "runs")
CLAIM_STATUSES = {"observed", "derived", "hypothesis", "conflicted", "unsupported"}
EXPERIMENT_RESULTS = {"passed", "failed", "error", "inconclusive"}
COMPUTE_RESULTS = {"completed", "failed", "cancelled", "timeout", "unknown"}
CAPABILITY_STATUSES = {"ready", "degraded", "unavailable", "not-requested", "not-verified"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def file_digest(path: pathlib.Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def directory_digest(path: pathlib.Path) -> tuple[str, int, int]:
    value = hashlib.sha256()
    count = 0
    total = 0
    for item in sorted(candidate for candidate in path.rglob("*") if candidate.is_file()):
        relative = item.relative_to(path).as_posix()
        digest = file_digest(item)
        size = item.stat().st_size
        value.update(relative.encode("utf-8"))
        value.update(digest.encode("ascii"))
        value.update(str(size).encode("ascii"))
        count += 1
        total += size
    return value.hexdigest(), count, total


def read_jsonl(path: pathlib.Path, errors: list[str]) -> list[dict[str, object]]:
    records = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"{path}:{number}: invalid JSON: {exc}")
            continue
        if not isinstance(value, dict):
            errors.append(f"{path}:{number}: record must be an object")
            continue
        records.append(value)
    return records


def unique_ids(records: list[dict[str, object]], label: str, errors: list[str]) -> set[str]:
    ids: set[str] = set()
    for record in records:
        identifier = record.get("id")
        if not isinstance(identifier, str) or not identifier:
            errors.append(f"{label}: record missing string id")
        elif identifier in ids:
            errors.append(f"{label}: duplicate id {identifier}")
        else:
            ids.add(identifier)
    return ids


def require_text(record: dict[str, object], key: str, label: str, errors: list[str]) -> None:
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label}: missing non-empty {key}")


def validate_identity(
    identity: object, label: str, errors: list[str], verify_files: bool
) -> None:
    if identity is None:
        return
    if not isinstance(identity, dict):
        errors.append(f"{label}: identity must be an object or null")
        return
    path_value = identity.get("path")
    kind = identity.get("kind")
    expected = identity.get("sha256")
    size = identity.get("bytes")
    if not isinstance(path_value, str) or not path_value:
        errors.append(f"{label}: identity missing path")
        return
    if kind not in ("file", "directory"):
        errors.append(f"{label}: identity kind must be file or directory")
    if not isinstance(expected, str) or not SHA256_RE.fullmatch(expected):
        errors.append(f"{label}: identity has invalid sha256")
        return
    if not isinstance(size, int) or size < 0:
        errors.append(f"{label}: identity has invalid byte size")
    if not verify_files:
        return
    path = pathlib.Path(path_value)
    if kind == "file" and path.is_file():
        actual, actual_size = file_digest(path), path.stat().st_size
    elif kind == "directory" and path.is_dir():
        actual, _, actual_size = directory_digest(path)
    else:
        errors.append(f"{label}: local path is unavailable: {path}")
        return
    if actual != expected:
        errors.append(f"{label}: SHA-256 mismatch: {path}")
    if actual_size != size:
        errors.append(f"{label}: byte-size mismatch: {path}")


def validate_file_records(
    values: object, label: str, errors: list[str], verify_files: bool
) -> None:
    if not isinstance(values, list):
        errors.append(f"{label}: expected a list")
        return
    for index, value in enumerate(values):
        item_label = f"{label}[{index}]"
        if not isinstance(value, dict):
            errors.append(f"{item_label}: expected an object")
            continue
        path_value = value.get("path")
        expected = value.get("sha256")
        size = value.get("bytes")
        if not isinstance(path_value, str) or not path_value:
            errors.append(f"{item_label}: missing path")
            continue
        if not isinstance(expected, str) or not SHA256_RE.fullmatch(expected):
            errors.append(f"{item_label}: invalid sha256")
            continue
        if not isinstance(size, int) or size < 0:
            errors.append(f"{item_label}: invalid byte size")
        if value.get("mutable") is True:
            continue
        if not verify_files:
            continue
        path = pathlib.Path(path_value)
        if not path.is_file():
            errors.append(f"{item_label}: file is unavailable: {path}")
        else:
            if file_digest(path) != expected:
                errors.append(f"{item_label}: SHA-256 mismatch: {path}")
            if path.stat().st_size != size:
                errors.append(f"{item_label}: byte-size mismatch: {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=pathlib.Path, required=True)
    parser.add_argument("--skip-file-hashes", action="store_true")
    args = parser.parse_args()
    science = args.root.expanduser().resolve() / ".science"
    errors: list[str] = []
    for relative in FILES:
        if not (science / relative).is_file():
            errors.append(f"missing required file: {science / relative}")
    for relative in DIRECTORIES:
        if not (science / relative).is_dir():
            errors.append(f"missing required directory: {science / relative}")
    eval_validation = "not-present"
    eval_root = science / "evals"
    if eval_root.is_dir():
        eval_runs = sorted(path.parent for path in eval_root.glob("*/run.json"))
        if eval_runs:
            eval_validator = (
                pathlib.Path(__file__).resolve().parents[2]
                / "science-evals/scripts/science_eval.py"
            )
            if not eval_validator.is_file():
                errors.append(f"science eval validator is unavailable: {eval_validator}")
                eval_validation = "failed"
            else:
                failed_evals = []
                for eval_run in eval_runs:
                    try:
                        process = subprocess.run(
                            [
                                sys.executable,
                                str(eval_validator),
                                "validate",
                                "--run-dir",
                                str(eval_run),
                            ],
                            check=False,
                            text=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            timeout=60,
                        )
                    except subprocess.TimeoutExpired:
                        failed_evals.append(f"{eval_run}: validation timeout")
                    else:
                        if process.returncode != 0:
                            failed_evals.append(f"{eval_run}:\n{process.stdout.rstrip()}")
                if failed_evals:
                    eval_validation = "failed"
                    errors.append("science eval validation failed:\n" + "\n".join(failed_evals))
                else:
                    eval_validation = f"passed({len(eval_runs)})"

    loop_validation = "not-present"
    if (science / "loop/contract.json").is_file():
        loop_validator = (
            pathlib.Path(__file__).resolve().parents[2]
            / "loop-engine/scripts/validate_loop.py"
        )
        if not loop_validator.is_file():
            errors.append(f"loop validator is unavailable: {loop_validator}")
        else:
            try:
                process = subprocess.run(
                    [sys.executable, str(loop_validator), "--root", str(args.root)],
                    check=False,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    timeout=60,
                )
            except subprocess.TimeoutExpired:
                loop_validation = "failed"
                errors.append("loop validation exceeded the 60-second integrity-check limit")
            else:
                loop_validation = "passed" if process.returncode == 0 else "failed"
                if process.returncode != 0:
                    errors.append("loop validation failed:\n" + process.stdout.rstrip())

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 2

    try:
        study = json.loads((science / "study.json").read_text(encoding="utf-8"))
        capabilities = json.loads((science / "capabilities.json").read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"ERROR: invalid project JSON: {exc}", file=sys.stderr)
        return 2
    if not isinstance(study, dict):
        errors.append("study.json: root must be an object")
        study = {}
    schema = study.get("schema")
    if schema == "codex-science.study.v1":
        errors.append("study.json: v1 project requires migrate_project.py")
    elif schema != "codex-science.study.v2":
        errors.append(f"study.json: unsupported schema {schema!r}")
    for key in ("id", "title", "question", "created_at"):
        require_text(study, key, "study.json", errors)
    if not isinstance(capabilities, dict) or capabilities.get("schema") != "codex-science.capabilities.v1":
        errors.append("capabilities.json: unsupported or missing schema")
    else:
        for name, value in capabilities.get("capabilities", {}).items():
            if not isinstance(value, dict) or value.get("status") not in CAPABILITY_STATUSES:
                errors.append(f"capability {name}: invalid status")

    sources = read_jsonl(science / "evidence/sources.jsonl", errors)
    claims = read_jsonl(science / "evidence/claims.jsonl", errors)
    searches = read_jsonl(science / "evidence/searches.jsonl", errors)
    datasets = read_jsonl(science / "datasets/registry.jsonl", errors)
    experiments = read_jsonl(science / "experiments/registry.jsonl", errors)
    compute = read_jsonl(science / "compute/jobs.jsonl", errors)
    artifacts = read_jsonl(science / "artifacts/manifest.jsonl", errors)
    forks = read_jsonl(science / "forks.jsonl", errors)
    source_ids = unique_ids(sources, "sources", errors)
    claim_ids = unique_ids(claims, "claims", errors)
    unique_ids(searches, "searches", errors)
    dataset_ids = unique_ids(datasets, "datasets", errors)
    experiment_ids = unique_ids(experiments, "experiments", errors)
    compute_ids = unique_ids(compute, "compute", errors)
    unique_ids(artifacts, "artifacts", errors)
    unique_ids(forks, "forks", errors)
    verify_files = not args.skip_file_hashes

    for source in sources:
        label = f"source {source.get('id', '<unknown>')}"
        for key in ("title", "location", "retrieved_at"):
            require_text(source, key, label, errors)
    for search in searches:
        label = f"search {search.get('id', '<unknown>')}"
        for key in ("query", "database", "reason", "created_at"):
            require_text(search, key, label, errors)
        for key in ("selected_sources", "rejected_sources"):
            if not isinstance(search.get(key), list):
                errors.append(f"{label}: {key} must be a list")
        if search.get("snapshot") is not None:
            validate_file_records(
                [search.get("snapshot")], f"{label} snapshot", errors, verify_files
            )

    card_ids: set[str] = set()
    for path in sorted((science / "evidence/paper-cards").glob("*.json")):
        try:
            card = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{path}: invalid JSON: {exc}")
            continue
        if not isinstance(card, dict) or card.get("schema") != "codex-science.paper-card.v1":
            errors.append(f"{path}: invalid paper-card schema")
            continue
        identifier = card.get("id")
        if not isinstance(identifier, str) or not identifier:
            errors.append(f"{path}: missing paper-card id")
        elif identifier in card_ids:
            errors.append(f"paper cards: duplicate id {identifier}")
        else:
            card_ids.add(identifier)
        if card.get("source_id") not in source_ids:
            errors.append(f"paper card {identifier}: unknown source {card.get('source_id')}")
        for key in ("question", "method", "created_at"):
            require_text(card, key, f"paper card {identifier}", errors)

    experiment_plans = {
        str(record.get("id")) for record in experiments if record.get("record_type") == "plan"
    }
    for experiment in experiments:
        identifier = str(experiment.get("id", "<unknown>"))
        record_type = experiment.get("record_type")
        if record_type == "plan":
            for key in ("objective", "test_oracle", "acceptance_threshold", "created_at"):
                require_text(experiment, key, f"experiment {identifier}", errors)
            validate_file_records(experiment.get("inputs", []), f"experiment {identifier} inputs", errors, verify_files)
            dataset_refs = experiment.get("datasets", [])
            if not isinstance(dataset_refs, list):
                errors.append(f"experiment {identifier}: datasets must be a list")
            else:
                for dataset_id in dataset_refs:
                    if dataset_id not in dataset_ids:
                        errors.append(f"experiment {identifier}: unknown dataset {dataset_id}")
        elif record_type == "result":
            if experiment.get("parent_id") not in experiment_plans:
                errors.append(f"experiment {identifier}: unknown parent plan")
            if experiment.get("status") not in EXPERIMENT_RESULTS:
                errors.append(f"experiment {identifier}: invalid result status")
            validate_file_records(experiment.get("outputs", []), f"experiment {identifier} outputs", errors, verify_files)
        else:
            errors.append(f"experiment {identifier}: record_type must be plan or result")

    for claim in claims:
        identifier = str(claim.get("id", "<unknown>"))
        require_text(claim, "text", f"claim {identifier}", errors)
        status = claim.get("status")
        refs = claim.get("sources", [])
        exp_refs = claim.get("experiments", [])
        if status not in CLAIM_STATUSES:
            errors.append(f"claim {identifier}: invalid status {status!r}")
        if not isinstance(refs, list) or not all(isinstance(item, str) for item in refs):
            errors.append(f"claim {identifier}: sources must be a list")
            refs = []
        if not isinstance(exp_refs, list) or not all(isinstance(item, str) for item in exp_refs):
            errors.append(f"claim {identifier}: experiments must be a list")
            exp_refs = []
        if not refs and not exp_refs and status not in ("hypothesis", "unsupported"):
            errors.append(f"claim {identifier}: status {status} requires evidence")
        for ref in refs:
            if ref not in source_ids:
                errors.append(f"claim {identifier}: unknown source {ref}")
        for ref in exp_refs:
            if ref not in experiment_ids:
                errors.append(f"claim {identifier}: unknown experiment {ref}")

    for dataset in datasets:
        identifier = str(dataset.get("id", "<unknown>"))
        record_type = dataset.get("record_type")
        require_text(dataset, "description", f"dataset {identifier}", errors)
        if record_type == "source":
            require_text(dataset, "location", f"dataset {identifier}", errors)
        elif record_type == "derived":
            parents = dataset.get("parents")
            if not isinstance(parents, list) or not parents:
                errors.append(f"dataset {identifier}: derived dataset needs parents")
            else:
                for parent in parents:
                    if parent not in dataset_ids:
                        errors.append(f"dataset {identifier}: unknown parent {parent}")
            for key in ("transformation", "command"):
                require_text(dataset, key, f"dataset {identifier}", errors)
        else:
            errors.append(f"dataset {identifier}: record_type must be source or derived")
        validate_identity(dataset.get("identity"), f"dataset {identifier}", errors, verify_files)

    compute_plans = {
        str(record.get("id")): record for record in compute if record.get("record_type") == "plan"
    }
    approvals = {
        str(record.get("parent_id")) for record in compute if record.get("record_type") == "approval"
    }
    for event in compute:
        identifier = str(event.get("id", "<unknown>"))
        record_type = event.get("record_type")
        if record_type == "plan":
            for key in ("backend", "target", "command", "time_limit", "stop_condition", "output_location"):
                require_text(event, key, f"compute {identifier}", errors)
            if not isinstance(event.get("requires_approval"), bool):
                errors.append(f"compute {identifier}: requires_approval must be boolean")
        elif record_type == "approval":
            if event.get("parent_id") not in compute_plans:
                errors.append(f"compute {identifier}: unknown parent plan")
            for key in ("approved_by", "scope", "created_at"):
                require_text(event, key, f"compute {identifier}", errors)
        elif record_type == "result":
            parent = event.get("parent_id")
            if parent not in compute_plans:
                errors.append(f"compute {identifier}: unknown parent plan")
            elif compute_plans[str(parent)].get("requires_approval") and parent not in approvals:
                errors.append(f"compute {identifier}: required approval is missing")
            if event.get("status") not in COMPUTE_RESULTS:
                errors.append(f"compute {identifier}: invalid result status")
            validate_file_records(event.get("logs", []), f"compute {identifier} logs", errors, verify_files)
            validate_file_records(event.get("outputs", []), f"compute {identifier} outputs", errors, verify_files)
        else:
            errors.append(f"compute {identifier}: invalid record_type")

    for artifact in artifacts:
        identifier = str(artifact.get("id", "<unknown>"))
        require_text(artifact, "kind", f"artifact {identifier}", errors)
        identity = {
            "path": artifact.get("path"),
            "kind": "file",
            "sha256": artifact.get("sha256"),
            "bytes": artifact.get("bytes"),
        }
        validate_identity(identity, f"artifact {identifier}", errors, verify_files)
        validate_file_records(artifact.get("inputs", []), f"artifact {identifier} inputs", errors, verify_files)

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(
        "Codex Science validation: PASS "
        f"({len(sources)} sources, {len(card_ids)} paper cards, {len(claim_ids)} claims, "
        f"{len(dataset_ids)} datasets, {len(experiment_ids)} experiment events, "
        f"{len(compute_ids)} compute events, {len(artifacts)} artifacts; "
        f"file_hashes={'skipped' if args.skip_file_hashes else 'verified'}, "
        f"loop={loop_validation}, evals={eval_validation})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
