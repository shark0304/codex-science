from __future__ import annotations

import json
import pathlib
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
EVAL = ROOT / "plugins/codex-science/skills/science-evals/scripts/science_eval.py"
WORKBENCH = ROOT / "plugins/codex-science/skills/science-workbench/scripts"


def set_path(value: dict[str, object], path: str, item: object) -> None:
    current = value
    parts = path.split(".")
    for part in parts[:-1]:
        child = current.setdefault(part, {})
        if not isinstance(child, dict):
            raise AssertionError(f"fixture path conflict: {path}")
        current = child
    current[parts[-1]] = item


def satisfying_response(task: dict[str, object]) -> dict[str, object]:
    checks = task["checks"]
    assert isinstance(checks, dict)
    value: dict[str, object] = {}
    defaults = {
        "array": [],
        "boolean": False,
        "null": None,
        "number": 0,
        "object": {},
        "string": "reviewed next action",
    }
    for path, expected_type in checks.get("types", {}).items():
        default = defaults[expected_type]
        set_path(value, path, list(default) if isinstance(default, list) else dict(default) if isinstance(default, dict) else default)
    for path, expected in checks.get("equals", {}).items():
        set_path(value, path, expected)
    for path, expected in checks.get("contains", {}).items():
        set_path(value, path, list(expected) if isinstance(expected, list) else expected)
    for path, minimum in checks.get("min_items", {}).items():
        current: object = value
        for part in path.split("."):
            current = current[part]  # type: ignore[index]
        if isinstance(current, list):
            current.extend({"fixture": index} for index in range(int(minimum) - len(current)))
    return value


class ScienceEvalTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="codex-science-eval-")
        self.root = pathlib.Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_eval(self, *arguments: str, expected: int = 0) -> subprocess.CompletedProcess[str]:
        process = subprocess.run(
            ["python3", str(EVAL), *arguments],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        self.assertEqual(process.returncode, expected, process.stdout)
        return process

    def initialize(self, name: str, system: str) -> pathlib.Path:
        run = self.root / name
        self.run_eval(
            "init",
            "--run-dir",
            str(run),
            "--system",
            system,
            "--model",
            "test-model",
            "--repetitions",
            "1",
        )
        return run

    def record_suite(self, run: pathlib.Path, degrade_first: bool = False) -> None:
        suite = json.loads((run / "suite.json").read_text(encoding="utf-8"))
        for index, task in enumerate(suite["tasks"]):
            response = satisfying_response(task)
            if degrade_first and index == 0:
                response["decision"] = {"status": "supported", "reason": "ignored conflict"}
            output = self.root / f"{run.name}-{task['id']}.json"
            output.write_text(json.dumps(response) + "\n", encoding="utf-8")
            self.run_eval(
                "record",
                "--run-dir",
                str(run),
                "--task",
                task["id"],
                "--attempt",
                "1",
                "--output",
                str(output),
                "--status",
                "completed",
                "--duration-seconds",
                "1",
                "--cost",
                "0.01",
            )

    def test_complete_runs_grade_validate_and_compare(self) -> None:
        run_a = self.initialize("run-a", "codex-science")
        run_b = self.initialize("run-b", "comparison-system")
        task_output = self.run_eval(
            "task", "--run-dir", str(run_a), "--id", "conflicted-evidence"
        ).stdout
        self.assertNotIn("checks", task_output)
        self.record_suite(run_a)
        self.record_suite(run_b, degrade_first=True)
        self.run_eval("grade", "--run-dir", str(run_a))
        self.run_eval("grade", "--run-dir", str(run_b))
        self.run_eval("validate", "--run-dir", str(run_a))
        self.run_eval("validate", "--run-dir", str(run_b))
        scores_a = json.loads((run_a / "scores.json").read_text(encoding="utf-8"))
        scores_b = json.loads((run_b / "scores.json").read_text(encoding="utf-8"))
        self.assertEqual(scores_a["structural_mean"], 100.0)
        self.assertEqual(scores_a["strict_pass_rate"], 1.0)
        self.assertLess(scores_b["structural_mean"], scores_a["structural_mean"])
        comparison = self.root / "comparison.md"
        self.run_eval(
            "compare",
            "--run-a",
            str(run_a),
            "--run-b",
            str(run_b),
            "--output",
            str(comparison),
        )
        text = comparison.read_text(encoding="utf-8")
        self.assertIn("codex-science", text)
        self.assertIn("comparison-system", text)
        self.assertIn("descriptive", text)

    def test_missing_attempts_count_as_zero(self) -> None:
        run = self.initialize("missing", "incomplete-system")
        self.run_eval("grade", "--run-dir", str(run))
        scores = json.loads((run / "scores.json").read_text(encoding="utf-8"))
        self.assertEqual(scores["recorded_attempts"], 0)
        self.assertEqual(scores["structural_mean"], 0.0)
        self.assertEqual(scores["strict_pass_rate"], 0.0)

    def test_output_tampering_is_rejected(self) -> None:
        run = self.initialize("tamper", "tampered-system")
        suite = json.loads((run / "suite.json").read_text(encoding="utf-8"))
        task = suite["tasks"][0]
        output = self.root / "raw.json"
        output.write_text(json.dumps(satisfying_response(task)) + "\n", encoding="utf-8")
        self.run_eval(
            "record",
            "--run-dir",
            str(run),
            "--task",
            task["id"],
            "--attempt",
            "1",
            "--output",
            str(output),
            "--status",
            "completed",
        )
        preserved = run / "outputs" / f"{task['id']}-attempt-1.json"
        preserved.write_text("{}\n", encoding="utf-8")
        result = self.run_eval("validate", "--run-dir", str(run), expected=2).stdout
        self.assertIn("SHA-256 mismatch", result)

    def test_study_validation_and_packet_include_eval_run(self) -> None:
        process = subprocess.run(
            [
                "python3",
                str(WORKBENCH / "init_science_project.py"),
                "--root",
                str(self.root),
                "--title",
                "Eval-integrated study",
                "--question",
                "Can an eval run be included in the research handoff?",
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        self.assertEqual(process.returncode, 0, process.stdout)
        run = self.root / ".science/evals/integration"
        self.run_eval(
            "init",
            "--run-dir",
            str(run),
            "--system",
            "codex-science",
            "--model",
            "test-model",
            "--repetitions",
            "1",
        )
        self.run_eval("grade", "--run-dir", str(run))
        validation = subprocess.run(
            [
                "python3",
                str(WORKBENCH / "validate_science_project.py"),
                "--root",
                str(self.root),
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        self.assertEqual(validation.returncode, 0, validation.stdout)
        self.assertIn("evals=passed(1)", validation.stdout)
        packet = subprocess.run(
            [
                "python3",
                str(WORKBENCH / "build_research_packet.py"),
                "--root",
                str(self.root),
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        self.assertEqual(packet.returncode, 0, packet.stdout)
        packet_path = next((self.root / ".science/artifacts").glob("research-packet-*.md"))
        text = packet_path.read_text(encoding="utf-8")
        self.assertIn("## Scientific-agent evaluations", text)
        self.assertIn("codex-science", text)


if __name__ == "__main__":
    unittest.main()
