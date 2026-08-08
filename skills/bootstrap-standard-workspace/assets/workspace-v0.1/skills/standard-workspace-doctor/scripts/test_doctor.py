#!/usr/bin/env python3
"""Validate the Doctor's read-only core gates."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from doctor import run_doctor
from json_schema_subset import JsonSchemaSubsetValidator


STANDARD_DIRECTORIES = (
    "environment",
    "project/plugin",
    "project/diagnostics",
    "mirror",
    "remotes",
    "requirements",
    "workspaces",
    "diagnostics",
    "tools",
    "knowledge",
    "docs",
    "memory",
    "feedback",
    "locales",
    "skills/example-skill",
    ".ai-workspace",
)


def host_facts_schema() -> dict[str, object]:
    """Build a minimal test schema for the current host-fact contract."""

    return {
        "$defs": {"nonEmpty": {"type": "string", "minLength": 1}},
        "type": "object",
        "additionalProperties": False,
        "required": ["schema_version", "snapshot", "facts"],
        "properties": {
            "schema_version": {"const": "0.1"},
            "snapshot": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "status", "context", "collector", "network_probe_requested"],
                "properties": {
                    "id": {"$ref": "#/$defs/nonEmpty"},
                    "status": {"enum": ["uninitialized", "verified"]},
                    "observed_at": {"type": ["string", "null"], "format": "date-time"},
                    "context": {"enum": ["ai-execution"]},
                    "collector": {"$ref": "#/$defs/nonEmpty"},
                    "network_probe_requested": {"type": "boolean"},
                },
            },
            "facts": {
                "type": "object",
                "additionalProperties": False,
                "required": ["commands", "toolchains", "environment_variables", "network"],
                "properties": {
                    "commands": {"type": "array", "items": {"type": "object"}},
                    "toolchains": {"type": "array", "items": {"type": "object"}},
                    "environment_variables": {"type": "array", "items": {"type": "object"}},
                    "network": {"type": "array", "items": {"type": "object"}},
                },
            },
        },
    }


def project_plugin_schema() -> dict[str, object]:
    """Build a minimal test schema for the current project-plugin contract."""

    required = [
        "schema_version",
        "plugin",
        "repositories",
        "modules",
        "workflows",
        "risk_areas",
        "knowledge",
        "capabilities",
        "facts",
        "inferences",
        "policies",
        "unresolved_questions",
    ]
    return {
        "$defs": {"id": {"type": "string", "pattern": "^[a-z0-9]+(?:-[a-z0-9]+)*$"}},
        "type": "object",
        "additionalProperties": False,
        "required": required,
        "properties": {
            "schema_version": {"const": "0.1"},
            "plugin": {
                "type": "object",
                "required": ["id", "display_name", "version", "api_version", "repository_model"],
                "properties": {
                    "id": {"$ref": "#/$defs/id"},
                    "display_name": {"type": "string", "minLength": 1},
                    "version": {"type": "string", "minLength": 1},
                    "api_version": {"const": "0.1"},
                    "repository_model": {"enum": ["single", "monorepo", "multi"]},
                },
            },
            "repositories": {"type": "array", "minItems": 1, "items": {"type": "object"}},
            "modules": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["id", "repository", "path", "role", "technology_adapters"],
                    "properties": {"role": {"enum": ["edit", "verify", "reference"]}},
                },
            },
            "workflows": {"type": "object"},
            "risk_areas": {"type": "array"},
            "knowledge": {"type": "array"},
            "capabilities": {"type": "object"},
            "facts": {"type": "array"},
            "inferences": {"type": "array"},
            "policies": {"type": "array"},
            "unresolved_questions": {"type": "array"},
        },
    }


def release_manifest_schema() -> dict[str, object]:
    """Build the V0.1 test schema for an installed Release receipt."""

    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["schema_version", "release_version", "files"],
        "properties": {
            "schema_version": {"const": "0.1"},
            "release_version": {"type": "string", "pattern": "^[0-9]+\\.[0-9]+\\.[0-9]+$"},
            "files": {
                "type": "array",
                "minItems": 1,
                "uniqueItems": True,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["path", "owner", "sha256"],
                    "properties": {
                        "path": {
                            "type": "string",
                            "minLength": 1,
                            "not": {"const": ".ai-workspace/release-manifest.json"},
                        },
                        "owner": {"enum": ["distribution", "generated", "workspace"]},
                        "sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                    },
                },
            },
        },
    }


def sha256_file(path: Path) -> str:
    """Compute the SHA-256 of a regular fixture file."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def release_manifest_document(root: Path) -> dict[str, object]:
    """Return an installed Release receipt for the minimal test workspace."""

    return {
        "schema_version": "0.1",
        "release_version": "0.1.0",
        "files": [
            {
                "path": "AI_WORKSPACE.md",
                "owner": "distribution",
                "sha256": sha256_file(root / "AI_WORKSPACE.md"),
            }
        ],
    }


