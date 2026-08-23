#!/usr/bin/env python3
"""Validate an Open Knowledge Format (OKF) v0.2 bundle.

Two levels of finding, kept deliberately distinct:

  ERROR  A conformance failure under SPEC §11. A bundle with any of these
         is not a conformant OKF bundle.
  WARN   Everything else. The spec states these as SHOULD, so a bundle may
         knowingly ignore them and still be conformant. A malformed optional
         family lands here too: §11 forbids a consumer from rejecting a
         concept over one.

Exit codes: 0 clean, 1 findings that fail the run, 2 the bundle or the
environment could not be inspected at all.
"""

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
LINK_RE = re.compile(r"(?<!!)\[[^\]^][^\]]*\]\(([^)\s#]+)(?:#[^)]*)?\)")
DATE_HEADING_RE = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2})\s*$")
FENCE_RE = re.compile(r"^\s{0,3}(```+|~~~+)")
FOOTNOTE_REF_RE = re.compile(r"\[\^([^\]\s]+)\]")
FOOTNOTE_DEF_RE = re.compile(r"^\s{0,3}\[\^([^\]\s]+)\]:")
SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")
AGENT_ACTOR_RE = re.compile(r"^[^\s/:]+/[^\s/]+$")
PREFIXED_ACTOR_RE = re.compile(r"^(human|process):\S+$")
EXTENSION_RE = re.compile(r"\.[A-Za-z0-9]{1,8}$")

STATUS_VALUES = {"draft", "stable", "deprecated"}
COMPUTATION_TYPE = "attested computation"

# Fields that name a path or URI (§6.2). `sources[].resource` is handled
# separately because it may instead be a scope descriptor.
PATH_FIELDS = ("resource", "computation")


class Finding:
    def __init__(self, level: str, path: Path, message: str) -> None:
        self.level = level
        self.path = path
        self.message = message

    def render(self, root: Path) -> str:
        rel = self.path.relative_to(root)
        return f"{self.level}: {rel}: {self.message}"


class Doc:
    """One markdown file, split into frontmatter and body."""

    def __init__(self, path: Path, text: str) -> None:
        self.path = path
        self.text = text
        self.raw_frontmatter, self.body = split_frontmatter(text)


def split_frontmatter(text: str) -> tuple[str | None, str]:
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return None, text
    return text[4:end], text[end + 5 :]


def parse_frontmatter(raw: str) -> tuple[dict[str, Any] | None, str | None]:
    """Parse a frontmatter block. Requires PyYAML; see require_yaml()."""
    try:
        parsed = yaml.safe_load(raw) or {}
    except Exception as exc:
        return None, str(exc)
    if not isinstance(parsed, dict):
        return None, "frontmatter must parse to a mapping"
    return parsed, None


def strip_code_blocks(body: str) -> str:
    """Blank out fenced code blocks so prose scans do not read code."""
    out: list[str] = []
    fence: str | None = None
    for line in body.splitlines():
        match = FENCE_RE.match(line)
        if fence is None and match:
            fence = match.group(1)[:3]
            out.append("")
            continue
        if fence is not None:
            if match and match.group(1).startswith(fence):
                fence = None
            out.append("")
            continue
        out.append(line)
    return "\n".join(out)


def iter_markdown_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.md") if ".git" not in p.parts)


# --------------------------------------------------------------- field checks
#
# Everything below reports WARN. These families are optional (§5, §10), and
# §11 forbids rejecting a bundle over them, so a malformed one is a lint
# finding, not a conformance failure.


def is_iso_datetime(value: Any) -> bool:
    """ISO 8601 datetime with an explicit UTC offset (§5)."""
    if isinstance(value, dt.datetime):
        return value.tzinfo is not None
    if not isinstance(value, str):
        return False
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def check_datetime(path: Path, label: str, value: Any, findings: list[Finding]) -> None:
    if value is None:
        return
    if not is_iso_datetime(value):
        findings.append(
            Finding("WARN", path, f"{label} must be an ISO 8601 datetime with a UTC offset: {value!r}")
        )


