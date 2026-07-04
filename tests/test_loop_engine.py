from __future__ import annotations

import json
import pathlib
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKBENCH = ROOT / "plugins/codex-science/skills/science-workbench/scripts"
LOOP = ROOT / "plugins/codex-science/skills/loop-engine/scripts"


class LoopEngineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="codex-science-loop-test-")
        self.root = pathlib.Path(self.temp.name)
        self.run_script(
            WORKBENCH / "init_science_project.py",
            "--root",
            str(self.root),
            "--title",
            "Loop Study",
            "--question",
            "Can a bounded loop satisfy every declared gate?",
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_script(
        self, script: pathlib.Path, *arguments: str, expected: int = 0
    ) -> subprocess.CompletedProcess[str]:
        process = subprocess.run(
            ["python3", str(script), *arguments],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        self.assertEqual(
            process.returncode,
            expected,
            msg=f"{script.name} returned {process.returncode}, expected {expected}:\n{process.stdout}",
        )
        return process

    def loop(self, *arguments: str, expected: int = 0) -> subprocess.CompletedProcess[str]:
        return self.run_script(
            LOOP / "loop_engine.py", "--root", str(self.root), *arguments, expected=expected
        )

    def registry(self, *arguments: str, expected: int = 0) -> subprocess.CompletedProcess[str]:
        return self.run_script(
            LOOP / "capability_registry.py",
            "--root",
            str(self.root),
            *arguments,
            expected=expected,
        )

    def initialize_loop(self, *extra: str) -> None:
        self.loop(
            "init",
            "--objective",
            "Close evidence and reproducibility gaps",
            "--gate",
            "evidence:Material claims have support",
            "--gate",
            "reproducibility:A clean rerun passes",
            "--max-iterations",
            "3",
            "--stall-limit",
            "2",
            "--min-progress",
            "0.1",
            *extra,
        )

    def scan_safe_capability(self) -> pathlib.Path:
        candidate = self.root / "candidate-skill"
        candidate.mkdir()
        (candidate / "SKILL.md").write_text(
            "---\nname: safe-skill\n"
            "description: A deterministic fixture capability used for loop validation tests.\n"
            "---\n\n# Safe skill\n\nReturn a local deterministic result.\n",
            encoding="utf-8",
        )
        report = self.root / "safe-scan.json"
        self.run_script(
            LOOP / "scan_capability.py",
            "--path",
            str(candidate),
            "--output",
            str(report),
        )
        return report

    def register_safe_capability(self, report: pathlib.Path) -> None:
        self.registry(
            "register",
            "--id",
            "safe-skill",
            "--kind",
            "skill",
            "--source",
            "https://example.org/safe-skill.git",
            "--revision",
            "0123456789abcdef0123456789abcdef01234567",
            "--license",
            "MIT",
            "--invocation",
            "$safe-skill",
            "--scan-report",
            str(report),
            "--trust",
            "approved",
            "--reviewed-by",
            "test-reviewer",
        )

    def test_closed_loop_lifecycle_and_packet(self) -> None:
        self.initialize_loop("--budget-unit", "credits", "--budget-limit", "10")
        report = self.scan_safe_capability()
        self.register_safe_capability(report)
        input_file = self.root / "input.txt"
        input_file.write_text("question\n", encoding="utf-8")
        first_output = self.root / "first.txt"
        first_output.write_text("partial result\n", encoding="utf-8")

        self.loop(
            "plan",
            "--id",
            "I001",
            "--objective",
            "Test the first hypothesis",
            "--capability",
            "safe-skill",
            "--input",
            str(input_file),
        )
        self.loop(
            "trace",
            "--id",
            "T001",
            "--iteration",
            "I001",
            "--status",
            "completed",
            "--summary",
            "Evidence remained incomplete",
            "--capability",
            "safe-skill",
            "--output",
            str(first_output),
            "--cost",
            "1.5",
        )
        self.loop(
            "evaluate",
            "--id",
            "V001",
            "--iteration",
            "I001",
            "--gate",
            "evidence",
            "--verdict",
            "fail",
            "--summary",
            "One claim is unsupported",
            "--evidence",
            str(first_output),
        )
        self.loop(
            "evaluate",
            "--id",
            "V002",
            "--iteration",
            "I001",
            "--gate",
            "reproducibility",
            "--verdict",
            "pass",
            "--summary",
            "The partial result reproduces",
            "--evidence",
            str(first_output),
        )
        output = self.loop(
            "decide",
            "--id",
            "X000",
            "--iteration",
            "I001",
            "--decision",
            "succeed",
            "--progress",
            "0.5",
            "--reason",
            "Attempt premature success",
            expected=2,
        ).stdout
        self.assertIn("gates are not passing", output)
        self.loop(
            "decide",
            "--id",
            "X001",
            "--iteration",
            "I001",
            "--decision",
            "continue",
            "--progress",
            "0.4",
            "--reason",
            "Evidence gate failed",
            "--next-action",
            "Acquire support for the unresolved claim",
        )

        final_output = self.root / "final.txt"
        final_output.write_text("supported and reproduced\n", encoding="utf-8")
        self.loop(
            "plan",
            "--id",
            "I002",
            "--objective",
            "Close the remaining evidence gap",
            "--capability",
            "safe-skill",
        )
        self.loop(
            "trace",
            "--id",
            "T002",
            "--iteration",
            "I002",
            "--status",
            "completed",
            "--summary",
            "All required evidence was produced",
            "--capability",
            "safe-skill",
            "--output",
            str(final_output),
            "--cost",
            "2",
        )
        for identifier, gate in (("V003", "evidence"), ("V004", "reproducibility")):
            self.loop(
                "evaluate",
                "--id",
                identifier,
                "--iteration",
                "I002",
                "--gate",
                gate,
                "--verdict",
                "pass",
                "--score",
                "1",
                "--summary",
                f"{gate} gate passed",
                "--evidence",
                str(final_output),
            )
        self.loop(
            "decide",
            "--id",
            "X002",
            "--iteration",
            "I002",
            "--decision",
            "succeed",
            "--progress",
            "1",
            "--reason",
            "Every required gate passed",
        )
        self.run_script(LOOP / "validate_loop.py", "--root", str(self.root))
        project_validation = self.run_script(
            WORKBENCH / "validate_science_project.py", "--root", str(self.root)
        ).stdout
        self.assertIn("loop=passed", project_validation)
        status = json.loads(self.loop("status").stdout)
        self.assertEqual(status["status"], "succeed")
        self.assertEqual(status["iterations"], 2)
        self.assertEqual(status["total_cost"], 3.5)

        self.run_script(
            WORKBENCH / "build_research_packet.py", "--root", str(self.root)
        )
        packet = next((self.root / ".science/artifacts").glob("research-packet-*.md"))
        packet_text = packet.read_text(encoding="utf-8")
        self.assertIn("## Closed-loop improvement", packet_text)
        self.assertIn("safe-skill", packet_text)
        self.assertIn("X002", packet_text)

    def test_stall_limit_forces_stop(self) -> None:
        self.loop(
            "init",
            "--objective",
            "Detect stalled work",
            "--gate",
            "quality:Required quality threshold",
            "--max-iterations",
            "3",
            "--stall-limit",
            "2",
            "--min-progress",
            "0.2",
        )
        evidence = self.root / "evidence.txt"
        evidence.write_text("still failing\n", encoding="utf-8")
        for number in (1, 2):
            iteration = f"I00{number}"
            self.loop("plan", "--id", iteration, "--objective", f"Attempt {number}")
            self.loop(
                "trace",
                "--id",
                f"T00{number}",
                "--iteration",
                iteration,
                "--status",
                "failed",
                "--summary",
                "No measurable improvement",
                "--output",
                str(evidence),
            )
            self.loop(
                "evaluate",
                "--id",
                f"V00{number}",
                "--iteration",
                iteration,
                "--gate",
                "quality",
                "--verdict",
                "fail",
                "--summary",
                "Quality remains below threshold",
                "--evidence",
                str(evidence),
            )
            decision_args = (
                "decide",
                "--id",
                f"X00{number}",
                "--iteration",
                iteration,
                "--decision",
                "continue",
                "--progress",
                "0",
                "--reason",
                "No progress",
                "--next-action",
                "Try another bounded change",
            )
            if number == 1:
                self.loop(*decision_args)
            else:
                output = self.loop(*decision_args, expected=2).stdout
                self.assertIn("low-progress limit", output)
                self.loop(
                    "decide",
                    "--id",
                    "X002-STOP",
                    "--iteration",
                    iteration,
                    "--decision",
                    "stop",
                    "--progress",
                    "0",
                    "--reason",
                    "Stall limit reached",
                )
        self.run_script(LOOP / "validate_loop.py", "--root", str(self.root))

    def test_blocked_scan_cannot_be_approved(self) -> None:
        self.initialize_loop()
        candidate = self.root / "unsafe-skill"
        candidate.mkdir()
        (candidate / "SKILL.md").write_text(
            "---\nname: unsafe-skill\n"
            "description: An intentionally unsafe fixture for a negative scanner test.\n"
            "---\n\n-----BEGIN " + "PRIVATE KEY-----\n",
            encoding="utf-8",
        )
        report = self.root / "unsafe-scan.json"
        self.run_script(
            LOOP / "scan_capability.py",
            "--path",
            str(candidate),
            "--output",
            str(report),
            expected=3,
        )
        output = self.registry(
            "register",
            "--id",
            "unsafe-skill",
            "--kind",
            "skill",
            "--source",
            "https://example.org/unsafe.git",
            "--revision",
            "deadbeef",
            "--license",
            "UNKNOWN",
            "--invocation",
            "$unsafe-skill",
            "--scan-report",
            str(report),
            "--trust",
            "approved",
            "--reviewed-by",
            "test-reviewer",
            expected=2,
        ).stdout
        self.assertIn("non-blocked scan", output)

    def test_scan_report_tampering_is_detected(self) -> None:
        self.initialize_loop()
        report = self.scan_safe_capability()
        self.register_safe_capability(report)
        report.write_text("{}\n", encoding="utf-8")
        output = self.run_script(
            LOOP / "validate_loop.py", "--root", str(self.root), expected=2
        ).stdout
        self.assertIn("SHA-256 mismatch", output)

    def test_approved_checkout_mutation_is_detected(self) -> None:
        self.initialize_loop()
        report = self.scan_safe_capability()
        self.register_safe_capability(report)
        skill = self.root / "candidate-skill/SKILL.md"
        skill.write_text(skill.read_text(encoding="utf-8") + "\nChanged after review.\n", encoding="utf-8")
        output = self.run_script(
            LOOP / "validate_loop.py", "--root", str(self.root), expected=2
        ).stdout
        self.assertIn("scanned checkout changed after approval", output)

    def test_budget_limit_forces_stop(self) -> None:
        self.loop(
            "init",
            "--objective",
            "Enforce the loop budget",
            "--gate",
            "quality:Required quality threshold",
            "--max-iterations",
            "3",
            "--budget-unit",
            "credits",
            "--budget-limit",
            "1",
        )
        evidence = self.root / "budget-evidence.txt"
        evidence.write_text("quality gate failed\n", encoding="utf-8")
        self.loop("plan", "--id", "I001", "--objective", "Use the available budget")
        self.loop(
            "trace",
            "--id",
            "T001",
            "--iteration",
            "I001",
            "--status",
            "failed",
            "--summary",
            "Budget was consumed without passing",
            "--cost",
            "1",
            "--output",
            str(evidence),
        )
        self.loop(
            "evaluate",
            "--id",
            "V001",
            "--iteration",
            "I001",
            "--gate",
            "quality",
            "--verdict",
            "fail",
            "--summary",
            "Quality remains below threshold",
            "--evidence",
            str(evidence),
        )
        output = self.loop(
            "decide",
            "--id",
            "X001",
            "--iteration",
            "I001",
            "--decision",
            "continue",
            "--progress",
            "0.5",
            "--reason",
            "Another attempt might help",
            "--next-action",
            "Spend more budget",
            expected=2,
        ).stdout
        self.assertIn("budget limit reached", output)
        self.loop(
            "decide",
            "--id",
            "X001-STOP",
            "--iteration",
            "I001",
            "--decision",
            "stop",
            "--reason",
            "Budget limit reached",
        )
        self.run_script(LOOP / "validate_loop.py", "--root", str(self.root))

    def test_warning_scan_requires_explicit_risk_acceptance(self) -> None:
        self.initialize_loop()
        candidate = self.root / "network-skill"
        candidate.mkdir()
        (candidate / "SKILL.md").write_text(
            "---\nname: network-skill\n"
            "description: A networked fixture used to verify explicit warning acceptance.\n"
            "---\n\nUse the bundled network client.\n",
            encoding="utf-8",
        )
        (candidate / "client.py").write_text(
            "import requests\nrequests.get('https://example.org', timeout=5)\n",
            encoding="utf-8",
        )
        report = self.root / "network-scan.json"
        self.run_script(
            LOOP / "scan_capability.py",
            "--path",
            str(candidate),
            "--output",
            str(report),
        )
        arguments = (
            "register",
            "--id",
            "network-skill",
            "--kind",
            "skill",
            "--source",
            "https://example.org/network-skill.git",
            "--revision",
            "89abcdef",
            "--license",
            "MIT",
            "--invocation",
            "$network-skill",
            "--scan-report",
            str(report),
            "--trust",
            "approved",
            "--reviewed-by",
            "test-reviewer",
        )
        output = self.registry(*arguments, expected=2).stdout
        self.assertIn("requires --accept-risk", output)
        self.registry(*arguments, "--accept-risk")
        self.run_script(LOOP / "validate_loop.py", "--root", str(self.root))


if __name__ == "__main__":
    unittest.main()
