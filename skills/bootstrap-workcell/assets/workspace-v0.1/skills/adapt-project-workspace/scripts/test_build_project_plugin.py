#!/usr/bin/env python3
"""Unit tests for deterministic project plugin validation."""

from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).with_name("build_project_plugin.py")
SPEC = importlib.util.spec_from_file_location("build_project_plugin", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


def valid_candidate() -> dict:
    """Return a minimal valid plugin candidate for isolated tests."""

    return {
        "schema_version": "0.1",
        "plugin": {
            "id": "sample-project",
            "display_name": "Sample Project",
            "version": "0.1.0",
            "api_version": "0.1",
            "repository_model": "single",
        },
        "repositories": [{"id": "core", "path": "repositories/core", "default_branch": "main"}],
        "modules": [
            {
                "id": "core-app",
                "repository": "core",
                "path": ".",
                "role": "edit",
                "technology_adapters": ["git"],
            }
        ],
        "workflows": {
            "build": [{"id": "build-core", "working_directory": "repositories/core", "argv": ["make"]}],
            "test": [],
            "verify": [],
            "review": [],
            "release": [],
            "rollback": [],
            "close": [],
        },
        "risk_areas": [],
        "knowledge": [],
        "capabilities": {"enabled": []},
        "facts": [
            {
                "id": "fact-repository",
                "kind": "repository",
                "source_type": "discovered",
                "source": ".git/config",
                "observed_at": "2026-07-31T00:00:00Z",
                "context": "project",
                "confidence": "high",
                "sensitivity": "private",
            }
        ],
        "inferences": [
            {
                "id": "inference-build",
                "statement": "The core repository owns the build.",
                "fact_refs": ["fact-repository"],
                "confidence": "medium",
            }
        ],
        "policies": [
            {
                "id": "policy-read-only-default",
                "statement": "Remote actions require explicit authorization.",
                "source_type": "user-confirmed",
            }
        ],
        "unresolved_questions": [],
    }


class BuildProjectPluginTest(unittest.TestCase):
    def test_valid_candidate_is_canonicalized(self) -> None:
        rendered = builder.canonical_json(valid_candidate())
        self.assertIn('"sample-project"', rendered)
        self.assertTrue(rendered.endswith("\n"))

    def test_absolute_or_parent_paths_are_rejected(self) -> None:
        candidate = valid_candidate()
        candidate["repositories"][0]["path"] = "/private/project"
        with self.assertRaises(builder.ValidationError):
            builder.validate_candidate(candidate)

        candidate = valid_candidate()
        candidate["modules"][0]["path"] = "../outside"
        with self.assertRaises(builder.ValidationError):
            builder.validate_candidate(candidate)

    def test_invalid_role_and_unknown_fact_reference_are_rejected(self) -> None:
        candidate = valid_candidate()
        candidate["modules"][0]["role"] = "owner"
        with self.assertRaises(builder.ValidationError):
            builder.validate_candidate(candidate)

        candidate = valid_candidate()
        candidate["inferences"][0]["fact_refs"] = ["missing-fact"]
        with self.assertRaises(builder.ValidationError):
            builder.validate_candidate(candidate)

    def test_credential_like_fields_are_rejected(self) -> None:
        candidate = copy.deepcopy(valid_candidate())
        candidate["plugin"]["api_token"] = "not-allowed"
        with self.assertRaises(builder.ValidationError):
            builder.validate_candidate(candidate)

        candidate = copy.deepcopy(valid_candidate())
        candidate["knowledge"] = [{"id": "private-source", "source": "https://token@example.com/docs"}]
        with self.assertRaises(builder.ValidationError):
            builder.validate_candidate(candidate)


if __name__ == "__main__":
    unittest.main()