def check_actor(path: Path, label: str, value: Any, findings: list[Finding]) -> None:
    # Only `generated.by` and `verified[].by` are checked. §5.1 says
    # `sources[].author` follows the same convention, but the spec's own
    # example writes `team:ga4-docs`, which the convention in §7 does not
    # define. Enforcing it would flag the spec's own bundles, so it is left
    # alone until upstream resolves the contradiction.
    if not isinstance(value, str) or not value.strip():
        findings.append(Finding("WARN", path, f"{label} should be a non-empty actor string"))
        return
    actor = value.strip()
    if PREFIXED_ACTOR_RE.match(actor) or AGENT_ACTOR_RE.match(actor):
        return
    findings.append(
        Finding(
            "WARN",
            path,
            f"{label} does not follow the actor convention (<producer>/<version>, human:<id>, process:<id>): {actor!r}",
        )
    )


def check_generated(path: Path, frontmatter: dict[str, Any], findings: list[Finding]) -> None:
    generated = frontmatter.get("generated")
    if generated is None:
        return
    if not isinstance(generated, dict):
        findings.append(Finding("WARN", path, "'generated' is malformed: expected a mapping with 'by' and 'at'"))
        return
    if "by" not in generated:
        findings.append(Finding("WARN", path, "'generated' is malformed: 'by' is required within it"))
    else:
        check_actor(path, "generated.by", generated.get("by"), findings)
    if "at" not in generated:
        findings.append(Finding("WARN", path, "'generated' should include 'at'"))
    else:
        check_datetime(path, "generated.at", generated.get("at"), findings)


def check_verified(path: Path, frontmatter: dict[str, Any], findings: list[Finding]) -> None:
    verified = frontmatter.get("verified")
    if verified is None:
        return
    # A bare mapping is a one-element list (§5.2).
    entries = [verified] if isinstance(verified, dict) else verified
    if not isinstance(entries, list):
        findings.append(Finding("WARN", path, "'verified' is malformed: expected a mapping or a list of mappings"))
        return
    for position, entry in enumerate(entries):
        label = f"verified[{position}]"
        if not isinstance(entry, dict):
            findings.append(Finding("WARN", path, f"{label} is malformed: expected a mapping with 'by' and 'at'"))
            continue
        if "by" not in entry:
            findings.append(Finding("WARN", path, f"{label} is malformed: 'by' is required within it"))
        else:
            check_actor(path, f"{label}.by", entry.get("by"), findings)
        if "at" not in entry:
            findings.append(Finding("WARN", path, f"{label} should include 'at'"))
        else:
            check_datetime(path, f"{label}.at", entry.get("at"), findings)


def check_usage_window(path: Path, label: str, window: Any, findings: list[Finding]) -> bool:
    if window is None:
        return False
    if not isinstance(window, dict):
        findings.append(Finding("WARN", path, f"{label} is malformed: expected a mapping with 'from' and 'to'"))
        return False
    for key in ("from", "to"):
        if key not in window:
            findings.append(Finding("WARN", path, f"{label} is malformed: '{key}' is required within it"))
        else:
            check_datetime(path, f"{label}.{key}", window.get(key), findings)
    return True


def check_sources(path: Path, frontmatter: dict[str, Any], findings: list[Finding]) -> set[str]:
    """Validate 'sources' and return the ids available for footnote attribution."""
    shared_window = check_usage_window(path, "usage_window", frontmatter.get("usage_window"), findings)
    sources = frontmatter.get("sources")
    ids: set[str] = set()
    if sources is None:
        if frontmatter.get("usage_window") is not None:
            findings.append(Finding("WARN", path, "'usage_window' has no 'sources' to frame"))
        return ids
    if not isinstance(sources, list):
        findings.append(Finding("WARN", path, "'sources' is malformed: expected a list of mappings"))
        return ids
    for position, entry in enumerate(sources):
        label = f"sources[{position}]"
        if not isinstance(entry, dict):
            findings.append(Finding("WARN", path, f"{label} is malformed: expected a mapping"))
            continue
        resource = entry.get("resource")
        if not isinstance(resource, str) or not resource.strip():
            findings.append(Finding("WARN", path, f"{label} is malformed: 'resource' is required within it"))
        source_id = entry.get("id")
        if source_id is not None:
            source_id = str(source_id)
            if source_id in ids:
                findings.append(Finding("WARN", path, f"{label}.id is a duplicate: {source_id!r}"))
            ids.add(source_id)
        check_datetime(path, f"{label}.last_modified", entry.get("last_modified"), findings)
        entry_window = check_usage_window(path, f"{label}.usage_window", entry.get("usage_window"), findings)
        usage_count = entry.get("usage_count")
        if usage_count is not None:
            if not isinstance(usage_count, int) or isinstance(usage_count, bool):
                findings.append(Finding("WARN", path, f"{label}.usage_count should be an integer"))
            if not (shared_window or entry_window):
                findings.append(
                    Finding("WARN", path, f"{label}.usage_count has no 'usage_window' to frame it")
                )
    return ids


