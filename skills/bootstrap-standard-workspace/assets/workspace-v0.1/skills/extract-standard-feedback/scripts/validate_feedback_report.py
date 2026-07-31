#!/usr/bin/env python3
"""对反馈报告执行无依赖的保守隐私与结构检查。"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

SLASH = chr(47)
BACKSLASH = chr(92)
FORBIDDEN = re.compile("|".join((SLASH + "Users" + SLASH, SLASH + "home" + SLASH + "[^" + SLASH + "]+" + SLASH, BACKSLASH * 2 + "Users" + BACKSLASH * 2, r"https?:" + SLASH * 2, r"(?:api[_-]?key|password|secret|token)\\s*[:=]")), re.I)
SCOPES = {"local", "project-plugin", "standard-candidate"}


def validate(document: Any) -> list[str]:
    """返回报告的最小结构和泄露风险错误。"""

    errors: list[str] = []
    if not isinstance(document, dict) or set(document) != {"schema_version", "feedback", "collection", "candidates"}:
        return ["报告顶层字段必须严格为 schema_version、feedback、collection、candidates"]
    feedback = document["feedback"]
    collection = document["collection"]
    candidates = document["candidates"]
    if document["schema_version"] != "0.1":
        errors.append("schema_version 必须为 0.1")
    if not isinstance(feedback, dict) or feedback.get("redaction_confirmed") is not True:
        errors.append("必须明确确认 redaction_confirmed = true")
    if not isinstance(feedback, dict) or not re.fullmatch(r"[0-9a-f]{64}", feedback.get("source_fingerprint", "")):
        errors.append("必须提供不可逆的 64 位 source_fingerprint")
    if not isinstance(collection, dict) or not collection.get("authorized_sources"):
        errors.append("必须声明至少一个 authorized_sources")
    if not isinstance(candidates, list) or not candidates:
        errors.append("必须至少包含一项候选")
        return errors
    for candidate in candidates:
        if not isinstance(candidate, dict) or candidate.get("scope") not in SCOPES:
            errors.append("候选 scope 必须是 local、project-plugin 或 standard-candidate")
            continue
        if not candidate.get("evidence") or not isinstance(candidate["evidence"], list):
            errors.append(f"候选 {candidate.get('id', '<unknown>')} 缺少证据摘要")
    for value in walk_strings(document):
        if FORBIDDEN.search(value):
            errors.append("报告疑似包含路径、URL 或凭证内容；请脱敏后重试")
            break
    return errors


def walk_strings(value: Any):
    """递归枚举 JSON 中的字符串值。"""

    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from walk_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_strings(child)


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: validate_feedback_report.py REPORT.json", file=sys.stderr)
        return 2
    try:
        document = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"无法读取报告：{error}", file=sys.stderr)
        return 1
    errors = validate(document)
    if errors:
        print("反馈报告无效：" + "；".join(errors), file=sys.stderr)
        return 1
    print("反馈报告检查通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
