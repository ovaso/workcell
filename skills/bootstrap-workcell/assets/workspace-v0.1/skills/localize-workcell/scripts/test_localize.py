#!/usr/bin/env python3
"""Exercise the offline overlay/replace localization safety contract."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from localize import apply, preview, rollback


def digest(path: Path) -> str:
    """Return a fixture file digest."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


class LocalizeTest(unittest.TestCase):
    """Keep direct replacement explicit, auditable, and recoverable."""

    def create_workspace(self, root: Path) -> tuple[Path, Path]:
        """Create a small self-hosting fixture with one distribution document."""

        (root / ".ai-workspace").mkdir()
        (root / "docs").mkdir()
        source = root / "docs/getting-started.md"
        source.write_text(
            "# Getting started\n\nOperators MUST run `workcell doctor` at https://example.test/docs.\n\n```sh\nworkcell doctor --json\n```\n",
            encoding="utf-8",
        )
        (root / "AI_WORKSPACE.md").write_text("# Workspace\n", encoding="utf-8")
        (root / ".ai-workspace/workspace.toml").write_text("[workspace]\nstatus = \"CREATED\"\n", encoding="utf-8")
        (root / ".ai-workspace/versions.lock").write_text("[versions]\nproduct = \"0.2.0\"\n", encoding="utf-8")
        (root / ".ai-workspace/release-manifest.json").write_text(
            json.dumps(
                {
                    "schema_version": "0.1",
                    "release_version": "0.2.0",
                    "files": [{"path": "docs/getting-started.md", "owner": "distribution", "sha256": digest(source)}],
                }
            ),
            encoding="utf-8",
        )
        translations = root / "reviewed-zh-CN"
        translated = translations / "docs/getting-started.md"
        translated.parent.mkdir(parents=True)
        translated.write_text(
            "# Demarrage\n\nL'operateur MUST execute `workcell doctor`; voir https://example.test/docs.\n\n```sh\nworkcell doctor --json\n```\n",
            encoding="utf-8",
        )
        return source, translations

    def test_replace_preview_apply_and_per_file_rollback(self) -> None:
        """Record an approved replacement as known integrity drift, then restore it."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, translations = self.create_workspace(root)
            original = source.read_text(encoding="utf-8")
            report = preview(root, translations, "zh-CN", "replace", {"standard-documents"})
            self.assertEqual([], report["untranslatable_items"])
            self.assertIn("--- source/docs/getting-started.md", report["files"][0]["diff"])
            result = apply(root, translations, "zh-CN", "replace", {"standard-documents"}, "ticket LOC-42", False)
            self.assertIn("Demarrage", source.read_text(encoding="utf-8"))
            registry = (root / ".ai-workspace/localization-overrides.toml").read_text(encoding="utf-8")
            self.assertIn('approval = "ticket LOC-42"', registry)
            self.assertTrue((root / result["snapshot"] / "files/docs/getting-started.md").is_file())
            rollback(root, result["snapshot"].split("/")[-1], {"docs/getting-started.md"}, "ticket LOC-42 rollback")
            self.assertEqual(original, source.read_text(encoding="utf-8"))
            self.assertNotIn("docs/getting-started.md", (root / ".ai-workspace/localization-overrides.toml").read_text(encoding="utf-8"))

    def test_protected_tokens_block_replace(self) -> None:
        """Reject a translation that changes the source command inside a fenced block."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, translations = self.create_workspace(root)
            translated = translations / "docs/getting-started.md"
            translated.write_text("# Demarrage\n\nMUST\n\n```sh\ntranslated command\n```\n", encoding="utf-8")
            report = preview(root, translations, "zh-CN", "replace", {"standard-documents"})
            self.assertTrue(report["untranslatable_items"])
            with self.assertRaisesRegex(ValueError, "protected content"):
                apply(root, translations, "zh-CN", "replace", {"standard-documents"}, "ticket LOC-43", False)

    def test_refresh_rollback_restores_the_previous_override_record(self) -> None:
        """Keep an older reviewed replacement registered when a refresh is rolled back."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, translations = self.create_workspace(root)
            first = apply(root, translations, "zh-CN", "replace", {"standard-documents"}, "ticket LOC-45", False)
            first_content = source.read_text(encoding="utf-8")
            translated = translations / "docs/getting-started.md"
            translated.write_text(
                "# Nouveau demarrage\n\nL'operateur MUST execute `workcell doctor`; voir https://example.test/docs.\n\n```sh\nworkcell doctor --json\n```\n",
                encoding="utf-8",
            )
            refreshed = apply(root, translations, "zh-CN", "replace", {"standard-documents"}, "ticket LOC-46", True)
            rollback(root, refreshed["snapshot"].split("/")[-1], {"docs/getting-started.md"}, "ticket LOC-46 rollback")
            self.assertEqual(first_content, source.read_text(encoding="utf-8"))
            registry = (root / ".ai-workspace/localization-overrides.toml").read_text(encoding="utf-8")
            self.assertIn(first["snapshot"].split("/")[-1], registry)

    def test_adapter_only_allows_display_and_prompt_fields(self) -> None:
        """Preserve adapter keys, structure, and machine-only values exactly."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.create_workspace(root)
            adapter = root / "skills/example/agents/openai.yaml"
            adapter.parent.mkdir(parents=True)
            adapter.write_text(
                'interface:\n  display_name: "Example"\n  short_description: "Description"\n  default_prompt: "Prompt"\n  machine_value: "stable"\n',
                encoding="utf-8",
            )
            translations = root / "reviewed-zh-CN"
            translated = translations / "skills/example/agents/openai.yaml"
            translated.parent.mkdir(parents=True, exist_ok=True)
            translated.write_text(
                'interface:\n  display_name: "Exemple"\n  short_description: "Description localisee"\n  default_prompt: "Invite localisee"\n  machine_value: "changed"\n',
                encoding="utf-8",
            )
            report = preview(root, translations, "zh-CN", "overlay", {"ai-adapters"})
            self.assertTrue(report["untranslatable_items"])


if __name__ == "__main__":
    unittest.main()
