#!/usr/bin/env python3
"""只读比较当前发行清单、工作区文件和候选发行清单。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


OWNERS = {"distribution", "generated", "workspace"}
SCHEMA_VERSION = "0.1"
RECEIPT_PATH = ".ai-workspace/release-manifest.json"
RELEASE_VERSION_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?$")


@dataclass(frozen=True)
class ManifestEntry:
    """表示一个经过基本格式校验的发行文件条目。"""

    path: str
    owner: str
    sha256: str


@dataclass(frozen=True)
class Action:
    """表示预览得到的单个文件动作或冲突。"""

    path: str
    action: str
    owner: str
    reason: str


class UpgradePreviewError(ValueError):
    """表示清单、路径或候选内容不满足安全预览要求。"""


def is_safe_relative_path(value: str) -> bool:
    """判断路径是否为无空段、当前段或父级逃逸的 POSIX 相对路径。"""

    path = Path(value)
    segments = value.split("/")
    return (
        bool(value)
        and "\\" not in value
        and not path.is_absolute()
        and all(segment not in {"", ".", ".."} for segment in segments)
    )


def sha256_file(path: Path) -> str:
    """流式计算普通文件的 SHA-256。"""

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest(path: Path) -> tuple[str, dict[str, ManifestEntry]]:
    """解析并验证发行清单的版本、路径、所有权和哈希格式。"""

    if path.is_symlink() or not path.is_file():
        raise UpgradePreviewError(f"清单必须是普通文件：{path}")
    try:
        document: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise UpgradePreviewError(f"无法读取清单 {path}: {exc}") from exc
    if not isinstance(document, dict):
        raise UpgradePreviewError(f"清单根必须是对象：{path}")
    if set(document) != {"schema_version", "release_version", "files"}:
        raise UpgradePreviewError(f"清单字段必须严格为 schema_version、release_version、files：{path}")
    if document.get("schema_version") != SCHEMA_VERSION:
        raise UpgradePreviewError(f"清单 schema_version 必须为 {SCHEMA_VERSION}：{path}")
    version = document.get("release_version")
    files = document.get("files")
    if not isinstance(version, str) or not RELEASE_VERSION_PATTERN.fullmatch(version):
        raise UpgradePreviewError(f"清单 release_version 非法：{path}")
    if not isinstance(files, list) or not files:
        raise UpgradePreviewError(f"清单 files 必须是非空数组：{path}")
    entries: dict[str, ManifestEntry] = {}
    for index, raw in enumerate(files):
        if not isinstance(raw, dict):
            raise UpgradePreviewError(f"files[{index}] 必须是对象：{path}")
        if set(raw) != {"path", "owner", "sha256"}:
            raise UpgradePreviewError(f"files[{index}] 字段必须严格为 path、owner、sha256：{path}")
        relative = raw.get("path")
        owner = raw.get("owner")
        checksum = raw.get("sha256")
        if not isinstance(relative, str) or not is_safe_relative_path(relative):
            raise UpgradePreviewError(f"files[{index}] 路径不安全：{relative!r}")
        if relative == RECEIPT_PATH:
            raise UpgradePreviewError(f"Release 清单禁止自哈希：{relative}")
        if relative in entries:
            raise UpgradePreviewError(f"清单路径重复：{relative}")
        if owner not in OWNERS:
            raise UpgradePreviewError(f"文件 {relative} 的 owner 非法：{owner!r}")
        if not isinstance(checksum, str) or len(checksum) != 64 or any(character not in "0123456789abcdef" for character in checksum):
            raise UpgradePreviewError(f"文件 {relative} 的 sha256 非法")
        entries[relative] = ManifestEntry(relative, owner, checksum)
    return version, entries


def actual_hash(path: Path) -> str | None:
    """返回普通文件哈希；文件不存在时返回 None，其他类型视为冲突。"""

    if not path.exists() and not path.is_symlink():
        return None
    if path.is_symlink() or not path.is_file():
        return "<non-regular-file>"
    return sha256_file(path)


def list_candidate_files(candidate_root: Path) -> set[str]:
    """列出候选资产全部普通文件，并把自排除收据作为独立事务文件。"""

    files: set[str] = set()
    for directory, directory_names, file_names in os.walk(candidate_root, followlinks=False):
        directory_names.sort(key=lambda value: value.encode("utf-8"))
        file_names.sort(key=lambda value: value.encode("utf-8"))
        directory_path = Path(directory)
        for directory_name in directory_names:
            child = directory_path / directory_name
            if child.is_symlink():
                raise UpgradePreviewError(f"候选发行包含符号链接目录：{child.relative_to(candidate_root).as_posix()}")
        for file_name in file_names:
            file_path = directory_path / file_name
            relative = file_path.relative_to(candidate_root).as_posix()
            mode = file_path.lstat().st_mode
            if stat.S_ISLNK(mode):
                raise UpgradePreviewError(f"候选发行包含符号链接文件：{relative}")
            if not stat.S_ISREG(mode):
                raise UpgradePreviewError(f"候选发行包含特殊文件：{relative}")
            if relative != RECEIPT_PATH:
                files.add(relative)
    return files


def verify_candidate(candidate_root: Path, entries: dict[str, ManifestEntry]) -> None:
    """确认候选普通文件集合与清单完全相同，且每个哈希一致。"""

    actual_files = list_candidate_files(candidate_root)
    manifest_files = set(entries)
    missing = sorted(manifest_files - actual_files)
    extra = sorted(actual_files - manifest_files)
    if missing:
        raise UpgradePreviewError(f"候选文件缺失：{missing[0]}")
    if extra:
        raise UpgradePreviewError(f"候选存在未列入 Release 清单的文件：{extra[0]}")

    for entry in entries.values():
        path = candidate_root / entry.path
        checksum = actual_hash(path)
        if checksum is None:
            raise UpgradePreviewError(f"候选文件缺失：{entry.path}")
        if checksum != entry.sha256:
            raise UpgradePreviewError(f"候选文件哈希不符：{entry.path}")


def preview_upgrade(
    workspace: Path,
    current_manifest: Path,
    candidate_root: Path,
    candidate_manifest: Path,
) -> dict[str, Any]:
    """生成不会修改工作区的升级文件动作计划。"""

    workspace = workspace.resolve()
    candidate_root = candidate_root.resolve()
    if not workspace.is_dir():
        raise UpgradePreviewError(f"工作区不存在：{workspace}")
    if not candidate_root.is_dir():
        raise UpgradePreviewError(f"候选目录不存在：{candidate_root}")
    current_version, current = load_manifest(current_manifest)
    candidate_version, candidate = load_manifest(candidate_manifest)
    installed_receipt = workspace / RECEIPT_PATH
    candidate_receipt = candidate_root / RECEIPT_PATH
    if installed_receipt.is_symlink() or not installed_receipt.is_file():
        raise UpgradePreviewError(f"当前工作区缺少普通安装收据：{RECEIPT_PATH}")
    if candidate_receipt.is_symlink() or not candidate_receipt.is_file():
        raise UpgradePreviewError(f"候选发行缺少普通安装收据：{RECEIPT_PATH}")
    if installed_receipt.read_bytes() != current_manifest.read_bytes():
        raise UpgradePreviewError("--current-manifest 与当前工作区安装收据不一致")
    if candidate_receipt.read_bytes() != candidate_manifest.read_bytes():
        raise UpgradePreviewError("--candidate-manifest 与候选发行安装收据不一致")
    verify_candidate(candidate_root, candidate)

    actions: list[Action] = []
    all_paths = sorted(set(current) | set(candidate))
    for relative in all_paths:
        old = current.get(relative)
        new = candidate.get(relative)
        target_hash = actual_hash(workspace / relative)

        if old is not None and new is not None and old.owner != new.owner:
            actions.append(Action(relative, "conflict", new.owner, f"所有权从 {old.owner} 变为 {new.owner}，需要显式 Migration"))
            continue

        if new is not None and new.owner == "workspace":
            action = "preserve" if target_hash is not None else "offer-seed"
            actions.append(Action(relative, action, new.owner, "工作区所有权内容不得由发行升级覆盖"))
            continue

        if new is not None and new.owner == "generated":
            actions.append(Action(relative, "regenerate", new.owner, "从升级后的结构化真相源重新生成"))
            continue

        if old is None and new is not None:
            if target_hash is None:
                actions.append(Action(relative, "add", new.owner, "新增发行文件"))
            else:
                actions.append(Action(relative, "conflict", new.owner, "目标路径已被未知现有内容占用"))
            continue

        if old is not None and new is None:
            if old.owner == "workspace":
                actions.append(Action(relative, "preserve", old.owner, "候选清单移除工作区文件时仍须保留"))
            elif old.owner == "generated":
                actions.append(Action(relative, "regenerate", old.owner, "由新版本生成器决定是否保留") )
            elif target_hash is None:
                actions.append(Action(relative, "unchanged", old.owner, "旧发行文件已经不存在"))
            elif target_hash == old.sha256:
                actions.append(Action(relative, "remove", old.owner, "候选发行移除未修改的旧发行文件"))
            else:
                actions.append(Action(relative, "conflict", old.owner, "待移除的旧发行文件存在本地修改或类型变化"))
            continue

        if old is None or new is None:
            raise AssertionError("路径集合分支不完整")
        if target_hash is None:
            actions.append(Action(relative, "conflict", new.owner, "当前发行文件缺失，无法判断是否应恢复"))
        elif target_hash != old.sha256:
            actions.append(Action(relative, "conflict", new.owner, "当前发行文件与已安装哈希不符"))
        elif old.sha256 == new.sha256:
            actions.append(Action(relative, "unchanged", new.owner, "候选内容未变化"))
        else:
            actions.append(Action(relative, "replace", new.owner, "替换未被本地修改的发行文件"))

    if installed_receipt.read_bytes() == candidate_receipt.read_bytes():
        actions.append(Action(RECEIPT_PATH, "unchanged", "distribution", "安装收据未变化"))
    else:
        actions.append(
            Action(
                RECEIPT_PATH,
                "replace-receipt",
                "distribution",
                "全部升级门禁成功后最后原子替换；收据自身不参与自哈希",
            )
        )

    conflicts = [action for action in actions if action.action == "conflict"]
    counts: dict[str, int] = {}
    for action in actions:
        counts[action.action] = counts.get(action.action, 0) + 1
    return {
        "current_version": current_version,
        "candidate_version": candidate_version,
        "safe_to_apply": not conflicts,
        "counts": counts,
        "actions": [asdict(action) for action in actions],
        "conflicts": [asdict(action) for action in conflicts],
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    """解析安全预览所需的显式路径参数。"""

    parser = argparse.ArgumentParser(description="只读预览标准工作区升级文件影响")
    parser.add_argument("--workspace", required=True, help="当前标准工作区根目录")
    parser.add_argument("--current-manifest", required=True, help="当前已安装发行清单")
    parser.add_argument("--candidate-root", required=True, help="已校验候选发行根目录")
    parser.add_argument("--candidate-manifest", required=True, help="候选发行清单")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """执行预览并用退出码区分安全、冲突和无效输入。"""

    args = parse_args(argv or sys.argv[1:])
    try:
        result = preview_upgrade(
            Path(args.workspace),
            Path(args.current_manifest),
            Path(args.candidate_root),
            Path(args.candidate_manifest),
        )
    except UpgradePreviewError as exc:
        print(json.dumps({"status": "INVALID", "error": str(exc)}, ensure_ascii=False, indent=2) if args.json else f"INVALID: {exc}")
        return 1
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"{result['current_version']} -> {result['candidate_version']} safe_to_apply={result['safe_to_apply']}")
        for action in result["actions"]:
            print(f"[{action['action']}] {action['path']}: {action['reason']}")
    return 0 if result["safe_to_apply"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
