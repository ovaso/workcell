#!/usr/bin/env python3
"""以只读方式检查标准工作区的 V0.1 核心不变量。"""

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
    """表示一条稳定、可序列化的 Doctor 检查结果。"""

    severity: str
    code: str
    path: str
    message: str


class WorkspaceDoctor:
    """收集工作区结构、安全和生命周期问题，不执行任何写操作。"""

    def __init__(self, root: Path) -> None:
        """初始化工作区根目录和结果集合。"""

        self.root = root.resolve()
        self.findings: list[Finding] = []
        self.workspace_state: str | None = None
        self.product_version: str | None = None
        self.validated_json_instances: set[str] = set()

    def add(self, severity: str, code: str, path: Path | str, message: str) -> None:
        """追加一条使用工作区相对路径表达的检查结果。"""

        path_obj = Path(path)
        try:
            display_path = str(path_obj.resolve().relative_to(self.root))
        except (OSError, ValueError):
            display_path = str(path)
        self.findings.append(Finding(severity, code, display_path or ".", message))

    def load_toml(self, path: Path, code: str) -> dict[str, Any] | None:
        """解析 TOML；解析失败时记录错误并返回空结果。"""

        try:
            with path.open("rb") as stream:
                value = tomllib.load(stream)
        except (OSError, tomllib.TOMLDecodeError) as exc:
            self.add("ERROR", code, path, f"TOML 无法解析：{exc}")
            return None
        return value

    def load_json(self, path: Path, code: str) -> Any | None:
        """严格解析 JSON；拒绝 NaN、Infinity 等非标准数值。"""

        try:
            return load_json_document(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            self.add("ERROR", code, path, f"JSON 无法解析：{exc}")
            return None

    def run(self) -> list[Finding]:
        """执行全部只读检查并返回稳定排序的结果。"""

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
        """使用随包 Schema 检查标准模板、当前环境事实和可选项目插件。"""

        for schema_relative, targets in JSON_SCHEMA_TARGETS:
            schema_path = self.root / schema_relative
            if self.has_symlink_component(schema_path):
                self.add("ERROR", "schema.path-symlink", schema_path, "Schema 路径包含符号链接，拒绝跟随读取")
                continue
            if not schema_path.is_file():
                self.add("ERROR", "schema.file-missing", schema_path, "缺少 Doctor 所需的随包 JSON Schema")
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
                    self.add("ERROR", "schema.instance-path-symlink", target_path, "JSON 实例路径包含符号链接，拒绝跟随读取")
                    continue
                if not target_path.is_file():
                    if required:
                        self.add("ERROR", "schema.instance-missing", target_path, "缺少必须接受 Schema 校验的 JSON 文件")
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
                        f"实例 {violation.instance_path} 不符合 {violation.schema_path}：{violation.message}",
                    )
                if not violations:
                    self.validated_json_instances.add(target_relative)

    def has_symlink_component(self, path: Path) -> bool:
        """判断工作区内目标自身或任一相对路径祖先是否为符号链接。"""

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
        """检查标准入口、目录、非空内容和明显的断链符号链接。"""

        if not self.root.is_dir():
            self.add("ERROR", "root.missing", self.root, "工作区根目录不存在或不是目录")
            return
        for relative in STANDARD_DIRECTORIES:
            path = self.root / relative
            if not path.exists():
                self.add("ERROR", "structure.directory-missing", path, "缺少标准目录")
            elif path.is_symlink() and not path.resolve().exists():
                self.add("ERROR", "structure.broken-symlink", path, "标准目录符号链接目标不存在")
            elif not path.is_dir():
                self.add("ERROR", "structure.not-directory", path, "标准目录路径不是目录")
        for relative in REQUIRED_FILES:
            path = self.root / relative
            if not path.exists():
                self.add("ERROR", "structure.file-missing", path, "缺少必需入口文件")
            elif path.is_symlink() and not path.resolve().exists():
                self.add("ERROR", "structure.broken-symlink", path, "必需文件符号链接目标不存在")
            elif not path.is_file():
                self.add("ERROR", "structure.not-file", path, "必需入口路径不是文件")
            elif path.stat().st_size == 0:
                self.add("ERROR", "structure.file-empty", path, "必需入口文件为空")

    def check_workspace_manifest(self) -> None:
        """检查工作区 Manifest 是否可解析并使用合法生命周期状态。"""

        path = self.root / ".ai-workspace/workspace.toml"
        if not path.is_file():
            return
        document = self.load_toml(path, "workspace.toml-invalid")
        if document is None:
            return
        state = first_value(document, (("workspace", "status"), ("workspace", "state"), ("state",)))
        if not isinstance(state, str):
            self.add("ERROR", "workspace.state-missing", path, "未找到机器可读的工作区状态")
            return
        self.workspace_state = state
        if state not in WORKSPACE_STATES:
            self.add("ERROR", "workspace.state-invalid", path, f"非法工作区状态：{state}")
        self.check_sensitive_values(document, path)

    def check_versions_lock(self) -> None:
        """检查版本锁文件可解析，并记录产品版本供 Release 收据核对。"""

        path = self.root / ".ai-workspace/versions.lock"
        if not path.is_file():
            return
        document = self.load_toml(path, "versions.lock-invalid")
        if document is None:
            return
        if not contains_scalar(document):
            self.add("ERROR", "versions.lock-empty", path, "版本锁没有任何标量版本值")
        versions = document.get("versions")
        product_version = versions.get("product") if isinstance(versions, dict) else None
        if not isinstance(product_version, str) or not product_version:
            self.add("ERROR", "versions.product-missing", path, "版本锁缺少 versions.product")
        else:
            self.product_version = product_version

    def check_release_receipt(self) -> None:
        """核对安装 Release 收据版本和 distribution 文件的当前 SHA-256。"""

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
                f"收据 release_version {release_version!r} 与 versions.lock product {self.product_version!r} 不一致",
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
                self.add("ERROR", "release.path-duplicate", receipt_path, f"收据 files[{index}] 重复登记路径：{relative}")
                continue
            seen_paths.add(relative)
            if relative == receipt_relative or owner != "distribution":
                continue
            if not is_portable_safe_relative_path(relative):
                self.add("ERROR", "release.path-unsafe", receipt_path, f"收据包含不安全路径：{relative!r}")
                continue
            managed_path = self.root / relative
            if self.has_symlink_component(managed_path):
                self.add("ERROR", "release.distribution-file-symlink", managed_path, "distribution 文件路径包含符号链接")
                continue
            try:
                metadata = managed_path.lstat()
            except FileNotFoundError:
                self.add("ERROR", "release.distribution-file-missing", managed_path, "Release 收据登记的 distribution 文件不存在")
                continue
            except OSError as exc:
                self.add("ERROR", "release.distribution-file-unreadable", managed_path, f"无法读取 distribution 文件元数据：{exc}")
                continue
            if not stat.S_ISREG(metadata.st_mode):
                self.add("ERROR", "release.distribution-file-not-regular", managed_path, "Release 收据登记路径不是普通文件")
                continue
            actual = self.compute_stable_sha256(managed_path, metadata)
            if actual is None:
                continue
            if isinstance(expected, str) and actual != expected:
                self.add(
                    "ERROR",
                    "release.distribution-file-drift",
                    managed_path,
                    f"distribution 文件 SHA-256 漂移：期望 {expected}，实际 {actual}",
                )

    def compute_stable_sha256(self, path: Path, before: os.stat_result) -> str | None:
        """流式计算普通文件哈希，并拒绝校验期间发生的目标替换。"""

        digest = hashlib.sha256()
        try:
            with path.open("rb") as stream:
                opened = os.fstat(stream.fileno())
                if not same_file_identity(before, opened) or not stat.S_ISREG(opened.st_mode):
                    self.add("ERROR", "release.distribution-file-raced", path, "distribution 文件在打开前被替换")
                    return None
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
            after = path.lstat()
        except OSError as exc:
            self.add("ERROR", "release.distribution-file-unreadable", path, f"无法读取 distribution 文件：{exc}")
            return None
        if not same_file_identity(before, after) or before.st_size != after.st_size or before.st_mtime_ns != after.st_mtime_ns:
            self.add("ERROR", "release.distribution-file-raced", path, "distribution 文件在校验期间发生变化")
            return None
        return digest.hexdigest()

    def check_runtime_skills(self) -> None:
        """检查运行时 Skill 名称、frontmatter 和模板残留。"""

        skills_root = self.root / "skills"
        if not skills_root.is_dir():
            return
        skill_files = sorted(skills_root.glob("*/SKILL.md"))
        if not skill_files:
            self.add("ERROR", "skills.none", skills_root, "没有发现运行时 Skill")
            return
        for path in skill_files:
            try:
                content = path.read_text(encoding="utf-8")
            except OSError as exc:
                self.add("ERROR", "skill.unreadable", path, f"无法读取 Skill：{exc}")
                continue
            if "[TODO" in content or re.search(r"\bTODO:\s", content):
                self.add("ERROR", "skill.template-placeholder", path, "Skill 仍包含模板 TODO")
            match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, flags=re.DOTALL)
            if not match:
                self.add("ERROR", "skill.frontmatter-missing", path, "缺少合法 YAML frontmatter 边界")
                continue
            name_match = re.search(r"^name:\s*([^\n]+)$", match.group(1), flags=re.MULTILINE)
            description_match = re.search(r"^description:\s*(\S.*)$", match.group(1), flags=re.MULTILINE)
            if not name_match:
                self.add("ERROR", "skill.name-missing", path, "frontmatter 缺少 name")
            elif name_match.group(1).strip().strip('"\'') != path.parent.name:
                self.add("ERROR", "skill.name-mismatch", path, "Skill 名称与目录名不一致")
            if not description_match:
                self.add("ERROR", "skill.description-missing", path, "frontmatter 缺少有效 description")

    def check_tasks(self) -> None:
        """检查任务生命周期、目录身份和模块角色收窄规则。"""

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
                self.add("ERROR", "task.table-missing", path, "缺少 task 表")
                continue
            task_id = task.get("id")
            state = task.get("status")
            if not isinstance(task_id, str):
                self.add("ERROR", "task.id-missing", path, "任务缺少机器可读 ID")
            elif task_id != path.parent.name:
                self.add("ERROR", "task.id-mismatch", path, "任务 ID 与目录名不一致")
            if not isinstance(state, str) or state not in TASK_STATES:
                self.add("ERROR", "task.state-invalid", path, f"非法或缺失任务状态：{state!r}")
            if not isinstance(task.get("project_plugin_ref"), str):
                self.add("ERROR", "task.project-plugin-ref-invalid", path, "task.project_plugin_ref 必须是字符串")
            project_roles = self.load_project_roles(path, task.get("project_plugin_ref"), state)
            self.check_task_scope(path, scope, project_roles)
            if not isinstance(workflow, dict):
                self.add("ERROR", "task.workflow-invalid", path, "workflow 必须是表")
            else:
                for key in ("current_plan", "next_action", "next_gate"):
                    if key not in workflow:
                        self.add("ERROR", "task.workflow-field-missing", path, f"workflow 缺少 {key}")
                if state in PLAN_REQUIRED_STATES and not workflow.get("current_plan"):
                    self.add("ERROR", "task.current-plan-missing", path, f"状态 {state} 必须指向 current_plan")
            self.check_task_gates(path, gates)
            if not isinstance(evidence, list):
                self.add("ERROR", "task.evidence-invalid", path, "evidence 必须是数组")
            self.check_sensitive_values(document, path)

    def load_project_roles(self, task_path: Path, reference: Any, task_state: Any) -> dict[str, int] | None:
        """读取任务引用的项目插件，并返回仓库角色上限。"""

        if not isinstance(reference, str) or not reference:
            if task_state not in {None, "INBOX", "PAUSED"}:
                self.add("ERROR", "task.project-plugin-ref-missing", task_path, "已定界任务必须引用项目插件")
            return None
        if not is_safe_relative_path(reference):
            self.add("ERROR", "task.project-plugin-ref-unsafe", task_path, f"不安全的项目插件路径：{reference}")
            return None
        if reference != "project/plugin/project-plugin.json":
            self.add("ERROR", "task.project-plugin-ref-noncanonical", task_path, "任务必须引用标准项目插件真相源")
            return None
        plugin_path = self.root / reference
        if self.has_symlink_component(plugin_path):
            self.add("ERROR", "task.project-plugin-ref-symlink", plugin_path, "项目插件路径包含符号链接，拒绝跟随读取")
            return None
        if not plugin_path.is_file():
            self.add("ERROR", "task.project-plugin-missing", plugin_path, "任务引用的项目插件不存在")
            return None
        if plugin_path.suffix.lower() != ".json":
            self.add("ERROR", "task.project-plugin-format-invalid", plugin_path, "项目插件必须使用 project-plugin.json")
            return None
        plugin = self.load_json(plugin_path, "project-plugin.json-invalid")
        if plugin is None:
            return None
        if not isinstance(plugin, dict):
            self.add("ERROR", "project.plugin-invalid", plugin_path, "项目插件根必须是对象")
            return None
        modules = plugin.get("modules")
        if not isinstance(modules, list):
            self.add("ERROR", "project.modules-invalid", plugin_path, "项目插件 modules 必须是数组")
            return None
        roles: dict[str, int] = {}
        for index, module in enumerate(modules):
            if not isinstance(module, dict):
                self.add("ERROR", "project.module-invalid", plugin_path, f"modules[{index}] 不是对象")
                continue
            module_id = module.get("id")
            project_role = module.get("role")
            if not isinstance(module_id, str) or not module_id:
                self.add("ERROR", "project.module-id-missing", plugin_path, f"modules[{index}] 缺少 ID")
                continue
            if module_id in roles:
                self.add("ERROR", "project.module-duplicate", plugin_path, f"项目模块重复：{module_id}")
                continue
            if project_role not in PROJECT_ROLE_CEILINGS:
                self.add("ERROR", "project.module-role-invalid", plugin_path, f"模块 {module_id!r} 的项目角色非法：{project_role!r}")
                continue
            roles[module_id] = PROJECT_ROLE_CEILINGS[project_role]
        return roles

    def check_task_scope(self, path: Path, scope: Any, project_roles: dict[str, int] | None) -> None:
        """验证四组模块数组互斥，并阻止任务角色扩大项目角色。"""

        if not isinstance(scope, dict):
            self.add("ERROR", "task.scope-invalid", path, "scope 必须是表")
            return
        seen: dict[str, str] = {}
        for task_role, task_rank in TASK_SCOPE_ROLES.items():
            modules = scope.get(task_role)
            if not isinstance(modules, list):
                self.add("ERROR", "task.scope-role-invalid", path, f"scope.{task_role} 必须是字符串数组")
                continue
            for index, module_id in enumerate(modules):
                if not isinstance(module_id, str) or not module_id:
                    self.add("ERROR", "task.scope-module-invalid", path, f"scope.{task_role}[{index}] 不是有效模块 ID")
                    continue
                if module_id in seen:
                    self.add("ERROR", "task.scope-module-duplicate", path, f"模块 {module_id!r} 同时出现在 {seen[module_id]} 和 {task_role}")
                    continue
                seen[module_id] = task_role
                if task_role == "excluded" or project_roles is None:
                    continue
                if module_id not in project_roles:
                    self.add("ERROR", "task.scope-module-unknown", path, f"模块 {module_id!r} 未登记在项目插件")
                elif task_rank > project_roles[module_id]:
                    self.add("ERROR", "task.module-role-expanded", path, f"模块 {module_id!r} 的任务角色 {task_role} 扩大了项目角色")

    def check_task_gates(self, path: Path, gates: Any) -> None:
        """验证门禁数组、状态和证据引用基本结构。"""

        if not isinstance(gates, list):
            self.add("ERROR", "task.gates-invalid", path, "gates 必须是数组")
            return
        seen: set[str] = set()
        for index, gate in enumerate(gates):
            if not isinstance(gate, dict):
                self.add("ERROR", "task.gate-invalid", path, f"gates[{index}] 不是表")
                continue
            gate_id = gate.get("id")
            status = gate.get("status")
            if not isinstance(gate_id, str) or not gate_id:
                self.add("ERROR", "task.gate-id-missing", path, f"gates[{index}] 缺少 ID")
            elif gate_id in seen:
                self.add("ERROR", "task.gate-duplicate", path, f"门禁重复：{gate_id}")
            else:
                seen.add(gate_id)
            if status not in GATE_STATES:
                self.add("ERROR", "task.gate-status-invalid", path, f"门禁 {gate_id!r} 状态非法：{status!r}")
            evidence_refs = gate.get("evidence_refs", [])
            if not isinstance(evidence_refs, list) or not all(isinstance(item, str) for item in evidence_refs):
                self.add("ERROR", "task.gate-evidence-invalid", path, f"门禁 {gate_id!r} 的 evidence_refs 必须是字符串数组")
            if status in {"passed", "waived"} and not evidence_refs:
                self.add("WARN", "task.gate-evidence-missing", path, f"门禁 {gate_id!r} 为 {status} 但没有证据引用")

    def check_diagnostics(self) -> None:
        """检查诊断默认拒绝、未配置状态和敏感值规则。"""

        path = self.root / "project/diagnostics/diagnostic-profile.toml"
        if not path.exists():
            if self.workspace_state == "DIAGNOSTICS_CONFIGURED":
                self.add("ERROR", "diagnostics.config-missing", path, "工作区状态要求诊断配置，但配置不存在")
            return
        document = self.load_toml(path, "diagnostics.toml-invalid")
        if document is None:
            return
        if document.get("schema_version") != "0.1":
            self.add("ERROR", "diagnostics.schema-version-invalid", path, "诊断 Profile schema_version 必须为 0.1")
        profile = document.get("profile")
        policies = document.get("policies")
        if not isinstance(profile, dict):
            self.add("ERROR", "diagnostics.profile-invalid", path, "profile 必须是表")
            return
        status = profile.get("status")
        if status not in {"unconfigured", "configuring", "draft", "verified", "degraded", "stale", "disabled"}:
            self.add("ERROR", "diagnostics.status-invalid", path, f"非法或缺失诊断状态：{status!r}")
        if self.workspace_state == "DIAGNOSTICS_CONFIGURED" and status != "verified":
            self.add("ERROR", "diagnostics.not-verified", path, "工作区已标记 DIAGNOSTICS_CONFIGURED，但诊断配置不是 verified")
        if status == "verified" and profile.get("configured_by_interview") is not True:
            self.add("ERROR", "diagnostics.interview-missing", path, "verified 诊断必须由交互问询配置")
        if not isinstance(policies, dict):
            self.add("ERROR", "diagnostics.policy-invalid", path, "policies 必须是表")
        else:
            if policies.get("default_action") != "deny":
                self.add("ERROR", "diagnostics.default-not-deny", path, "诊断配置必须默认拒绝")
            if policies.get("credential_output") != "deny" or policies.get("unknown_target") != "deny":
                self.add("ERROR", "diagnostics.fail-closed-invalid", path, "凭证输出和未知目标必须拒绝")
            if status != "verified":
                enabled = [key for key in ("remote_shell", "remote_write") if policies.get(key) != "deny"]
                if enabled:
                    self.add("ERROR", "diagnostics.unverified-open", path, f"非 verified 状态仍开启高风险能力：{', '.join(enabled)}")
        self.check_sensitive_values(document, path)
        targets = document.get("targets")
        providers = document.get("providers")
        correlations = document.get("correlations")
        for section, entries in (("targets", targets), ("providers", providers), ("correlations", correlations)):
            if not isinstance(entries, list):
                self.add("ERROR", f"diagnostics.{section}-invalid", path, f"{section} 必须是表数组")
        if isinstance(providers, list):
            for index, provider in enumerate(providers):
                if not isinstance(provider, dict):
                    self.add("ERROR", "diagnostics.provider-invalid", path, f"providers[{index}] 不是表")
                    continue
                if status != "verified" and provider.get("enabled") is True:
                    self.add("ERROR", "diagnostics.provider-enabled", path, "非 verified 状态不能启用 Provider")
                credential_refs = provider.get("credential_refs", [])
                if not isinstance(credential_refs, list) or not all(
                    isinstance(item, str) and item.startswith(REFERENCE_PREFIXES) for item in credential_refs
                ):
                    self.add("ERROR", "diagnostics.credential-ref-invalid", path, "Provider 凭证必须使用受支持的引用")
        retention = document.get("retention", {})
        if isinstance(retention, dict) and isinstance(retention.get("evidence_directory"), str):
            if not is_safe_relative_path(retention["evidence_directory"]):
                self.add("ERROR", "diagnostics.retention-path-unsafe", path, "证据目录必须是安全的工作区相对路径")
        for section in ("authorizations", "facts"):
            if section in document and not isinstance(document[section], list):
                self.add("ERROR", f"diagnostics.{section}-invalid", path, f"{section} 必须是表数组")

    def check_sensitive_values(self, value: Any, path: Path, trail: tuple[str, ...] = ()) -> None:
        """递归发现疑似直接写入 TOML 的凭证值。"""

        if isinstance(value, dict):
            for key, child in value.items():
                normalized = str(key).lower()
                next_trail = trail + (str(key),)
                if normalized in SENSITIVE_KEYS and isinstance(child, str) and child and not child.startswith(REFERENCE_PREFIXES):
                    self.add("ERROR", "security.literal-secret", path, f"疑似凭证字段 {'.'.join(next_trail)} 必须改为引用")
                self.check_sensitive_values(child, path, next_trail)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                self.check_sensitive_values(child, path, trail + (str(index),))

    def check_ownership_manifest(self) -> None:
        """验证所有权规则与发行路径 allowlist 的安全性。"""

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
            self.add("ERROR", "ownership.rules-invalid", ownership_path, "ownership rules 必须是表数组")
        else:
            seen_patterns: set[str] = set()
            for index, rule in enumerate(rules):
                if not isinstance(rule, dict):
                    self.add("ERROR", "ownership.rule-invalid", ownership_path, f"rules[{index}] 不是表")
                    continue
                pattern = rule.get("pattern")
                owner = rule.get("owner")
                if not isinstance(pattern, str) or not is_safe_relative_path(pattern):
                    self.add("ERROR", "ownership.pattern-unsafe", ownership_path, f"rules[{index}] pattern 非法：{pattern!r}")
                elif pattern in seen_patterns:
                    self.add("ERROR", "ownership.pattern-duplicate", ownership_path, f"所有权 pattern 重复：{pattern}")
                else:
                    seen_patterns.add(pattern)
                if owner not in {"distribution", "generated", "workspace"}:
                    self.add("ERROR", "ownership.owner-invalid", ownership_path, f"rules[{index}] owner 非法：{owner!r}")
                elif owner == "distribution" and isinstance(pattern, str):
                    distribution_patterns.add(pattern)
        try:
            lines = manifest_path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            self.add("ERROR", "distribution.manifest-unreadable", manifest_path, f"无法读取发行清单：{exc}")
            return
        seen_paths: set[str] = set()
        for number, raw in enumerate(lines, start=1):
            relative = raw.strip()
            if not relative or relative.startswith("#"):
                continue
            if not is_safe_relative_path(relative) or any(character.isspace() for character in relative):
                self.add("ERROR", "distribution.path-unsafe", manifest_path, f"第 {number} 行路径不安全：{relative!r}")
                continue
            if relative in seen_paths:
                self.add("ERROR", "distribution.path-duplicate", manifest_path, f"发行路径重复：{relative}")
                continue
            seen_paths.add(relative)
            if relative not in distribution_patterns:
                self.add(
                    "ERROR",
                    "distribution.owner-rule-missing",
                    ownership_path,
                    f"发行路径缺少完全同名的 distribution 所有权规则：{relative}",
                )
            managed = self.root / relative
            if not managed.exists() or managed.is_symlink():
                self.add("ERROR", "distribution.path-missing", managed, "发行清单路径不存在或是符号链接")


