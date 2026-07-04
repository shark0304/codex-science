#!/usr/bin/env python3
"""Capture a secret-free local environment snapshot and register its checksum."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import platform
import re
import socket
import subprocess
import sys
import uuid


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def digest(path: pathlib.Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def run(command: list[str], cwd: pathlib.Path) -> dict[str, object]:
    try:
        proc = subprocess.run(
            command,
            cwd=cwd,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"available": False, "error": str(exc)}
    return {
        "available": proc.returncode == 0,
        "exit_code": proc.returncode,
        "output": proc.stdout.strip()[:8192],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=pathlib.Path, required=True)
    parser.add_argument("--label", default="environment")
    parser.add_argument("--hash", dest="hashes", type=pathlib.Path, action="append", default=[])
    args = parser.parse_args()

    root = args.root.expanduser().resolve()
    science = root / ".science"
    runs = science / "runs"
    manifest = science / "artifacts" / "manifest.jsonl"
    if not runs.is_dir() or not manifest.is_file():
        print(f"ERROR: initialize a Codex Science project first: {science}", file=sys.stderr)
        return 2

    captured_at = utc_now()
    label = re.sub(r"[^a-zA-Z0-9._-]+", "-", args.label).strip("-") or "environment"
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = runs / f"environment-{label}-{stamp}-{uuid.uuid4().hex[:8]}.json"

    files = []
    for value in args.hashes:
        path = value.expanduser().resolve()
        if not path.is_file():
            print(f"ERROR: hash input is not a file: {path}", file=sys.stderr)
            return 2
        files.append({"path": str(path), "sha256": digest(path), "bytes": path.stat().st_size})

    snapshot = {
        "schema": "codex-science.environment.v1",
        "captured_at": captured_at,
        "label": args.label,
        "working_directory": str(root),
        "host": {
            "hostname": socket.gethostname(),
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "cpu_count": os.cpu_count(),
            "python": platform.python_version(),
        },
        "git": {
            "revision": run(["git", "rev-parse", "HEAD"], root),
            "branch": run(["git", "branch", "--show-current"], root),
            "status": run(["git", "status", "--porcelain"], root),
        },
        "hashed_files": files,
        "privacy": "Environment variables and credentials are intentionally excluded.",
    }
    output.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    artifact = {
        "id": "A-" + uuid.uuid4().hex[:12],
        "created_at": captured_at,
        "path": str(output),
        "kind": "environment",
        "sha256": digest(output),
        "bytes": output.stat().st_size,
        "command": "capture_environment.py",
        "inputs": files,
        "environment": {
            "platform": platform.platform(),
            "python": platform.python_version(),
        },
    }
    with manifest.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(artifact, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"Captured environment at {output}")
    print(f"Registered {artifact['id']} sha256={artifact['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
