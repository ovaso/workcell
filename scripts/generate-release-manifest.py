#!/usr/bin/env python3
"""为标准工作区发行资产生成确定性的安装 Release 完整性清单。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
import tempfile
import tomllib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any


SCHEMA_VERSION = "0.1"
MANIFEST_PATH = ".ai-workspace/release-manifest.json"
OWNERS = {"distribution", "generated", "workspace"}
RELEASE_VERSION_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?$")


class ReleaseManifestError(ValueError):
    """表示资产、所有权策略或生成结果不满足 Release 清单契约。"""


@dataclass(frozen=True)
class OwnershipRule:
    """表示一条按文件顺序参与 first-match 的所有权规则。"""

    pattern: str
    owner: str


def sha256_file(path: Path) -> str:
    """流式计算普通文件的 SHA-256。"""

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_relative_pattern(pattern: str) -> None:
    """校验 V0.1 所有权规则仅使用安全精确路径或末尾目录通配符。"""

    if not pattern or pattern.startswith("/") or "\\" in pattern or "//" in pattern:
        raise ReleaseManifestError(f"所有权 pattern 非法：{pattern!r}")
    path_parts = PurePosixPath(pattern.removesuffix("/**")).parts
    if any(part in {"", ".", ".."} for part in path_parts):
        raise ReleaseManifestError(f"所有权 pattern 含不安全路径段：{pattern!r}")
    wildcard_count = sum(pattern.count(token) for token in ("*", "?", "["))
    if wildcard_count and (not pattern.endswith("/**") or wildcard_count != 2):
        raise ReleaseManifestError(f"V0.1 不支持该所有权通配符：{pattern!r}")
    if pattern == "/**":
        raise ReleaseManifestError("所有权目录通配符必须包含相对目录")


def load_ownership(path: Path) -> tuple[str, list[OwnershipRule]]:
    """读取并严格校验 first-match 所有权策略。"""

    if path.is_symlink() or not path.is_file():
        raise ReleaseManifestError(f"ownership.toml 必须是普通文件：{path}")
    try:
        with path.open("rb") as stream:
            document: Any = tomllib.load(stream)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ReleaseManifestError(f"无法读取 ownership.toml：{exc}") from exc
    if not isinstance(document, dict):
        raise ReleaseManifestError("ownership.toml 根必须是表")
    ownership = document.get("ownership")
    raw_rules = document.get("rules")
    if not isinstance(ownership, dict):
        raise ReleaseManifestError("ownership.toml 缺少 [ownership]")
    if ownership.get("version") != SCHEMA_VERSION:
        raise ReleaseManifestError("ownership.toml version 必须为 0.1")
    default_owner = ownership.get("default")
    if default_owner not in OWNERS:
        raise ReleaseManifestError(f"ownership.toml default 非法：{default_owner!r}")
    if ownership.get("resolution") != "first-match":
        raise ReleaseManifestError("ownership.toml resolution 必须为 first-match")
    if not isinstance(raw_rules, list) or not raw_rules:
        raise ReleaseManifestError("ownership.toml rules 必须为非空表数组")

    rules: list[OwnershipRule] = []
    seen_patterns: set[str] = set()
    for index, raw_rule in enumerate(raw_rules):
        if not isinstance(raw_rule, dict):
            raise ReleaseManifestError(f"rules[{index}] 必须是表")
        pattern = raw_rule.get("pattern")
        owner = raw_rule.get("owner")
        if not isinstance(pattern, str):
            raise ReleaseManifestError(f"rules[{index}].pattern 必须是字符串")
        validate_relative_pattern(pattern)
        if pattern in seen_patterns:
            raise ReleaseManifestError(f"所有权 pattern 重复：{pattern}")
        if owner not in OWNERS:
            raise ReleaseManifestError(f"rules[{index}].owner 非法：{owner!r}")
        seen_patterns.add(pattern)
        rules.append(OwnershipRule(pattern, owner))
    return default_owner, rules


def rule_matches(pattern: str, relative_path: str) -> bool:
    """按 V0.1 精确路径与 `/**` 目录规则判断是否匹配。"""

    if pattern.endswith("/**"):
        directory = pattern[:-3]
        return relative_path == directory or relative_path.startswith(f"{directory}/")
    return relative_path == pattern


def resolve_owner(relative_path: str, default_owner: str, rules: list[OwnershipRule]) -> str:
    """按声明顺序返回第一条命中规则的 owner，否则返回默认 owner。"""

    for rule in rules:
        if rule_matches(rule.pattern, relative_path):
            return rule.owner
    return default_owner


def list_regular_files(asset_root: Path) -> list[tuple[str, Path]]:
    """列出资产内全部普通文件，并拒绝符号链接和特殊文件。"""

    files: list[tuple[str, Path]] = []
    for directory, directory_names, file_names in os.walk(asset_root, followlinks=False):
        directory_names.sort(key=lambda value: value.encode("utf-8"))
        file_names.sort(key=lambda value: value.encode("utf-8"))
        directory_path = Path(directory)
        for directory_name in directory_names:
            child = directory_path / directory_name
            if child.is_symlink():
                raise ReleaseManifestError(f"发行资产禁止符号链接目录：{child}")
        for file_name in file_names:
            file_path = directory_path / file_name
            relative_path = file_path.relative_to(asset_root).as_posix()
            file_mode = file_path.lstat().st_mode
            if stat.S_ISLNK(file_mode):
                raise ReleaseManifestError(f"发行资产禁止符号链接文件：{relative_path}")
            if not stat.S_ISREG(file_mode):
                raise ReleaseManifestError(f"发行资产禁止特殊文件：{relative_path}")
            if relative_path != MANIFEST_PATH:
                files.append((relative_path, file_path))
    return sorted(files, key=lambda item: item[0].encode("utf-8"))


def build_manifest(asset_root: Path, release_version: str) -> dict[str, Any]:
    """根据资产文件和 first-match 所有权生成内存中的 Release 清单。"""

    if not RELEASE_VERSION_PATTERN.fullmatch(release_version):
        raise ReleaseManifestError(f"release_version 非法：{release_version!r}")
    if asset_root.is_symlink() or not asset_root.is_dir():
        raise ReleaseManifestError(f"资产根必须是非符号链接目录：{asset_root}")
    manifest_path = asset_root / MANIFEST_PATH
    if manifest_path.is_symlink() or (manifest_path.exists() and not manifest_path.is_file()):
        raise ReleaseManifestError(f"Release 清单路径必须是普通文件或尚不存在：{manifest_path}")
    ownership_path = asset_root / ".ai-workspace/ownership.toml"
    default_owner, rules = load_ownership(ownership_path)

    entries = []
    for relative_path, file_path in list_regular_files(asset_root):
        entries.append(
            {
                "path": relative_path,
                "owner": resolve_owner(relative_path, default_owner, rules),
                "sha256": sha256_file(file_path),
            }
        )
    if not entries:
        raise ReleaseManifestError("发行资产至少需要一个普通文件")
    return {
        "schema_version": SCHEMA_VERSION,
        "release_version": release_version,
        "files": entries,
    }


def canonical_bytes(document: dict[str, Any]) -> bytes:
    """把清单编码为固定缩进、UTF-8 和末尾换行的规范字节。"""

    return (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def write_manifest(asset_root: Path, content: bytes) -> Path:
    """在资产内部原子替换 Release 清单，避免留下部分写入。"""

    manifest_path = asset_root / MANIFEST_PATH
    if manifest_path.is_symlink():
        raise ReleaseManifestError(f"Release 清单路径禁止为符号链接：{manifest_path}")
    if not manifest_path.parent.is_dir() or manifest_path.parent.is_symlink():
        raise ReleaseManifestError("Release 清单父目录必须是资产内的普通目录")

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix=".release-manifest.", dir=manifest_path.parent, delete=False) as stream:
            temporary_path = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        temporary_path.chmod(0o644)
        os.replace(temporary_path, manifest_path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
    return manifest_path


def parse_args(argv: list[str]) -> argparse.Namespace:
    """解析构建或只读校验所需参数。"""

    parser = argparse.ArgumentParser(description="生成标准工作区安装 Release 完整性清单")
    parser.add_argument("--asset-root", required=True, help="workspace-vX.Y 发行资产根目录")
    parser.add_argument("--release-version", required=True, help="不可变 Release 的产品版本")
    parser.add_argument("--check", action="store_true", help="只校验现有清单是否为当前资产的规范输出")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """生成清单，或以只读方式检查其完整性与确定性。"""

    args = parse_args(argv or sys.argv[1:])
    asset_root = Path(args.asset_root).absolute()
    try:
        expected = canonical_bytes(build_manifest(asset_root, args.release_version))
        manifest_path = asset_root / MANIFEST_PATH
        if args.check:
            try:
                actual = manifest_path.read_bytes()
            except OSError as exc:
                raise ReleaseManifestError(f"无法读取现有 Release 清单：{exc}") from exc
            if actual != expected:
                raise ReleaseManifestError("现有 Release 清单与资产文件或所有权策略不一致")
            print(f"VALID: {manifest_path}")
            return 0
        written_path = write_manifest(asset_root, expected)
        print(f"GENERATED: {written_path}")
        return 0
    except ReleaseManifestError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
