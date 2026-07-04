from __future__ import annotations

import http.server
import importlib.util
import json
import os
import pathlib
import subprocess
import tempfile
import threading
import unittest
import urllib.parse


ROOT = pathlib.Path(__file__).resolve().parents[1]
CONNECTOR = ROOT / "plugins/codex-science/skills/scientific-connectors/scripts/literature_connectors.py"
WORKBENCH = ROOT / "plugins/codex-science/skills/science-workbench/scripts"
SPEC = importlib.util.spec_from_file_location("literature_connectors", CONNECTOR)
assert SPEC and SPEC.loader
CONNECTOR_MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONNECTOR_MODULE)


class ProviderHandler(http.server.BaseHTTPRequestHandler):
    requests: list[str] = []

    def log_message(self, format: str, *args: object) -> None:
        return

    def do_GET(self) -> None:
        type(self).requests.append(self.path)
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        if parsed.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "/crossref/works")
            self.end_headers()
            return
        if parsed.path == "/crossref/works":
            value = {
                "status": "ok",
                "echo_contact": query.get("mailto", [""])[0],
                "message": {
                    "items": [
                        {
                            "DOI": "10.1000/example",
                            "title": ["Crossref fixture study"],
                            "author": [{"given": "Ada", "family": "Lovelace"}],
                            "published": {"date-parts": [[2024, 5, 1]]},
                            "type": "journal-article",
                            "URL": "https://doi.org/10.1000/example",
                            "container-title": ["Fixture Journal"],
                        }
                    ]
                },
            }
        elif parsed.path == "/eutils/esearch.fcgi":
            value = {
                "esearchresult": {"idlist": ["12345"]},
                "echo_email": query.get("email", [""])[0],
                "echo_key": query.get("api_key", [""])[0],
            }
        elif parsed.path == "/eutils/esummary.fcgi":
            value = {
                "result": {
                    "uids": ["12345"],
                    "12345": {
                        "title": "PubMed fixture study",
                        "pubdate": "2023 Jan",
                        "authors": [{"name": "Turing A"}],
                        "articleids": [{"idtype": "doi", "value": "10.1000/pubmed"}],
                        "pubtype": ["Journal Article"],
                        "fulljournalname": "Biomedical Fixtures",
                    },
                }
            }
        elif parsed.path == "/openalex/works":
            value = {
                "echo_key": query.get("api_key", [""])[0],
                "results": [
                    {
                        "id": "https://openalex.org/W1",
                        "doi": "https://doi.org/10.1000/openalex",
                        "title": "OpenAlex fixture study",
                        "publication_year": 2022,
                        "authorships": [{"author": {"display_name": "Grace Hopper"}}],
                        "type": "article",
                        "primary_location": {"source": {"display_name": "Open Fixtures"}},
                    }
                ]
            }
        else:
            self.send_error(404)
            return
        payload = json.dumps(value).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


class ConnectorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), ProviderHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="codex-science-connectors-")
        self.root = pathlib.Path(self.temp.name)
        ProviderHandler.requests.clear()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_script(
        self,
        script: pathlib.Path,
        *arguments: str,
        expected: int = 0,
        environment: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        if environment:
            env.update(environment)
        process = subprocess.run(
            ["python3", str(script), *arguments],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env,
        )
        self.assertEqual(process.returncode, expected, process.stdout)
        return process

    def test_crossref_snapshot_and_explicit_import(self) -> None:
        output = self.root / "crossref.json"
        self.run_script(
            CONNECTOR,
            "crossref",
            "--query",
            "fixture query",
            "--limit",
            "1",
            "--base-url",
            self.base + "/crossref/works",
            "--output",
            str(output),
            environment={"CROSSREF_MAILTO": "researcher@example.org"},
        )
        snapshot = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(snapshot["results"][0]["doi"], "10.1000/example")
        self.assertNotIn("mailto=", snapshot["requests"][0]["url"])
        self.assertNotIn("researcher@example.org", output.read_text(encoding="utf-8"))
        self.assertNotIn("researcher%40example.org", ProviderHandler.requests[0])

        self.run_script(
            WORKBENCH / "init_science_project.py",
            "--root",
            str(self.root),
            "--title",
            "Connector import",
            "--question",
            "Can selected metadata be imported safely?",
        )
        self.run_script(
            CONNECTOR,
            "import",
            "--root",
            str(self.root),
            "--file",
            str(output),
            "--prefix",
            "CR",
            "--search-id",
            "Q-CR-001",
            "--reason",
            "Screen one Crossref result",
            "--select",
            "1",
        )
        source = json.loads(
            (self.root / ".science/evidence/sources.jsonl").read_text(encoding="utf-8")
        )
        search = json.loads(
            (self.root / ".science/evidence/searches.jsonl").read_text(encoding="utf-8")
        )
        self.assertEqual(source["id"], "CR001")
        self.assertEqual(source["access_status"], "metadata-only")
        self.assertEqual(source["review_status"], "unknown")
        self.assertEqual(search["selected_sources"], ["CR001"])
        self.run_script(
            WORKBENCH / "validate_science_project.py", "--root", str(self.root)
        )
        self.run_script(
            WORKBENCH / "build_research_packet.py", "--root", str(self.root)
        )
        packet = next((self.root / ".science/artifacts").glob("research-packet-*.md"))
        packet_text = packet.read_text(encoding="utf-8")
        self.assertIn("Q-CR-001", packet_text)
        self.assertIn("crossref.json", packet_text)

    def test_custom_endpoints_do_not_receive_credentials_and_redaction_helpers(self) -> None:
        pubmed = self.root / "pubmed.json"
        self.run_script(
            CONNECTOR,
            "pubmed",
            "--query",
            "biomarker",
            "--base-url",
            self.base + "/eutils",
            "--output",
            str(pubmed),
            environment={"NCBI_EMAIL": "private@example.org", "NCBI_API_KEY": "ncbi-secret-value"},
        )
        pubmed_value = json.loads(pubmed.read_text(encoding="utf-8"))
        self.assertEqual(pubmed_value["results"][0]["provider_id"], "12345")
        self.assertEqual(pubmed_value["results"][0]["doi"], "10.1000/pubmed")
        pubmed_text = pubmed.read_text(encoding="utf-8")
        self.assertNotIn("private@example.org", pubmed_text)
        self.assertNotIn("ncbi-secret-value", pubmed_text)
        self.assertTrue(all("api_key=" not in item["url"] for item in pubmed_value["requests"]))
        self.assertTrue(all("email=" not in item["url"] for item in pubmed_value["requests"]))

        openalex = self.root / "openalex.json"
        self.run_script(
            CONNECTOR,
            "openalex",
            "--query",
            "open science",
            "--base-url",
            self.base + "/openalex/works",
            "--output",
            str(openalex),
            environment={"OPENALEX_API_KEY": "openalex-secret-value"},
        )
        openalex_value = json.loads(openalex.read_text(encoding="utf-8"))
        self.assertEqual(openalex_value["results"][0]["doi"], "10.1000/openalex")
        self.assertNotIn("api_key=", openalex_value["requests"][0]["url"])
        self.assertNotIn("openalex-secret-value", openalex.read_text(encoding="utf-8"))
        request_text = "\n".join(ProviderHandler.requests)
        self.assertNotIn("private%40example.org", request_text)
        self.assertNotIn("ncbi-secret-value", request_text)
        self.assertNotIn("openalex-secret-value", request_text)

        sanitized = CONNECTOR_MODULE.sanitized_url(
            "https://example.test/works?api_key=secret&query=biology"
        )
        self.assertIn("api_key=REDACTED", sanitized)
        redacted = CONNECTOR_MODULE.redact(
            {"nested": ["prefix-secret-suffix"], "token": "secret"}, ["secret"]
        )
        self.assertEqual(redacted["nested"], ["prefix-REDACTED-suffix"])
        self.assertEqual(redacted["token"], "REDACTED")

    def test_production_openalex_requires_key_and_external_http_is_rejected(self) -> None:
        environment = os.environ.copy()
        environment.pop("OPENALEX_API_KEY", None)
        process = subprocess.run(
            [
                "python3",
                str(CONNECTOR),
                "openalex",
                "--query",
                "test",
                "--output",
                str(self.root / "missing-key.json"),
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=environment,
        )
        self.assertEqual(process.returncode, 2, process.stdout)
        self.assertIn("OPENALEX_API_KEY", process.stdout)

        output = self.run_script(
            CONNECTOR,
            "crossref",
            "--query",
            "test",
            "--base-url",
            "http://example.org/works",
            "--output",
            str(self.root / "http.json"),
            expected=2,
        ).stdout
        self.assertIn("must use HTTPS", output)

        redirect_output = self.run_script(
            CONNECTOR,
            "crossref",
            "--query",
            "test",
            "--base-url",
            self.base + "/redirect",
            "--output",
            str(self.root / "redirect.json"),
            expected=2,
        ).stdout
        self.assertIn("HTTP Error 302", redirect_output)
        self.assertEqual(len(ProviderHandler.requests), 1)


if __name__ == "__main__":
    unittest.main()
