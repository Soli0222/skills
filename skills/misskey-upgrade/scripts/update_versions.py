#!/usr/bin/env python3
"""Preserve the fork suffix and update only the two release package versions."""

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

PACKAGES = ("package.json", "packages/misskey-js/package.json")
NUMBER = r"(?:0|[1-9][0-9]*)"
PRERELEASE = rf"(?:{NUMBER}|[0-9]*[A-Za-z-][0-9A-Za-z-]*)"
UPSTREAM = rf"{NUMBER}\.{NUMBER}\.{NUMBER}(?:-{PRERELEASE}(?:\.{PRERELEASE})*)?"
FORK = re.compile(rf"({UPSTREAM})(-psr\.{NUMBER}\.{NUMBER})")
VERSION_LINE = re.compile(r'(?m)^(\s*"version"\s*:\s*)"([^"\r\n]*)"')


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def commit(repo, ref):
    return git(repo, "rev-parse", "--verify", "--end-of-options", ref + "^{commit}")


def version_at(repo, sha, path):
    return json.loads(git(repo, "show", f"{sha}:{path}"))["version"]


def update(repo, base, upstream, apply=False):
    repo = Path(repo).resolve()
    if Path(git(repo, "rev-parse", "--show-toplevel")).resolve() != repo:
        raise ValueError("--repo must be the repository root")
    base_sha, upstream_sha = commit(repo, base), commit(repo, upstream)
    old = [version_at(repo, base_sha, path) for path in PACKAGES]
    if old[0] != old[1] or not isinstance(old[0], str):
        raise ValueError("Base package versions must be equal strings")
    match = FORK.fullmatch(old[0])
    if not match:
        raise ValueError("Base version must end in -psr.x.y")
    upstream_version = version_at(repo, upstream_sha, PACKAGES[0])
    if (not isinstance(upstream_version, str)
            or not re.fullmatch(UPSTREAM, upstream_version)
            or FORK.fullmatch(upstream_version)):
        raise ValueError("Unsupported upstream version (fork suffix/build metadata not accepted)")
    target = upstream_version + match[2]
    changes = []
    # Validate both files before writing either; preserve formatting and other edits.
    for relative in PACKAGES:
        path = repo / relative
        if path.is_symlink() or path.resolve() != path:
            raise ValueError(f"Refusing symlink path: {relative}")
        content = path.read_bytes().decode("utf-8")
        current = json.loads(content)["version"]
        matches = list(VERSION_LINE.finditer(content))
        if len(matches) != 1 or matches[0][2] != current:
            raise ValueError(f"Expected one unambiguous version field: {relative}")
        start, end = matches[0].span(2)
        replacement = content[:start] + target + content[end:]
        changes.append((path, content, replacement))
    if apply:
        for path, before, after in changes:
            if before != after:
                path.write_bytes(after.encode("utf-8"))
    return {"version": target, "base_sha": base_sha, "upstream_sha": upstream_sha,
            "applied": apply,
            "changed_files": [str(p.relative_to(repo)) for p, a, b in changes if a != b]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--base", required=True, help="Pre-merge develop commit")
    parser.add_argument("--upstream", required=True, help="Pinned upstream commit")
    parser.add_argument("--apply", action="store_true", help="Write files (default: dry-run)")
    args = parser.parse_args()
    try:
        print(json.dumps(update(args.repo, args.base, args.upstream, args.apply), indent=2))
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        print(f"Version update refused: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
