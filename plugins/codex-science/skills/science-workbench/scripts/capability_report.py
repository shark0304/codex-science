#!/usr/bin/env python3
"""Write a secret-free capability inventory for optional scientific tools."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import shutil
import subprocess
import sys


TOOLS = {
    "python": ("python3", ["--version"]),
    "r": ("R", ["--version"]),
    "julia": ("julia", ["--version"]),
    "git": ("git", ["--version"]),
    "jupyter": ("jupyter", ["--version"]),
    "pandoc": ("pandoc", ["--version"]),
    "quarto": ("quarto", ["--version"]),
    "latex": ("latexmk", ["--version"]),
    "docker": ("docker", ["--version"]),
    "podman": ("podman", ["--version"]),
    "ssh": ("ssh", ["-V"]),
    "slurm_submit": ("sbatch", ["--version"]),
    "slurm_queue": ("squeue", ["--version"]),
    "modal": ("modal", ["--version"]),
    "nvidia_gpu": ("nvidia-smi", ["--query-gpu=name,driver_version,memory.total", "--format=csv,noheader"]),
}


def probe(executable: str, arguments: list[str]) -> dict[str, object]:
    path = shutil.which(executable)
    if not path:
        return {"status": "unavailable", "path": "", "version": ""}
    try:
        proc = subprocess.run(
            [path, *arguments],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=5,
        )
        output = proc.stdout.strip().splitlines()
        return {
            "status": "ready" if proc.returncode == 0 else "degraded",
            "path": path,
            "version": output[0][:500] if output else "",
            "exit_code": proc.returncode,
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "degraded", "path": path, "version": "", "error": str(exc)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=pathlib.Path, required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    path = args.root.expanduser().resolve() / ".science/capabilities.json"
    if not path.parent.is_dir():
        print(f"ERROR: initialize a Codex Science project first: {path.parent}", file=sys.stderr)
        return 2
    tools = {name: probe(executable, options) for name, (executable, options) in TOOLS.items()}
    report = {
        "schema": "codex-science.capabilities.v1",
        "captured_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "capabilities": {
            "local_compute": {"status": "ready", "evidence": ["current process environment"]},
            "ssh_compute": {"status": tools["ssh"]["status"], "evidence": [tools["ssh"]["path"]]},
            "slurm_compute": {
                "status": "ready" if tools["slurm_submit"]["status"] == tools["slurm_queue"]["status"] == "ready" else "unavailable",
                "evidence": [tools["slurm_submit"]["path"], tools["slurm_queue"]["path"]],
            },
            "modal_compute": {"status": tools["modal"]["status"], "evidence": [tools["modal"]["path"]]},
            "notebook": {"status": tools["jupyter"]["status"], "evidence": [tools["jupyter"]["path"]]},
            "document_rendering": {
                "status": "ready" if tools["pandoc"]["status"] == "ready" or tools["quarto"]["status"] == "ready" else "degraded",
                "evidence": [tools["pandoc"]["path"], tools["quarto"]["path"]],
            },
            "gpu_compute": {"status": tools["nvidia_gpu"]["status"], "evidence": [tools["nvidia_gpu"]["path"]]},
            "scientific_connectors": {
                "status": "not-verified",
                "evidence": [],
                "note": "Connector authorization is a Codex deployment capability and is not inferred from local files.",
            },
            "independent_reviewer": {
                "status": "not-verified",
                "evidence": [],
                "note": "Requires a fresh reviewer context or explicitly authorized reviewer agent.",
            },
        },
        "tools": tools,
        "privacy": "Environment variables, credentials and file contents are excluded; executable paths may contain local account names.",
    }
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        for name, capability in report["capabilities"].items():
            print(f"{name:24} {capability['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
