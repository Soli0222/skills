#!/usr/bin/env python3
"""Validate an Open Knowledge Format bundle."""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - depends on host environment
    yaml = None


RESERVED = {"index.md", "log.md"}
LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)\s#]+)(?:#[^)]*)?\)")
DATE_HEADING_RE = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2})\s*$")


class Finding:
    def __init__(self, level: str, path: Path, message: str) -> None:
        self.level = level
        self.path = path
        self.message = message

    def render(self, root: Path) -> str:
        rel = self.path.relative_to(root)
        return f"{self.level}: {rel}: {self.message}"


def split_frontmatter(text: str) -> tuple[str | None, str]:
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return None, text
    return text[4:end], text[end + 5 :]


def parse_frontmatter(raw: str) -> tuple[dict[str, Any] | None, str | None]:
    if yaml is not None:
        try:
            parsed = yaml.safe_load(raw) or {}
        except Exception as exc:
            return None, str(exc)
        if not isinstance(parsed, dict):
            return None, "frontmatter must parse to a mapping"
        return parsed, None

    parsed: dict[str, Any] = {}
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if line[:1].isspace():
            continue
        if ":" not in line:
            return None, "frontmatter contains a non key/value line; install PyYAML for full YAML support"
        key, value = line.split(":", 1)
        key = key.strip()
        if not key:
            return None, "frontmatter contains an empty key"
        parsed[key] = value.strip()
    return parsed, None


def iter_markdown_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.md") if ".git" not in p.parts)


def validate_concept(root: Path, path: Path, text: str, findings: list[Finding]) -> None:
    raw, _body = split_frontmatter(text)
    if raw is None:
        findings.append(Finding("ERROR", path, "concept document must start with YAML frontmatter"))
        return
    frontmatter, error = parse_frontmatter(raw)
    if error:
        findings.append(Finding("ERROR", path, f"invalid YAML frontmatter: {error}"))
        return
    concept_type = frontmatter.get("type") if frontmatter else None
    if concept_type is None or str(concept_type).strip() == "":
        findings.append(Finding("ERROR", path, "frontmatter must include non-empty 'type'"))


def validate_index(root: Path, path: Path, text: str, findings: list[Finding]) -> None:
    raw, _body = split_frontmatter(text)
    if raw is not None:
        parsed, error = parse_frontmatter(raw)
        if error:
            findings.append(Finding("ERROR", path, f"invalid root index frontmatter: {error}"))
        elif path.parent != root and parsed:
            findings.append(Finding("WARN", path, "index.md frontmatter is only intended for bundle-level metadata"))
    for line_no, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("* ") and "](" not in stripped:
            findings.append(Finding("WARN", path, f"index list item on line {line_no} has no markdown link"))


def validate_log(path: Path, text: str, findings: list[Finding]) -> None:
    for line_no, line in enumerate(text.splitlines(), start=1):
        if not line.startswith("## "):
            continue
        match = DATE_HEADING_RE.match(line)
        if not match:
            findings.append(Finding("ERROR", path, f"log date heading on line {line_no} must be YYYY-MM-DD"))
            continue
        try:
            dt.date.fromisoformat(match.group(1))
        except ValueError:
            findings.append(Finding("ERROR", path, f"log date heading on line {line_no} is not a valid date"))


def resolve_link(root: Path, source: Path, target: str) -> Path | None:
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target):
        return None
    if target.startswith("/"):
        return root / target.lstrip("/")
    return (source.parent / target).resolve()


def validate_links(root: Path, path: Path, text: str, findings: list[Finding]) -> None:
    for target in LINK_RE.findall(text):
        resolved = resolve_link(root, path, target)
        if resolved is None:
            continue
        if target.endswith("/") and resolved.is_dir():
            continue
        if not resolved.exists():
            findings.append(Finding("WARN", path, f"link target does not exist: {target}"))


def validate(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for path in iter_markdown_files(root):
        text = path.read_text(encoding="utf-8")
        if path.name == "index.md":
            validate_index(root, path, text, findings)
        elif path.name == "log.md":
            validate_log(path, text, findings)
        else:
            validate_concept(root, path, text, findings)
        validate_links(root, path, text, findings)
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate an OKF bundle")
    parser.add_argument("bundle", type=Path, help="Path to the OKF bundle root")
    args = parser.parse_args()

    root = args.bundle.resolve()
    if not root.is_dir():
        print(f"ERROR: {root} is not a directory", file=sys.stderr)
        return 2

    findings = validate(root)
    for finding in findings:
        print(finding.render(root))

    errors = [finding for finding in findings if finding.level == "ERROR"]
    if errors:
        print(f"\nFAILED: {len(errors)} error(s), {len(findings) - len(errors)} warning(s)")
        return 1
    print(f"OK: 0 error(s), {len(findings)} warning(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
