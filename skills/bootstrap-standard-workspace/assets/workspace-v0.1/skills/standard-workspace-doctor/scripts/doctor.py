#!/usr/bin/env python3
"""Check Standard Workspace V0.1 core invariants without modifying the workspace."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from json_schema_subset import JsonSchemaSubsetValidator, load_json_document


WORKSPACE_STATES = {
    "CREATED",
    "ENVIRONMENT_INITIALIZED",
    "PROJECT_ATTACHED",
    "PROJECT_ADAPTED",
    "DIAGNOSTICS_CONFIGURED",
    "READY",
    "DEGRADED",
    "PAUSED",
    "ARCHIVED",
}
TASK_STATES = {
    "INBOX",
    "SCOPED",
    "PLANNED",
    "READY",
    "IMPLEMENTING",
    "VERIFYING",
    "DEV_FEEDBACK",
    "TEST_FEEDBACK",
    "QC_READY",
    "RELEASE_READY",
    "DONE",
    "ARCHIVED",
    "PAUSED",
}
TASK_SCOPE_ROLES = {"excluded": -1, "reference": 0, "verify": 1, "edit": 2}
PROJECT_ROLE_CEILINGS = {"reference": 0, "verify": 1, "edit": 2}
GATE_STATES = {"pending", "passed", "failed", "waived", "not-applicable"}
PLAN_REQUIRED_STATES = {
    "PLANNED",
    "READY",
    "IMPLEMENTING",
    "VERIFYING",
    "DEV_FEEDBACK",
    "TEST_FEEDBACK",
    "QC_READY",
    "RELEASE_READY",
    "DONE",
    "ARCHIVED",
}
STANDARD_DIRECTORIES = (
    ".ai-workspace",
    "environment",
    "project",
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
    "skills",
)
REQUIRED_FILES = (
    "AI_WORKSPACE.md",
    "AGENTS.md",
    ".ai-workspace/workspace.toml",
    ".ai-workspace/versions.lock",
    ".ai-workspace/release-manifest.json",
    ".ai-workspace/distribution.manifest",
    ".ai-workspace/ownership.toml",
)
SENSITIVE_KEYS = {
    "password",
    "passwd",
    "token",
    "secret",
    "private_key",
    "api_key",
    "access_key",
    "client_secret",
}
REFERENCE_PREFIXES = ("env://", "keychain://", "file-ref://", "vault://", "secret-ref://")
JSON_SCHEMA_TARGETS = (
    (
        ".ai-workspace/schemas/environment-facts.schema.json",
        (
            (".ai-workspace/templates/host-facts.json", True),
            ("environment/current/host-facts.json", True),
        ),
    ),
    (
        ".ai-workspace/schemas/project-plugin.schema.json",
        (
            (".ai-workspace/templates/project-plugin.json", True),
            ("project/plugin/project-plugin.json", False),
        ),
    ),
    (
        ".ai-workspace/schemas/release-manifest.schema.json",
        ((".ai-workspace/release-manifest.json", True),),
    ),
)


@dataclass(frozen=True)
class Finding:
    """Represent a stable, serializable Doctor check result."""

    severity: str
    code: str
    path: str
    message: str


class WorkspaceDoctor:
    """Collect workspace structure, safety, and lifecycle issues without writes."""

    def __init__(self, root: Path) -> None:
        """Initialize the workspace root and result collection."""

        self.root = root.resolve()
        self.findings: list[Finding] = []
        self.workspace_state: str | None = None
        self.product_version: str | None = None
        self.validated_json_instances: set[str] = set()

    def add(self, severity: str, code: str, path: Path | str, message: str) -> None:
        """Append a check result expressed with a workspace-relative path."""

        path_obj = Path(path)
        try:
            display_path = path_obj.resolve().relative_to(self.root).as_posix()
        except (OSError, ValueError):
            display_path = str(path)
        self.findings.append(Finding(severity, code, display_path or ".", message))

    def load_toml(self, path: Path, code: str) -> dict[str, Any] | None:
        """Parse TOML; record an error and return an empty result on failure."""

        try:
            with path.open("rb") as stream:
                value = tomllib.load(stream)
        except (OSError, tomllib.TOMLDecodeError) as exc:
            self.add("ERROR", code, path, f"Unable to parse TOML: {exc}")
            return None
        return value

    def load_json(self, path: Path, code: str) -> Any | None:
        """Parse JSON strictly, rejecting non-standard values such as NaN and Infinity."""

        try:
            return load_json_document(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            self.add("ERROR", code, path, f"Unable to parse JSON: {exc}")
            return None

    def run(self) -> list[Finding]:
        """Run every read-only check and return results in stable order."""

        self.check_required_structure()
        self.check_json_schema_instances()
        self.check_workspace_manifest()
        self.check_versions_lock()
        self.check_release_receipt()
        self.check_runtime_skills()
        self.check_tasks()
        self.check_diagnostics()
        self.check_ownership_manifest()
        return sorted(self.findings, key=lambda item: (severity_rank(item.severity), item.code, item.path))

    def check_json_schema_instances(self) -> None:
        """Validate templates, current environment facts, and an optional project plugin."""

        for schema_relative, targets in JSON_SCHEMA_TARGETS:
            schema_path = self.root / schema_relative
            if self.has_symlink_component(schema_path):
                self.add("ERROR", "schema.path-symlink", schema_path, "Schema path contains a symlink; refusing to follow it")
                continue
            if not schema_path.is_file():
                self.add("ERROR", "schema.file-missing", schema_path, "Bundled JSON Schema required by the Doctor is missing")
                continue
            schema = self.load_json(schema_path, "schema.json-invalid")
            if schema is None:
                continue
            validator = JsonSchemaSubsetValidator(schema)
            definition_issues = validator.inspect_schema()
            for issue in definition_issues:
                self.add(
                    "ERROR",
                    "schema.definition-invalid",
                    schema_path,
                    f"{issue.schema_path}: {issue.message}",
                )
            if definition_issues:
                continue
            for target_relative, required in targets:
                target_path = self.root / target_relative
                if self.has_symlink_component(target_path):
                    self.add("ERROR", "schema.instance-path-symlink", target_path, "JSON instance path contains a symlink; refusing to follow it")
                    continue
                if not target_path.is_file():
                    if required:
                        self.add("ERROR", "schema.instance-missing", target_path, "JSON file required to pass schema validation is missing")
                    continue
                instance = self.load_json(target_path, "schema.instance-json-invalid")
                if instance is None:
                    continue
                violations = validator.validate(instance)
                for violation in violations:
                    self.add(
                        "ERROR",
                        "schema.instance-invalid",
                        target_path,
                        f"Instance {violation.instance_path} violates {violation.schema_path}: {violation.message}",
                    )
                if not violations:
                    self.validated_json_instances.add(target_relative)

    def has_symlink_component(self, path: Path) -> bool:
        """Return whether a target or any relative ancestor is a symlink."""

        try:
            relative = path.relative_to(self.root)
        except ValueError:
            return True
        current = self.root
        for part in relative.parts:
            current = current / part
            if current.is_symlink():
                return True
        return False

    def check_required_structure(self) -> None:
        """Check standard entry points, directories, non-empty files, and broken symlinks."""

        if not self.root.is_dir():
            self.add("ERROR", "root.missing", self.root, "Workspace root does not exist or is not a directory")
            return
        for relative in STANDARD_DIRECTORIES:
            path = self.root / relative
            if not path.exists():
                self.add("ERROR", "structure.directory-missing", path, "Standard directory is missing")
            elif path.is_symlink() and not path.resolve().exists():
                self.add("ERROR", "structure.broken-symlink", path, "Standard-directory symlink target does not exist")
            elif not path.is_dir():
                self.add("ERROR", "structure.not-directory", path, "Standard-directory path is not a directory")
        for relative in REQUIRED_FILES:
            path = self.root / relative
            if not path.exists():
                self.add("ERROR", "structure.file-missing", path, "Required entry file is missing")
            elif path.is_symlink() and not path.resolve().exists():
                self.add("ERROR", "structure.broken-symlink", path, "Required-file symlink target does not exist")
            elif not path.is_file():
                self.add("ERROR", "structure.not-file", path, "Required entry path is not a file")
            elif path.stat().st_size == 0:
                self.add("ERROR", "structure.file-empty", path, "Required entry file is empty")

    def check_workspace_manifest(self) -> None:
        """Check that the workspace manifest parses and uses a valid lifecycle state."""

        path = self.root / ".ai-workspace/workspace.toml"
        if not path.is_file():
            return
        document = self.load_toml(path, "workspace.toml-invalid")
        if document is None:
            return
        state = first_value(document, (("workspace", "status"), ("workspace", "state"), ("state",)))
        if not isinstance(state, str):
            self.add("ERROR", "workspace.state-missing", path, "Machine-readable workspace state was not found")
            return
        self.workspace_state = state
        if state not in WORKSPACE_STATES:
            self.add("ERROR", "workspace.state-invalid", path, f"Invalid workspace state: {state}")
        self.check_sensitive_values(document, path)

    def check_versions_lock(self) -> None:
        """Parse the version lock and retain the product version for receipt checks."""

        path = self.root / ".ai-workspace/versions.lock"
        if not path.is_file():
            return
        document = self.load_toml(path, "versions.lock-invalid")
        if document is None:
            return
        if not contains_scalar(document):
            self.add("ERROR", "versions.lock-empty", path, "Version lock contains no scalar version value")
        versions = document.get("versions")
        product_version = versions.get("product") if isinstance(versions, dict) else None
        if not isinstance(product_version, str) or not product_version:
            self.add("ERROR", "versions.product-missing", path, "Version lock is missing versions.product")
        else:
            self.product_version = product_version

    def check_release_receipt(self) -> None:
        """Check the installed Release receipt version and current distribution hashes."""

        receipt_relative = ".ai-workspace/release-manifest.json"
        if receipt_relative not in self.validated_json_instances:
            return
        receipt_path = self.root / receipt_relative
        receipt = self.load_json(receipt_path, "release.receipt-json-invalid")
        if not isinstance(receipt, dict):
            return
        release_version = receipt.get("release_version")
        if self.product_version is not None and release_version != self.product_version:
            self.add(
                "ERROR",
                "release.version-mismatch",
                receipt_path,
                f"Receipt release_version {release_version!r} does not match versions.lock product {self.product_version!r}",
            )
        entries = receipt.get("files")
        if not isinstance(entries, list):
            return
        seen_paths: set[str] = set()
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict):
                continue
            relative = entry.get("path")
            owner = entry.get("owner")
            expected = entry.get("sha256")
            if not isinstance(relative, str):
                continue
            if relative in seen_paths:
                self.add("ERROR", "release.path-duplicate", receipt_path, f"Receipt files[{index}] duplicates path: {relative}")
                continue
            seen_paths.add(relative)
            if relative == receipt_relative or owner != "distribution":
                continue
            if not is_portable_safe_relative_path(relative):
                self.add("ERROR", "release.path-unsafe", receipt_path, f"Receipt contains an unsafe path: {relative!r}")
                continue
            managed_path = self.root / relative
            if self.has_symlink_component(managed_path):
                self.add("ERROR", "release.distribution-file-symlink", managed_path, "Distribution file path contains a symlink")
                continue
            try:
                metadata = managed_path.lstat()
            except FileNotFoundError:
                self.add("ERROR", "release.distribution-file-missing", managed_path, "Distribution file recorded by the Release receipt does not exist")
                continue
            except OSError as exc:
                self.add("ERROR", "release.distribution-file-unreadable", managed_path, f"Unable to read distribution file metadata: {exc}")
                continue
            if not stat.S_ISREG(metadata.st_mode):
                self.add("ERROR", "release.distribution-file-not-regular", managed_path, "Path recorded by the Release receipt is not a regular file")
                continue
            actual = self.compute_stable_sha256(managed_path, metadata)
            if actual is None:
                continue
            if isinstance(expected, str) and actual != expected:
                self.add(
                    "ERROR",
                    "release.distribution-file-drift",
                    managed_path,
                    f"Distribution file SHA-256 drift: expected {expected}, got {actual}",
                )

    def compute_stable_sha256(self, path: Path, before: os.stat_result) -> str | None:
        """Hash a regular file by streaming and reject replacement during validation."""

        digest = hashlib.sha256()
        try:
            with path.open("rb") as stream:
                opened = os.fstat(stream.fileno())
                if not same_file_identity(before, opened) or not stat.S_ISREG(opened.st_mode):
                    self.add("ERROR", "release.distribution-file-raced", path, "Distribution file was replaced before opening")
                    return None
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
            after = path.lstat()
        except OSError as exc:
            self.add("ERROR", "release.distribution-file-unreadable", path, f"Unable to read distribution file: {exc}")
            return None
        if not same_file_identity(before, after) or before.st_size != after.st_size or before.st_mtime_ns != after.st_mtime_ns:
            self.add("ERROR", "release.distribution-file-raced", path, "Distribution file changed during validation")
            return None
        return digest.hexdigest()

    def check_runtime_skills(self) -> None:
        """Check runtime Skill names, frontmatter, and template residue."""

        skills_root = self.root / "skills"
        if not skills_root.is_dir():
            return
        skill_files = sorted(skills_root.glob("*/SKILL.md"))
        if not skill_files:
            self.add("ERROR", "skills.none", skills_root, "No runtime Skill found")
            return
        for path in skill_files:
            try:
                content = path.read_text(encoding="utf-8")
            except OSError as exc:
                self.add("ERROR", "skill.unreadable", path, f"Unable to read Skill: {exc}")
                continue
            if "[TODO" in content or re.search(r"\bTODO:\s", content):
                self.add("ERROR", "skill.template-placeholder", path, "Skill still contains a template TODO")
            match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, flags=re.DOTALL)
            if not match:
                self.add("ERROR", "skill.frontmatter-missing", path, "Valid YAML frontmatter boundaries are missing")
                continue
            name_match = re.search(r"^name:\s*([^\n]+)$", match.group(1), flags=re.MULTILINE)
            description_match = re.search(r"^description:\s*(\S.*)$", match.group(1), flags=re.MULTILINE)
            if not name_match:
                self.add("ERROR", "skill.name-missing", path, "Frontmatter is missing name")
            elif name_match.group(1).strip().strip('"\'') != path.parent.name:
                self.add("ERROR", "skill.name-mismatch", path, "Skill name does not match the directory name")
            if not description_match:
                self.add("ERROR", "skill.description-missing", path, "Frontmatter is missing a valid description")

    def check_tasks(self) -> None:
        """Check task lifecycle, directory identity, and module-role narrowing."""

        requirements_root = self.root / "requirements"
        if not requirements_root.is_dir():
            return
        for path in sorted(requirements_root.glob("*/task.toml")):
            document = self.load_toml(path, "task.toml-invalid")
            if document is None:
                continue
            task = document.get("task")
            scope = document.get("scope")
            workflow = document.get("workflow")
            gates = document.get("gates")
            evidence = document.get("evidence")
            if not isinstance(task, dict):
                self.add("ERROR", "task.table-missing", path, "Task table is missing")
                continue
            task_id = task.get("id")
            state = task.get("status")
            if not isinstance(task_id, str):
                self.add("ERROR", "task.id-missing", path, "Task is missing a machine-readable ID")
            elif task_id != path.parent.name:
                self.add("ERROR", "task.id-mismatch", path, "Task ID does not match the directory name")
            if not isinstance(state, str) or state not in TASK_STATES:
                self.add("ERROR", "task.state-invalid", path, f"Invalid or missing task state: {state!r}")
            if not isinstance(task.get("project_plugin_ref"), str):
                self.add("ERROR", "task.project-plugin-ref-invalid", path, "task.project_plugin_ref must be a string")
            project_roles = self.load_project_roles(path, task.get("project_plugin_ref"), state)
            self.check_task_scope(path, scope, project_roles)
            if not isinstance(workflow, dict):
                self.add("ERROR", "task.workflow-invalid", path, "workflow must be a table")
            else:
                for key in ("current_plan", "next_action", "next_gate"):
                    if key not in workflow:
                        self.add("ERROR", "task.workflow-field-missing", path, f"workflow is missing {key}")
                if state in PLAN_REQUIRED_STATES and not workflow.get("current_plan"):
                    self.add("ERROR", "task.current-plan-missing", path, f"State {state} must point to current_plan")
            self.check_task_gates(path, gates)
            if not isinstance(evidence, list):
                self.add("ERROR", "task.evidence-invalid", path, "evidence must be an array")
            self.check_sensitive_values(document, path)

    def load_project_roles(self, task_path: Path, reference: Any, task_state: Any) -> dict[str, int] | None:
        """Read the task's project plugin and return repository role ceilings."""

        if not isinstance(reference, str) or not reference:
            if task_state not in {None, "INBOX", "PAUSED"}:
                self.add("ERROR", "task.project-plugin-ref-missing", task_path, "A scoped task must reference a project plugin")
            return None
        if not is_safe_relative_path(reference):
            self.add("ERROR", "task.project-plugin-ref-unsafe", task_path, f"Unsafe project plugin path: {reference}")
            return None
        if reference != "project/plugin/project-plugin.json":
            self.add("ERROR", "task.project-plugin-ref-noncanonical", task_path, "Task must reference the canonical project-plugin source of truth")
            return None
        plugin_path = self.root / reference
        if self.has_symlink_component(plugin_path):
            self.add("ERROR", "task.project-plugin-ref-symlink", plugin_path, "Project plugin path contains a symlink; refusing to follow it")
            return None
        if not plugin_path.is_file():
            self.add("ERROR", "task.project-plugin-missing", plugin_path, "Project plugin referenced by the task does not exist")
            return None
        if plugin_path.suffix.lower() != ".json":
            self.add("ERROR", "task.project-plugin-format-invalid", plugin_path, "Project plugin must use project-plugin.json")
            return None
        plugin = self.load_json(plugin_path, "project-plugin.json-invalid")
        if plugin is None:
            return None
        if not isinstance(plugin, dict):
            self.add("ERROR", "project.plugin-invalid", plugin_path, "Project plugin root must be an object")
            return None
        modules = plugin.get("modules")
        if not isinstance(modules, list):
            self.add("ERROR", "project.modules-invalid", plugin_path, "Project plugin modules must be an array")
            return None
        roles: dict[str, int] = {}
        for index, module in enumerate(modules):
            if not isinstance(module, dict):
                self.add("ERROR", "project.module-invalid", plugin_path, f"modules[{index}] is not an object")
                continue
            module_id = module.get("id")
            project_role = module.get("role")
            if not isinstance(module_id, str) or not module_id:
                self.add("ERROR", "project.module-id-missing", plugin_path, f"modules[{index}] is missing an ID")
                continue
            if module_id in roles:
                self.add("ERROR", "project.module-duplicate", plugin_path, f"Duplicate project module: {module_id}")
                continue
            if project_role not in PROJECT_ROLE_CEILINGS:
                self.add("ERROR", "project.module-role-invalid", plugin_path, f"Module {module_id!r} has invalid project role: {project_role!r}")
                continue
            roles[module_id] = PROJECT_ROLE_CEILINGS[project_role]
        return roles

    def check_task_scope(self, path: Path, scope: Any, project_roles: dict[str, int] | None) -> None:
        """Validate disjoint module arrays and prevent task-role expansion."""

        if not isinstance(scope, dict):
            self.add("ERROR", "task.scope-invalid", path, "scope must be a table")
            return
        seen: dict[str, str] = {}
        for task_role, task_rank in TASK_SCOPE_ROLES.items():
            modules = scope.get(task_role)
            if not isinstance(modules, list):
                self.add("ERROR", "task.scope-role-invalid", path, f"scope.{task_role} must be an array of strings")
                continue
            for index, module_id in enumerate(modules):
                if not isinstance(module_id, str) or not module_id:
                    self.add("ERROR", "task.scope-module-invalid", path, f"scope.{task_role}[{index}] is not a valid module ID")
                    continue
                if module_id in seen:
                    self.add("ERROR", "task.scope-module-duplicate", path, f"Module {module_id!r} appears in both {seen[module_id]} and {task_role}")
                    continue
                seen[module_id] = task_role
                if task_role == "excluded" or project_roles is None:
                    continue
                if module_id not in project_roles:
                    self.add("ERROR", "task.scope-module-unknown", path, f"Module {module_id!r} is not registered in the project plugin")
                elif task_rank > project_roles[module_id]:
                    self.add("ERROR", "task.module-role-expanded", path, f"Task role {task_role} for module {module_id!r} expands the project role")

    def check_task_gates(self, path: Path, gates: Any) -> None:
        """Validate basic gate-array, status, and evidence-reference structure."""

        if not isinstance(gates, list):
            self.add("ERROR", "task.gates-invalid", path, "gates must be an array")
            return
        seen: set[str] = set()
        for index, gate in enumerate(gates):
            if not isinstance(gate, dict):
                self.add("ERROR", "task.gate-invalid", path, f"gates[{index}] is not a table")
                continue
            gate_id = gate.get("id")
            status = gate.get("status")
            if not isinstance(gate_id, str) or not gate_id:
                self.add("ERROR", "task.gate-id-missing", path, f"gates[{index}] is missing an ID")
            elif gate_id in seen:
                self.add("ERROR", "task.gate-duplicate", path, f"Duplicate gate: {gate_id}")
            else:
                seen.add(gate_id)
            if status not in GATE_STATES:
                self.add("ERROR", "task.gate-status-invalid", path, f"Gate {gate_id!r} has invalid status: {status!r}")
            evidence_refs = gate.get("evidence_refs", [])
            if not isinstance(evidence_refs, list) or not all(isinstance(item, str) for item in evidence_refs):
                self.add("ERROR", "task.gate-evidence-invalid", path, f"evidence_refs for gate {gate_id!r} must be an array of strings")
            if status in {"passed", "waived"} and not evidence_refs:
                self.add("WARN", "task.gate-evidence-missing", path, f"Gate {gate_id!r} is {status} but has no evidence reference")

    def check_diagnostics(self) -> None:
        """Check diagnostic deny defaults, unconfigured state, and sensitive-value rules."""

        path = self.root / "project/diagnostics/diagnostic-profile.toml"
        if not path.exists():
            if self.workspace_state == "DIAGNOSTICS_CONFIGURED":
                self.add("ERROR", "diagnostics.config-missing", path, "Workspace state requires diagnostic configuration, but it is missing")
            return
        document = self.load_toml(path, "diagnostics.toml-invalid")
        if document is None:
            return
        if document.get("schema_version") != "0.1":
            self.add("ERROR", "diagnostics.schema-version-invalid", path, "Diagnostic profile schema_version must be 0.1")
        profile = document.get("profile")
        policies = document.get("policies")
        if not isinstance(profile, dict):
            self.add("ERROR", "diagnostics.profile-invalid", path, "profile must be a table")
            return
        status = profile.get("status")
        if status not in {"unconfigured", "configuring", "draft", "verified", "degraded", "stale", "disabled"}:
            self.add("ERROR", "diagnostics.status-invalid", path, f"Invalid or missing diagnostic status: {status!r}")
        if self.workspace_state == "DIAGNOSTICS_CONFIGURED" and status != "verified":
            self.add("ERROR", "diagnostics.not-verified", path, "Workspace is DIAGNOSTICS_CONFIGURED but diagnostic configuration is not verified")
        if status == "verified" and profile.get("configured_by_interview") is not True:
            self.add("ERROR", "diagnostics.interview-missing", path, "Verified diagnostics must be configured by an interactive questionnaire")
        if not isinstance(policies, dict):
            self.add("ERROR", "diagnostics.policy-invalid", path, "policies must be a table")
        else:
            if policies.get("default_action") != "deny":
                self.add("ERROR", "diagnostics.default-not-deny", path, "Diagnostic configuration must deny by default")
            if policies.get("credential_output") != "deny" or policies.get("unknown_target") != "deny":
                self.add("ERROR", "diagnostics.fail-closed-invalid", path, "Credential output and unknown targets must be denied")
            if status != "verified":
                enabled = [key for key in ("remote_shell", "remote_write") if policies.get(key) != "deny"]
                if enabled:
                    self.add("ERROR", "diagnostics.unverified-open", path, f"High-risk capability enabled while status is not verified: {', '.join(enabled)}")
        self.check_sensitive_values(document, path)
        targets = document.get("targets")
        providers = document.get("providers")
        correlations = document.get("correlations")
        for section, entries in (("targets", targets), ("providers", providers), ("correlations", correlations)):
            if not isinstance(entries, list):
                self.add("ERROR", f"diagnostics.{section}-invalid", path, f"{section} must be an array of tables")
        if isinstance(providers, list):
            for index, provider in enumerate(providers):
                if not isinstance(provider, dict):
                    self.add("ERROR", "diagnostics.provider-invalid", path, f"providers[{index}] is not a table")
                    continue
                if status != "verified" and provider.get("enabled") is True:
                    self.add("ERROR", "diagnostics.provider-enabled", path, "A Provider cannot be enabled while status is not verified")
                credential_refs = provider.get("credential_refs", [])
                if not isinstance(credential_refs, list) or not all(
                    isinstance(item, str) and item.startswith(REFERENCE_PREFIXES) for item in credential_refs
                ):
                    self.add("ERROR", "diagnostics.credential-ref-invalid", path, "Provider credentials must use a supported reference")
        retention = document.get("retention", {})
        if isinstance(retention, dict) and isinstance(retention.get("evidence_directory"), str):
            if not is_safe_relative_path(retention["evidence_directory"]):
                self.add("ERROR", "diagnostics.retention-path-unsafe", path, "Evidence directory must be a safe workspace-relative path")
        for section in ("authorizations", "facts"):
            if section in document and not isinstance(document[section], list):
                self.add("ERROR", f"diagnostics.{section}-invalid", path, f"{section} must be an array of tables")

    def check_sensitive_values(self, value: Any, path: Path, trail: tuple[str, ...] = ()) -> None:
        """Recursively find likely credential values written directly to TOML."""

        if isinstance(value, dict):
            for key, child in value.items():
                normalized = str(key).lower()
                next_trail = trail + (str(key),)
                if normalized in SENSITIVE_KEYS and isinstance(child, str) and child and not child.startswith(REFERENCE_PREFIXES):
                    self.add("ERROR", "security.literal-secret", path, f"Likely credential field {'.'.join(next_trail)} must use a reference")
                self.check_sensitive_values(child, path, next_trail)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                self.check_sensitive_values(child, path, trail + (str(index),))

    def check_ownership_manifest(self) -> None:
        """Validate ownership rules and the release-path allowlist."""

        ownership_path = self.root / ".ai-workspace/ownership.toml"
        manifest_path = self.root / ".ai-workspace/distribution.manifest"
        if not ownership_path.is_file() or not manifest_path.is_file():
            return
        ownership = self.load_toml(ownership_path, "ownership.toml-invalid")
        if ownership is None:
            return
        rules = ownership.get("rules")
        distribution_patterns: set[str] = set()
        if not isinstance(rules, list):
            self.add("ERROR", "ownership.rules-invalid", ownership_path, "ownership rules must be an array of tables")
        else:
            seen_patterns: set[str] = set()
            for index, rule in enumerate(rules):
                if not isinstance(rule, dict):
                    self.add("ERROR", "ownership.rule-invalid", ownership_path, f"rules[{index}] is not a table")
                    continue
                pattern = rule.get("pattern")
                owner = rule.get("owner")
                if not isinstance(pattern, str) or not is_safe_relative_path(pattern):
                    self.add("ERROR", "ownership.pattern-unsafe", ownership_path, f"rules[{index}] has an invalid pattern: {pattern!r}")
                elif pattern in seen_patterns:
                    self.add("ERROR", "ownership.pattern-duplicate", ownership_path, f"Duplicate ownership pattern: {pattern}")
                else:
                    seen_patterns.add(pattern)
                if owner not in {"distribution", "generated", "workspace"}:
                    self.add("ERROR", "ownership.owner-invalid", ownership_path, f"rules[{index}] has an invalid owner: {owner!r}")
                elif owner == "distribution" and isinstance(pattern, str):
                    distribution_patterns.add(pattern)
        try:
            lines = manifest_path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            self.add("ERROR", "distribution.manifest-unreadable", manifest_path, f"Unable to read distribution manifest: {exc}")
            return
        seen_paths: set[str] = set()
        for number, raw in enumerate(lines, start=1):
            relative = raw.strip()
            if not relative or relative.startswith("#"):
                continue
            if not is_safe_relative_path(relative) or any(character.isspace() for character in relative):
                self.add("ERROR", "distribution.path-unsafe", manifest_path, f"Unsafe path on line {number}: {relative!r}")
                continue
            if relative in seen_paths:
                self.add("ERROR", "distribution.path-duplicate", manifest_path, f"Duplicate distribution path: {relative}")
                continue
            seen_paths.add(relative)
            if relative not in distribution_patterns:
                self.add(
                    "ERROR",
                    "distribution.owner-rule-missing",
                    ownership_path,
                    f"Distribution path lacks an exact distribution ownership rule: {relative}",
                )
            managed = self.root / relative
            if not managed.exists() or managed.is_symlink():
                self.add("ERROR", "distribution.path-missing", managed, "Distribution-manifest path is missing or is a symlink")


