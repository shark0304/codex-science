#!/usr/bin/env python3
"""Shared primitives for the Codex Science loop ledgers."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import pathlib
import re
import tempfile
from typing import Any


ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9._-]{0,63}$")


class LoopError(ValueError):
    """A user-correctable loop state or input error."""


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def digest(path: pathlib.Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def file_identity(value: str | pathlib.Path) -> dict[str, object]:
    path = pathlib.Path(value).expanduser().resolve()
    if not path.is_file():
        raise LoopError(f"file is unavailable: {path}")
    return {"path": str(path), "sha256": digest(path), "bytes": path.stat().st_size}


def validate_identity(value: object, label: str, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{label}: identity must be an object")
        return
    path_value = value.get("path")
    expected = value.get("sha256")
    size = value.get("bytes")
    if not isinstance(path_value, str) or not path_value:
        errors.append(f"{label}: missing path")
        return
    if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
        errors.append(f"{label}: invalid SHA-256")
        return
    if not isinstance(size, int) or size < 0:
        errors.append(f"{label}: invalid byte size")
    path = pathlib.Path(path_value)
    if not path.is_file():
        errors.append(f"{label}: file is unavailable: {path}")
        return
    if digest(path) != expected:
        errors.append(f"{label}: SHA-256 mismatch: {path}")
    if path.stat().st_size != size:
        errors.append(f"{label}: byte-size mismatch: {path}")


def validate_id(value: str, label: str = "id") -> str:
    if not ID_RE.fullmatch(value):
        raise LoopError(f"{label} must match {ID_RE.pattern}")
    return value


def science_dir(root: pathlib.Path) -> pathlib.Path:
    return root.expanduser().resolve() / ".science"


def require_study(root: pathlib.Path) -> pathlib.Path:
    science = science_dir(root)
    if not (science / "study.json").is_file():
        raise LoopError(f"missing Codex Science study: {science / 'study.json'}")
    return science


def require_loop(root: pathlib.Path) -> pathlib.Path:
    loop = require_study(root) / "loop"
    if not (loop / "contract.json").is_file():
        raise LoopError(f"loop is not initialized: {loop}")
    return loop


def read_json(path: pathlib.Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LoopError(f"invalid JSON at {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise LoopError(f"JSON root must be an object: {path}")
    return value


def read_jsonl(path: pathlib.Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise LoopError(f"cannot read {path}: {exc}") from exc
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise LoopError(f"{path}:{number}: invalid JSON: {exc}") from exc
        if not isinstance(value, dict):
            raise LoopError(f"{path}:{number}: record must be an object")
        records.append(value)
    return records


def append_jsonl(path: pathlib.Path, record: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def atomic_json(path: pathlib.Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        temporary = pathlib.Path(stream.name)
    temporary.replace(path)


def ensure_new(records: list[dict[str, Any]], identifier: str, label: str) -> None:
    if any(record.get("id") == identifier for record in records):
        raise LoopError(f"duplicate {label} id: {identifier}")


def latest_gate_evaluations(
    evaluations: list[dict[str, Any]], iteration_id: str
) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for evaluation in evaluations:
        if evaluation.get("iteration_id") == iteration_id:
            gate_id = evaluation.get("gate_id")
            if isinstance(gate_id, str):
                latest[gate_id] = evaluation
    return latest


def load_contract(loop: pathlib.Path) -> dict[str, Any]:
    contract = read_json(loop / "contract.json")
    if contract.get("schema") != "codex-science.loop-contract.v1":
        raise LoopError("unsupported loop contract schema")
    return contract


def load_lock(loop: pathlib.Path) -> dict[str, dict[str, Any]]:
    value = read_json(loop / "capability-lock.json")
    if value.get("schema") != "codex-science.capability-lock.v1":
        raise LoopError("unsupported capability lock schema")
    capabilities = value.get("capabilities")
    if not isinstance(capabilities, list):
        raise LoopError("capability lock entries must be a list")
    return {
        str(item.get("id")): item
        for item in capabilities
        if isinstance(item, dict) and item.get("id")
    }
