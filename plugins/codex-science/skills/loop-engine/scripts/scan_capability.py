#!/usr/bin/env python3
"""Statically inventory and scan a local skill, plugin, or tool checkout."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import sys

from _loop_common import LoopError, atomic_json, digest, utc_now


SKIP_DIRECTORIES = {".git", "__pycache__", ".pytest_cache", ".ruff_cache", "node_modules"}
TEXT_SUFFIXES = {
    "",
    ".bash",
    ".cfg",
    ".ini",
    ".js",
    ".json",
    ".md",
    ".mjs",
    ".py",
    ".sh",
    ".toml",
    ".ts",
    ".txt",
    ".yaml",
    ".yml",
}
CRITICAL_PATTERNS = {
    "EMBEDDED_PRIVATE_KEY": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "EMBEDDED_GITHUB_TOKEN": re.compile(r"\b(?:ghp|github_pat)_[A-Za-z0-9_]{20,}\b"),
    "EMBEDDED_API_SECRET": re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    "ASSIGNED_AUTH_SECRET": re.compile(
        r"(?:ANTHROPIC_AUTH_TOKEN|OPENAI_API_KEY)\s*=\s*['\"]?(?!<|\$\{)[^\s'\"]{12,}"
    ),
    "DESTRUCTIVE_ROOT_DELETE": re.compile(r"\brm\s+-[A-Za-z]*r[A-Za-z]*f[A-Za-z]*\s+/(?:\s|$)"),
}
WARNING_PATTERNS = {
    "PIPE_TO_SHELL": re.compile(r"(?:curl|wget)[^\n|]{0,300}\|\s*(?:ba)?sh\b", re.IGNORECASE),
    "SHELL_TRUE": re.compile(r"shell\s*=\s*True"),
    "OS_SYSTEM": re.compile(r"\bos\.system\s*\("),
    "PRIVILEGE_ESCALATION": re.compile(r"(?:^|\s)sudo(?:\s|$)"),
    "WORLD_WRITABLE": re.compile(r"\bchmod\s+(?:-R\s+)?777\b"),
    "PACKAGE_INSTALL": re.compile(r"(?:pip|pip3|npm|pnpm|yarn|uv)\s+(?:install|add)\b"),
    "NETWORK_CODE": re.compile(r"\b(?:requests\.(?:get|post)|urllib\.request|fetch\s*\(|curl\s|wget\s)"),
    "SUBPROCESS": re.compile(r"\bsubprocess\.(?:run|Popen|call|check_output|check_call)\s*\("),
}


def finding(
    severity: str, code: str, relative: str, line: int | None, message: str
) -> dict[str, object]:
    return {
        "severity": severity,
        "code": code,
        "path": relative,
        "line": line,
        "message": message,
    }


def inventory(root: pathlib.Path, output: pathlib.Path) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    files: list[dict[str, object]] = []
    findings: list[dict[str, object]] = []
    for current, directories, names in os.walk(root, followlinks=False):
        current_path = pathlib.Path(current)
        kept = []
        for name in sorted(directories):
            path = current_path / name
            relative = path.relative_to(root).as_posix()
            if name in SKIP_DIRECTORIES:
                continue
            if path.is_symlink():
                link_value = os.readlink(path)
                files.append(
                    {
                        "path": relative,
                        "sha256": hashlib.sha256(("symlink:" + link_value).encode("utf-8")).hexdigest(),
                        "bytes": len(link_value.encode("utf-8")),
                        "kind": "symlink",
                    }
                )
                try:
                    target = path.resolve(strict=True)
                    target.relative_to(root)
                    severity = "warning"
                    message = f"directory symlink resolves inside candidate: {target}"
                except (FileNotFoundError, ValueError):
                    severity = "critical"
                    message = "directory symlink is broken or escapes candidate root"
                findings.append(finding(severity, "SYMLINK_DIRECTORY", relative, None, message))
                continue
            kept.append(name)
        directories[:] = kept

        for name in sorted(names):
            path = current_path / name
            if path.resolve(strict=False) == output.resolve(strict=False):
                continue
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                link_value = os.readlink(path)
                files.append(
                    {
                        "path": relative,
                        "sha256": hashlib.sha256(("symlink:" + link_value).encode("utf-8")).hexdigest(),
                        "bytes": len(link_value.encode("utf-8")),
                        "kind": "symlink",
                    }
                )
                try:
                    target = path.resolve(strict=True)
                    target.relative_to(root)
                    severity = "warning"
                    message = f"file symlink resolves inside candidate: {target}"
                except (FileNotFoundError, ValueError):
                    severity = "critical"
                    message = "file symlink is broken or escapes candidate root"
                findings.append(finding(severity, "SYMLINK_FILE", relative, None, message))
                continue
            if not path.is_file():
                continue
            size = path.stat().st_size
            checksum = digest(path)
            files.append({"path": relative, "sha256": checksum, "bytes": size, "kind": "file"})
            if path.suffix.lower() not in TEXT_SUFFIXES or size > 1024 * 1024:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for code, pattern in CRITICAL_PATTERNS.items():
                match = pattern.search(text)
                if match:
                    line = text.count("\n", 0, match.start()) + 1
                    findings.append(finding("critical", code, relative, line, "critical static pattern matched"))
            for code, pattern in WARNING_PATTERNS.items():
                match = pattern.search(text)
                if match:
                    line = text.count("\n", 0, match.start()) + 1
                    findings.append(finding("warning", code, relative, line, "manual review required"))
    return files, findings


def tree_digest(files: list[dict[str, object]]) -> str:
    value = hashlib.sha256()
    for item in sorted(files, key=lambda candidate: str(candidate["path"])):
        value.update(str(item["path"]).encode("utf-8"))
        value.update(str(item["sha256"]).encode("ascii"))
        value.update(str(item["bytes"]).encode("ascii"))
        value.update(str(item.get("kind", "file")).encode("ascii"))
    return value.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    root = args.path.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if not root.is_dir():
        print(f"ERROR: candidate directory is unavailable: {root}", file=sys.stderr)
        return 2
    try:
        files, findings = inventory(root, output)
        if len(files) > 10000:
            raise LoopError("candidate exceeds 10,000 files; narrow the scan scope")
        relative_paths = {str(item["path"]) for item in files}
        if "SKILL.md" not in relative_paths and ".codex-plugin/plugin.json" not in relative_paths:
            findings.append(
                finding(
                    "warning",
                    "CAPABILITY_METADATA_MISSING",
                    ".",
                    None,
                    "candidate has neither root SKILL.md nor .codex-plugin/plugin.json",
                )
            )
        critical = sum(item["severity"] == "critical" for item in findings)
        warnings = sum(item["severity"] == "warning" for item in findings)
        status = "block" if critical else "review" if warnings else "pass"
        report = {
            "schema": "codex-science.capability-scan.v1",
            "created_at": utc_now(),
            "root": str(root),
            "status": status,
            "tree_sha256": tree_digest(files),
            "file_count": len(files),
            "total_bytes": sum(int(item["bytes"]) for item in files),
            "summary": {"critical": critical, "warnings": warnings},
            "findings": findings,
            "files": files,
            "limitations": "Static pattern scanning does not establish safety, intent, license, dependency integrity, or scientific validity.",
        }
        atomic_json(output, report)
    except (LoopError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(
        f"Capability scan: {status.upper()} ({len(files)} files, "
        f"{critical} critical, {warnings} warnings) -> {output}"
    )
    return 3 if status == "block" else 0


if __name__ == "__main__":
    raise SystemExit(main())
