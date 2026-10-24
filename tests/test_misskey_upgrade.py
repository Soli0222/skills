"""Offline integration tests; no operations on the real Misskey repository."""

import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "skills/misskey-upgrade/scripts/update_versions.py"
spec = importlib.util.spec_from_file_location("update_versions", SCRIPT)
versions = importlib.util.module_from_spec(spec)
spec.loader.exec_module(versions)


class VersionUpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name).resolve()
        self.git("init", "-q")
        for path in versions.PACKAGES:
            self.write_package(path, "2026.9.0-psr.9.11")
        self.base = self.save()
        for path in versions.PACKAGES:
            self.write_package(path, "2026.10.1-alpha.1")
        self.upstream = self.save()

    def git(self, *args):
        return subprocess.run(
            ["git", "-C", str(self.repo), "-c", "user.name=Fixture",
             "-c", "user.email=fixture@example.invalid", "-c", "commit.gpgsign=false",
             "-c", "core.hooksPath=/dev/null", *args],
            check=True, capture_output=True, text=True,
        ).stdout.strip()

    def write_package(self, relative, version):
        path = self.repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"version": version, "custom": "keep"}, indent="\t") + "\n")

    def save(self):
        self.git("add", ".")
        self.git("commit", "-qm", "fixture")
        return self.git("rev-parse", "HEAD")

    def run_helper(self, *extra):
        return subprocess.run(
            ["python3", str(SCRIPT), "--repo", str(self.repo), "--base", self.base,
             "--upstream", self.upstream, *extra], capture_output=True, text=True,
        )

    def test_dry_run_apply_and_resume_preserve_bytes_and_suffix(self):
        before = {p: (self.repo / p).read_bytes() for p in versions.PACKAGES}
        dry = self.run_helper()
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertEqual(json.loads(dry.stdout)["version"], "2026.10.1-alpha.1-psr.9.11")
        self.assertEqual(before, {p: (self.repo / p).read_bytes() for p in versions.PACKAGES})
        applied = self.run_helper("--apply")
        self.assertEqual(applied.returncode, 0, applied.stderr)
        for path, content in before.items():
            self.assertEqual((self.repo / path).read_bytes(),
                             content.replace(b"2026.10.1-alpha.1", b"2026.10.1-alpha.1-psr.9.11"))
        self.assertEqual(json.loads(self.run_helper("--apply").stdout)["changed_files"], [])

    def test_conflicted_second_file_does_not_write_first(self):
        first = self.repo / versions.PACKAGES[0]
        before = first.read_bytes()
        (self.repo / versions.PACKAGES[1]).write_text("<<<<<<< HEAD\n")
        result = self.run_helper("--apply")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(first.read_bytes(), before)

    def test_mismatched_base_versions_refused(self):
        self.write_package(versions.PACKAGES[0], "2026.9.0-psr.9.10")
        self.base = self.save()
        before = self.git("status", "--porcelain")
        self.assertEqual(self.run_helper("--apply").returncode, 1)
        self.assertEqual(self.git("status", "--porcelain"), before)

    def test_stable_upstream_and_build_metadata(self):
        self.write_package(versions.PACKAGES[0], "2026.10.1")
        self.upstream = self.save()
        self.assertEqual(json.loads(self.run_helper().stdout)["version"], "2026.10.1-psr.9.11")
        self.write_package(versions.PACKAGES[0], "2026.10.1+build.1")
        self.upstream = self.save()
        self.assertEqual(self.run_helper("--apply").returncode, 1)


if __name__ == "__main__":
    unittest.main()
