from __future__ import annotations

import json
import os
import pathlib
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins/codex-science/skills/science-workbench/scripts"
CLI = SCRIPTS / "science.py"


class ResearchPortalTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="codex-science-portal-")
        self.root = pathlib.Path(self.temp.name)
        self.study = self.root / "study"
        self.run_cli(
            "init",
            "--root",
            str(self.study),
            "--title",
            "Visual research workspace",
            "--question",
            "Can an offline portal preserve research context safely?",
            "--profile",
            "quick",
            "--domain",
            "general",
        )

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

    def run_script(self, name: str, *arguments: str, expected: int = 0) -> str:
        process = subprocess.run(
            ["python3", str(SCRIPTS / name), "--root", str(self.study), *arguments],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        self.assertEqual(process.returncode, expected, process.stdout)
        return process.stdout

    def test_portal_resume_and_parity_are_safe_and_inspectable(self) -> None:
        science = self.study / ".science"
        malicious_title = "Evidence <script>alert('x')</script> & review"
        self.run_script(
            "science_ledger.py",
            "add-source",
            "--id",
            "S001",
            "--title",
            malicious_title,
            "--location",
            "https://example.org/evidence",
            "--type",
            "paper",
            "--review-status",
            "unknown",
        )
        self.run_script(
            "literature_ledger.py",
            "search",
            "--id",
            "Q001",
            "--query",
            "offline research portal",
            "--database",
            "fixture-index",
            "--reason",
            "Exercise the visual evidence view",
            "--selected",
            "S001",
        )
        self.run_script(
            "science_ledger.py",
            "add-claim",
            "--id",
            "C001",
            "--text",
            "The fixture source is visible in the local portal.",
            "--status",
            "observed",
            "--sources",
            "S001",
        )
        secret = "portal-secret-must-not-appear"
        doctor_output = self.run_cli(
            "doctor",
            "--root",
            str(self.study),
            "--save",
            "--json",
            environment={"OPENALEX_API_KEY": secret},
        ).stdout
        self.assertNotIn(secret, doctor_output)
        self.run_cli("parity", "--root", str(self.study), "--save")
        self.run_cli("resume", "--root", str(self.study))
        self.run_cli("portal", "--root", str(self.study))
        self.run_cli("validate", "--root", str(self.study))

        portal = (science / "PORTAL.html").read_text(encoding="utf-8")
        self.assertIn("Research pulse", portal)
        self.assertIn("Public Claude Science capability audit", portal)
        self.assertIn("Content-Security-Policy", portal)
        self.assertNotIn("<script", portal.lower())
        self.assertNotIn(malicious_title, portal)
        self.assertIn("Evidence &lt;script&gt;alert", portal)
        self.assertNotIn(secret, portal)

        resume = (science / "RESUME.md").read_text(encoding="utf-8")
        study = json.loads((science / "study.json").read_text(encoding="utf-8"))
        self.assertIn(study["id"], resume)
        self.assertIn("## New-thread prompt", resume)
        self.assertIn("$science-workbench", resume)

        parity = json.loads((science / "PARITY.json").read_text(encoding="utf-8"))
        self.assertEqual(parity["schema"], "codex-science.parity-report.v1")
        self.assertEqual(parity["counts"], {"degraded": 4, "ready": 4, "unavailable": 1})
        self.assertEqual(len(parity["capabilities"]), 9)
        self.assertEqual(
            parity["source"]["url"],
            "https://www.anthropic.com/news/claude-science-ai-workbench",
        )

    def test_parity_tampering_is_rejected(self) -> None:
        science = self.study / ".science"
        parity = json.loads((science / "PARITY.json").read_text(encoding="utf-8"))
        parity["capabilities"][0]["status"] = "perfect-parity"
        (science / "PARITY.json").write_text(
            json.dumps(parity, indent=2) + "\n", encoding="utf-8"
        )
        output = self.run_cli(
            "validate", "--root", str(self.study), expected=2
        ).stdout
        self.assertIn("invalid status", output)


if __name__ == "__main__":
    unittest.main()