def check_tags(path: Path, frontmatter: dict[str, Any], findings: list[Finding]) -> None:
    tags = frontmatter.get("tags")
    if tags is not None and not isinstance(tags, list):
        findings.append(Finding("WARN", path, "'tags' should be a YAML list of short strings"))


def check_lifecycle(path: Path, frontmatter: dict[str, Any], findings: list[Finding]) -> None:
    status = frontmatter.get("status")
    if status is not None and str(status).strip() not in STATUS_VALUES:
        findings.append(
            Finding("WARN", path, f"'status' should be one of draft, stable, deprecated: {status!r}")
        )
    check_datetime(path, "stale_after", frontmatter.get("stale_after"), findings)


def find_section(body: str, heading: str) -> str | None:
    """Return the body of a top-level section, ignoring fenced code."""
    lines = body.splitlines()
    fence: str | None = None
    start = None
    for index, line in enumerate(lines):
        match = FENCE_RE.match(line)
        if match:
            if fence is None:
                fence = match.group(1)[:3]
            elif match.group(1).startswith(fence):
                fence = None
            continue
        if fence is not None:
            continue
        if start is None:
            if line.strip().lower() == f"# {heading}".lower():
                start = index + 1
        elif line.startswith("# "):
            return "\n".join(lines[start:index])
    if start is not None:
        return "\n".join(lines[start:])
    return None


def has_code_block(section: str) -> bool:
    for line in section.splitlines():
        if FENCE_RE.match(line):
            return True
        if line.startswith("    ") and line.strip():
            return True
    return False


def check_computation(path: Path, frontmatter: dict[str, Any], body: str, findings: list[Finding]) -> None:
    if str(frontmatter.get("type", "")).strip().lower() != COMPUTATION_TYPE:
        return
    runtime = frontmatter.get("runtime")
    if not isinstance(runtime, str) or not runtime.strip():
        findings.append(Finding("WARN", path, "'Attested Computation' requires a non-empty 'runtime'"))

    section = find_section(body, "Computation")
    inline = section is not None and section.strip() != ""
    computation = frontmatter.get("computation")
    referenced = False
    if computation is not None:
        if isinstance(computation, str) and computation.strip():
            referenced = True
        else:
            findings.append(Finding("WARN", path, "'computation' must be a non-empty path string"))
    if inline and referenced:
        findings.append(
            Finding("WARN", path, "computation is given twice: both 'computation' and a '# Computation' body section")
        )
    elif not inline and not referenced:
        findings.append(
            Finding("WARN", path, "computation is missing: set 'computation' or add a '# Computation' body section")
        )
    elif inline and not has_code_block(section or ""):
        findings.append(Finding("WARN", path, "'# Computation' section has no code block"))

    parameters = frontmatter.get("parameters")
    if parameters is not None:
        if not isinstance(parameters, list):
            findings.append(Finding("WARN", path, "'parameters' is malformed: expected a list of mappings"))
        else:
            for position, entry in enumerate(parameters):
                label = f"parameters[{position}]"
                if not isinstance(entry, dict):
                    findings.append(Finding("WARN", path, f"{label} is malformed: expected a mapping"))
                    continue
                if not str(entry.get("name", "")).strip():
                    findings.append(Finding("WARN", path, f"{label} is malformed: 'name' is required within it"))
                for key in ("type", "required"):
                    if key not in entry:
                        findings.append(Finding("WARN", path, f"{label} should include '{key}'"))

    executor = frontmatter.get("executor")
    if executor is not None:
        if not isinstance(executor, dict):
            findings.append(Finding("WARN", path, "'executor' is malformed: expected a mapping"))
        else:
            if not str(executor.get("resource", "")).strip():
                findings.append(Finding("WARN", path, "'executor' should name a 'resource'"))
            receipt = executor.get("receipt")
            if receipt is None:
                findings.append(Finding("WARN", path, "'executor' should declare 'receipt' fields"))
            elif not isinstance(receipt, list):
                findings.append(Finding("WARN", path, "'executor.receipt' is malformed: expected a list of field names"))

    attester = frontmatter.get("attester")
    if attester is not None:
        if not isinstance(attester, dict):
            findings.append(Finding("WARN", path, "'attester' is malformed: expected a mapping"))
        elif not str(attester.get("resource", "")).strip():
            findings.append(Finding("WARN", path, "'attester' should name a 'resource'"))