def host_facts_document() -> dict[str, object]:
    """Return host facts valid as both a template and uninitialized projection."""

    return {
        "schema_version": "0.1",
        "snapshot": {
            "id": "uninitialized",
            "status": "uninitialized",
            "context": "ai-execution",
            "collector": "not-run",
            "network_probe_requested": False,
        },
        "facts": {"commands": [], "toolchains": [], "environment_variables": [], "network": []},
    }


def project_plugin_document() -> dict[str, object]:
    """Return a minimal valid plugin for templates and project instances."""

    return {
        "schema_version": "0.1",
        "plugin": {
            "id": "test-project",
            "display_name": "Test",
            "version": "0.1.0",
            "api_version": "0.1",
            "repository_model": "single",
        },
        "repositories": [{"id": "repo", "path": "repositories/repo", "default_branch": "main"}],
        "modules": [
            {
                "id": "api",
                "repository": "repo",
                "path": ".",
                "role": "reference",
                "technology_adapters": [],
            }
        ],
        "workflows": {"build": [], "test": [], "verify": [], "review": [], "release": [], "rollback": [], "close": []},
        "risk_areas": [],
        "knowledge": [],
        "capabilities": {"enabled": []},
        "facts": [],
        "inferences": [],
        "policies": [],
        "unresolved_questions": [],
    }


