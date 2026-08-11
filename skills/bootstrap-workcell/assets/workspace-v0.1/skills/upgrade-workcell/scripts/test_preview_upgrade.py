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
    """Cover release replacement, migration gates, and unsafe input cases."""

    def write_manifest(self, path: Path, version: str, entries: list[dict[str, str]]) -> None:
        """Write a minimal test Release manifest."""

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"schema_version": "0.1", "release_version": version, "files": entries}),
            encoding="utf-8",
        )

    def workspace_entry(self, root: Path) -> dict[str, str]:
        """Return the workspace metadata entry for a test Release manifest."""

        path = root / ".ai-workspace/workspace.toml"
        return {
            "path": ".ai-workspace/workspace.toml",
            "owner": "workspace",
            "sha256": checksum(path.read_bytes()),
        }

    def write_workspace_metadata(self, root: Path, managed_by: str) -> None:
        """Write the stable product identity used by the compatibility gate."""

        metadata = root / ".ai-workspace/workspace.toml"
        metadata.parent.mkdir(parents=True, exist_ok=True)
        metadata.write_text(
            "[workspace]\n"
            f'managed_by = "{managed_by}"\n',
            encoding="utf-8",
        )

    def prepare(
        self,
        root: Path,
        old: bytes,
        new: bytes,
        *,
        current_version: str = "0.1.0",
        candidate_version: str = "0.1.0",
        current_product: str = "workcell",
        candidate_product: str = "workcell",
    ) -> tuple[Path, Path, Path, Path]:
        """Create current and candidate roots with one release file and identity."""

        workspace = root / "workspace"
        candidate = root / "candidate"
        workspace.mkdir()
        candidate.mkdir()
        (workspace / "skills").mkdir()
        (candidate / "skills").mkdir()
        (workspace / "skills/runtime.txt").write_bytes(old)
        (candidate / "skills/runtime.txt").write_bytes(new)
        self.write_workspace_metadata(workspace, current_product)
        self.write_workspace_metadata(candidate, candidate_product)
        current_manifest = workspace / ".ai-workspace/release-manifest.json"
        candidate_manifest = candidate / ".ai-workspace/release-manifest.json"
        self.write_manifest(
            current_manifest,
            current_version,
            [
                self.workspace_entry(workspace),
                {"path": "skills/runtime.txt", "owner": "distribution", "sha256": checksum(old)},
            ],
        )
        self.write_manifest(
            candidate_manifest,
            candidate_version,
            [
                self.workspace_entry(candidate),
                {"path": "skills/runtime.txt", "owner": "distribution", "sha256": checksum(new)},
            ],
        )
        return workspace, current_manifest, candidate, candidate_manifest

    def test_unmodified_distribution_file_can_be_replaced(self) -> None:
        """Confirm an unmodified release file produces a safe replacement."""

        with tempfile.TemporaryDirectory() as directory:
            paths = self.prepare(Path(directory), b"old", b"new")
            result = preview_upgrade(*paths)
            self.assertTrue(result["safe_to_apply"])
            runtime_action = next(action for action in result["actions"] if action["path"] == "skills/runtime.txt")
            self.assertEqual("replace", runtime_action["action"])
            self.assertEqual("replace-receipt", result["actions"][-1]["action"])
            self.assertEqual(".ai-workspace/release-manifest.json", result["actions"][-1]["path"])

    def test_locally_modified_distribution_file_conflicts(self) -> None:
        """Ensure a candidate Release does not silently overwrite local changes."""

        with tempfile.TemporaryDirectory() as directory:
            paths = self.prepare(Path(directory), b"old", b"new")
            (paths[0] / "skills/runtime.txt").write_bytes(b"user change")
            result = preview_upgrade(*paths)
            self.assertFalse(result["safe_to_apply"])
            runtime_action = next(action for action in result["actions"] if action["path"] == "skills/runtime.txt")
            self.assertEqual("conflict", runtime_action["action"])

    def test_workspace_owned_file_is_preserved(self) -> None:
        """Confirm a workspace-owned file produces only a preserve action."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = self.prepare(root, b"user", b"seed")
            entry_old = [
                self.workspace_entry(paths[0]),
                {"path": "skills/runtime.txt", "owner": "workspace", "sha256": checksum(b"user")},
            ]
            entry_new = [
                self.workspace_entry(paths[2]),
                {"path": "skills/runtime.txt", "owner": "workspace", "sha256": checksum(b"seed")},
            ]
            self.write_manifest(paths[1], "0.1.0", entry_old)
            self.write_manifest(paths[3], "0.1.0", entry_new)
            result = preview_upgrade(*paths)
            self.assertTrue(result["safe_to_apply"])
            runtime_action = next(action for action in result["actions"] if action["path"] == "skills/runtime.txt")
            self.assertEqual("preserve", runtime_action["action"])

    def test_removed_unmodified_distribution_file_can_be_planned(self) -> None:
        """Confirm candidate removal affects only an unmodified release file."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = self.prepare(root, b"old", b"new")
            (paths[2] / "skills/runtime.txt").unlink()
            (paths[2] / "replacement.txt").write_bytes(b"replacement")
            self.write_manifest(
                paths[3],
                "0.1.0",
                [
                    self.workspace_entry(paths[2]),
                    {"path": "replacement.txt", "owner": "distribution", "sha256": checksum(b"replacement")},
                ],
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

    def test_cross_product_and_version_without_migration_conflicts(self) -> None:
        """Block Standard Workspace V0.1 from being treated as a Workcell V0.2 migration."""

        with tempfile.TemporaryDirectory() as directory:
            paths = self.prepare(
                Path(directory),
                b"old",
                b"new",
                current_version="0.1.0",
                candidate_version="0.2.0",
                current_product="ai-native-standard-workspace",
                candidate_product="workcell",
            )
            legacy_lock = paths[0] / ".ai-workspace/versions.lock"
            candidate_lock = paths[2] / ".ai-workspace/versions.lock"
            legacy_lock.write_bytes(b"legacy lock")
            candidate_lock.write_bytes(b"candidate lock")
            legacy_locale = paths[0] / "locales/operator-notes.md"
            candidate_locale = paths[2] / "locales/operator-notes.md"
            legacy_locale.parent.mkdir()
            candidate_locale.parent.mkdir()
            legacy_locale.write_bytes(b"legacy notes")
            candidate_locale.write_bytes(b"candidate notes")
            self.write_manifest(
                paths[1],
                "0.1.0",
                [
                    self.workspace_entry(paths[0]),
                    {"path": ".ai-workspace/versions.lock", "owner": "workspace", "sha256": checksum(b"legacy lock")},
                    {"path": "locales/operator-notes.md", "owner": "workspace", "sha256": checksum(b"legacy notes")},
                    {"path": "skills/runtime.txt", "owner": "distribution", "sha256": checksum(b"old")},
                ],
            )
            self.write_manifest(
                paths[3],
                "0.2.0",
                [
                    self.workspace_entry(paths[2]),
                    {"path": ".ai-workspace/versions.lock", "owner": "workspace", "sha256": checksum(b"candidate lock")},
                    {"path": "locales/operator-notes.md", "owner": "workspace", "sha256": checksum(b"candidate notes")},
                    {"path": "skills/runtime.txt", "owner": "distribution", "sha256": checksum(b"new")},
                ],
            )
            result = preview_upgrade(*paths)
            self.assertFalse(result["safe_to_apply"])
            metadata_action = next(
                action
                for action in result["conflicts"]
                if action["path"] == ".ai-workspace/workspace.toml"
            )
            self.assertEqual("conflict", metadata_action["action"])
            self.assertIn("ai-native-standard-workspace", metadata_action["reason"])
            self.assertIn("workcell", metadata_action["reason"])
            self.assertIn("formal Migration", metadata_action["reason"])
            self.assertFalse(
                any(
                    action["action"] == "preserve" and action["path"] == ".ai-workspace/workspace.toml"
                    for action in result["actions"]
                )
            )
            for workspace_path in (".ai-workspace/versions.lock", "locales/operator-notes.md"):
                action = next(action for action in result["conflicts"] if action["path"] == workspace_path)
                self.assertEqual("conflict", action["action"])

    def test_cross_product_without_version_change_conflicts(self) -> None:
        """Require a Migration when product identity changes at the same version."""

        with tempfile.TemporaryDirectory() as directory:
            paths = self.prepare(
                Path(directory),
                b"old",
                b"new",
                current_product="ai-native-standard-workspace",
                candidate_product="workcell",
            )
            result = preview_upgrade(*paths)
            self.assertFalse(result["safe_to_apply"])
            metadata_action = next(
                action
                for action in result["conflicts"]
                if action["path"] == ".ai-workspace/workspace.toml"
            )
            self.assertIn("product changes", metadata_action["reason"])

    def test_cross_version_without_product_change_conflicts(self) -> None:
        """Require a Migration when a Workcell Release version changes."""

        with tempfile.TemporaryDirectory() as directory:
            paths = self.prepare(
                Path(directory),
                b"old",
                b"new",
                current_version="0.1.0",
                candidate_version="0.2.0",
            )
            result = preview_upgrade(*paths)
            self.assertFalse(result["safe_to_apply"])
            metadata_action = next(
                action
                for action in result["conflicts"]
                if action["path"] == ".ai-workspace/workspace.toml"
            )
            self.assertIn("release version changes", metadata_action["reason"])

    def test_identity_outside_workspace_table_conflicts(self) -> None:
        """Do not accept a same-named field outside the canonical workspace table."""

        with tempfile.TemporaryDirectory() as directory:
            paths = self.prepare(Path(directory), b"old", b"new")
            self.write_workspace_metadata(paths[2], "workcell")
            (paths[2] / ".ai-workspace/workspace.toml").write_text(
                '[other]\nmanaged_by = "workcell"\n',
                encoding="utf-8",
            )
            self.write_manifest(
                paths[3],
                "0.1.0",
                [
                    self.workspace_entry(paths[2]),
                    {"path": "skills/runtime.txt", "owner": "distribution", "sha256": checksum(b"new")},
                ],
            )

            result = preview_upgrade(*paths)

            self.assertIsNone(result["candidate_product"])
            self.assertFalse(result["safe_to_apply"])
            metadata_action = next(
                action
                for action in result["conflicts"]
                if action["path"] == ".ai-workspace/workspace.toml"
            )
            self.assertIn("Cannot establish", metadata_action["reason"])

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
