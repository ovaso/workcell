#!/usr/bin/env python3
"""Unit tests for the read-only host fact collector."""

from __future__ import annotations

import importlib.util
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path


SCRIPT_PATH = Path(__file__).with_name("inspect_host.py")
SPEC = importlib.util.spec_from_file_location("inspect_host", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
inspect_host = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(inspect_host)


class InspectHostTest(unittest.TestCase):
    def test_environment_classification_never_needs_values(self) -> None:
        self.assertEqual(("secret", "credential-like-name"), inspect_host.classify_env_name("API_TOKEN"))
        self.assertEqual(("private", "identity-path-or-endpoint-name"), inspect_host.classify_env_name("HOME"))
        self.assertEqual(("public", "explicit-safe-name"), inspect_host.classify_env_name("LANG"))
        self.assertEqual(("secret", "unknown-defaults-to-secret"), inspect_host.classify_env_name("MYSTERY_FLAG"))

    def test_network_target_rejects_credential_and_query_expansion(self) -> None:
        with self.assertRaises(ValueError):
            inspect_host.sanitize_network_target("https://user:pass@example.com/health")
        with self.assertRaises(ValueError):
            inspect_host.sanitize_network_target("https://example.com/health?token=x")
        self.assertEqual(
            ("tcp", "tcp://example.com:443"),
            inspect_host.sanitize_network_target("tcp://EXAMPLE.com:443"),
        )
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            inspect_host.parse_args(["--context", "desktop"])

    def test_snapshot_contains_names_but_not_environment_values(self) -> None:
        variable_name = "STANDARD_WORKSPACE_TEST_SECRET"
        previous = os.environ.get(variable_name)
        os.environ[variable_name] = "must-not-appear"
        try:
            args = inspect_host.parse_args(
                [
                    "--context",
                    "task",
                    "--no-default-commands",
                    "--env-name",
                    variable_name,
                    "--network-target",
                    "https://example.com/health",
                ]
            )
            snapshot = inspect_host.build_snapshot(args)
            rendered = json.dumps(snapshot)
            self.assertIn(variable_name, rendered)
            self.assertNotIn("must-not-appear", rendered)
            self.assertIn("declared-not-probed", rendered)
            self.assertEqual("verified", snapshot["snapshot"]["status"])
            self.assertEqual(
                {"commands", "toolchains", "environment_variables", "network"},
                set(snapshot["facts"]),
            )
            self.assertNotIn("platform", snapshot["facts"])

            degraded_args = inspect_host.parse_args(
                ["--context", "task", "--status", "degraded", "--no-default-commands", "--skip-environment-names"]
            )
            self.assertEqual("degraded", inspect_host.build_snapshot(degraded_args)["snapshot"]["status"])
        finally:
            if previous is None:
                os.environ.pop(variable_name, None)
            else:
                os.environ[variable_name] = previous

    def test_output_refuses_overwrite_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "snapshot.json"
            output.write_text("existing", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                inspect_host.write_json({"ok": True}, str(output), force=False)


if __name__ == "__main__":
    unittest.main()