class DoctorTest(unittest.TestCase):
    """Cover a valid workspace and critical fail-closed scenarios."""

    def create_workspace(self, root: Path) -> None:
        """Create a minimal valid test workspace independent of product assets."""

        for relative in STANDARD_DIRECTORIES:
            (root / relative).mkdir(parents=True, exist_ok=True)
        (root / "AI_WORKSPACE.md").write_text("# AI Workspace\n", encoding="utf-8")
        (root / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
        (root / ".ai-workspace/workspace.toml").write_text(
            '[workspace]\nid = "test-workspace"\nname = "Test Workspace"\nstatus = "CREATED"\n'
            'managed_by = "ai-native-standard-workspace"\n',
            encoding="utf-8",
        )
        (root / ".ai-workspace/versions.lock").write_text(
            '[versions]\nproduct = "0.1.0"\nworkspace = "0.1"\n', encoding="utf-8"
        )
        (root / "skills/example-skill/SKILL.md").write_text(
            "---\nname: example-skill\ndescription: Execute one deterministic example capability.\n---\n\n# Example\n",
            encoding="utf-8",
        )
        (root / ".ai-workspace/ownership.toml").write_text(
            '[ownership]\nversion = "0.1"\ndefault = "workspace"\n'
            '[[rules]]\npattern = "AI_WORKSPACE.md"\nowner = "distribution"\n',
            encoding="utf-8",
        )
        (root / ".ai-workspace/distribution.manifest").write_text("AI_WORKSPACE.md\n", encoding="utf-8")
        (root / ".ai-workspace/schemas").mkdir()
        (root / ".ai-workspace/templates").mkdir()
        (root / "environment/current").mkdir()
        (root / ".ai-workspace/schemas/environment-facts.schema.json").write_text(
            json.dumps(host_facts_schema()), encoding="utf-8"
        )
        (root / ".ai-workspace/schemas/project-plugin.schema.json").write_text(
            json.dumps(project_plugin_schema()), encoding="utf-8"
        )
        (root / ".ai-workspace/schemas/release-manifest.schema.json").write_text(
            json.dumps(release_manifest_schema()), encoding="utf-8"
        )
        host_document = json.dumps(host_facts_document())
        (root / ".ai-workspace/templates/host-facts.json").write_text(host_document, encoding="utf-8")
        (root / "environment/current/host-facts.json").write_text(host_document, encoding="utf-8")
        project_document = json.dumps(project_plugin_document())
        (root / ".ai-workspace/templates/project-plugin.json").write_text(project_document, encoding="utf-8")
        (root / "project/plugin/project-plugin.json").write_text(project_document, encoding="utf-8")
        (root / ".ai-workspace/release-manifest.json").write_text(
            json.dumps(release_manifest_document(root)), encoding="utf-8"
        )

    def test_minimal_workspace_passes(self) -> None:
        """Confirm a minimal valid structure produces no errors."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.create_workspace(root)
            result = run_doctor(root)
            self.assertEqual("PASS", result["status"])

    def test_release_manifest_is_required_and_schema_validated(self) -> None:
        """Fail closed when the Release receipt is missing or schema-invalid."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.create_workspace(root)
            receipt_path = root / ".ai-workspace/release-manifest.json"
            receipt_path.unlink()
            missing = run_doctor(root)
            self.assertTrue(
                any(item["code"] == "structure.file-missing" and item["path"] == ".ai-workspace/release-manifest.json" for item in missing["findings"])
            )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.create_workspace(root)
            receipt_path = root / ".ai-workspace/release-manifest.json"
            receipt = release_manifest_document(root)
            receipt["files"][0]["sha256"] = "invalid"
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            invalid = run_doctor(root)
            self.assertTrue(
                any(item["code"] == "schema.instance-invalid" and item["path"] == ".ai-workspace/release-manifest.json" for item in invalid["findings"])
            )

    def test_release_manifest_version_matches_versions_lock(self) -> None:
        """Require the receipt version to equal the versions.lock product version."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.create_workspace(root)
            receipt_path = root / ".ai-workspace/release-manifest.json"
            receipt = release_manifest_document(root)
            receipt["release_version"] = "9.9.9"
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            result = run_doctor(root)
            self.assertTrue(any(item["code"] == "release.version-mismatch" for item in result["findings"]))

    def test_release_manifest_detects_distribution_file_failures(self) -> None:
        """Report missing, linked, non-regular, and drifted distribution files as ERROR."""

        with tempfile.TemporaryDirectory() as directory:
            container = Path(directory)
            root = container / "workspace"
            root.mkdir()
            self.create_workspace(root)
            outside = container / "outside.txt"
            outside.write_text("outside\n", encoding="utf-8")
            try:
                (root / "docs/distribution-link").symlink_to(outside)
            except (NotImplementedError, OSError) as exc:
                self.skipTest(f"Host cannot create test symlinks: {exc}")
            receipt = release_manifest_document(root)
            receipt["files"] = [
                {"path": "AI_WORKSPACE.md", "owner": "distribution", "sha256": "0" * 64},
                {"path": "docs/missing.txt", "owner": "distribution", "sha256": "0" * 64},
                {"path": "docs", "owner": "distribution", "sha256": "0" * 64},
                {"path": "docs/distribution-link", "owner": "distribution", "sha256": "0" * 64},
            ]
            (root / ".ai-workspace/release-manifest.json").write_text(json.dumps(receipt), encoding="utf-8")
            result = run_doctor(root)
            codes = {item["code"] for item in result["findings"]}
            self.assertTrue(
                {
                    "release.distribution-file-drift",
                    "release.distribution-file-missing",
                    "release.distribution-file-not-regular",
                    "release.distribution-file-symlink",
                }.issubset(codes)
            )

    def test_release_manifest_allows_mutable_owner_changes(self) -> None:
        """Confirm installed hashes do not freeze generated and workspace entries."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.create_workspace(root)
            receipt = release_manifest_document(root)
            receipt["files"].extend(
                [
                    {"path": "AGENTS.md", "owner": "generated", "sha256": "0" * 64},
                    {"path": "project/local-state.json", "owner": "workspace", "sha256": "0" * 64},
                ]
            )
            (root / ".ai-workspace/release-manifest.json").write_text(json.dumps(receipt), encoding="utf-8")
            (root / "AGENTS.md").write_text("# Runtime generated agents\n", encoding="utf-8")
            result = run_doctor(root)
            self.assertEqual("PASS", result["status"])

    def test_json_schema_subset_covers_v01_keywords(self) -> None:
        """Confirm every V0.1 schema keyword has actual validation semantics."""

        schema = {
            "$defs": {
                "item": {
                    "allOf": [
                        {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["kind", "name"],
                            "properties": {
                                "kind": {"enum": ["allowed", "forbidden"]},
                                "name": {"type": "string", "minLength": 2, "maxLength": 5, "pattern": "^[a-z]+$"},
                            },
                        },
                        {
                            "not": {
                                "type": "object",
                                "required": ["kind"],
                                "properties": {"kind": {"const": "forbidden"}},
                            }
                        },
                    ]
                }
            },
            "type": "object",
            "additionalProperties": False,
            "required": ["mode", "items", "score", "observed_at", "labels", "optional"],
            "properties": {
                "mode": {"enum": ["safe"]},
                "items": {
                    "type": "array",
                    "minItems": 1,
                    "uniqueItems": True,
                    "items": {"$ref": "#/$defs/item"},
                },
                "score": {"type": "integer", "minimum": 1},
                "observed_at": {"type": "string", "format": "date-time"},
                "labels": {
                    "type": "object",
                    "propertyNames": {"type": "string", "maxLength": 5, "pattern": "^[a-z]+$"},
                    "additionalProperties": {"type": "string", "minLength": 1},
                },
                "optional": {"type": ["string", "null"]},
            },
        }
        validator = JsonSchemaSubsetValidator(schema)
        self.assertEqual([], validator.inspect_schema())
        valid = {
            "mode": "safe",
            "items": [{"kind": "allowed", "name": "tool"}],
            "score": 1,
            "observed_at": "2026-07-31T12:30:00Z",
            "labels": {"team": "core"},
            "optional": None,
        }
        self.assertEqual([], validator.validate(valid))
        self.assertEqual([], validator.validate({**valid, "observed_at": "2026-07-31t12:30:00z"}))
        self.assertEqual([], validator.validate({**valid, "observed_at": "1990-12-31T23:59:60Z"}))

        invalid = {
            "mode": "unsafe",
            "items": [
                {"kind": "forbidden", "name": "A"},
                {"kind": "allowed", "name": "toolong"},
                {"kind": "allowed", "name": "toolong"},
                {"kind": "allowed"},
            ],
            "score": 0,
            "observed_at": "not-a-date",
            "labels": {"TOOLONG": ""},
            "optional": 3,
            "extra": True,
        }
        violations = validator.validate(invalid)
        constraint_paths = {violation.schema_path.rsplit("/", 1)[-1] for violation in violations}
        self.assertTrue(
            {
                "additionalProperties",
                "enum",
                "format",
                "maxLength",
                "minLength",
                "minimum",
                "not",
                "pattern",
                "required",
                "type",
                "uniqueItems",
            }.issubset(constraint_paths)
        )
        self.assertTrue(any(violation.schema_path.endswith("/minItems") for violation in validator.validate({**valid, "items": []})))

    def test_schema_contract_drift_fails_templates(self) -> None:
        """Fail closed when a bundled schema adds a required field absent from templates."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.create_workspace(root)
            schema_path = root / ".ai-workspace/schemas/environment-facts.schema.json"
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            schema["required"].append("future_required_field")
            schema_path.write_text(json.dumps(schema), encoding="utf-8")
            result = run_doctor(root)
            matching = [item for item in result["findings"] if item["code"] == "schema.instance-invalid"]
            self.assertEqual("FAIL", result["status"])
            self.assertTrue(any(item["path"] == ".ai-workspace/templates/host-facts.json" for item in matching))

    def test_unsupported_schema_drift_fails_closed(self) -> None:
        """Do not silently ignore a newly added unsupported constraint."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.create_workspace(root)
            schema_path = root / ".ai-workspace/schemas/project-plugin.schema.json"
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            schema["maxProperties"] = 20
            schema_path.write_text(json.dumps(schema), encoding="utf-8")
            result = run_doctor(root)
            self.assertEqual("FAIL", result["status"])
            self.assertTrue(any(item["code"] == "schema.definition-invalid" for item in result["findings"]))

        hidden_constraint = JsonSchemaSubsetValidator({"const": {"maxProperties": 0}, "$ref": "#/const"})
        self.assertTrue(any("maxProperties" in item.message for item in hidden_constraint.inspect_schema()))

    def test_current_host_facts_instance_drift_fails(self) -> None:
        """Report ERROR when current host facts drift from the schema."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.create_workspace(root)
            current_path = root / "environment/current/host-facts.json"
            document = json.loads(current_path.read_text(encoding="utf-8"))
            del document["facts"]["network"]
            current_path.write_text(json.dumps(document), encoding="utf-8")
            result = run_doctor(root)
            matching = [item for item in result["findings"] if item["code"] == "schema.instance-invalid"]
            self.assertEqual("FAIL", result["status"])
            self.assertTrue(any(item["path"] == "environment/current/host-facts.json" for item in matching))

    def test_duplicate_json_key_fails_closed(self) -> None:
        """Ensure duplicate JSON keys are not silently overwritten by the parser."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.create_workspace(root)
            current_path = root / "environment/current/host-facts.json"
            current_path.write_text('{"schema_version":"0.1","schema_version":"0.1"}', encoding="utf-8")
            result = run_doctor(root)
            self.assertEqual("FAIL", result["status"])
            self.assertTrue(any(item["code"] == "schema.instance-json-invalid" for item in result["findings"]))

    def test_project_plugin_instance_drift_fails(self) -> None:
        """Report ERROR when an existing project-plugin role violates the schema."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.create_workspace(root)
            plugin_path = root / "project/plugin/project-plugin.json"
            document = json.loads(plugin_path.read_text(encoding="utf-8"))
            document["modules"][0]["role"] = "owner"
            plugin_path.write_text(json.dumps(document), encoding="utf-8")
            result = run_doctor(root)
            matching = [item for item in result["findings"] if item["code"] == "schema.instance-invalid"]
            self.assertEqual("FAIL", result["status"])
            self.assertTrue(any(item["path"] == "project/plugin/project-plugin.json" for item in matching))

    def test_missing_required_file_fails(self) -> None:
        """Fail closed when an entry file is missing."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.create_workspace(root)
            (root / "AI_WORKSPACE.md").unlink()
            result = run_doctor(root)
            self.assertEqual("FAIL", result["status"])
            self.assertTrue(any(item["code"] == "structure.file-missing" for item in result["findings"]))

    def test_invalid_workspace_state_fails(self) -> None:
        """Ensure an unknown lifecycle state cannot pass the gate."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.create_workspace(root)
            (root / ".ai-workspace/workspace.toml").write_text('[workspace]\nstatus = "MAGIC"\n', encoding="utf-8")
            result = run_doctor(root)
            self.assertTrue(any(item["code"] == "workspace.state-invalid" for item in result["findings"]))

    def test_task_role_cannot_expand_project_role(self) -> None:
        """Ensure a task cannot expand a reference module to edit."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.create_workspace(root)
            task_root = root / "requirements/task-1"
            task_root.mkdir()
            (task_root / "task.toml").write_text(
                'gates = []\nrisk_tags = []\nevidence = []\n'
                '[task]\nid = "task-1"\ntitle = "Role check"\ntype = "review"\nstatus = "SCOPED"\n'
                'project_plugin_ref = "project/plugin/project-plugin.json"\n'
                '[scope]\nedit = ["api"]\nverify = []\nreference = []\nexcluded = []\n'
                '[workflow]\ncurrent_plan = ""\nnext_action = "Plan"\nnext_gate = "PLANNED"\n',
                encoding="utf-8",
            )
            result = run_doctor(root)
            self.assertTrue(any(item["code"] == "task.module-role-expanded" for item in result["findings"]))

    def test_task_project_plugin_ref_rejects_symlink(self) -> None:
        """Ensure a task cannot follow a project-plugin symlink outside the workspace."""

        with tempfile.TemporaryDirectory() as directory:
            container = Path(directory)
            root = container / "workspace"
            root.mkdir()
            self.create_workspace(root)
            outside = container / "outside-project-plugin.json"
            outside.write_text(json.dumps(project_plugin_document()), encoding="utf-8")
            plugin_path = root / "project/plugin/project-plugin.json"
            plugin_path.unlink()
            try:
                plugin_path.symlink_to(outside)
            except (NotImplementedError, OSError) as exc:
                self.skipTest(f"Host cannot create test symlinks: {exc}")
            task_root = root / "requirements/task-symlink"
            task_root.mkdir()
            (task_root / "task.toml").write_text(
                'gates = []\nevidence = []\n'
                '[task]\nid = "task-symlink"\ntitle = "Symlink"\ntype = "review"\nstatus = "SCOPED"\n'
                'project_plugin_ref = "project/plugin/project-plugin.json"\n'
                '[scope]\nedit = []\nverify = []\nreference = []\nexcluded = []\n'
                '[workflow]\ncurrent_plan = ""\nnext_action = "Stop"\nnext_gate = "PLANNED"\n',
                encoding="utf-8",
            )
            result = run_doctor(root)
            self.assertEqual("FAIL", result["status"])
            self.assertTrue(any(item["code"] == "task.project-plugin-ref-symlink" for item in result["findings"]))

    def test_dev_feedback_task_state_is_supported(self) -> None:
        """Confirm development feedback uses the schema's DEV_FEEDBACK state."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.create_workspace(root)
            task_root = root / "requirements/task-feedback"
            task_root.mkdir()
            (task_root / "task.toml").write_text(
                'gates = []\nevidence = []\n'
                '[task]\nid = "task-feedback"\ntitle = "Feedback"\ntype = "defect"\n'
                'status = "DEV_FEEDBACK"\nproject_plugin_ref = "project/plugin/project-plugin.json"\n'
                '[scope]\nedit = []\nverify = []\nreference = ["api"]\nexcluded = []\n'
                '[workflow]\ncurrent_plan = "plans/plan-1.md"\nnext_action = "Fix and re-verify"\n'
                'next_gate = "VERIFYING"\n',
                encoding="utf-8",
            )
            result = run_doctor(root)
            self.assertFalse(any(item["code"] == "task.state-invalid" for item in result["findings"]))

    def test_unconfigured_diagnostics_cannot_open_remote_actions(self) -> None:
        """Ensure unconfigured diagnostics cannot enable remote actions."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.create_workspace(root)
            (root / "project/diagnostics/diagnostic-profile.toml").write_text(
                'schema_version = "0.1"\ntargets = []\nproviders = []\ncorrelations = []\n'
                '[profile]\nid = "test-diagnostics"\napi_version = "0.1"\nstatus = "unconfigured"\n'
                'configured_by_interview = false\n'
                '[policies]\ndefault_action = "deny"\nremote_shell = "ask"\nremote_write = "deny"\n'
                'credential_output = "deny"\nunknown_target = "deny"\n'
                '[retention]\nevidence_directory = "requirements"\nredaction_required = true\n',
                encoding="utf-8",
            )
            result = run_doctor(root)
            self.assertTrue(any(item["code"] == "diagnostics.unverified-open" for item in result["findings"]))

    def test_distribution_manifest_requires_exact_distribution_rule(self) -> None:
        """Ensure a distribution entry cannot rely only on a broad ownership rule."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.create_workspace(root)
            (root / ".ai-workspace/ownership.toml").write_text(
                '[ownership]\nversion = "0.1"\ndefault = "workspace"\n'
                '[[rules]]\npattern = "**"\nowner = "distribution"\n',
                encoding="utf-8",
            )
            result = run_doctor(root)
            self.assertTrue(any(item["code"] == "distribution.owner-rule-missing" for item in result["findings"]))


if __name__ == "__main__":
    unittest.main()
