#!/usr/bin/env python3
"""Validate installed-Release manifest determinism, coverage, and first-match ownership."""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
GENERATOR_PATH = REPOSITORY_ROOT / "scripts/generate-release-manifest.py"
MODULE_SPEC = importlib.util.spec_from_file_location("release_manifest_generator", GENERATOR_PATH)
if MODULE_SPEC is None or MODULE_SPEC.loader is None:
    raise RuntimeError(f"Unable to load generator: {GENERATOR_PATH}")
GENERATOR = importlib.util.module_from_spec(MODULE_SPEC)
sys.modules[MODULE_SPEC.name] = GENERATOR
MODULE_SPEC.loader.exec_module(GENERATOR)


class ReleaseManifestGeneratorTest(unittest.TestCase):
    """Cover canonical output, self-exclusion, drift detection, and invalid assets."""

    def prepare_asset(self, root: Path) -> Path:
        """Create a minimal release asset with broad and narrow rules."""

        asset = root / "asset"
        (asset / ".ai-workspace").mkdir(parents=True)
        (asset / "distribution").mkdir()
        (asset / ".ai-workspace/ownership.toml").write_text(
            """[ownership]
version = "0.1"
default = "workspace"
resolution = "first-match"

[[rules]]
pattern = "distribution/**"
owner = "generated"

[[rules]]
pattern = "distribution/specific.txt"
owner = "distribution"

[[rules]]
pattern = "exact.txt"
owner = "distribution"

[[rules]]
pattern = ".ai-workspace/release-manifest.json"
owner = "distribution"
""",
            encoding="utf-8",
        )
        (asset / "distribution/specific.txt").write_text("first match\n", encoding="utf-8")
        (asset / "exact.txt").write_text("exact\n", encoding="utf-8")
        (asset / "workspace.txt").write_text("workspace\n", encoding="utf-8")
        return asset

    def test_manifest_is_deterministic_complete_and_excludes_itself(self) -> None:
        """Confirm stable output, full file coverage, and strict first-match resolution."""

        with tempfile.TemporaryDirectory() as directory:
            asset = self.prepare_asset(Path(directory))
            first = GENERATOR.canonical_bytes(GENERATOR.build_manifest(asset, "0.1.0"))
            manifest_path = GENERATOR.write_manifest(asset, first)
            second = GENERATOR.canonical_bytes(GENERATOR.build_manifest(asset, "0.1.0"))
            self.assertEqual(first, second)
            self.assertEqual(first, manifest_path.read_bytes())

            document = json.loads(first)
            entries = {entry["path"]: entry for entry in document["files"]}
            self.assertEqual("0.1", document["schema_version"])
            self.assertEqual("0.1.0", document["release_version"])
            self.assertNotIn(GENERATOR.MANIFEST_PATH, entries)
            self.assertEqual(
                sorted(entries, key=lambda value: value.encode("utf-8")),
                [entry["path"] for entry in document["files"]],
            )
            self.assertEqual("generated", entries["distribution/specific.txt"]["owner"])
            self.assertEqual("distribution", entries["exact.txt"]["owner"])
            self.assertEqual("workspace", entries["workspace.txt"]["owner"])
            self.assertEqual(
                hashlib.sha256(b"exact\n").hexdigest(),
                entries["exact.txt"]["sha256"],
            )

            actual_files = {
                path.relative_to(asset).as_posix()
                for path in asset.rglob("*")
                if path.is_file() and path.relative_to(asset).as_posix() != GENERATOR.MANIFEST_PATH
            }
            self.assertEqual(actual_files, set(entries))

    def test_check_rejects_file_drift(self) -> None:
        """Ensure read-only checking rejects asset drift after generation."""

        with tempfile.TemporaryDirectory() as directory:
            asset = self.prepare_asset(Path(directory))
            GENERATOR.write_manifest(
                asset,
                GENERATOR.canonical_bytes(GENERATOR.build_manifest(asset, "0.1.0")),
            )
            (asset / "exact.txt").write_text("changed\n", encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                status = GENERATOR.main(
                    [
                        "--asset-root",
                        str(asset),
                        "--release-version",
                        "0.1.0",
                        "--check",
                    ]
                )
            self.assertEqual(1, status)

    def test_symlink_is_rejected(self) -> None:
        """Ensure the manifest does not omit or follow asset symlinks silently."""

        with tempfile.TemporaryDirectory() as directory:
            asset = self.prepare_asset(Path(directory))
            link_path = asset / "linked.txt"
            try:
                link_path.symlink_to(asset / "exact.txt")
            except (NotImplementedError, OSError):
                self.skipTest("The current platform cannot create the test symlink")
            with self.assertRaises(GENERATOR.ReleaseManifestError):
                GENERATOR.build_manifest(asset, "0.1.0")


if __name__ == "__main__":
    unittest.main()
