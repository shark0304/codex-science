from __future__ import annotations

import json
import pathlib
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins/codex-science/skills/science-workbench/scripts"


class WorkbenchTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="codex-science-test-")
        self.root = pathlib.Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_script(
        self, name: str, *arguments: str, expected: int = 0
    ) -> subprocess.CompletedProcess[str]:
        process = subprocess.run(
            ["python3", str(SCRIPTS / name), "--root", str(self.root), *arguments],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        self.assertEqual(
            process.returncode,
            expected,
            msg=f"{name} returned {process.returncode}, expected {expected}:\n{process.stdout}",
        )
        return process

    def initialize(self) -> None:
        self.run_script(
            "init_science_project.py",
            "--title",
            "Reproducibility Study",
            "--question",
            "Does the recorded result meet its preregistered threshold?",
        )

    def test_full_research_lifecycle(self) -> None:
        self.initialize()
        science = self.root / ".science"
        raw = self.root / "raw.csv"
        raw.write_text("x,y\n1,2\n2,4\n", encoding="utf-8")
        derived = self.root / "derived.csv"
        derived.write_text("x,y2\n1,4\n2,8\n", encoding="utf-8")
        result = self.root / "result.json"
        result.write_text('{"effect": 2.0, "error": 0.0}\n', encoding="utf-8")
        log = self.root / "job.log"
        log.write_text("completed\n", encoding="utf-8")

        self.run_script("capability_report.py")
        self.run_script(
            "science_ledger.py",
            "add-source",
            "--id",
            "S001",
            "--title",
            "Reference study",
            "--location",
            "https://example.org/reference",
            "--type",
            "paper",
            "--review-status",
            "peer-reviewed",
        )
        self.run_script(
            "literature_ledger.py",
            "search",
            "--id",
            "Q001",
            "--query",
            "reference effect",
            "--database",
            "example-index",
            "--reason",
            "Find direct evidence",
            "--selected",
            "S001",
        )
        self.run_script(
            "literature_ledger.py",
            "paper-card",
            "--id",
            "P001",
            "--source",
            "S001",
            "--question",
            "What effect was measured?",
            "--method",
            "Controlled comparison",
            "--outcomes",
            "Effect estimate",
        )
        self.run_script(
            "dataset_ledger.py",
            "register",
            "--id",
            "D001",
            "--path",
            str(raw),
            "--description",
            "Raw measurements",
            "--license",
            "CC0-1.0",
            "--access",
            "public",
        )
        self.run_script(
            "dataset_ledger.py",
            "derive",
            "--id",
            "D002",
            "--parent",
            "D001",
            "--path",
            str(derived),
            "--description",
            "Deterministically transformed measurements",
            "--transformation",
            "Multiply y by two",
            "--command",
            "python transform.py",
            "--license",
            "CC0-1.0",
            "--access",
            "public",
        )
        self.run_script(
            "experiment_ledger.py",
            "plan",
            "--id",
            "E001",
            "--objective",
            "Estimate the effect",
            "--oracle",
            "Reference calculation agrees",
            "--threshold",
            "absolute error <= 0.01",
            "--command",
            "python analysis.py",
            "--dataset",
            "D002",
            "--seed",
            "42",
        )
        self.run_script(
            "experiment_ledger.py",
            "result",
            "--id",
            "E001-R001",
            "--parent",
            "E001",
            "--status",
            "passed",
            "--exit-code",
            "0",
            "--output",
            str(result),
        )
        self.run_script(
            "science_ledger.py",
            "add-claim",
            "--id",
            "C001",
            "--text",
            "The recorded result meets the preregistered threshold.",
            "--status",
            "derived",
            "--sources",
            "S001",
            "--experiments",
            "E001-R001",
        )
        self.run_script(
            "compute_job.py",
            "plan",
            "--id",
            "J001",
            "--backend",
            "ssh",
            "--target",
            "research-cluster",
            "--command",
            "python analysis.py",
            "--resource",
            "cpus=2",
            "--data-class",
            "public",
            "--time-limit",
            "10m",
            "--stop-condition",
            "non-zero exit or 10m timeout",
            "--output-location",
            str(result),
        )
        self.run_script(
            "compute_job.py",
            "result",
            "--id",
            "J001-R000",
            "--parent",
            "J001",
            "--status",
            "failed",
            expected=2,
        )
        self.run_script(
            "compute_job.py",
            "approve",
            "--id",
            "J001-A001",
            "--parent",
            "J001",
            "--approved-by",
            "test-user",
            "--scope",
            "Exact recorded command and target",
        )
        self.run_script(
            "compute_job.py",
            "result",
            "--id",
            "J001-R001",
            "--parent",
            "J001",
            "--status",
            "completed",
            "--exit-code",
            "0",
            "--job-id",
            "job-1",
            "--log",
            str(log),
            "--output",
            str(result),
        )
        self.run_script(
            "capture_environment.py",
            "--label",
            "baseline",
            "--hash",
            str(raw),
        )
        self.run_script(
            "record_artifact.py",
            "--file",
            str(result),
            "--kind",
            "result",
            "--command",
            "python analysis.py",
            "--input",
            str(derived),
        )
        self.run_script("validate_science_project.py")
        self.run_script("audit_project.py")
        self.run_script("build_research_packet.py")
        self.run_script("validate_science_project.py")

        packets = list((science / "artifacts").glob("research-packet-*.md"))
        self.assertEqual(len(packets), 1)
        packet_text = packets[0].read_text(encoding="utf-8")
        self.assertIn("## Dataset", packet_text)
        self.assertIn("E001-R001", packet_text)
        self.assertIn("J001-A001", packet_text)

    def test_tampered_artifact_is_rejected(self) -> None:
        self.initialize()
        artifact = self.root / "figure.txt"
        artifact.write_text("registered\n", encoding="utf-8")
        self.run_script(
            "record_artifact.py",
            "--file",
            str(artifact),
            "--kind",
            "figure",
        )
        artifact.write_text("mutated\n", encoding="utf-8")
        output = self.run_script("validate_science_project.py", expected=2).stdout
        self.assertIn("SHA-256 mismatch", output)

    def test_study_fork_preserves_provenance(self) -> None:
        self.initialize()
        destination = self.root / "fork"
        self.run_script(
            "fork_study.py",
            "--destination",
            str(destination),
            "--reason",
            "Compare an alternative hypothesis",
        )
        fork_study = json.loads(
            (destination / ".science/study.json").read_text(encoding="utf-8")
        )
        self.assertEqual(fork_study["fork_of"], "reproducibility-study")
        process = subprocess.run(
            [
                "python3",
                str(SCRIPTS / "validate_science_project.py"),
                "--root",
                str(destination),
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        self.assertEqual(process.returncode, 0, process.stdout)

    def test_v1_migration_preserves_backup_and_validates(self) -> None:
        self.initialize()
        science = self.root / ".science"
        study_path = science / "study.json"
        study = json.loads(study_path.read_text(encoding="utf-8"))
        study["schema"] = "codex-science.study.v1"
        study_path.write_text(json.dumps(study, indent=2) + "\n", encoding="utf-8")

        for relative in (
            "GOVERNANCE.md",
            "capabilities.json",
            "evidence/searches.jsonl",
            "datasets/registry.jsonl",
            "compute/jobs.jsonl",
            "forks.jsonl",
        ):
            (science / relative).unlink()

        self.run_script("migrate_project.py")
        backup = json.loads(
            (science / "study.v1.backup.json").read_text(encoding="utf-8")
        )
        migrated = json.loads(study_path.read_text(encoding="utf-8"))
        self.assertEqual(backup["schema"], "codex-science.study.v1")
        self.assertEqual(migrated["schema"], "codex-science.study.v2")
        self.assertEqual(migrated["migrated_from"], "codex-science.study.v1")
        self.run_script("validate_science_project.py")

    def test_unknown_evidence_references_are_rejected(self) -> None:
        self.initialize()
        output = self.run_script(
            "literature_ledger.py",
            "paper-card",
            "--id",
            "P404",
            "--source",
            "S404",
            "--question",
            "Can an unknown source be cited?",
            "--method",
            "Negative validation test",
            expected=2,
        ).stdout
        self.assertIn("unknown source", output.lower())

        output = self.run_script(
            "experiment_ledger.py",
            "plan",
            "--id",
            "E404",
            "--objective",
            "Reject a missing dataset",
            "--oracle",
            "The command exits with an error",
            "--threshold",
            "No event is written",
            "--dataset",
            "D404",
            expected=2,
        ).stdout
        self.assertIn("unknown dataset", output.lower())


if __name__ == "__main__":
    unittest.main()
