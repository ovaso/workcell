#!/usr/bin/env python3
"""Unit tests for the self-contained Skill frontmatter validator."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = REPO_ROOT / "scripts" / "validate-skill.py"
SPEC = importlib.util.spec_from_file_location("validate_skill", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ValidateSkillTests(unittest.TestCase):
    def validate_text(self, text: str) -> list[str]:
        with tempfile.TemporaryDirectory() as temporary_directory:
            skill = Path(temporary_directory)
            (skill / "SKILL.md").write_text(text, encoding="utf-8")
            return MODULE.validate_skill(skill)

    def test_accepts_repository_frontmatter_subset(self) -> None:
        errors = self.validate_text(
            "---\nname: example-skill\ndescription: Perform one bounded workflow.\n---\n\n# Example\n"
        )
        self.assertEqual([], errors)

    def test_rejects_missing_description(self) -> None:
        errors = self.validate_text("---\nname: example-skill\n---\n")
        self.assertTrue(any("description" in error for error in errors))

    def test_rejects_invalid_name(self) -> None:
        errors = self.validate_text(
            "---\nname: Example_Skill\ndescription: Invalid name.\n---\n"
        )
        self.assertTrue(any("hyphen-case" in error for error in errors))

    def test_rejects_unknown_frontmatter_key(self) -> None:
        errors = self.validate_text(
            "---\nname: example-skill\ndescription: Example.\nowner: example\n---\n"
        )
        self.assertTrue(any("unsupported" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
