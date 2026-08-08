#!/usr/bin/env python3
"""Unit and repository tests for GitHub configuration validation."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = REPO_ROOT / "scripts" / "validate-github-config.py"
SPEC = importlib.util.spec_from_file_location("validate_github_config", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class GitHubConfigurationTests(unittest.TestCase):
    def test_current_repository_is_valid(self) -> None:
        self.assertEqual([], MODULE.validate_repository(REPO_ROOT))

    def test_rejects_mutable_action_reference(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workflow = Path(temporary_directory) / "example.yml"
            workflow.write_text(
                "name: Example\non:\n  workflow_dispatch:\npermissions:\n  contents: read\n"
                "jobs:\n  example:\n    runs-on: ubuntu-latest\n    steps:\n"
                "      - uses: actions/checkout@v4\n",
                encoding="utf-8",
            )
            errors = MODULE.validate_workflow(workflow)
        self.assertTrue(any("full commit SHA" in error for error in errors))

    def test_accepts_full_action_commit_sha(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workflow = Path(temporary_directory) / "example.yml"
            workflow.write_text(
                "name: Example\non:\n  workflow_dispatch:\npermissions:\n  contents: read\n"
                "jobs:\n  example:\n    runs-on: ubuntu-latest\n    steps:\n"
                "      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1\n",
                encoding="utf-8",
            )
            errors = MODULE.validate_workflow(workflow)
        self.assertEqual([], errors)


if __name__ == "__main__":
    unittest.main()