def check_legacy(path: Path, frontmatter: dict[str, Any], body: str, findings: list[Finding]) -> None:
    if "timestamp" in frontmatter and "generated" not in frontmatter:
        findings.append(
            Finding("WARN", path, "v0.1 'timestamp' is superseded by 'generated: { by, at }' (§13.1)")
        )
    if find_section(body, "Citations") is not None:
        findings.append(
            Finding("WARN", path, "v0.1 '# Citations' section is superseded by 'sources' and footnotes (§13.1)")
        )


def check_footnotes(path: Path, body: str, source_ids: set[str], findings: list[Finding]) -> None:
    prose = strip_code_blocks(body)
    defined = set()
    referenced: dict[str, None] = {}
    for line in prose.splitlines():
        definition = FOOTNOTE_DEF_RE.match(line)
        if definition:
            defined.add(definition.group(1))
            continue
        for label in FOOTNOTE_REF_RE.findall(line):
            referenced.setdefault(label, None)
    for label in referenced:
        if label not in source_ids:
            findings.append(
                Finding("WARN", path, f"footnote [^{label}] does not match any sources[].id")
            )
        if label not in defined:
            findings.append(Finding("WARN", path, f"footnote [^{label}] has no definition"))


# ------------------------------------------------------------------ path checks


def looks_like_path(value: str) -> bool:
    """Tell a path from a scope descriptor such as 'all queries in project X' (§5.1)."""
    if SCHEME_RE.match(value) or not value:
        return False
    if any(character.isspace() for character in value):
        return False
    if value.startswith(("/", "./", "../")):
        return True
    return bool(EXTENSION_RE.search(value))


def resolve_link(root: Path, source: Path, target: str) -> Path | None:
    if SCHEME_RE.match(target):
        return None
    if target.startswith("/"):
        return root / target.lstrip("/")
    return (source.parent / target).resolve()


def check_path_target(root: Path, path: Path, label: str, target: Any, findings: list[Finding]) -> None:
    if not isinstance(target, str) or not target.strip():
        return
    resolved = resolve_link(root, path, target.strip())
    if resolved is None or resolved.exists():
        return
    findings.append(Finding("WARN", path, f"{label} target does not exist: {target}"))


def check_paths(root: Path, path: Path, frontmatter: dict[str, Any], findings: list[Finding]) -> None:
    for field in PATH_FIELDS:
        check_path_target(root, path, f"'{field}'", frontmatter.get(field), findings)
    for field in ("executor", "attester"):
        block = frontmatter.get(field)
        if isinstance(block, dict):
            check_path_target(root, path, f"'{field}.resource'", block.get("resource"), findings)
    sources = frontmatter.get("sources")
    if isinstance(sources, list):
        for position, entry in enumerate(sources):
            if not isinstance(entry, dict):
                continue
            resource = entry.get("resource")
            # A scope descriptor is not a path; only check the path forms (§5.1, §6.2).
            if isinstance(resource, str) and looks_like_path(resource.strip()):
                check_path_target(root, path, f"sources[{position}].resource", resource, findings)


# ------------------------------------------------------------------ file checks


def validate_concept(root: Path, doc: Doc, findings: list[Finding], lint: bool) -> None:
    path = doc.path
    if doc.raw_frontmatter is None:
        findings.append(Finding("ERROR", path, "concept document must start with YAML frontmatter"))
        return
    frontmatter, error = parse_frontmatter(doc.raw_frontmatter)
    if error or frontmatter is None:
        findings.append(Finding("ERROR", path, f"invalid YAML frontmatter: {error}"))
        return
    concept_type = frontmatter.get("type")
    if concept_type is None or str(concept_type).strip() == "":
        findings.append(Finding("ERROR", path, "frontmatter must include non-empty 'type'"))
    if not lint:
        return

    check_legacy(path, frontmatter, doc.body, findings)
    check_tags(path, frontmatter, findings)
    check_generated(path, frontmatter, findings)
    check_verified(path, frontmatter, findings)
    source_ids = check_sources(path, frontmatter, findings)
    check_lifecycle(path, frontmatter, findings)
    check_computation(path, frontmatter, doc.body, findings)
    check_footnotes(path, doc.body, source_ids, findings)
    check_paths(root, path, frontmatter, findings)


