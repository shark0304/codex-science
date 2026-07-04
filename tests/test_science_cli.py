from __future__ import annotations

import json
import os
import pathlib
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKBENCH = ROOT / "plugins/codex-science/skills/science-workbench/scripts"
CLI = WORKBENCH / "science.py"


class ScienceCliTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="codex-science-cli-")
        self.root = pathlib.Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_cli(
        self,
        *arguments: str,
        expected: int = 0,
        environment: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        if environment:
            env.update(environment)
        process = subprocess.run(
            ["python3", str(CLI), *arguments],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env,
        )
        self.assertEqual(process.returncode, expected, process.stdout)
        return process

    def initialize(self, profile: str = "standard") -> pathlib.Path:
        study = self.root / "study"
        self.run_cli(
            "init",
            "--root",
            str(study),
            "--title",
            "Unified research service",
            "--question",
            "Can one entry point preserve an auditable research workflow?",
            "--profile",
            profile,
            "--domain",
            "computational-science",
        )
        return study

    def test_service_catalog_and_doctor_never_emit_secret_values(self) -> None:
        catalog = json.loads(self.run_cli("services", "--json").stdout)
        self.assertEqual(catalog["schema"], "codex-science.service-catalog.v1")
        self.assertGreaterEqual(len(catalog["services"]), 10)

        secrets = {
            "CROSSREF_MAILTO": "private-contact@example.org",
            "NCBI_EMAIL": "private-ncbi@example.org",
            "NCBI_API_KEY": "private-ncbi-key",
            "OPENALEX_API_KEY": "private-openalex-key",
        }
        output = self.run_cli(
            "doctor", "--root", str(self.root), "--json", environment=secrets
        ).stdout
        for value in secrets.values():
            self.assertNotIn(value, output)
        doctor = json.loads(output)
        self.assertTrue(
            all(item["configured"] for item in doctor["credentials"].values())
        )
        self.assertEqual(doctor["providers"]["openalex"]["status"], "ready")
        self.assertGreaterEqual(len(doctor["skills"]), 8)

    def test_guided_init_status_next_and_configuration(self) -> None:
        study = self.initialize("deep")
        science = study / ".science"
        workflow = json.loads((science / "workflow.json").read_text(encoding="utf-8"))
        self.assertEqual(workflow["profile"], "deep")
        self.assertEqual(workflow["domain"], "computational-science")
        self.assertEqual(workflow["stages"]["iteration"], "required")

        status = json.loads(
            self.run_cli(
                "status", "--root", str(study), "--json", "--no-write"
            ).stdout
        )
        self.assertEqual(status["schema"], "codex-science.status.v1")
        self.assertEqual(len(status["stages"]), 11)
        self.assertEqual(status["next_actions"][0]["stage"], "framing")
        self.assertIn("[framing]", self.run_cli("next", "--root", str(study)).stdout)

        self.run_cli(
            "configure",
            "--root",
            str(study),
            "--stage",
            "data=not-requested",
            "--stage",
            "protocol=not-requested",
        )
        configured = json.loads((science / "workflow.json").read_text(encoding="utf-8"))
        self.assertEqual(configured["stages"]["data"], "not-requested")
        self.assertEqual(configured["stages"]["protocol"], "not-requested")
        self.run_cli("validate", "--root", str(study))

        configured["stages"]["data"] = "pretend-passed"
        (science / "workflow.json").write_text(
            json.dumps(configured, indent=2) + "\n", encoding="utf-8"
        )
        invalid = self.run_cli(
            "validate", "--root", str(study), expected=2
        ).stdout
        self.assertIn("invalid requirement", invalid)

    def test_handoff_builds_packet_and_refreshes_dashboard(self) -> None:
        study = self.initialize("quick")
        handoff_output = self.run_cli(
            "handoff", "--root", str(study), expected=1
        ).stdout
        self.assertIn("milestone completion remains blocked", handoff_output)
        self.assertIn("framing", handoff_output)
        self.assertIn("evidence", handoff_output)
        science = study / ".science"
        status = json.loads((science / "STATUS.json").read_text(encoding="utf-8"))
        handoff = next(item for item in status["stages"] if item["id"] == "handoff")
        self.assertEqual(handoff["status"], "ready")
        packets = sorted((science / "artifacts").glob("research-packet-*.md"))
        self.assertEqual(len(packets), 1)
        self.assertIn("Research workflow dashboard", packets[0].read_text(encoding="utf-8"))
        manifest = [
            json.loads(line)
            for line in (science / "artifacts/manifest.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertEqual(manifest[-1]["kind"], "research-packet")
        self.run_cli("validate", "--root", str(study))

    def test_quick_profile_can_reach_an_honest_handoff(self) -> None:
        study = self.initialize("quick")
        science = study / ".science"
        (science / "QUESTION.md").write_text(
            "# Research question\n\nCan the unified workflow preserve evidence?\n\n"
            "## Scope\n\n- Population or system: local research projects\n\n"
            "## Hypotheses and falsifiers\n\n- Evidence that would falsify the hypothesis: a broken source reference\n",
            encoding="utf-8",
        )
        (science / "PLAN.md").write_text(
            "# Study plan\n\n## Success criteria and test oracle\n\n"
            "The project validator accepts every recorded reference.\n",
            encoding="utf-8",
        )

        def run_script(name: str, *arguments: str) -> None:
            process = subprocess.run(
                [
                    "python3",
                    str(WORKBENCH / name),
                    "--root",
                    str(study),
                    *arguments,
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            self.assertEqual(process.returncode, 0, process.stdout)

        run_script(
            "science_ledger.py",
            "add-source",
            "--id",
            "S001",
            "--title",
            "Workflow fixture",
            "--location",
            "https://example.org/workflow",
            "--type",
            "paper",
            "--review-status",
            "unknown",
        )
        run_script(
            "literature_ledger.py",
            "search",
            "--id",
            "Q001",
            "--query",
            "auditable workflow",
            "--database",
            "fixture-index",
            "--reason",
            "Test the unified handoff",
            "--selected",
            "S001",
        )
        run_script(
            "science_ledger.py",
            "add-claim",
            "--id",
            "C001",
            "--text",
            "The fixture has a recorded source.",
            "--status",
            "observed",
            "--sources",
            "S001",
        )
        output = self.run_cli("handoff", "--root", str(study)).stdout
        self.assertIn("Handoff complete", output)
        status = json.loads((science / "STATUS.json").read_text(encoding="utf-8"))
        self.assertEqual(status["required_ready"], status["required_total"])

    def test_existing_v2_project_can_add_workflow_and_eval_passthrough(self) -> None:
        study = self.initialize()
        workflow = study / ".science/workflow.json"
        workflow.unlink()
        process = subprocess.run(
            [
                "python3",
                str(WORKBENCH / "migrate_project.py"),
                "--root",
                str(study),
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        self.assertEqual(process.returncode, 0, process.stdout)
        self.assertTrue(workflow.is_file())

        run = self.root / "eval-run"
        self.run_cli(
            "eval",
            "init",
            "--run-dir",
            str(run),
            "--system",
            "codex-science",
            "--model",
            "cli-test",
            "--repetitions",
            "1",
        )
        self.run_cli("eval", "grade", "--run-dir", str(run))
        self.run_cli("eval", "validate", "--run-dir", str(run))
        scores = json.loads((run / "scores.json").read_text(encoding="utf-8"))
        self.assertEqual(scores["recorded_attempts"], 0)
        self.assertEqual(scores["expected_attempts"], 8)


if __name__ == "__main__":
    unittest.main()
