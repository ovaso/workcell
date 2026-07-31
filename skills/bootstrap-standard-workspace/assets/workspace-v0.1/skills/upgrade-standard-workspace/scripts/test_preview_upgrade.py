#!/usr/bin/env python3
"""验证升级预览对用户内容和发行冲突的保护。"""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from preview_upgrade import UpgradePreviewError, preview_upgrade


def checksum(content: bytes) -> str:
    """计算测试清单使用的 SHA-256。"""

    return hashlib.sha256(content).hexdigest()


class UpgradePreviewTest(unittest.TestCase):
    """覆盖替换、保护、冲突、删除和路径逃逸场景。"""

    def write_manifest(self, path: Path, version: str, entries: list[dict[str, str]]) -> None:
        """写入一个最小测试发行清单。"""

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"schema_version": "0.1", "release_version": version, "files": entries}),
            encoding="utf-8",
        )

    def prepare(self, root: Path, old: bytes, new: bytes) -> tuple[Path, Path, Path, Path]:
        """创建包含单个发行文件的当前和候选目录。"""

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
        """确认未修改发行文件生成安全替换动作。"""

        with tempfile.TemporaryDirectory() as directory:
            paths = self.prepare(Path(directory), b"old", b"new")
            result = preview_upgrade(*paths)
            self.assertTrue(result["safe_to_apply"])
            self.assertEqual("replace", result["actions"][0]["action"])
            self.assertEqual("replace-receipt", result["actions"][-1]["action"])
            self.assertEqual(".ai-workspace/release-manifest.json", result["actions"][-1]["path"])

    def test_locally_modified_distribution_file_conflicts(self) -> None:
        """确认本地修改不会被候选发行静默覆盖。"""

        with tempfile.TemporaryDirectory() as directory:
            paths = self.prepare(Path(directory), b"old", b"new")
            (paths[0] / "skills/runtime.txt").write_bytes(b"user change")
            result = preview_upgrade(*paths)
            self.assertFalse(result["safe_to_apply"])
            self.assertEqual("conflict", result["actions"][0]["action"])

    def test_workspace_owned_file_is_preserved(self) -> None:
        """确认工作区所有权文件只生成保留动作。"""

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
        """确认候选删除只作用于未修改的发行文件。"""

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
        """确认清单不能通过父级路径逃出工作区。"""

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
        """确认候选发行不能携带完整性清单未覆盖的普通文件。"""

        with tempfile.TemporaryDirectory() as directory:
            paths = self.prepare(Path(directory), b"old", b"new")
            (paths[2] / "unlisted.txt").write_text("unlisted", encoding="utf-8")
            with self.assertRaises(UpgradePreviewError):
                preview_upgrade(*paths)

    def test_manifest_cannot_hash_itself(self) -> None:
        """确认安装收据路径不能出现在自身 files 数组中。"""

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
        """确认升级预览拒绝旧式无 schema_version 清单。"""

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
