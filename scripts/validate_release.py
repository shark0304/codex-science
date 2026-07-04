#!/usr/bin/env python3
"""Validate the public Codex Science repository without third-party packages."""

from __future__ import annotations

import json
import pathlib
import re
import stat
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins/codex-science"
MANIFEST = PLUGIN / ".codex-plugin/plugin.json"
MARKETPLACE = ROOT / ".agents/plugins/marketplace.json"
SEMVER = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)
SKILL_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SECRET_PATTERNS = {
    "GitHub token": re.compile(r"\b(?:ghp|github_pat)_[A-Za-z0-9_]{20,}\b"),
    "API secret": re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "assigned auth token": re.compile(
        r"(?:ANTHROPIC_AUTH_TOKEN|OPENAI_API_KEY)\s*=\s*['\"]?(?!<|\$\{)[^\s'\"]{12,}"
    ),
}
TEXT_SUFFIXES = {
    "",
    ".json",
    ".md",
    ".py",
    ".txt",
    ".yaml",
    ".yml",
}


def load_json(path: pathlib.Path, errors: list[str]) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors.append(f"{path.relative_to(ROOT)}: invalid JSON: {exc}")
        return {}


def is_within(path: pathlib.Path, parent: pathlib.Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def parse_frontmatter(path: pathlib.Path, errors: list[str]) -> dict[str, str]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        errors.append(f"{path.relative_to(ROOT)}: unreadable: {exc}")
        return {}
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        errors.append(f"{path.relative_to(ROOT)}: missing YAML frontmatter")
        return {}
    try:
        end = lines.index("---", 1)
    except ValueError:
        errors.append(f"{path.relative_to(ROOT)}: unterminated YAML frontmatter")
        return {}
    values: dict[str, str] = {}
    for line in lines[1:end]:
        if ":" not in line or line[:1].isspace():
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip().strip("'\"")
    return values


def validate_manifest(errors: list[str]) -> None:
    value = load_json(MANIFEST, errors)
    if not isinstance(value, dict):
        errors.append("plugin.json: root must be an object")
        return
    for key in ("name", "version", "description", "author", "license", "skills", "interface"):
        if key not in value:
            errors.append(f"plugin.json: missing {key}")
    if value.get("name") != "codex-science":
        errors.append("plugin.json: name must be codex-science")
    if not isinstance(value.get("version"), str) or not SEMVER.fullmatch(str(value.get("version"))):
        errors.append("plugin.json: version must be semantic x.y.z")
    if value.get("license") != "MIT":
        errors.append("plugin.json: public release must declare MIT")
    if value.get("skills") != "./skills/":
        errors.append("plugin.json: skills must point to ./skills/")
    author = value.get("author")
    if not isinstance(author, dict) or not author.get("name"):
        errors.append("plugin.json: author.name is required")
    interface = value.get("interface")
    for key in ("displayName", "shortDescription", "longDescription", "developerName", "category"):
        if not isinstance(interface, dict) or not interface.get(key):
            errors.append(f"plugin.json: interface.{key} is required")


def validate_marketplace(errors: list[str]) -> None:
    value = load_json(MARKETPLACE, errors)
    if not isinstance(value, dict) or value.get("name") != "codex-science":
        errors.append("marketplace.json: marketplace name must be codex-science")
        return
    plugins = value.get("plugins")
    if not isinstance(plugins, list) or len(plugins) != 1 or not isinstance(plugins[0], dict):
        errors.append("marketplace.json: exactly one plugin entry is required")
        return
    entry = plugins[0]
    source = entry.get("source")
    if entry.get("name") != "codex-science":
        errors.append("marketplace.json: plugin name must be codex-science")
    if not isinstance(source, dict) or source.get("source") != "local":
        errors.append("marketplace.json: source must be a local repository path")
        return
    source_path = source.get("path")
    if not isinstance(source_path, str):
        errors.append("marketplace.json: source.path is required")
        return
    resolved = (ROOT / source_path).resolve()
    if not is_within(resolved, ROOT) or resolved != PLUGIN.resolve():
        errors.append("marketplace.json: source.path must resolve to plugins/codex-science")
    policy = entry.get("policy")
    if not isinstance(policy, dict) or policy.get("installation") != "AVAILABLE":
        errors.append("marketplace.json: policy.installation must be AVAILABLE")


def validate_skills(errors: list[str]) -> int:
    skill_files = sorted((PLUGIN / "skills").glob("*/SKILL.md"))
    if not skill_files:
        errors.append("plugin: no skills found")
        return 0
    for path in skill_files:
        values = parse_frontmatter(path, errors)
        name = values.get("name")
        description = values.get("description")
        if name != path.parent.name or not name or not SKILL_NAME.fullmatch(name):
            errors.append(f"{path.relative_to(ROOT)}: name must match its directory")
        if not description or len(description) < 40:
            errors.append(f"{path.relative_to(ROOT)}: description is missing or too short")
        agent = path.parent / "agents/openai.yaml"
        if not agent.is_file():
            errors.append(f"{agent.relative_to(ROOT)}: missing")
        else:
            agent_text = agent.read_text(encoding="utf-8")
            for field in ("display_name:", "short_description:", "default_prompt:"):
                if field not in agent_text:
                    errors.append(f"{agent.relative_to(ROOT)}: missing {field[:-1]}")
            if f"${name}" not in agent_text:
                errors.append(f"{agent.relative_to(ROOT)}: default prompt must invoke ${name}")
    return len(skill_files)


def validate_scripts(errors: list[str]) -> int:
    scripts = sorted((PLUGIN / "skills").glob("*/scripts/*.py"))
    if not scripts:
        errors.append("plugin: no Python scripts found")
        return 0
    for path in scripts:
        text = path.read_text(encoding="utf-8")
        if not text.startswith("#!/usr/bin/env python3\n"):
            errors.append(f"{path.relative_to(ROOT)}: missing python3 shebang")
        if not path.stat().st_mode & stat.S_IXUSR:
            errors.append(f"{path.relative_to(ROOT)}: script is not executable")
    return len(scripts)


def validate_repository(errors: list[str]) -> None:
    required = ("README.md", "LICENSE", "SECURITY.md", "CONTRIBUTING.md", ".gitignore")
    for relative in required:
        if not (ROOT / relative).is_file():
            errors.append(f"repository: missing {relative}")
    for path in ROOT.rglob("*"):
        if ".git" in path.parts:
            continue
        if path.is_symlink():
            if not is_within(path, ROOT):
                errors.append(f"{path.relative_to(ROOT)}: symlink escapes repository")
            continue
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        unfinished = ("TO" + "DO", "FIX" + "ME")
        if any(re.search(rf"\b{marker}\b", text) for marker in unfinished):
            errors.append(f"{path.relative_to(ROOT)}: unresolved work marker")
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                errors.append(f"{path.relative_to(ROOT)}: possible {label}")


def main() -> int:
    errors: list[str] = []
    validate_manifest(errors)
    validate_marketplace(errors)
    skill_count = validate_skills(errors)
    script_count = validate_scripts(errors)
    validate_repository(errors)
    if errors:
        for error in sorted(set(errors)):
            print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(
        "Codex Science release validation: PASS "
        f"({skill_count} skills, {script_count} plugin scripts, manifests and secret scan verified)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