def validate_index(root: Path, doc: Doc, findings: list[Finding], lint: bool) -> None:
    path = doc.path
    is_root = path.parent == root
    if doc.raw_frontmatter is not None:
        parsed, error = parse_frontmatter(doc.raw_frontmatter)
        if error:
            findings.append(Finding("ERROR", path, f"invalid index frontmatter: {error}"))
        elif not is_root:
            findings.append(
                Finding("ERROR", path, "only a bundle-root index.md may carry frontmatter (§8)")
            )
        elif parsed and lint:
            extra = sorted(key for key in parsed if key != "okf_version")
            if extra:
                findings.append(
                    Finding(
                        "WARN",
                        path,
                        f"root index frontmatter should carry only 'okf_version'; also found: {', '.join(extra)}",
                    )
                )
            version = parsed.get("okf_version")
            if version is not None and str(version).strip() not in {"0.1", "0.2"}:
                findings.append(Finding("WARN", path, f"unrecognized okf_version: {version!r}"))
    if not lint:
        return
    for line_no, line in enumerate(doc.text.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith(("* ", "- ")) and "](" not in stripped:
            findings.append(Finding("WARN", path, f"index list item on line {line_no} has no markdown link"))


def validate_log(doc: Doc, findings: list[Finding]) -> None:
    for line_no, line in enumerate(doc.text.splitlines(), start=1):
        if not line.startswith("## "):
            continue
        match = DATE_HEADING_RE.match(line)
        if not match:
            findings.append(Finding("ERROR", doc.path, f"log date heading on line {line_no} must be YYYY-MM-DD"))
            continue
        try:
            dt.date.fromisoformat(match.group(1))
        except ValueError:
            findings.append(Finding("ERROR", doc.path, f"log date heading on line {line_no} is not a valid date"))


def validate_links(root: Path, doc: Doc, findings: list[Finding]) -> None:
    for target in LINK_RE.findall(strip_code_blocks(doc.text)):
        resolved = resolve_link(root, doc.path, target)
        if resolved is None:
            continue
        if target.endswith("/") and resolved.is_dir():
            continue
        if not resolved.exists():
            findings.append(Finding("WARN", doc.path, f"link target does not exist: {target}"))


def validate(root: Path, lint: bool = True) -> list[Finding]:
    findings: list[Finding] = []
    for path in iter_markdown_files(root):
        doc = Doc(path, path.read_text(encoding="utf-8"))
        if path.name == "index.md":
            validate_index(root, doc, findings, lint)
        elif path.name == "log.md":
            validate_log(doc, findings)
        else:
            validate_concept(root, doc, findings, lint)
        if lint:
            validate_links(root, doc, findings)
    return findings


def require_yaml() -> None:
    if yaml is None:
        print(
            "ERROR: PyYAML is required to validate an OKF bundle.\n"
            "Conformance rests on the frontmatter being parseable YAML (SPEC §11), "
            "which cannot be checked without a real YAML parser.\n"
            "Install it with: python3 -m pip install pyyaml",
            file=sys.stderr,
        )
        raise SystemExit(2)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate an OKF v0.2 bundle")
    parser.add_argument("bundle", type=Path, help="Path to the OKF bundle root")
    parser.add_argument(
        "--conformance",
        action="store_true",
        help="Check only SPEC §11 conformance, skipping the quality lint",
    )
    parser.add_argument("--strict", action="store_true", help="Treat warnings as failures")
    args = parser.parse_args()

    require_yaml()

    root = args.bundle.resolve()
    if not root.is_dir():
        print(f"ERROR: {root} is not a directory", file=sys.stderr)
        return 2

    findings = validate(root, lint=not args.conformance)
    for finding in findings:
        print(finding.render(root))

    errors = [finding for finding in findings if finding.level == "ERROR"]
    warnings = len(findings) - len(errors)
    if errors:
        print(f"\nNOT CONFORMANT: {len(errors)} error(s), {warnings} warning(s)")
        return 1
    if warnings and args.strict:
        print(f"\nFAILED (--strict): conformant, but {warnings} warning(s)")
        return 1
    print(f"CONFORMANT: 0 error(s), {warnings} warning(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