def first_value(document: dict[str, Any], paths: Iterable[tuple[str, ...]]) -> Any:
    """按候选路径顺序返回第一个存在的嵌套值。"""

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
    """判断嵌套结构中是否至少包含一个标量版本值。"""

    if isinstance(value, dict):
        return any(contains_scalar(child) for child in value.values())
    if isinstance(value, list):
        return any(contains_scalar(child) for child in value)
    return isinstance(value, (str, int, float, bool))


def is_safe_relative_path(value: str) -> bool:
    """拒绝绝对路径、空路径和包含父级逃逸的路径。"""

    path = Path(value)
    return bool(value) and not path.is_absolute() and ".." not in path.parts


def is_portable_safe_relative_path(value: str) -> bool:
    """验证 Release 收据使用平台无关的正斜线工作区相对路径。"""

    if not value or "\\" in value or "\x00" in value or re.match(r"^[A-Za-z]:", value):
        return False
    if value.startswith("/") or value in {".", ".."} or "//" in value:
        return False
    return all(part not in {"", ".", ".."} for part in value.split("/"))


def same_file_identity(left: os.stat_result, right: os.stat_result) -> bool:
    """比较两次文件元数据是否指向同一文件对象。"""

    return left.st_dev == right.st_dev and left.st_ino == right.st_ino


def severity_rank(severity: str) -> int:
    """提供 ERROR、WARN、INFO 的固定排序权重。"""

    return {"ERROR": 0, "WARN": 1, "INFO": 2}.get(severity, 3)


def summarize(findings: list[Finding], strict: bool = False) -> dict[str, Any]:
    """把检查结果归一化为命令行与 JSON 共用摘要。"""

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
    """运行 Doctor 并返回不含副作用的结构化结果。"""

    return summarize(WorkspaceDoctor(root).run(), strict=strict)


def parse_args(argv: list[str]) -> argparse.Namespace:
    """解析命令行参数。"""

    parser = argparse.ArgumentParser(description="只读检查标准 AI 工作区")
    parser.add_argument("workspace", nargs="?", default=".", help="标准工作区根目录")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument("--strict", action="store_true", help="把警告也视为失败")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """执行 CLI 并以退出码表达门禁结果。"""

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