def first_value(document: dict[str, Any], paths: Iterable[tuple[str, ...]]) -> Any:
    """Return the first present nested value in candidate-path order."""

    for path in paths:
        current: Any = document
        for key in path:
            if not isinstance(current, dict) or key not in current:
                break
            current = current[key]
        else:
            return current
    return None


def contains_scalar(value: Any) -> bool:
    """Return whether a nested structure contains at least one scalar version."""

    if isinstance(value, dict):
        return any(contains_scalar(child) for child in value.values())
    if isinstance(value, list):
        return any(contains_scalar(child) for child in value)
    return isinstance(value, (str, int, float, bool))


def is_safe_relative_path(value: str) -> bool:
    """Reject absolute, empty, and parent-escaping paths."""

    path = Path(value)
    return bool(value) and not path.is_absolute() and ".." not in path.parts


def is_portable_safe_relative_path(value: str) -> bool:
    """Validate platform-neutral slash-separated workspace-relative receipt paths."""

    if not value or "\\" in value or "\x00" in value or re.match(r"^[A-Za-z]:", value):
        return False
    if value.startswith("/") or value in {".", ".."} or "//" in value:
        return False
    return all(part not in {"", ".", ".."} for part in value.split("/"))


def same_file_identity(left: os.stat_result, right: os.stat_result) -> bool:
    """Compare two metadata snapshots for the same file object."""

    return left.st_dev == right.st_dev and left.st_ino == right.st_ino


