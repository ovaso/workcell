#!/usr/bin/env python3
"""Validate upgrade-preview protection for user content and release conflicts."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from preview_upgrade import UpgradePreviewError, preview_upgrade


def checksum(content: bytes) -> str:
    """Compute a SHA-256 used by test manifests."""

    return hashlib.sha256(content).hexdigest()


class UpgradePreviewTest(unittest.TestCase):
    """Cover replace, preserve, conflict, remove, and path-escape cases."""

    def write_manifest(self, path: Path, version: str, entries: list[dict[str, str]]) -> None:
        """Write a minimal test Release manifest."""

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"schema_version": "0.1", "release_version": version, "files": entries}),
            encoding="utf-8",
        )

    def prepare(self, root: Path, old: bytes, new: bytes) -> tuple[Path, Path, Path, Path]:
        """Create current and candidate roots with one release file."""

        workspace = root / "workspace"
        candidate = root / "candidate"
        workspace.mkdir()
        candidate.mkdir()
        (workspace / "skills").mkdir()
        (candidate / "skills").mkdir()
        (workspace / "skills/runtime.txt").write_bytes(old)
        (candidate / "skills/runtime.txt").write_bytes(new)
        current_manifest = workspace / ".ai-workspace/release-manifest.json"
        candidate_manifest = candidate / ".ai-workspace/release-manifest.json"
        self.write_manifest(
            current_manifest,
            "0.1.0",
            [{"path": "skills/runtime.txt", "owner": "distribution", "sha256": checksum(old)}],
        )
        self.write_manifest(
            candidate_manifest,
            "0.2.0",
            [{"path": "skills/runtime.txt", "owner": "distribution", "sha256": checksum(new)}],
        )
        return workspace, current_manifest, candidate, candidate_manifest

    def test_unmodified_distribution_file_can_be_replaced(self) -> None:
        """Confirm an unmodified release file produces a safe replacement."""

        with tempfile.TemporaryDirectory() as directory:
            paths = self.prepare(Path(directory), b"old", b"new")
            result = preview_upgrade(*paths)
            self.assertTrue(result["safe_to_apply"])
            self.assertEqual("replace", result["actions"][0]["action"])
            self.assertEqual("replace-receipt", result["actions"][-1]["action"])
            self.assertEqual(".ai-workspace/release-manifest.json", result["actions"][-1]["path"])

    def test_locally_modified_distribution_file_conflicts(self) -> None:
        """Ensure a candidate Release does not silently overwrite local changes."""

        with tempfile.TemporaryDirectory() as directory:
            paths = self.prepare(Path(directory), b"old", b"new")
            (paths[0] / "skills/runtime.txt").write_bytes(b"user change")
            result = preview_upgrade(*paths)
            self.assertFalse(result["safe_to_apply"])
            self.assertEqual("conflict", result["actions"][0]["action"])

    def test_workspace_owned_file_is_preserved(self) -> None:
        """Confirm a workspace-owned file produces only a preserve action."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = self.prepare(root, b"user", b"seed")
            entry_old = [{"path": "skills/runtime.txt", "owner": "workspace", "sha256": checksum(b"user")}]
            entry_new = [{"path": "skills/runtime.txt", "owner": "workspace", "sha256": checksum(b"seed")}]
            self.write_manifest(paths[1], "0.1.0", entry_old)
            self.write_manifest(paths[3], "0.2.0", entry_new)
            result = preview_upgrade(*paths)
            self.assertTrue(result["safe_to_apply"])
            self.assertEqual("preserve", result["actions"][0]["action"])

    def test_removed_unmodified_distribution_file_can_be_planned(self) -> None:
        """Confirm candidate removal affects only an unmodified release file."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = self.prepare(root, b"old", b"new")
            (paths[2] / "skills/runtime.txt").unlink()
            (paths[2] / "replacement.txt").write_bytes(b"replacement")
            self.write_manifest(
                paths[3],
                "0.2.0",
                [{"path": "replacement.txt", "owner": "distribution", "sha256": checksum(b"replacement")}],
            )
            result = preview_upgrade(*paths)
            self.assertTrue(result["safe_to_apply"])
            runtime_action = next(action for action in result["actions"] if action["path"] == "skills/runtime.txt")
            self.assertEqual("remove", runtime_action["action"])

    def test_parent_path_escape_is_rejected(self) -> None:
        """Ensure a manifest cannot escape the workspace through a parent path."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = self.prepare(root, b"old", b"new")
            self.write_manifest(
                paths[3],
                "0.2.0",
                [{"path": "../escape", "owner": "distribution", "sha256": checksum(b"new")}],
            )
            with self.assertRaises(UpgradePreviewError):
                preview_upgrade(*paths)

    def test_candidate_extra_file_is_rejected(self) -> None:
        """Ensure a candidate cannot contain regular files omitted from its manifest."""

        with tempfile.TemporaryDirectory() as directory:
            paths = self.prepare(Path(directory), b"old", b"new")
            (paths[2] / "unlisted.txt").write_text("unlisted", encoding="utf-8")
            with self.assertRaises(UpgradePreviewError):
                preview_upgrade(*paths)

    def test_manifest_cannot_hash_itself(self) -> None:
        """Ensure the installed receipt path cannot appear in its own files array."""

        with tempfile.TemporaryDirectory() as directory:
            paths = self.prepare(Path(directory), b"old", b"new")
            self.write_manifest(
                paths[3],
                "0.2.0",
                [
                    {
                        "path": ".ai-workspace/release-manifest.json",
                        "owner": "distribution",
                        "sha256": checksum(b"receipt"),
                    }
                ],
            )
            with self.assertRaises(UpgradePreviewError):
                preview_upgrade(*paths)

    def test_schema_version_is_required(self) -> None:
        """Ensure the preview rejects a legacy manifest without schema_version."""

        with tempfile.TemporaryDirectory() as directory:
            paths = self.prepare(Path(directory), b"old", b"new")
            paths[3].write_text(
                json.dumps(
                    {
                        "release_version": "0.2.0",
                        "files": [
                            {
                                "path": "skills/runtime.txt",
                                "owner": "distribution",
                                "sha256": checksum(b"new"),
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(UpgradePreviewError):
                preview_upgrade(*paths)


if __name__ == "__main__":
    unittest.main()
