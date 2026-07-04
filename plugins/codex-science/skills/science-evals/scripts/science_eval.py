#!/usr/bin/env python3
"""Prepare, record, grade, validate, and compare scientific-agent eval runs."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import shutil
import statistics
import sys
import tempfile
from typing import Any


DEFAULT_SUITE = pathlib.Path(__file__).resolve().parents[1] / "assets/core-benchmark-v1.json"
MISSING = object()
STATUSES = {"completed", "failed", "blocked", "timeout", "refused"}


class EvalError(ValueError):
    """An invalid suite, run, record, or comparison."""


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def digest(path: pathlib.Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def atomic_json(path: pathlib.Path, value: dict[str, object], overwrite: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        raise EvalError(f"file exists; refusing to overwrite: {path}")
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        temporary = pathlib.Path(stream.name)
    temporary.replace(path)


def read_json(path: pathlib.Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvalError(f"invalid JSON at {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise EvalError(f"JSON root must be an object: {path}")
    return value


def read_jsonl(path: pathlib.Path) -> list[dict[str, Any]]:
    records = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise EvalError(f"cannot read {path}: {exc}") from exc
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise EvalError(f"{path}:{number}: invalid JSON: {exc}") from exc
        if not isinstance(value, dict):
            raise EvalError(f"{path}:{number}: record must be an object")
        records.append(value)
    return records


def append_jsonl(path: pathlib.Path, value: dict[str, object]) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")


def validate_suite(suite: dict[str, Any]) -> None:
    if suite.get("schema") != "codex-science.eval-suite.v1":
        raise EvalError("unsupported eval suite schema")
    for key in ("id", "version", "description"):
        if not isinstance(suite.get(key), str) or not suite[key].strip():
            raise EvalError(f"suite is missing {key}")
    tasks = suite.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise EvalError("suite requires a non-empty tasks list")
    identifiers: set[str] = set()
    for task in tasks:
        if not isinstance(task, dict):
            raise EvalError("suite task must be an object")
        identifier = task.get("id")
        if not isinstance(identifier, str) or not identifier:
            raise EvalError("suite task is missing id")
        if identifier in identifiers:
            raise EvalError(f"duplicate task id: {identifier}")
        identifiers.add(identifier)
        for key in ("title", "category", "prompt"):
            if not isinstance(task.get(key), str) or not task[key].strip():
                raise EvalError(f"task {identifier} is missing {key}")
        threshold = task.get("pass_threshold")
        if not isinstance(threshold, (int, float)) or not 0 <= threshold <= 100:
            raise EvalError(f"task {identifier} has invalid pass threshold")
        checks = task.get("checks")
        if not isinstance(checks, dict):
            raise EvalError(f"task {identifier} checks must be an object")
        if not isinstance(checks.get("required_paths", []), list):
            raise EvalError(f"task {identifier} required_paths must be a list")
        for key in ("types", "equals", "contains", "min_items"):
            if not isinstance(checks.get(key, {}), dict):
                raise EvalError(f"task {identifier} {key} must be an object")
        if not isinstance(checks.get("forbidden_text", []), list):
            raise EvalError(f"task {identifier} forbidden_text must be a list")


def run_paths(run_dir: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path, pathlib.Path]:
    root = run_dir.expanduser().resolve()
    return root / "run.json", root / "suite.json", root / "results.jsonl"


def load_run(run_dir: pathlib.Path) -> tuple[pathlib.Path, dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    root = run_dir.expanduser().resolve()
    run_path, suite_path, results_path = run_paths(root)
    if not run_path.is_file() or not suite_path.is_file() or not results_path.is_file():
        raise EvalError(f"incomplete eval run: {root}")
    run = read_json(run_path)
    suite = read_json(suite_path)
    validate_suite(suite)
    return root, run, suite, read_jsonl(results_path)


def tasks_by_id(suite: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(task["id"]): task for task in suite["tasks"] if isinstance(task, dict)}


def command_init(args: argparse.Namespace) -> None:
    suite_source = args.suite.expanduser().resolve()
    suite = read_json(suite_source)
    validate_suite(suite)
    run_dir = args.run_dir.expanduser().resolve()
    if run_dir.exists() and any(run_dir.iterdir()):
        raise EvalError(f"run directory is not empty: {run_dir}")
    if args.repetitions < 1 or args.repetitions > 100:
        raise EvalError("repetitions must be between 1 and 100")
    run_dir.mkdir(parents=True, exist_ok=True)
    suite_path = run_dir / "suite.json"
    atomic_json(suite_path, suite, overwrite=False)
    run = {
        "schema": "codex-science.eval-run.v1",
        "id": f"{suite['id']}-{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "suite_id": suite["id"],
        "suite_version": suite["version"],
        "suite_sha256": digest(suite_path),
        "system": args.system,
        "model": args.model,
        "configuration": args.configuration,
        "repetitions": args.repetitions,
        "created_at": utc_now(),
        "protocol": "Fresh context per task; same tools, data, limits, and stopping rule across systems.",
    }
    atomic_json(run_dir / "run.json", run, overwrite=False)
    (run_dir / "results.jsonl").write_text("", encoding="utf-8")
    (run_dir / "outputs").mkdir()
    print(
        f"Initialized eval run {run['id']} with {len(suite['tasks'])} tasks x "
        f"{args.repetitions} repetitions at {run_dir}"
    )


def command_task(args: argparse.Namespace) -> None:
    _, _, suite, _ = load_run(args.run_dir)
    task = tasks_by_id(suite).get(args.id)
    if not task:
        raise EvalError(f"unknown task id: {args.id}")
    public = {
        "id": task["id"],
        "title": task["title"],
        "category": task["category"],
        "prompt": task["prompt"],
    }
    print(json.dumps(public, ensure_ascii=False, indent=2))


def read_human_rubric(path: pathlib.Path | None, suite: dict[str, Any]) -> tuple[dict[str, int] | None, float | None]:
    if path is None:
        return None, None
    value = read_json(path.expanduser().resolve())
    dimensions = suite.get("human_rubric", [])
    if not isinstance(dimensions, list) or not dimensions:
        raise EvalError("suite does not define a human rubric")
    scores: dict[str, int] = {}
    for dimension in dimensions:
        score = value.get(dimension)
        if not isinstance(score, int) or not 0 <= score <= 4:
            raise EvalError(f"human rubric {dimension} must be an integer from 0 to 4")
        scores[str(dimension)] = score
    return scores, 100.0 * sum(scores.values()) / (4 * len(scores))


def command_record(args: argparse.Namespace) -> None:
    root, run, suite, records = load_run(args.run_dir)
    tasks = tasks_by_id(suite)
    if args.task not in tasks:
        raise EvalError(f"unknown task id: {args.task}")
    if not 1 <= args.attempt <= int(run.get("repetitions", 0)):
        raise EvalError("attempt is outside the configured repetition count")
    if args.status not in STATUSES:
        raise EvalError(f"invalid result status: {args.status}")
    if args.duration_seconds < 0 or args.cost < 0:
        raise EvalError("duration and cost must be non-negative")
    if any(
        item.get("task_id") == args.task and item.get("attempt") == args.attempt
        for item in records
    ):
        raise EvalError(f"duplicate result: {args.task} attempt {args.attempt}")
    source = args.output.expanduser().resolve()
    if not source.is_file():
        raise EvalError(f"raw output is unavailable: {source}")
    destination = root / "outputs" / f"{args.task}-attempt-{args.attempt}.json"
    if destination.exists():
        raise EvalError(f"output snapshot exists: {destination}")
    shutil.copyfile(source, destination)
    rubric, human_score = read_human_rubric(args.human_rubric, suite)
    record = {
        "schema": "codex-science.eval-result.v1",
        "id": f"{args.task}-attempt-{args.attempt}",
        "task_id": args.task,
        "attempt": args.attempt,
        "status": args.status,
        "output": {
            "path": str(destination),
            "sha256": digest(destination),
            "bytes": destination.stat().st_size,
        },
        "duration_seconds": args.duration_seconds,
        "cost": args.cost,
        "human_rubric": rubric,
        "human_score": human_score,
        "notes": args.notes,
        "recorded_at": utc_now(),
    }
    append_jsonl(root / "results.jsonl", record)
    print(f"Recorded {record['id']} status={args.status} sha256={record['output']['sha256']}")


def resolve(value: object, path: str) -> object:
    current = value
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return MISSING
        current = current[part]
    return current


def has_type(value: object, expected: str) -> bool:
    checks = {
        "array": lambda item: isinstance(item, list),
        "boolean": lambda item: isinstance(item, bool),
        "null": lambda item: item is None,
        "number": lambda item: isinstance(item, (int, float)) and not isinstance(item, bool),
        "object": lambda item: isinstance(item, dict),
        "string": lambda item: isinstance(item, str),
    }
    return expected in checks and checks[expected](value)


def grade_output(task: dict[str, Any], output: pathlib.Path) -> tuple[float, list[dict[str, object]]]:
    text = output.read_text(encoding="utf-8")
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        return 0.0, [{"check": "valid-json", "passed": False, "detail": str(exc)}]
    if not isinstance(value, dict):
        return 0.0, [{"check": "json-object", "passed": False, "detail": "root is not an object"}]
    checks = task["checks"]
    findings: list[dict[str, object]] = []
    for path in checks.get("required_paths", []):
        actual = resolve(value, str(path))
        findings.append(
            {
                "check": f"required:{path}",
                "passed": actual is not MISSING,
                "detail": "present" if actual is not MISSING else "missing",
            }
        )
    for path, expected in checks.get("types", {}).items():
        actual = resolve(value, path)
        findings.append(
            {
                "check": f"type:{path}",
                "passed": actual is not MISSING and has_type(actual, str(expected)),
                "detail": {
                    "expected": expected,
                    "actual": "missing" if actual is MISSING else type(actual).__name__,
                },
            }
        )
    for path, expected in checks.get("equals", {}).items():
        actual = resolve(value, path)
        findings.append(
            {
                "check": f"equals:{path}",
                "passed": actual is not MISSING and actual == expected,
                "detail": {"expected": expected, "actual": None if actual is MISSING else actual},
            }
        )
    for path, expected in checks.get("contains", {}).items():
        actual = resolve(value, path)
        if isinstance(expected, list) and isinstance(actual, list):
            passed = all(item in actual for item in expected)
        elif isinstance(expected, str) and isinstance(actual, str):
            passed = expected in actual
        else:
            passed = False
        findings.append(
            {
                "check": f"contains:{path}",
                "passed": passed,
                "detail": {"expected": expected, "actual": None if actual is MISSING else actual},
            }
        )
    for path, minimum in checks.get("min_items", {}).items():
        actual = resolve(value, path)
        passed = isinstance(actual, (list, dict)) and len(actual) >= int(minimum)
        findings.append(
            {
                "check": f"min-items:{path}",
                "passed": passed,
                "detail": {"minimum": minimum, "actual": len(actual) if isinstance(actual, (list, dict)) else None},
            }
        )
    for phrase in checks.get("forbidden_text", []):
        findings.append(
            {
                "check": f"forbidden-text:{phrase}",
                "passed": str(phrase).lower() not in text.lower(),
                "detail": "absent" if str(phrase).lower() not in text.lower() else "present",
            }
        )
    passed = sum(bool(item["passed"]) for item in findings)
    score = 100.0 * passed / len(findings) if findings else 0.0
    return score, findings


def command_grade(args: argparse.Namespace) -> None:
    root, run, suite, records = load_run(args.run_dir)
    tasks = tasks_by_id(suite)
    record_map = {(str(item.get("task_id")), int(item.get("attempt", 0))): item for item in records}
    expected = [
        (task_id, attempt)
        for task_id in tasks
        for attempt in range(1, int(run["repetitions"]) + 1)
    ]
    grades = []
    for task_id, attempt in expected:
        record = record_map.get((task_id, attempt))
        if record is None:
            grades.append(
                {
                    "task_id": task_id,
                    "attempt": attempt,
                    "status": "missing",
                    "score": 0.0,
                    "passed": False,
                    "findings": [{"check": "recorded", "passed": False, "detail": "missing attempt"}],
                    "human_score": None,
                }
            )
            continue
        identity = record.get("output")
        path = pathlib.Path(str(identity.get("path", ""))) if isinstance(identity, dict) else pathlib.Path()
        intact = (
            isinstance(identity, dict)
            and path.is_file()
            and digest(path) == identity.get("sha256")
            and path.stat().st_size == identity.get("bytes")
        )
        if record.get("status") != "completed" or not intact:
            findings = [
                {
                    "check": "completed-intact-output",
                    "passed": False,
                    "detail": "status is not completed or output identity failed",
                }
            ]
            score = 0.0
        else:
            score, findings = grade_output(tasks[task_id], path)
        grades.append(
            {
                "task_id": task_id,
                "attempt": attempt,
                "status": record.get("status"),
                "score": round(score, 6),
                "passed": score >= float(tasks[task_id]["pass_threshold"]),
                "findings": findings,
                "human_score": record.get("human_score"),
            }
        )
    scores = [float(item["score"]) for item in grades]
    human = [float(item["human_score"]) for item in grades if item.get("human_score") is not None]
    summary = {
        "schema": "codex-science.eval-scores.v1",
        "run_id": run["id"],
        "suite_id": run["suite_id"],
        "suite_sha256": run["suite_sha256"],
        "system": run["system"],
        "model": run["model"],
        "graded_at": utc_now(),
        "expected_attempts": len(expected),
        "recorded_attempts": len(records),
        "structural_mean": round(statistics.mean(scores), 6) if scores else 0.0,
        "strict_pass_rate": round(sum(bool(item["passed"]) for item in grades) / len(expected), 6),
        "human_mean": round(statistics.mean(human), 6) if human else None,
        "human_scored_attempts": len(human),
        "total_duration_seconds": sum(float(item.get("duration_seconds", 0)) for item in records),
        "total_cost": sum(float(item.get("cost", 0)) for item in records),
        "grades": grades,
        "interpretation_boundary": "Transparent process-discipline benchmark; not proof of overall scientific intelligence or product parity.",
    }
    atomic_json(root / "scores.json", summary)
    rows = [
        "| Task | Attempt | Status | Structural | Pass | Human |",
        "| --- | ---: | --- | ---: | --- | ---: |",
    ]
    for item in grades:
        human_value = "" if item["human_score"] is None else f"{item['human_score']:.2f}"
        rows.append(
            f"| {item['task_id']} | {item['attempt']} | {item['status']} | "
            f"{item['score']:.2f} | {'yes' if item['passed'] else 'no'} | {human_value} |"
        )
    report = (
        f"# Science eval report: {run['system']}\n\n"
        f"Model: `{run['model']}`  \nSuite: `{run['suite_id']}`  \n"
        f"Suite SHA-256: `{run['suite_sha256']}`\n\n"
        f"Structural mean: **{summary['structural_mean']:.2f}**  \n"
        f"Strict pass rate: **{100 * summary['strict_pass_rate']:.2f}%**  \n"
        f"Coverage: **{summary['recorded_attempts']}/{summary['expected_attempts']}**  \n"
        f"Human mean: **{summary['human_mean'] if summary['human_mean'] is not None else 'not scored'}**\n\n"
        + "\n".join(rows)
        + "\n\nThis transparent suite measures research-process discipline, not full scientific or product parity.\n"
    )
    (root / "report.md").write_text(report, encoding="utf-8")
    print(
        f"Graded {len(expected)} expected attempts: mean={summary['structural_mean']:.2f}, "
        f"pass_rate={100 * summary['strict_pass_rate']:.2f}%"
    )


def command_validate(args: argparse.Namespace) -> None:
    root, run, suite, records = load_run(args.run_dir)
    errors = []
    if run.get("schema") != "codex-science.eval-run.v1":
        errors.append("run: invalid schema")
    if digest(root / "suite.json") != run.get("suite_sha256"):
        errors.append("run: suite SHA-256 mismatch")
    tasks = tasks_by_id(suite)
    seen: set[tuple[str, int]] = set()
    repetitions = int(run.get("repetitions", 0))
    for record in records:
        identifier = str(record.get("id", "<unknown>"))
        if record.get("schema") != "codex-science.eval-result.v1":
            errors.append(f"result {identifier}: invalid schema")
        task_id = str(record.get("task_id"))
        attempt = record.get("attempt")
        if task_id not in tasks:
            errors.append(f"result {identifier}: unknown task")
        if not isinstance(attempt, int) or not 1 <= attempt <= repetitions:
            errors.append(f"result {identifier}: invalid attempt")
            continue
        key = (task_id, attempt)
        if key in seen:
            errors.append(f"result {identifier}: duplicate task attempt")
        seen.add(key)
        if record.get("status") not in STATUSES:
            errors.append(f"result {identifier}: invalid status")
        identity = record.get("output")
        if not isinstance(identity, dict):
            errors.append(f"result {identifier}: missing output identity")
            continue
        path = pathlib.Path(str(identity.get("path", "")))
        if not path.is_file():
            errors.append(f"result {identifier}: output unavailable")
        else:
            if digest(path) != identity.get("sha256"):
                errors.append(f"result {identifier}: output SHA-256 mismatch")
            if path.stat().st_size != identity.get("bytes"):
                errors.append(f"result {identifier}: output byte-size mismatch")
    scores_path = root / "scores.json"
    if scores_path.is_file():
        scores = read_json(scores_path)
        if scores.get("schema") != "codex-science.eval-scores.v1":
            errors.append("scores: invalid schema")
        if scores.get("suite_sha256") != run.get("suite_sha256"):
            errors.append("scores: suite identity mismatch")
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        raise EvalError(f"eval validation failed with {len(errors)} error(s)")
    print(
        f"Science eval validation: PASS ({len(tasks)} tasks, {repetitions} repetitions, "
        f"{len(records)} recorded attempts)"
    )


def task_means(scores: dict[str, Any]) -> dict[str, float]:
    grouped: dict[str, list[float]] = {}
    for item in scores.get("grades", []):
        if isinstance(item, dict):
            grouped.setdefault(str(item.get("task_id")), []).append(float(item.get("score", 0)))
    return {key: statistics.mean(values) for key, values in grouped.items()}


def command_compare(args: argparse.Namespace) -> None:
    root_a, run_a, _, _ = load_run(args.run_a)
    root_b, run_b, _, _ = load_run(args.run_b)
    scores_a = read_json(root_a / "scores.json")
    scores_b = read_json(root_b / "scores.json")
    if run_a.get("suite_sha256") != run_b.get("suite_sha256"):
        raise EvalError("runs use different suite snapshots")
    if scores_a.get("suite_sha256") != scores_b.get("suite_sha256"):
        raise EvalError("score files use different suite snapshots")
    means_a = task_means(scores_a)
    means_b = task_means(scores_b)
    task_ids = sorted(set(means_a) | set(means_b))
    rows = [
        "| Task | A mean | B mean | B - A |",
        "| --- | ---: | ---: | ---: |",
    ]
    for task_id in task_ids:
        a = means_a.get(task_id, 0.0)
        b = means_b.get(task_id, 0.0)
        rows.append(f"| {task_id} | {a:.2f} | {b:.2f} | {b - a:+.2f} |")
    output = args.output.expanduser().resolve()
    if output.exists():
        raise EvalError(f"comparison output exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    report = (
        "# Scientific-agent comparison\n\n"
        f"Suite SHA-256: `{run_a['suite_sha256']}`\n\n"
        f"A: **{run_a['system']}** / `{run_a['model']}` — structural mean "
        f"{scores_a['structural_mean']:.2f}, pass rate {100 * scores_a['strict_pass_rate']:.2f}%  \n"
        f"B: **{run_b['system']}** / `{run_b['model']}` — structural mean "
        f"{scores_b['structural_mean']:.2f}, pass rate {100 * scores_b['strict_pass_rate']:.2f}%\n\n"
        + "\n".join(rows)
        + "\n\nDifferences are descriptive. This transparent process suite does not prove overall scientific or product parity.\n"
    )
    output.write_text(report, encoding="utf-8")
    print(f"Wrote comparison to {output}")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    sub = root.add_subparsers(dest="command", required=True)
    initialize = sub.add_parser("init")
    initialize.add_argument("--run-dir", type=pathlib.Path, required=True)
    initialize.add_argument("--suite", type=pathlib.Path, default=DEFAULT_SUITE)
    initialize.add_argument("--system", required=True)
    initialize.add_argument("--model", required=True)
    initialize.add_argument("--configuration", default="")
    initialize.add_argument("--repetitions", type=int, default=3)
    initialize.set_defaults(func=command_init)
    task = sub.add_parser("task")
    task.add_argument("--run-dir", type=pathlib.Path, required=True)
    task.add_argument("--id", required=True)
    task.set_defaults(func=command_task)
    record = sub.add_parser("record")
    record.add_argument("--run-dir", type=pathlib.Path, required=True)
    record.add_argument("--task", required=True)
    record.add_argument("--attempt", type=int, required=True)
    record.add_argument("--output", type=pathlib.Path, required=True)
    record.add_argument("--status", choices=sorted(STATUSES), required=True)
    record.add_argument("--duration-seconds", type=float, default=0.0)
    record.add_argument("--cost", type=float, default=0.0)
    record.add_argument("--human-rubric", type=pathlib.Path)
    record.add_argument("--notes", default="")
    record.set_defaults(func=command_record)
    grade = sub.add_parser("grade")
    grade.add_argument("--run-dir", type=pathlib.Path, required=True)
    grade.set_defaults(func=command_grade)
    validate = sub.add_parser("validate")
    validate.add_argument("--run-dir", type=pathlib.Path, required=True)
    validate.set_defaults(func=command_validate)
    compare = sub.add_parser("compare")
    compare.add_argument("--run-a", type=pathlib.Path, required=True)
    compare.add_argument("--run-b", type=pathlib.Path, required=True)
    compare.add_argument("--output", type=pathlib.Path, required=True)
    compare.set_defaults(func=command_compare)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        args.func(args)
    except (EvalError, OSError, UnicodeDecodeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