def severity_rank(severity: str) -> int:
    """Provide fixed ordering weights for ERROR, WARN, and INFO."""

    return {"ERROR": 0, "WARN": 1, "INFO": 2}.get(severity, 3)


def summarize(findings: list[Finding], strict: bool = False) -> dict[str, Any]:
    """Normalize check results into a summary shared by CLI and JSON output."""

    counts = {severity: sum(item.severity == severity for item in findings) for severity in ("ERROR", "WARN", "INFO")}
    failed = counts["ERROR"] > 0 or (strict and counts["WARN"] > 0)
    if failed:
        status = "FAIL"
    elif counts["WARN"]:
        status = "PASS_WITH_WARNINGS"
    else:
        status = "PASS"
    return {"status": status, "counts": counts, "findings": [asdict(item) for item in findings]}


def run_doctor(root: Path, strict: bool = False) -> dict[str, Any]:
    """Run the Doctor and return structured results without side effects."""

    return summarize(WorkspaceDoctor(root).run(), strict=strict)


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description="Inspect a Standard AI Workspace read-only")
    parser.add_argument("workspace", nargs="?", default=".", help="Standard Workspace root")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as failures")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and express the gate result through its exit code."""

    args = parse_args(argv or sys.argv[1:])
    result = run_doctor(Path(args.workspace), strict=args.strict)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"{result['status']}: ERROR={result['counts']['ERROR']} WARN={result['counts']['WARN']} INFO={result['counts']['INFO']}")
        for finding in result["findings"]:
            print(f"[{finding['severity']}] {finding['code']} {finding['path']}: {finding['message']}")
    return 0 if result["status"] != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
